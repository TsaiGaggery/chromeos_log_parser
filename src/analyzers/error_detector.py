"""
ErrorDetector - Scan logs for error patterns and map to timeline.

Detects various error patterns like ERROR, WARNING, FAILED, CRASH, etc.
and maps them to vmlog timestamps for visualization.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bisect import bisect_left


class ErrorDetector:
    """Scans logs for error patterns and maps to timeline."""
    
    # Error patterns with (regex, label, severity)
    # Severity: 1=info, 2=warning, 3=error, 4=critical
    ERROR_PATTERNS = [
        (re.compile(r'\bCRASH\b', re.IGNORECASE), 'CRASH', 4),
        (re.compile(r'\bpanic\b', re.IGNORECASE), 'PANIC', 4),
        (re.compile(r'\bOOM\b|\bOut of memory\b', re.IGNORECASE), 'OOM', 4),
        (re.compile(r'\bkilled\b', re.IGNORECASE), 'KILLED', 4),
        (re.compile(r'\bFATAL\b', re.IGNORECASE), 'FATAL', 4),
        (re.compile(r'\bERROR\b', re.IGNORECASE), 'ERROR', 3),
        (re.compile(r'\bFAILED\b|\bfailure\b', re.IGNORECASE), 'FAILED', 3),
        (re.compile(r'\btimeout\b', re.IGNORECASE), 'TIMEOUT', 3),
        (re.compile(r'\brefused\b', re.IGNORECASE), 'REFUSED', 3),
        (re.compile(r'\bdenied\b', re.IGNORECASE), 'DENIED', 3),
        (re.compile(r'\bWARNING\b|\bWARN\b', re.IGNORECASE), 'WARNING', 2),
        (re.compile(r'\bCRIT\b|\bCRITICAL\b', re.IGNORECASE), 'CRITICAL', 4),
    ]
    
    # Timestamp patterns for different log formats
    TIMESTAMP_PATTERNS = [
        # ISO format: 2025-10-31T11:58:18.896902Z
        (re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d+)?Z?'), 'iso'),
        # Syslog format: Oct 31 11:58:18 or Nov  5 09:30:00
        (re.compile(r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'), 'syslog'),
        # Kernel timestamp: [27268.556000]
        (re.compile(r'\[(\d+\.\d+)\]'), 'kernel'),
        # vmlog format: [1027/151447]
        (re.compile(r'\[(\d{4})/(\d{6})\]'), 'vmlog'),
        # Chrome log format: 1031/115818.896902
        (re.compile(r'(\d{4})/(\d{6})\.(\d+)'), 'chrome'),
    ]
    
    # Month name mapping for syslog format
    MONTH_MAP = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    def __init__(self, reference_year: Optional[int] = None, context_lines: int = 5):
        """
        Initialize the error detector.
        
        Args:
            reference_year: Year to use for timestamps without year
            context_lines: Number of lines of context around errors
        """
        self.reference_year = reference_year or datetime.now().year
        self.context_lines = context_lines
    
    def scan_logs(self, logs: Dict[str, str]) -> List[Dict]:
        """
        Scan all logs for error patterns.
        
        Args:
            logs: Dictionary mapping log names to content
            
        Returns:
            List of error dictionaries
        """
        all_errors = []
        
        for log_name, content in logs.items():
            errors = self._scan_single_log(log_name, content)
            all_errors.extend(errors)
        
        # Sort by timestamp (put None timestamps at the end)
        all_errors.sort(key=lambda x: (x['timestamp'] is None, x['timestamp'] or datetime.max))
        
        return all_errors
    
    def _scan_single_log(self, log_name: str, content: str) -> List[Dict]:
        """
        Scan a single log for error patterns.
        
        Args:
            log_name: Name of the log file
            content: Log content
            
        Returns:
            List of error dictionaries
        """
        errors = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern, label, severity in self.ERROR_PATTERNS:
                if pattern.search(line):
                    # Extract timestamp from line
                    timestamp = self._extract_timestamp(line)
                    
                    # Get context lines
                    context = self._get_context(lines, line_num - 1, self.context_lines)
                    
                    error = {
                        'source': log_name,
                        'timestamp': timestamp,
                        'line_number': line_num,
                        'severity': severity,
                        'type': label,
                        'message': line.strip()[:500],  # Limit message length
                        'context': context,
                    }
                    errors.append(error)
                    break  # Only match first pattern per line
        
        return errors
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """
        Try to extract timestamp from log line.
        
        Args:
            line: Log line
            
        Returns:
            datetime object or None
        """
        for pattern, fmt in self.TIMESTAMP_PATTERNS:
            match = pattern.search(line)
            if match:
                try:
                    return self._parse_timestamp(match, fmt)
                except (ValueError, IndexError):
                    continue
        return None
    
    def _parse_timestamp(self, match: re.Match, fmt: str) -> Optional[datetime]:
        """
        Parse matched timestamp string.
        
        Args:
            match: Regex match object
            fmt: Format identifier
            
        Returns:
            datetime object
        """
        if fmt == 'iso':
            # 2025-10-31T11:58:18
            ts_str = match.group(1)
            return datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S')
        
        elif fmt == 'syslog':
            # Oct 31 11:58:18
            ts_str = match.group(1)
            parts = ts_str.split()
            month = self.MONTH_MAP.get(parts[0], 1)
            day = int(parts[1])
            time_parts = parts[2].split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            second = int(time_parts[2])
            return datetime(self.reference_year, month, day, hour, minute, second)
        
        elif fmt == 'kernel':
            # [27268.556000] - This is seconds since boot, can't convert to datetime
            # Return None and let caller handle it
            return None
        
        elif fmt == 'vmlog':
            # [1027/151447] -> month=10, day=27, hour=15, min=14, sec=47
            date_part = match.group(1)
            time_part = match.group(2)
            month = int(date_part[:2])
            day = int(date_part[2:])
            hour = int(time_part[:2])
            minute = int(time_part[2:4])
            second = int(time_part[4:])
            return datetime(self.reference_year, month, day, hour, minute, second)
        
        elif fmt == 'chrome':
            # 1031/115818.896902 -> month=10, day=31, etc.
            date_part = match.group(1)
            time_part = match.group(2)
            month = int(date_part[:2])
            day = int(date_part[2:])
            hour = int(time_part[:2])
            minute = int(time_part[2:4])
            second = int(time_part[4:])
            return datetime(self.reference_year, month, day, hour, minute, second)
        
        return None
    
    def _get_context(self, lines: List[str], error_idx: int, context_size: int) -> List[str]:
        """
        Get context lines around error.
        
        Args:
            lines: All lines in the log
            error_idx: Index of the error line
            context_size: Number of lines before and after
            
        Returns:
            List of context lines
        """
        start = max(0, error_idx - context_size)
        end = min(len(lines), error_idx + context_size + 1)
        return lines[start:end]
    
    def map_to_vmlog_timeline(self, errors: List[Dict], vmlog_data: List[Dict]) -> List[Dict]:
        """
        Find nearest vmlog entry for each error.
        
        Args:
            errors: List of error dictionaries
            vmlog_data: List of parsed vmlog entries
            
        Returns:
            Errors with added vmlog_index field
        """
        if not vmlog_data:
            return errors
        
        # Create sorted list of vmlog timestamps
        vmlog_timestamps = [entry['timestamp'] for entry in vmlog_data if entry.get('timestamp')]
        
        for error in errors:
            if error.get('timestamp'):
                # Find nearest vmlog entry using binary search
                idx = self._find_nearest_timestamp(vmlog_timestamps, error['timestamp'])
                if idx is not None:
                    error['vmlog_index'] = idx
                    error['vmlog_timestamp'] = vmlog_timestamps[idx]
        
        return errors
    
    def _find_nearest_timestamp(self, timestamps: List[datetime], target: datetime) -> Optional[int]:
        """
        Find index of nearest timestamp using binary search.
        
        Args:
            timestamps: Sorted list of timestamps
            target: Target timestamp
            
        Returns:
            Index of nearest timestamp
        """
        if not timestamps:
            return None
        
        idx = bisect_left(timestamps, target)
        
        if idx == 0:
            return 0
        if idx == len(timestamps):
            return len(timestamps) - 1
        
        # Check which is closer
        before = timestamps[idx - 1]
        after = timestamps[idx]
        
        if (target - before) <= (after - target):
            return idx - 1
        return idx
    
    def get_errors_by_severity(self, errors: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Group errors by severity level.
        
        Args:
            errors: List of error dictionaries
            
        Returns:
            Dictionary mapping severity to list of errors
        """
        by_severity = {1: [], 2: [], 3: [], 4: []}
        for error in errors:
            severity = error.get('severity', 1)
            by_severity.setdefault(severity, []).append(error)
        return by_severity
    
    def get_errors_by_source(self, errors: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group errors by source log file.
        
        Args:
            errors: List of error dictionaries
            
        Returns:
            Dictionary mapping source to list of errors
        """
        by_source = {}
        for error in errors:
            source = error.get('source', 'unknown')
            by_source.setdefault(source, []).append(error)
        return by_source
    
    def get_error_summary(self, errors: List[Dict]) -> Dict:
        """
        Generate summary statistics for errors.
        
        Args:
            errors: List of error dictionaries
            
        Returns:
            Summary dictionary
        """
        summary = {
            'total_count': len(errors),
            'by_severity': {},
            'by_type': {},
            'by_source': {},
        }
        
        severity_names = {1: 'info', 2: 'warning', 3: 'error', 4: 'critical'}
        
        for error in errors:
            # Count by severity
            sev = error.get('severity', 1)
            sev_name = severity_names.get(sev, 'unknown')
            summary['by_severity'][sev_name] = summary['by_severity'].get(sev_name, 0) + 1
            
            # Count by type
            err_type = error.get('type', 'UNKNOWN')
            summary['by_type'][err_type] = summary['by_type'].get(err_type, 0) + 1
            
            # Count by source
            source = error.get('source', 'unknown')
            summary['by_source'][source] = summary['by_source'].get(source, 0) + 1
        
        return summary
