"""
TempLoggerParser - Parse temp_logger entries from /var/log/messages.

Format:
2025-10-27T07:44:13.519238Z NOTICE temp_logger[4157]:  x86_pkg_temp:55C INT3400_Thermal:20C TSR0:44C TSR1:56C TSR2:34C TCPU:55C TCPU_PCI:55C iwlwifi_1:35C PL1:6.000W  Fan0RPM:2776
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class TempLoggerParser:
    """Parses temp_logger entries from system messages logs."""
    
    # Pattern to match temp_logger lines
    TEMP_LOGGER_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+'
        r'(?:NOTICE|INFO|WARNING)?\s*'
        r'temp_logger\[\d+\]:\s*(.+)$'
    )
    
    # Pattern to extract temperature values (ends with C)
    TEMP_VALUE_PATTERN = re.compile(r'(\w+):(\d+)C')
    
    # Pattern to extract power values (ends with W)
    POWER_VALUE_PATTERN = re.compile(r'(\w+):([\d.]+)W')
    
    # Pattern to extract RPM values
    RPM_VALUE_PATTERN = re.compile(r'(\w+RPM):(\d+)')
    
    def __init__(self):
        """Initialize the parser."""
        self.temperature_sensors = set()
        self.power_sensors = set()
        self.fan_sensors = set()
    
    def parse_content(self, content: str) -> List[Dict]:
        """
        Parse messages log content for temp_logger entries.
        
        Args:
            content: Log file content
            
        Returns:
            List of dictionaries with timestamp and sensor readings
        """
        entries = []
        
        for line in content.split('\n'):
            entry = self._parse_line(line)
            if entry:
                entries.append(entry)
        
        # Sort by timestamp
        entries.sort(key=lambda x: x.get('timestamp', datetime.min))
        
        return entries
    
    def _parse_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single temp_logger line.
        
        Args:
            line: Log line
            
        Returns:
            Dictionary with parsed data or None
        """
        match = self.TEMP_LOGGER_PATTERN.match(line.strip())
        if not match:
            return None
        
        timestamp_str = match.group(1)
        data_part = match.group(2)
        
        # Parse timestamp
        try:
            # Handle ISO format with microseconds
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Convert to naive datetime (remove timezone)
            timestamp = timestamp.replace(tzinfo=None)
        except ValueError:
            return None
        
        entry = {
            'timestamp': timestamp,
            'timestamp_raw': timestamp_str,
            'temperatures': {},
            'power': {},
            'fans': {},
        }
        
        # Extract temperature values
        for match in self.TEMP_VALUE_PATTERN.finditer(data_part):
            sensor_name = match.group(1)
            temp_value = int(match.group(2))
            entry['temperatures'][sensor_name] = temp_value
            self.temperature_sensors.add(sensor_name)
        
        # Extract power values
        for match in self.POWER_VALUE_PATTERN.finditer(data_part):
            sensor_name = match.group(1)
            power_value = float(match.group(2))
            entry['power'][sensor_name] = power_value
            self.power_sensors.add(sensor_name)
        
        # Extract fan RPM values
        for match in self.RPM_VALUE_PATTERN.finditer(data_part):
            sensor_name = match.group(1)
            rpm_value = int(match.group(2))
            entry['fans'][sensor_name] = rpm_value
            self.fan_sensors.add(sensor_name)
        
        return entry
    
    def parse_from_logs(self, logs: Dict[str, str]) -> List[Dict]:
        """
        Parse temp_logger from multiple log files.
        
        Args:
            logs: Dictionary of log name to content
            
        Returns:
            Combined list of temp_logger entries
        """
        all_entries = []
        
        for log_name, content in logs.items():
            # Look for messages files
            if 'messages' in log_name.lower():
                entries = self.parse_content(content)
                all_entries.extend(entries)
        
        # Sort by timestamp and remove duplicates
        all_entries.sort(key=lambda x: x.get('timestamp', datetime.min))
        
        return all_entries
    
    def get_all_sensor_names(self) -> Dict[str, List[str]]:
        """
        Get all discovered sensor names.
        
        Returns:
            Dictionary with temperature, power, and fan sensor names
        """
        return {
            'temperature': sorted(self.temperature_sensors),
            'power': sorted(self.power_sensors),
            'fans': sorted(self.fan_sensors),
        }
    
    def get_time_range(self, entries: List[Dict]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get time range of entries."""
        if not entries:
            return None, None
        
        timestamps = [e['timestamp'] for e in entries if e.get('timestamp')]
        if not timestamps:
            return None, None
        
        return min(timestamps), max(timestamps)
    
    def get_temperature_summary(self, entries: List[Dict]) -> Dict:
        """
        Calculate temperature statistics.
        
        Args:
            entries: List of temp_logger entries
            
        Returns:
            Dictionary with min, max, avg for each sensor
        """
        summary = {}
        
        for sensor in self.temperature_sensors:
            values = [e['temperatures'].get(sensor) for e in entries 
                     if e.get('temperatures', {}).get(sensor) is not None]
            
            if values:
                summary[sensor] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values),
                }
        
        return summary
