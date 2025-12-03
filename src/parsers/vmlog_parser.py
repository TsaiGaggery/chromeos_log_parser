"""
VmlogParser - Parse vmlog files from ChromeOS logs.

vmlog format:
time pgmajfault pgmajfault_f pgmajfault_a pswpin pswpout cpuusage cpufreq0 cpufreq1 cpufreq2 cpufreq3
[1027/124537] 0 0 0 0 0 0.02 700000 700000 700000 1246034

Timestamp format: [MMDD/HHMMSS] where:
- MMDD = month (2 digits) + day (2 digits)
- HHMMSS = hour (2 digits) + minute (2 digits) + second (2 digits)
- Example: [1027/124537] = October 27, 12:45:37 UTC

Values:
- cpuusage: 0.02 means 2% CPU usage
- cpufreq: in kHz, so 700000 = 700 MHz, 1246034 = 1246.034 MHz
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class VmlogParser:
    """Parses vmlog files from ChromeOS logs."""
    
    # Default column names in vmlog
    DEFAULT_COLUMNS = [
        'time', 'pgmajfault', 'pgmajfault_f', 'pgmajfault_a',
        'pswpin', 'pswpout', 'cpuusage', 
        'cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3'
    ]
    
    # Regex pattern for vmlog timestamp [MMDD/HHMMSS]
    TIMESTAMP_PATTERN = re.compile(r'\[(\d{4})/(\d{6})\]')
    
    # CPU frequency columns (values are in kHz)
    CPUFREQ_COLUMNS = ['cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3']
    
    def __init__(self, reference_year: Optional[int] = None, convert_freq_to_mhz: bool = True):
        """
        Initialize the parser.
        
        Args:
            reference_year: Year to use for timestamps (defaults to current year)
            convert_freq_to_mhz: If True, convert cpufreq from kHz to MHz
        """
        self.reference_year = reference_year or datetime.now().year
        self.columns = self.DEFAULT_COLUMNS.copy()
        self.convert_freq_to_mhz = convert_freq_to_mhz
    
    def parse_file(self, filepath: str) -> List[Dict]:
        """
        Parse a vmlog file.
        
        Args:
            filepath: Path to the vmlog file
            
        Returns:
            List of dictionaries with parsed vmlog entries
        """
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> List[Dict]:
        """
        Parse vmlog content from a string.
        
        Args:
            content: vmlog file content as string
            
        Returns:
            List of dictionaries with parsed vmlog entries
        """
        lines = content.strip().split('\n')
        if not lines:
            return []
        
        entries = []
        columns = self.DEFAULT_COLUMNS.copy()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a header line
            if self._is_header_line(line):
                columns = self._parse_header(line)
                self.columns = columns
                continue
            
            # Try to parse as data line
            entry = self._parse_line(line, columns)
            if entry:
                entries.append(entry)
        
        return entries
    
    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header line (starts with 'time')."""
        return line.strip().startswith('time ')
    
    def _parse_header(self, line: str) -> List[str]:
        """
        Parse header line to extract column names.
        
        Args:
            line: Header line
            
        Returns:
            List of column names
        """
        return line.strip().split()
    
    def _parse_line(self, line: str, columns: List[str]) -> Optional[Dict]:
        """
        Parse a single vmlog data line.
        
        Args:
            line: Data line
            columns: Column names
            
        Returns:
            Dictionary with parsed values, or None if parsing fails
        """
        # Try to match timestamp at the beginning
        match = self.TIMESTAMP_PATTERN.match(line)
        if not match:
            return None
        
        # Extract timestamp
        timestamp = self._parse_timestamp(match.group(0))
        if not timestamp:
            return None
        
        # Split the rest of the line
        remaining = line[match.end():].strip()
        values = remaining.split()
        
        # Build result dictionary
        result = {'timestamp': timestamp, 'timestamp_raw': match.group(0)}
        
        # Map values to columns (skip 'time' column as we already have timestamp)
        value_columns = [c for c in columns if c != 'time']
        
        for i, col in enumerate(value_columns):
            if i < len(values):
                try:
                    # cpuusage is a float (0.02 = 2%)
                    if col == 'cpuusage':
                        result[col] = float(values[i])
                    # cpufreq values are in kHz, optionally convert to MHz
                    elif col in self.CPUFREQ_COLUMNS:
                        raw_value = int(values[i])
                        if self.convert_freq_to_mhz:
                            # Convert kHz to MHz (700000 kHz = 700.000 MHz)
                            result[col] = raw_value / 1000.0
                        else:
                            result[col] = raw_value
                    else:
                        result[col] = int(values[i])
                except ValueError:
                    # Handle malformed values
                    result[col] = 0
            else:
                result[col] = 0
        
        return result
    
    def _parse_timestamp(self, time_str: str) -> Optional[datetime]:
        """
        Convert [MMDD/HHMMSS] to datetime object.
        
        Args:
            time_str: Timestamp string in [MMDD/HHMMSS] format
            
        Returns:
            datetime object, or None if parsing fails
        """
        match = self.TIMESTAMP_PATTERN.match(time_str)
        if not match:
            return None
        
        date_part = match.group(1)  # MMDD
        time_part = match.group(2)  # HHMMSS
        
        try:
            month = int(date_part[:2])
            day = int(date_part[2:])
            hour = int(time_part[:2])
            minute = int(time_part[2:4])
            second = int(time_part[4:])
            
            # Create datetime with reference year
            return datetime(self.reference_year, month, day, hour, minute, second)
        except (ValueError, IndexError):
            return None
    
    def parse_multiple_files(self, filepaths: List[str]) -> List[Dict]:
        """
        Parse multiple vmlog files and merge results.
        
        Args:
            filepaths: List of file paths
            
        Returns:
            Combined list of entries sorted by timestamp
        """
        all_entries = []
        for filepath in filepaths:
            try:
                entries = self.parse_file(filepath)
                all_entries.extend(entries)
            except Exception as e:
                print(f"Warning: Failed to parse {filepath}: {e}")
        
        # Sort by timestamp
        all_entries.sort(key=lambda x: x.get('timestamp', datetime.min))
        return all_entries
    
    def get_time_range(self, entries: List[Dict]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Get the time range covered by vmlog entries.
        
        Args:
            entries: List of parsed vmlog entries
            
        Returns:
            Tuple of (start_time, end_time), or (None, None) if empty
        """
        if not entries:
            return None, None
        
        timestamps = [e['timestamp'] for e in entries if e.get('timestamp')]
        if not timestamps:
            return None, None
        
        return min(timestamps), max(timestamps)
    
    def get_metrics_summary(self, entries: List[Dict]) -> Dict:
        """
        Calculate summary statistics for vmlog metrics.
        
        Args:
            entries: List of parsed vmlog entries
            
        Returns:
            Dictionary with min, max, avg for each metric
        """
        if not entries:
            return {}
        
        metrics = ['cpuusage', 'pgmajfault', 'pswpin', 'pswpout', 
                   'cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3']
        
        summary = {}
        for metric in metrics:
            values = [e.get(metric, 0) for e in entries if metric in e]
            if values:
                summary[metric] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values)
                }
        
        return summary
