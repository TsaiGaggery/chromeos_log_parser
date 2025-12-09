"""
SystemLogParser - Parse various ChromeOS system logs for events.

Handles the following log files:
- messages: Main system log (kernel, services)
- net.log: Network/WiFi logs (shill, wpa_supplicant)
- power_manager/powerd.LATEST: Power management daemon
- typecd.log: USB Type-C daemon
- bluetooth.log: Bluetooth stack
- ui/ui.LATEST: Chrome browser UI logs
- chrome/chrome: Chrome browser logs
- fwupd.log: Firmware update daemon

All logs use similar ISO timestamp format:
    YYYY-MM-DDTHH:MM:SS.ffffffZ LEVEL source[pid]: message
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class SystemLogParser:
    """Parses various ChromeOS system logs for meaningful events."""
    
    # Standard timestamp pattern for most ChromeOS logs
    # Format: 2025-10-31T11:42:38.454641Z INFO source[pid]: message
    TIMESTAMP_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+'
        r'(INFO|WARNING|ERR(?:OR)?|NOTICE|VERBOSE\d*)\s+'
        r'(\S+?)(?:\[(\d+)\])?:\s*(.*)$'
    )
    
    # Alternative pattern for Chrome logs without brackets
    # Format: 2025-10-31T11:37:00.003226Z ERROR chrome[1574:1574]: message
    CHROME_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+'
        r'(INFO|WARNING|ERR(?:OR)?|NOTICE|VERBOSE\d*)\s+'
        r'(\w+)(?:\[(\d+(?::\d+)?)\])?:\s*(.*)$'
    )
    
    # Event patterns for each log type with importance levels
    # Level: 1=info, 2=warning, 3=notable, 4=critical
    LOG_PATTERNS = {
        'messages': {
            'color': 'rgb(139, 148, 158)',  # gray
            'patterns': [
                # Kernel/USB events
                (re.compile(r'USB (dis)?connect', re.IGNORECASE), 'USB', 2, 'rgb(99, 102, 255)'),  # indigo
                # Power events
                (re.compile(r'Power source (AC|DC)', re.IGNORECASE), 'POWER', 3, 'rgb(163, 113, 247)'),  # purple
                (re.compile(r'Thermal state (Normal|Fair|Serious|Critical)', re.IGNORECASE), 'THERMAL', 3, 'rgb(255, 107, 129)'),  # red
                # System errors
                (re.compile(r'ERR|error|failed|failure', re.IGNORECASE), 'ERROR', 3, 'rgb(248, 81, 73)'),  # bright red
            ]
        },
        'net': {
            'color': 'rgb(88, 166, 255)',  # blue
            'patterns': [
                # WiFi state changes
                (re.compile(r'CTRL-EVENT-CONNECTED|Associated with', re.IGNORECASE), 'WIFI_CONNECT', 3, 'rgb(63, 185, 80)'),  # green
                (re.compile(r'CTRL-EVENT-DISCONNECTED|CTRL-EVENT-SUBNET-STATUS-UPDATE', re.IGNORECASE), 'WIFI_DISCONNECT', 3, 'rgb(248, 81, 73)'),  # red
                (re.compile(r'StateChanged.*completed|StateChanged.*authenticating', re.IGNORECASE), 'WIFI_STATE', 2, 'rgb(88, 166, 255)'),  # blue
                (re.compile(r'reassociation|roam|Selected BSS', re.IGNORECASE), 'WIFI_ROAM', 2, 'rgb(255, 159, 64)'),  # orange
                (re.compile(r'RSSI dropped|signal level', re.IGNORECASE), 'WIFI_SIGNAL', 2, 'rgb(201, 203, 207)'),  # light gray
                (re.compile(r'ScanDone', re.IGNORECASE), 'WIFI_SCAN', 1, 'rgb(139, 148, 158)'),  # gray
            ]
        },
        'powerd': {
            'color': 'rgb(163, 113, 247)',  # purple
            'patterns': [
                # Power state events
                (re.compile(r'lid (open|close)|Lid state', re.IGNORECASE), 'LID', 3, 'rgb(88, 166, 255)'),  # blue
                (re.compile(r'power button|PWR_BTN', re.IGNORECASE), 'POWER_BTN', 3, 'rgb(163, 113, 247)'),  # purple
                (re.compile(r'tablet mode|Tablet mode', re.IGNORECASE), 'TABLET_MODE', 2, 'rgb(57, 197, 207)'),  # cyan
                (re.compile(r'suspend|resume|Dark resume', re.IGNORECASE), 'SUSPEND', 3, 'rgb(163, 113, 247)'),  # purple
                (re.compile(r'Backlight.*level|brightness', re.IGNORECASE), 'BACKLIGHT', 1, 'rgb(255, 220, 100)'),  # yellow
                (re.compile(r'Battery.*threshold|low_battery|battery percent', re.IGNORECASE), 'BATTERY', 2, 'rgb(63, 185, 80)'),  # green
                (re.compile(r'Adaptive Charging|Charge Limit', re.IGNORECASE), 'CHARGING', 2, 'rgb(63, 185, 80)'),  # green
                (re.compile(r'Shutdown from suspend', re.IGNORECASE), 'SHUTDOWN', 4, 'rgb(248, 81, 73)'),  # red
            ]
        },
        'typecd': {
            'color': 'rgb(57, 197, 207)',  # cyan
            'patterns': [
                # Type-C events
                (re.compile(r'Partner (enumerated|removed)', re.IGNORECASE), 'TYPEC_PARTNER', 3, 'rgb(57, 197, 207)'),  # cyan
                (re.compile(r'Cable (added|removed)', re.IGNORECASE), 'TYPEC_CABLE', 3, 'rgb(57, 197, 207)'),  # cyan
                (re.compile(r'PD revision', re.IGNORECASE), 'PD_VERSION', 2, 'rgb(99, 102, 255)'),  # indigo
                (re.compile(r"Can't enter mode|data role", re.IGNORECASE), 'TYPEC_MODE', 2, 'rgb(255, 159, 64)'),  # orange
                (re.compile(r'Alt mode|alt mode', re.IGNORECASE), 'ALT_MODE', 2, 'rgb(99, 102, 255)'),  # indigo
                (re.compile(r'Product VDO|Id Header VDO', re.IGNORECASE), 'TYPEC_ID', 1, 'rgb(139, 148, 158)'),  # gray
            ]
        },
        'bluetooth': {
            'color': 'rgb(99, 102, 255)',  # indigo
            'patterns': [
                # Bluetooth events
                (re.compile(r'(dis)?connected', re.IGNORECASE), 'BT_CONNECT', 3, 'rgb(99, 102, 255)'),  # indigo
                (re.compile(r'pairing|paired', re.IGNORECASE), 'BT_PAIR', 3, 'rgb(63, 185, 80)'),  # green
                (re.compile(r'track_changed|MediaUpdate', re.IGNORECASE), 'BT_MEDIA', 1, 'rgb(139, 148, 158)'),  # gray
                (re.compile(r'A2DP|AVRCP|HFP|HSP', re.IGNORECASE), 'BT_PROFILE', 2, 'rgb(99, 102, 255)'),  # indigo
                (re.compile(r'scan|discovery', re.IGNORECASE), 'BT_SCAN', 1, 'rgb(139, 148, 158)'),  # gray
            ]
        },
        'ui': {
            'color': 'rgb(255, 159, 64)',  # orange
            'patterns': [
                # Chrome UI events
                (re.compile(r'tablet.mode.*Off|tablet.mode.*On', re.IGNORECASE), 'TABLET_MODE', 2, 'rgb(57, 197, 207)'),  # cyan
                (re.compile(r'Lid event|lid=', re.IGNORECASE), 'LID', 2, 'rgb(88, 166, 255)'),  # blue
                (re.compile(r'power\s*button|PowerEventObserver', re.IGNORECASE), 'POWER_BTN', 2, 'rgb(163, 113, 247)'),  # purple
                (re.compile(r'display.*added|display.*removed|Got display event', re.IGNORECASE), 'DISPLAY', 2, 'rgb(99, 102, 255)'),  # indigo
                (re.compile(r'ERR(?:OR)?|Failed|error', re.IGNORECASE), 'ERROR', 3, 'rgb(248, 81, 73)'),  # red
            ]
        },
        'chrome': {
            'color': 'rgb(255, 159, 64)',  # orange
            'patterns': [
                # Chrome errors and events
                (re.compile(r'ERR(?:OR)?.*|Failed to', re.IGNORECASE), 'CHROME_ERROR', 3, 'rgb(248, 81, 73)'),  # red
                (re.compile(r'WARNING', re.IGNORECASE), 'CHROME_WARN', 2, 'rgb(255, 220, 100)'),  # yellow
                (re.compile(r'Camera (module|hal)', re.IGNORECASE), 'CAMERA', 2, 'rgb(99, 102, 255)'),  # indigo
                (re.compile(r'GPU|gpu initialization', re.IGNORECASE), 'GPU', 2, 'rgb(163, 113, 247)'),  # purple
                (re.compile(r'login|signin|OOBE', re.IGNORECASE), 'LOGIN', 2, 'rgb(63, 185, 80)'),  # green
                (re.compile(r'battery_saver|Battery', re.IGNORECASE), 'BATTERY', 2, 'rgb(63, 185, 80)'),  # green
            ]
        },
        'fwupd': {
            'color': 'rgb(201, 203, 207)',  # light gray
            'patterns': [
                # Firmware update events
                (re.compile(r'battery level', re.IGNORECASE), 'FW_BATTERY', 2, 'rgb(63, 185, 80)'),  # green
                (re.compile(r'power state', re.IGNORECASE), 'FW_POWER', 2, 'rgb(163, 113, 247)'),  # purple
                (re.compile(r'device (added|removed|changed)', re.IGNORECASE), 'FW_DEVICE', 2, 'rgb(99, 102, 255)'),  # indigo
                (re.compile(r'firmware|update', re.IGNORECASE), 'FW_UPDATE', 3, 'rgb(255, 159, 64)'),  # orange
            ]
        }
    }
    
    def __init__(self, reference_year: int = None, min_level: int = 2):
        """
        Initialize the parser.
        
        Args:
            reference_year: Year for timestamp parsing (default: current year)
            min_level: Minimum event level to include (1-4, default: 2)
        """
        self.reference_year = reference_year or datetime.now().year
        self.min_level = min_level
    
    def detect_log_type(self, log_name: str) -> Optional[str]:
        """
        Detect the type of log from its filename/path.
        
        Returns one of: messages, net, powerd, typecd, bluetooth, ui, chrome, fwupd
        """
        log_name_lower = log_name.lower()
        
        if 'net.log' in log_name_lower or '/net.log' in log_name_lower:
            return 'net'
        elif 'powerd' in log_name_lower or 'power_manager' in log_name_lower:
            return 'powerd'
        elif 'typecd' in log_name_lower:
            return 'typecd'
        elif 'bluetooth' in log_name_lower:
            return 'bluetooth'
        elif '/ui/ui.' in log_name_lower or 'ui.latest' in log_name_lower:
            return 'ui'
        elif '/chrome/chrome' in log_name_lower:
            return 'chrome'
        elif 'fwupd' in log_name_lower:
            return 'fwupd'
        elif 'messages' in log_name_lower:
            return 'messages'
        
        return None
    
    def parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse ISO timestamp from log line."""
        try:
            # Handle microseconds and Z suffix
            if ts_str.endswith('Z'):
                ts_str = ts_str[:-1]  # Remove Z
            
            # Parse with microseconds
            if '.' in ts_str:
                return datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S.%f')
            else:
                return datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            return None
    
    def parse_line(self, line: str, log_type: str) -> Optional[Dict]:
        """
        Parse a single log line.
        
        Returns dict with timestamp, level, source, message, or None if not parseable.
        """
        line = line.strip()
        if not line:
            return None
        
        # Try standard pattern first
        match = self.TIMESTAMP_PATTERN.match(line)
        if not match:
            match = self.CHROME_PATTERN.match(line)
        
        if not match:
            return None
        
        ts_str, level, source, pid, message = match.groups()
        timestamp = self.parse_timestamp(ts_str)
        
        if timestamp is None:
            return None
        
        return {
            'timestamp': timestamp,
            'level': level,
            'source': source,
            'pid': pid,
            'message': message,
            'raw_line': line
        }
    
    def categorize_event(self, parsed_line: Dict, log_type: str) -> Optional[Dict]:
        """
        Categorize an event based on log type patterns.
        
        Returns event dict if matches a pattern, None otherwise.
        """
        if log_type not in self.LOG_PATTERNS:
            return None
        
        message = parsed_line.get('message', '')
        log_config = self.LOG_PATTERNS[log_type]
        
        for pattern, category, level, color in log_config['patterns']:
            if level < self.min_level:
                continue
            
            if pattern.search(message):
                return {
                    'timestamp': parsed_line['timestamp'],
                    'log_type': log_type,
                    'category': category,
                    'level': level,
                    'color': color,
                    'message': message[:100] + ('...' if len(message) > 100 else ''),
                    'source': parsed_line.get('source', ''),
                    'raw_line': parsed_line.get('raw_line', '')
                }
        
        return None
    
    def parse_content(self, content: str, log_type: str) -> List[Dict]:
        """
        Parse log content and extract categorized events.
        
        Args:
            content: Log file content
            log_type: Type of log (messages, net, powerd, etc.)
            
        Returns:
            List of event dicts with timestamp, category, level, color, message
        """
        events = []
        seen_events = set()  # For deduplication
        
        for line in content.split('\n'):
            parsed = self.parse_line(line, log_type)
            if not parsed:
                continue
            
            event = self.categorize_event(parsed, log_type)
            if event:
                # Deduplicate by timestamp + message
                event_key = (
                    event['timestamp'].isoformat() if event['timestamp'] else '',
                    event['message']
                )
                if event_key not in seen_events:
                    events.append(event)
                    seen_events.add(event_key)
        
        return events
    
    def map_to_vmlog_timeline(self, events: List[Dict], vmlog_entries: List[Dict]) -> List[Dict]:
        """
        Map events to vmlog timeline for chart display.
        
        Args:
            events: List of parsed events
            vmlog_entries: List of vmlog entries for reference timeline
            
        Returns:
            Updated events list with index reference
        """
        if not vmlog_entries or not events:
            return events
        
        vmlog_timestamps = [e.get('timestamp') for e in vmlog_entries if e.get('timestamp')]
        if not vmlog_timestamps:
            return events
        
        vmlog_start = min(vmlog_timestamps)
        vmlog_end = max(vmlog_timestamps)
        
        # Filter and map events
        mapped_events = []
        for event in events:
            ts = event.get('timestamp')
            if not ts:
                continue
            
            # Only include events within vmlog timerange (with buffer)
            from datetime import timedelta
            buffer = timedelta(minutes=5)
            if vmlog_start - buffer <= ts <= vmlog_end + buffer:
                mapped_events.append(event)
        
        return mapped_events


def get_log_type_display_name(log_type: str) -> str:
    """Get display name for log type."""
    names = {
        'messages': 'System Messages',
        'net': 'Network',
        'powerd': 'Power Manager',
        'typecd': 'Type-C',
        'bluetooth': 'Bluetooth',
        'ui': 'UI',
        'chrome': 'Chrome',
        'fwupd': 'Firmware'
    }
    return names.get(log_type, log_type.title())


def get_log_type_icon(log_type: str) -> str:
    """Get SVG icon for log type (Bootstrap Icons)."""
    icons = {
        'messages': 'terminal',
        'net': 'wifi',
        'powerd': 'battery-charging',
        'typecd': 'usb-symbol',
        'bluetooth': 'bluetooth',
        'ui': 'window',
        'chrome': 'browser-chrome',
        'fwupd': 'gear'
    }
    return icons.get(log_type, 'file-text')
