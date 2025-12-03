"""
UserFeedbackParser - Parse user feedback text file with multiline sections.

User feedback format:
Single text file with sections marked as:
- Simple: key=value
- Multiline:
    SECTION_NAME=<multiline>
    ---------- START ----------
    [content]
    ---------- END ----------
"""

import re
from typing import Dict, List, Optional, Tuple


class UserFeedbackParser:
    """Parses user feedback text file with multiline sections."""
    
    # Pattern for multiline section start
    MULTILINE_PATTERN = re.compile(
        r'^([A-Za-z0-9_.-]+)=<multiline>\s*$',
        re.MULTILINE
    )
    
    # Start and end markers
    START_MARKER = '---------- START ----------'
    END_MARKER = '---------- END ----------'
    
    # Alternative markers (some logs use different formats)
    ALT_START_MARKERS = [
        '---------- START ----------',
        '========== START ==========',
        '--- START ---',
    ]
    ALT_END_MARKERS = [
        '---------- END ----------',
        '========== END ==========',
        '--- END ---',
    ]
    
    # Known section names that map to log files
    SECTION_TO_LOGNAME = {
        'syslog': 'syslog',
        'chrome_system_log': 'chrome_system_log',
        'chrome_system_log.PREVIOUS': 'chrome_system_log.PREVIOUS',
        'vmlog.LATEST': 'vmlog.LATEST',
        'vmlog.PREVIOUS': 'vmlog.PREVIOUS',
        'dmesg': 'dmesg',
        'messages': 'messages',
        'ui.LATEST': 'ui.LATEST',
        'powerd.LATEST': 'powerd.LATEST',
        'bluetooth.log': 'bluetooth.log',
        'cros_ec.log': 'cros_ec.log',
        'net.log': 'net.log',
    }
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    def parse_file(self, filepath: str) -> Dict:
        """
        Parse entire feedback file into sections.
        
        Args:
            filepath: Path to user feedback text file
            
        Returns:
            Dictionary with metadata, sections, and logs
        """
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> Dict:
        """
        Parse user feedback content from string.
        
        Args:
            content: Full feedback file content
            
        Returns:
            Dictionary with:
            - metadata: Header information
            - sections: All parsed sections
            - logs: Sections that map to log files
        """
        result = {
            'metadata': {},
            'sections': {},
            'logs': {}
        }
        
        # Split into sections
        sections = self._split_sections(content)
        result['sections'] = sections
        
        # Extract metadata from header sections
        result['metadata'] = self._extract_metadata(sections)
        
        # Map sections to log names
        for section_name, section_content in sections.items():
            log_name = self._section_to_logname(section_name)
            if log_name:
                result['logs'][log_name] = section_content
        
        return result
    
    def _split_sections(self, content: str) -> Dict[str, str]:
        """
        Split file content into named sections.
        
        Args:
            content: Full file content
            
        Returns:
            Dictionary mapping section names to content
        """
        sections = {}
        lines = content.split('\n')
        
        current_section = None
        current_content = []
        in_multiline = False
        started = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for multiline section start
            multiline_match = self.MULTILINE_PATTERN.match(line)
            if multiline_match:
                # Save previous section if exists
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                current_section = multiline_match.group(1)
                current_content = []
                in_multiline = True
                started = False
                i += 1
                continue
            
            # Check for START marker
            if in_multiline and not started:
                if self._is_start_marker(line):
                    started = True
                    i += 1
                    continue
            
            # Check for END marker
            if in_multiline and started:
                if self._is_end_marker(line):
                    # Save the multiline section
                    sections[current_section] = '\n'.join(current_content)
                    current_section = None
                    current_content = []
                    in_multiline = False
                    started = False
                    i += 1
                    continue
            
            # Accumulate content
            if in_multiline and started:
                current_content.append(line)
            elif not in_multiline:
                # Check for simple key=value
                simple_match = self._parse_simple_line(line)
                if simple_match:
                    key, value = simple_match
                    # Skip if it's a multiline marker
                    if value != '<multiline>':
                        sections[key] = value
            
            i += 1
        
        # Handle case where file ends without END marker
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _is_start_marker(self, line: str) -> bool:
        """Check if line is a START marker."""
        stripped = line.strip()
        return stripped in self.ALT_START_MARKERS or 'START' in stripped and '-' * 5 in stripped
    
    def _is_end_marker(self, line: str) -> bool:
        """Check if line is an END marker."""
        stripped = line.strip()
        return stripped in self.ALT_END_MARKERS or 'END' in stripped and '-' * 5 in stripped
    
    def _parse_simple_line(self, line: str) -> Optional[Tuple[str, str]]:
        """
        Parse simple key=value line.
        
        Args:
            line: Single line
            
        Returns:
            Tuple of (key, value) or None
        """
        if '=' not in line:
            return None
        
        # Find first = and split
        idx = line.index('=')
        key = line[:idx].strip()
        value = line[idx+1:].strip()
        
        # Validate key (should be alphanumeric with some punctuation)
        if not re.match(r'^[A-Za-z0-9_.-]+$', key):
            return None
        
        return key, value
    
    def _extract_metadata(self, sections: Dict[str, str]) -> Dict:
        """
        Extract metadata from sections.
        
        Args:
            sections: Parsed sections
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'chromeos_version': None,
            'board': None,
            'hardware_class': None,
            'timestamp': None,
            'description': None,
        }
        
        # Known metadata keys
        metadata_keys = {
            'CHROMEOS_RELEASE_VERSION': 'chromeos_version',
            'CHROMEOS_RELEASE_BOARD': 'board',
            'HWID': 'hardware_class',
            'CHROMEOS_RELEASE_DESCRIPTION': 'description',
            'timestamp': 'timestamp',
            'date': 'timestamp',
        }
        
        for section_key, meta_key in metadata_keys.items():
            if section_key in sections:
                value = sections[section_key]
                if value not in ['<not available>', '<empty>', '']:
                    metadata[meta_key] = value
        
        return metadata
    
    def _section_to_logname(self, section_name: str) -> Optional[str]:
        """
        Map section name to log file name.
        
        Args:
            section_name: Section name from feedback file
            
        Returns:
            Log file name or None
        """
        # Direct mapping
        if section_name in self.SECTION_TO_LOGNAME:
            return self.SECTION_TO_LOGNAME[section_name]
        
        # Check for vmlog variants
        if section_name.startswith('vmlog'):
            return section_name
        
        # Check for common log patterns
        log_patterns = ['syslog', 'dmesg', 'messages', 'chrome', 'ui.', 'powerd']
        for pattern in log_patterns:
            if pattern in section_name.lower():
                return section_name
        
        return None
    
    def get_vmlog_content(self, parsed_data: Dict) -> Optional[str]:
        """
        Get vmlog content from parsed data.
        
        Args:
            parsed_data: Output from parse_file or parse_content
            
        Returns:
            vmlog content string or None
        """
        logs = parsed_data.get('logs', {})
        
        # Try LATEST first
        if 'vmlog.LATEST' in logs:
            return logs['vmlog.LATEST']
        
        # Try any vmlog
        for key, content in logs.items():
            if 'vmlog' in key.lower():
                return content
        
        return None
    
    def get_section_names(self, parsed_data: Dict) -> List[str]:
        """
        Get list of all section names.
        
        Args:
            parsed_data: Output from parse_file or parse_content
            
        Returns:
            List of section names
        """
        return list(parsed_data.get('sections', {}).keys())
