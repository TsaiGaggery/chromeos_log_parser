"""
CrosEcParser - Parse cros_ec.log for Embedded Controller events.

The cros_ec.log contains events from the Embedded Controller including:
- Power state transitions (S0, S3, S5)
- Lid open/close events
- AC adapter events (plug/unplug)
- Battery events and charging status
- Thermal throttling events
- USB-C/PD events
- Display Port mode events
- TCPC (Type-C Port Controller) events
- EC firmware messages
"""

import re
from datetime import datetime
from typing import Dict, List, Optional


class CrosEcParser:
    """Parses cros_ec.log for meaningful EC events."""
    
    # Event categories with patterns and importance levels
    # Level: 1=info, 2=warning, 3=notable, 4=critical
    # Pattern order matters - more specific patterns should come first
    EC_EVENT_PATTERNS = [
        # Fan stall - critical issue (check first)
        (re.compile(r'Fan\s*\d+\s*stalled|fan stall', re.IGNORECASE),
         'FAN_STALL', 4, 'rgb(248, 81, 73)'),  # bright red - critical
        
        # Power state transitions (format: "power state 7 = G3S5" or transitions like S5S4, S4S3)
        (re.compile(r'power state \d+ = (G3|S[0-5]|S[0-5]S[0-5]|G3S5|S0ix)', re.IGNORECASE), 
         'POWER', 3, 'rgb(163, 113, 247)'),  # purple
        
        # PD (Power Delivery) state transitions (format: "PD:S5->S3", "PD:S3->S0")
        (re.compile(r'PD:[A-Z0-9]+->[A-Z0-9]+', re.IGNORECASE),
         'PD_STATE', 3, 'rgb(163, 113, 247)'),  # purple - same as power
        
        # Lid events
        (re.compile(r'lid\s*(open|close|state)|Lid\s*(Open|Close)', re.IGNORECASE),
         'LID', 3, 'rgb(88, 166, 255)'),  # blue
        
        # Active charger change (format: "Act Chg: -1" or "Act Chg: 0")
        (re.compile(r'Act Chg:\s*-?\d+', re.IGNORECASE),
         'CHARGER', 3, 'rgb(63, 185, 80)'),  # green
        
        # Charge request (format: "charge_request(13344mV, 4916mA)")
        (re.compile(r'charge_request\(\d+mV,\s*\d+mA\)', re.IGNORECASE),
         'CHARGER', 2, 'rgb(63, 185, 80)'),  # green
        
        # New charger port (format: "I: New chg p-1" or "I: New chg p0")
        (re.compile(r'New chg p-?\d+', re.IGNORECASE),
         'CHARGER', 3, 'rgb(63, 185, 80)'),  # green
        
        # PD request (format: "C0: Req [4] 20000mV 3250mA")
        (re.compile(r'C\d+:\s*Req\s*\[\d+\]\s*\d+mV\s*\d+mA', re.IGNORECASE),
         'USB_PD', 2, 'rgb(57, 197, 207)'),  # cyan
        
        # Motion sensor events
        (re.compile(r'Motion (pre-resume|pre-suspend|pre-shutdown)', re.IGNORECASE),
         'MOTION', 2, 'rgb(201, 203, 207)'),  # light gray
        
        # TCPC state changes (format: "C0: TCPC init ready", "TCPC Enter Low Power Mode")
        (re.compile(r'TCPC (init ready|Enter Low Power|Exit Low Power)|C\d+:\s*TCPC', re.IGNORECASE),
         'TCPC', 2, 'rgb(99, 102, 255)'),  # indigo
        
        # USB charge mode changes (format: "USB charge p0 m2 i0")
        (re.compile(r'USB charge p\d+ m\d+ i\d+', re.IGNORECASE),
         'USB_CHARGE', 2, 'rgb(57, 197, 207)'),  # cyan
        
        # CL (charge limit) events (format: "CL: p-1 s-1 i512 v0")
        (re.compile(r'CL:\s*p-?\d+\s+s-?\d+', re.IGNORECASE),
         'CHARGE_LIMIT', 2, 'rgb(57, 197, 207)'),  # cyan
        
        # Thermal throttling or thermal events
        (re.compile(r'thermal|throttl|overheat|prochot', re.IGNORECASE),
         'THERMAL', 3, 'rgb(255, 107, 129)'),  # red
        
        # EC errors and warnings (more specific patterns)
        (re.compile(r'failed|error|ERR:|WARN:|stall', re.IGNORECASE),
         'EC_WARN', 3, 'rgb(248, 81, 73)'),  # bright red
        
        # Display Port / Alt mode events
        (re.compile(r'DP mode|Entered DP|DP HPD|DisplayPort', re.IGNORECASE),
         'DP_MODE', 2, 'rgb(255, 159, 64)'),  # orange
        
        # Device initialization (format: "DEVICE_ID=261", "raa489000_init")
        (re.compile(r'DEVICE_ID=\d+|_init\(\d+\)', re.IGNORECASE),
         'INIT', 1, 'rgb(139, 148, 158)'),  # gray
        
        # Button events
        (re.compile(r'power\s*button|PWR_BTN|volume\s*(up|down)', re.IGNORECASE),
         'BUTTON', 2, 'rgb(139, 148, 158)'),  # gray
        
        # Accelerometer / sensor init (format: "alt-lid-accel: MS Done Init")
        (re.compile(r'MS Done Init|ODR:', re.IGNORECASE),
         'SENSOR_INIT', 1, 'rgb(139, 148, 158)'),  # gray
    ]
    
    # Default patterns to skip - these create too much noise
    # Can be overridden by config.json ec_events.skip_patterns
    DEFAULT_SKIP_PATTERNS = [
        r'Battery \d+%.*Display.*%',  # Skip frequent battery status updates
    ]
    
    # Timestamp patterns in cros_ec.log
    TIMESTAMP_PATTERNS = [
        # Format: 2025-10-31T11:58:18.123456Z (ISO format - highest priority)
        (re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d+)?Z?'), 'iso'),
        # Format: Oct 31 11:58:18
        (re.compile(r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'), 'syslog'),
        # Format: [1.234567] or [12345.678901] (kernel uptime in brackets)
        (re.compile(r'\[(\d+\.\d+)'), 'kernel_uptime'),
    ]
    
    MONTH_MAP = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    def __init__(self, reference_year: Optional[int] = None, skip_patterns: Optional[List[str]] = None):
        """
        Initialize the parser.
        
        Args:
            reference_year: Year to use for timestamps without year info
            skip_patterns: List of regex patterns to skip (overrides defaults)
        """
        self.reference_year = reference_year or datetime.now().year
        
        # Compile skip patterns - use provided patterns or defaults
        pattern_strings = skip_patterns if skip_patterns is not None else self.DEFAULT_SKIP_PATTERNS
        self.skip_patterns = [re.compile(p, re.IGNORECASE) for p in pattern_strings]
    
    def parse_content(self, content: str) -> List[Dict]:
        """
        Parse cros_ec.log content and extract EC events.
        
        Args:
            content: Raw cros_ec.log content
            
        Returns:
            List of event dictionaries with timestamp, type, level, color, message
        """
        events = []
        seen_events = set()  # Track (timestamp, message) to deduplicate
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            # Skip noisy patterns first
            should_skip = False
            for skip_pattern in self.skip_patterns:
                if skip_pattern.search(line):
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # Check each pattern
            for pattern, event_type, level, color in self.EC_EVENT_PATTERNS:
                if pattern.search(line):
                    timestamp = self._extract_timestamp(line)
                    message = line.strip()[:200]
                    
                    # Deduplicate events with same timestamp and message
                    ts_str = timestamp.isoformat() if timestamp else 'none'
                    event_key = (ts_str, message)
                    if event_key in seen_events:
                        break  # Skip duplicate
                    seen_events.add(event_key)
                    
                    event = {
                        'source': 'cros_ec.log',
                        'timestamp': timestamp,
                        'line_number': line_num,
                        'type': event_type,
                        'level': level,
                        'color': color,
                        'message': line.strip()[:200],  # Limit message length
                    }
                    events.append(event)
                    break  # Only match first pattern per line
        
        return events
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """
        Extract timestamp from log line.
        
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
        Parse matched timestamp.
        
        Args:
            match: Regex match object
            fmt: Format identifier
            
        Returns:
            datetime object
        """
        if fmt == 'kernel_uptime':
            # Kernel uptime - can't convert to absolute time without boot time
            # Return None and let caller handle it
            return None
        
        elif fmt == 'syslog':
            # Oct 31 11:58:18
            time_str = match.group(1)
            parts = time_str.split()
            month = self.MONTH_MAP.get(parts[0], 1)
            day = int(parts[1])
            time_parts = parts[2].split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            second = int(time_parts[2])
            
            return datetime(self.reference_year, month, day, hour, minute, second)
        
        elif fmt == 'iso':
            # 2025-10-31T11:58:18
            time_str = match.group(1)
            return datetime.fromisoformat(time_str.replace('Z', ''))
        
        return None
    
    def map_to_vmlog_timeline(self, events: List[Dict], vmlog_data: List[Dict]) -> List[Dict]:
        """
        Map EC events to vmlog timeline for events without absolute timestamps.
        
        For events with kernel uptime timestamps, tries to correlate with
        vmlog timestamps based on relative positioning.
        
        Args:
            events: List of EC events
            vmlog_data: Parsed vmlog entries with timestamps
            
        Returns:
            Events with vmlog_timestamp field added where possible
        """
        if not vmlog_data:
            return events
        
        # Get vmlog time range
        vmlog_timestamps = [e.get('timestamp') for e in vmlog_data if e.get('timestamp')]
        if not vmlog_timestamps:
            return events
        
        vmlog_start = min(vmlog_timestamps)
        vmlog_end = max(vmlog_timestamps)
        
        for event in events:
            ts = event.get('timestamp')
            if ts:
                # Check if timestamp is within vmlog range
                if vmlog_start <= ts <= vmlog_end:
                    event['vmlog_timestamp'] = ts
                else:
                    # Try to find closest vmlog timestamp
                    closest = min(vmlog_timestamps, key=lambda x: abs((x - ts).total_seconds()))
                    if abs((closest - ts).total_seconds()) < 60:  # Within 1 minute
                        event['vmlog_timestamp'] = closest
            else:
                # No absolute timestamp - use middle of vmlog range as fallback
                # This is imperfect but better than nothing
                pass
        
        return events
    
    def filter_by_level(self, events: List[Dict], min_level: int = 1) -> List[Dict]:
        """
        Filter events by minimum importance level.
        
        Args:
            events: List of events
            min_level: Minimum level to include (1=info, 2=warning, 3=notable, 4=critical)
            
        Returns:
            Filtered events
        """
        return [e for e in events if e.get('level', 1) >= min_level]
