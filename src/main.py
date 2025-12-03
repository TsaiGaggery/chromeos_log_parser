#!/usr/bin/env python3
"""
ChromeOS Log Analyzer - Main CLI Application

A tool for parsing, analyzing, and visualizing ChromeOS logs from
generated_logs archives or user feedback files.

Usage:
    python -m src.main -i <input_path> -o <output.html>
    python -m src.main --input logs/ --output report.html --verbose
"""

import argparse
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers import VmlogParser, GeneratedLogsParser, UserFeedbackParser, TempLoggerParser
from src.analyzers import ErrorDetector, MetricsAnalyzer
from src.visualizers import ChartGenerator, HTMLBuilder


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='ChromeOS Log Analyzer - Parse and visualize ChromeOS logs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze extracted generated_logs directory
    python -m src.main -i ./generated_logs/ -o report.html

    # Analyze user feedback text file
    python -m src.main -i feedback.txt -o report.html

    # Analyze ZIP archive directly
    python -m src.main -i logs.zip -o report.html --verbose
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input path: directory with extracted logs, ZIP file, or user feedback text file'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='chromeos_log_report.html',
        help='Output HTML report path (default: chromeos_log_report.html)'
    )
    
    parser.add_argument(
        '-t', '--type',
        choices=['auto', 'generated', 'feedback'],
        default='auto',
        help='Log type: auto-detect, generated_logs, or user feedback (default: auto)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--max-points',
        type=int,
        default=5000,
        help='Maximum data points for charts (default: 5000)'
    )
    
    parser.add_argument(
        '--year',
        type=int,
        default=None,
        help='Reference year for timestamps (default: current year)'
    )
    
    return parser.parse_args()


def detect_input_type(input_path: str) -> str:
    """
    Auto-detect input type.
    
    Args:
        input_path: Path to input file or directory
        
    Returns:
        'generated' for generated_logs, 'feedback' for user feedback file
    """
    path = Path(input_path)
    
    # Check if it's a ZIP file
    if zipfile.is_zipfile(input_path):
        return 'generated'
    
    # Check if it's a directory
    if path.is_dir():
        # Look for feedback/ subdirectory (generated_logs structure)
        if (path / 'feedback').exists():
            return 'generated'
        # Check for nested directory
        for item in path.iterdir():
            if item.is_dir() and (item / 'feedback').exists():
                return 'generated'
        return 'generated'  # Assume directory is generated_logs
    
    # Check if it's a text file (user feedback)
    if path.is_file():
        # Try to detect by content
        try:
            with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
                head = f.read(4096)
            
            # Check for user feedback markers
            if '=<multiline>' in head or '---------- START ----------' in head:
                return 'feedback'
            
            # Default to feedback for single files
            return 'feedback'
        except Exception:
            return 'feedback'
    
    return 'generated'


def log_message(message: str, verbose: bool = True):
    """Print log message if verbose mode is enabled."""
    if verbose:
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")


def get_vmlog_segment_name(log_name: str) -> Tuple[str, Optional[datetime]]:
    """
    Extract segment name and start time from vmlog filename.
    
    Examples:
        vmlog.1.LATEST -> ('LATEST', None) - skip these
        vmlog.1.PREVIOUS -> ('PREVIOUS', None) - skip these
        vmlog.20251027-074818 -> ('20251027-074818', datetime(2025,10,27,7,48,18))
    """
    basename = os.path.basename(log_name)
    
    # Pattern for datetime format: vmlog.YYYYMMDD-HHMMSS or vmlog.1.YYYYMMDD-HHMMSS
    datetime_pattern = re.compile(r'vmlog(?:\.\d+)?\.(\d{8}-\d{6})$')
    match = datetime_pattern.search(basename)
    
    if match:
        dt_str = match.group(1)
        try:
            # Parse YYYYMMDD-HHMMSS
            dt = datetime.strptime(dt_str, '%Y%m%d-%H%M%S')
            return (dt_str, dt)
        except ValueError:
            pass
    
    # Check for LATEST/PREVIOUS (we'll skip these)
    if 'LATEST' in basename.upper() or 'PREVIOUS' in basename.upper():
        return (basename, None)
    
    return (basename, None)


def group_vmlog_by_segment(logs: Dict[str, str]) -> Dict[str, Dict]:
    """
    Group vmlog files by their datetime segment.
    Only includes vmlog.YYYYMMDD-HHMMSS format, skips LATEST/PREVIOUS.
    
    Args:
        logs: Dict mapping log names to content
        
    Returns:
        Dict mapping segment name to {'files': [(log_name, content)], 'start_time': datetime, 'end_time': datetime}
    """
    segments = {}
    
    for log_name, content in logs.items():
        basename = os.path.basename(log_name)
        
        # Only process vmlog files
        if 'vmlog' not in basename.lower():
            continue
        
        segment_name, start_time = get_vmlog_segment_name(log_name)
        
        # Skip LATEST/PREVIOUS, only process datetime-based vmlogs
        if start_time is None:
            continue
        
        if segment_name not in segments:
            segments[segment_name] = {
                'files': [],
                'start_time': start_time,
                'end_time': None  # Will be calculated from data
            }
        
        segments[segment_name]['files'].append((log_name, content))
    
    return segments


def split_entries_by_time_gap(entries: List[Dict], max_gap_seconds: float = 5.0) -> List[List[Dict]]:
    """
    Split vmlog entries into separate chunks when time gap exceeds threshold.
    
    Args:
        entries: Sorted list of vmlog entries
        max_gap_seconds: Maximum allowed gap between consecutive entries (default: 5 seconds)
        
    Returns:
        List of entry chunks, each chunk is continuous in time
    """
    if not entries:
        return []
    
    chunks = []
    current_chunk = [entries[0]]
    
    for i in range(1, len(entries)):
        prev_ts = entries[i-1].get('timestamp')
        curr_ts = entries[i].get('timestamp')
        
        if prev_ts and curr_ts:
            gap = (curr_ts - prev_ts).total_seconds()
            if gap > max_gap_seconds:
                # Start a new chunk
                chunks.append(current_chunk)
                current_chunk = []
        
        current_chunk.append(entries[i])
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def filter_thermal_by_timerange(thermal_data: List[Dict], 
                                 start_time: datetime, 
                                 end_time: datetime) -> List[Dict]:
    """
    Filter thermal data to only include entries within the given time range.
    
    Args:
        thermal_data: All thermal entries
        start_time: Start of time range
        end_time: End of time range
        
    Returns:
        Filtered thermal entries
    """
    filtered = []
    for entry in thermal_data:
        ts = entry.get('timestamp')
        if ts and start_time <= ts <= end_time:
            filtered.append(entry)
    return filtered


def find_messages_logs(logs: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Find /var/log/messages files for temp_logger parsing.
    
    Args:
        logs: Dict mapping log names to content
        
    Returns:
        List of (log_name, content) tuples
    """
    messages_logs = []
    
    for log_name, content in logs.items():
        # Match messages, messages.1, messages.2, etc.
        basename = os.path.basename(log_name)
        if basename.startswith('messages') or '/var/log/messages' in log_name:
            messages_logs.append((log_name, content))
    
    return messages_logs


def main():
    """Main entry point."""
    args = parse_arguments()
    start_time = time.time()
    
    # Validate input
    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    log_message(f"Starting ChromeOS Log Analyzer", args.verbose)
    log_message(f"Input: {input_path}", args.verbose)
    log_message(f"Output: {args.output}", args.verbose)
    
    # Detect input type
    if args.type == 'auto':
        input_type = detect_input_type(input_path)
        log_message(f"Auto-detected input type: {input_type}", args.verbose)
    else:
        input_type = args.type
    
    # Parse logs based on type
    log_message("Parsing logs...", args.verbose)
    
    try:
        if input_type == 'generated':
            parser = GeneratedLogsParser()
            parsed_data = parser.parse_directory(input_path)
        else:  # feedback
            parser = UserFeedbackParser()
            parsed_data = parser.parse_file(input_path)
            # Convert feedback format to match generated_logs format
            parsed_data['logs'] = parsed_data.get('sections', {})
        
        log_message(f"Parsed {len(parsed_data.get('logs', {}))} log files", args.verbose)
    except Exception as e:
        print(f"Error parsing logs: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # ========================================
    # Group vmlog files by segment (datetime format only)
    # ========================================
    log_message("Grouping vmlog files by segment...", args.verbose)
    
    vmlog_segments = group_vmlog_by_segment(parsed_data.get('logs', {}))
    log_message(f"Found {len(vmlog_segments)} vmlog file groups: {list(vmlog_segments.keys())}", args.verbose)
    
    # Parse vmlog data for each segment, then split by time gaps
    vmlog_parser = VmlogParser(reference_year=args.year, convert_freq_to_mhz=True)
    chart_gen = ChartGenerator()
    segment_data = {}  # segment_name -> {'entries': [], 'start_time': dt, 'end_time': dt}
    
    for file_group_name, segment_info in vmlog_segments.items():
        # Collect all entries from files in this group
        all_entries = []
        for log_name, content in segment_info['files']:
            try:
                entries = vmlog_parser.parse_content(content)
                all_entries.extend(entries)
                log_message(f"  [{file_group_name}] Extracted {len(entries)} entries from {os.path.basename(log_name)}", args.verbose)
            except Exception as e:
                log_message(f"  Warning: Failed to parse {log_name}: {e}", args.verbose)
        
        # Sort by timestamp
        all_entries.sort(key=lambda x: x.get('timestamp', datetime.min))
        
        # Split into chunks by time gaps (>5 seconds = new chart)
        chunks = split_entries_by_time_gap(all_entries, max_gap_seconds=5.0)
        log_message(f"  [{file_group_name}] Split into {len(chunks)} continuous segments", args.verbose)
        
        # Create separate segment for each chunk
        for chunk_idx, chunk_entries in enumerate(chunks):
            if not chunk_entries:
                continue
            
            # Generate segment name
            if len(chunks) == 1:
                segment_name = file_group_name
            else:
                segment_name = f"{file_group_name}_part{chunk_idx + 1}"
            
            seg_start_time = chunk_entries[0].get('timestamp')
            seg_end_time = chunk_entries[-1].get('timestamp')
            
            # Sample if too large
            if len(chunk_entries) > args.max_points:
                log_message(f"    [{segment_name}] Sampling from {len(chunk_entries)} to {args.max_points} points", args.verbose)
                chunk_entries = chart_gen.sample_data(chunk_entries, args.max_points)
            
            segment_data[segment_name] = {
                'entries': chunk_entries,
                'start_time': seg_start_time,
                'end_time': seg_end_time
            }
            log_message(f"    [{segment_name}] {len(chunk_entries)} entries, {seg_start_time} ~ {seg_end_time}", args.verbose)
    
    log_message(f"Total segments after splitting: {len(segment_data)}", args.verbose)
    
    # ========================================
    # Parse temp_logger from /var/log/messages
    # ========================================
    log_message("Parsing thermal data from temp_logger...", args.verbose)
    
    messages_logs = find_messages_logs(parsed_data.get('logs', {}))
    temp_parser = TempLoggerParser()
    all_thermal_data = []
    
    for log_name, content in messages_logs:
        try:
            entries = temp_parser.parse_content(content)
            all_thermal_data.extend(entries)
            log_message(f"  Extracted {len(entries)} thermal entries from {os.path.basename(log_name)}", args.verbose)
        except Exception as e:
            log_message(f"  Warning: Failed to parse temp_logger from {log_name}: {e}", args.verbose)
    
    # Sort thermal data by timestamp
    all_thermal_data.sort(key=lambda x: x.get('timestamp', datetime.min))
    log_message(f"Total thermal entries: {len(all_thermal_data)}", args.verbose)
    
    # ========================================
    # Detect errors
    # ========================================
    log_message("Scanning for errors...", args.verbose)
    
    error_detector = ErrorDetector(reference_year=args.year)
    errors = error_detector.scan_logs(parsed_data.get('logs', {}))
    
    # Combine all vmlog data for error mapping
    all_vmlog_data = []
    for seg_info in segment_data.values():
        all_vmlog_data.extend(seg_info['entries'])
    all_vmlog_data.sort(key=lambda x: x.get('timestamp', datetime.min))
    
    errors = error_detector.map_to_vmlog_timeline(errors, all_vmlog_data)
    log_message(f"Found {len(errors)} error entries", args.verbose)
    
    # ========================================
    # Generate multi-chart configuration
    # Each vmlog segment gets: CPU chart + Thermal chart (if matching data)
    # ========================================
    log_message("Generating chart configurations...", args.verbose)
    
    charts_config = []
    total_thermal_entries = 0
    
    # Create charts for each vmlog segment
    for segment_name in sorted(segment_data.keys()):
        seg_info = segment_data[segment_name]
        entries = seg_info['entries']
        seg_start = seg_info['start_time']
        seg_end = seg_info['end_time']
        
        if not entries:
            continue
        
        # Filter critical errors for this time range
        from datetime import timedelta
        buffer = timedelta(seconds=30)
        segment_errors = [
            e for e in errors
            if e.get('severity', 0) >= 3  # Error and Critical
            and e.get('timestamp') is not None
            and seg_start - buffer <= e['timestamp'] <= seg_end + buffer
        ]
        critical_count = sum(1 for e in segment_errors if e.get('severity', 0) == 4)
        error_count = sum(1 for e in segment_errors if e.get('severity', 0) == 3)
        
        # Create CPU usage + frequency chart with error annotations
        cpu_chart = chart_gen.create_cpu_usage_chart(
            entries,
            errors=segment_errors,
            chart_id=f'cpu_{segment_name.replace("-", "_")}',
            title=f'CPU Usage & Frequency - vmlog.{segment_name}'
        )
        cpu_chart['type'] = 'cpu'
        cpu_chart['segment'] = segment_name
        charts_config.append(cpu_chart)
        log_message(f"  Created CPU chart for vmlog.{segment_name} (Critical: {critical_count}, Error: {error_count})", args.verbose)
        
        # Filter thermal data for this vmlog time range
        # Add a bit of buffer (expand range by a few seconds)
        segment_thermal = filter_thermal_by_timerange(
            all_thermal_data, 
            seg_start - buffer, 
            seg_end + buffer
        )
        
        if segment_thermal:
            total_thermal_entries += len(segment_thermal)
            # Sample if too large
            if len(segment_thermal) > args.max_points // 2:
                segment_thermal = chart_gen.sample_data(segment_thermal, args.max_points // 2)
            
            thermal_chart = chart_gen.create_thermal_chart(
                segment_thermal,
                chart_id=f'thermal_{segment_name.replace("-", "_")}',
                title=f'Thermal & Fan - vmlog.{segment_name}'
            )
            thermal_chart['type'] = 'thermal'
            thermal_chart['segment'] = segment_name
            charts_config.append(thermal_chart)
            log_message(f"  Created thermal chart for vmlog.{segment_name} ({len(segment_thermal)} entries)", args.verbose)
    
    # ========================================
    # Build HTML report with multiple charts
    # ========================================
    log_message("Building HTML report...", args.verbose)
    
    html_builder = HTMLBuilder()
    
    # Add generation metadata
    metadata = parsed_data.get('metadata', {})
    metadata['generation_time'] = datetime.now().isoformat()
    metadata['input_path'] = input_path
    metadata['total_vmlog_entries'] = sum(len(s['entries']) for s in segment_data.values())
    metadata['thermal_entries'] = total_thermal_entries
    metadata['error_count'] = len(errors)
    metadata['vmlog_segments'] = list(segment_data.keys())
    
    try:
        # Use multi-chart report builder
        output_path = html_builder.save_multi_chart_report(
            args.output,
            parsed_data,
            charts_config,
            errors,
            metadata
        )
        
        # Get file size
        file_size = os.path.getsize(output_path)
        size_str = f"{file_size / 1024 / 1024:.2f} MB" if file_size > 1024*1024 else f"{file_size / 1024:.1f} KB"
        
        elapsed = time.time() - start_time
        
        log_message(f"Report saved to: {output_path}", args.verbose)
        log_message(f"Report size: {size_str}", args.verbose)
        log_message(f"Completed in {elapsed:.2f} seconds", args.verbose)
        
        print(f"\n✓ Report generated: {output_path}")
        print(f"  - vmlog segments: {len(segment_data)}")
        print(f"  - Total vmlog entries: {sum(len(s['entries']) for s in segment_data.values())}")
        print(f"  - Thermal entries: {total_thermal_entries}")
        print(f"  - Errors found: {len(errors)}")
        print(f"  - Charts generated: {len(charts_config)}")
        print(f"  - File size: {size_str}")
        
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Cleanup
    if input_type == 'generated' and hasattr(parser, 'cleanup'):
        parser.cleanup()


if __name__ == '__main__':
    main()
