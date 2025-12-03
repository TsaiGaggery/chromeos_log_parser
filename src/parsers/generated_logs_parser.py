"""
GeneratedLogsParser - Parse extracted generated_logs directory structure.

Expected structure:
├── feedback/
│   ├── vmlog.LATEST -> vmlog.20251031-113706
│   ├── vmlog.PREVIOUS
│   ├── syslog
│   ├── chrome_system_log
│   └── [other log files]
├── var/log/
│   └── [system logs]
└── home/chronos/user/log/
    └── [user logs]
"""

import os
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class GeneratedLogsParser:
    """Parses extracted generated_logs directory structure."""
    
    # Priority log files to look for
    PRIORITY_LOGS = [
        'vmlog.LATEST',
        'vmlog.PREVIOUS',
        'syslog',
        'chrome_system_log',
        'chrome_system_log.PREVIOUS',
        'dmesg',
        'messages',
        'net.log',
        'bluetooth.log',
        'cros_ec.log',
        'powerd.LATEST',
        'powerd.PREVIOUS',
        'ui.LATEST',
        'ui.PREVIOUS',
    ]
    
    # Metadata file patterns
    METADATA_PATTERNS = [
        re.compile(r'^CHROMEOS_'),
        re.compile(r'^BUILD_'),
        re.compile(r'^PRODUCT_'),
    ]
    
    # Binary file extensions to skip
    BINARY_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bin', '.dat', '.gz', '.bz2', '.xz'}
    
    def __init__(self):
        """Initialize the parser."""
        self._temp_dir = None
    
    def parse_directory(self, root_path: str) -> Dict:
        """
        Scan directory and read all log files.
        
        Args:
            root_path: Path to extracted logs directory or ZIP file
            
        Returns:
            Dictionary structure with metadata, logs, and directory structure
        """
        # Handle ZIP file
        if zipfile.is_zipfile(root_path):
            root_path = self._extract_archive(root_path)
        
        result = {
            'metadata': {},
            'logs': {},
            'structure': {},
            'source_path': root_path
        }
        
        # Find the actual logs root (may be nested)
        logs_root = self._find_logs_root(root_path)
        
        # Extract metadata
        result['metadata'] = self._extract_metadata(logs_root)
        
        # Scan and read log files
        result['logs'], result['structure'] = self._scan_directory(logs_root)
        
        return result
    
    def _extract_archive(self, zip_path: str) -> str:
        """
        Extract ZIP archive to temporary directory.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Path to extracted directory
        """
        self._temp_dir = tempfile.mkdtemp(prefix='chromeos_logs_')
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(self._temp_dir)
        
        return self._temp_dir
    
    def _find_logs_root(self, root_path: str) -> str:
        """
        Find the actual root of log files (may be nested in extracted archive).
        
        Args:
            root_path: Starting path
            
        Returns:
            Path to logs root directory
        """
        # Check if feedback/ exists at this level
        if os.path.exists(os.path.join(root_path, 'feedback')):
            return root_path
        
        # Check one level down
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            if os.path.isdir(item_path):
                if os.path.exists(os.path.join(item_path, 'feedback')):
                    return item_path
        
        # No feedback directory found, use root as-is
        return root_path
    
    def _extract_metadata(self, root_path: str) -> Dict:
        """
        Parse CHROMEOS_* files in feedback/ directory.
        
        Args:
            root_path: Root logs directory
            
        Returns:
            Dictionary with metadata
        """
        metadata = {
            'chromeos_version': None,
            'board': None,
            'build_type': None,
            'hardware_class': None,
            'collection_time': None,
        }
        
        feedback_dir = os.path.join(root_path, 'feedback')
        if not os.path.exists(feedback_dir):
            return metadata
        
        # Read lsb-release file if available
        lsb_release = os.path.join(feedback_dir, 'lsb-release')
        if os.path.exists(lsb_release):
            try:
                content = self._read_log_file(lsb_release)
                metadata.update(self._parse_lsb_release(content))
            except Exception:
                pass
        
        # Check for individual CHROMEOS_ files
        for filename in os.listdir(feedback_dir):
            for pattern in self.METADATA_PATTERNS:
                if pattern.match(filename):
                    filepath = os.path.join(feedback_dir, filename)
                    try:
                        content = self._read_log_file(filepath)
                        key = filename.lower()
                        metadata[key] = content.strip()
                    except Exception:
                        pass
        
        return metadata
    
    def _parse_lsb_release(self, content: str) -> Dict:
        """
        Parse lsb-release file content.
        
        Args:
            content: File content
            
        Returns:
            Parsed metadata
        """
        result = {}
        for line in content.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if 'version' in key:
                    result['chromeos_version'] = value
                elif 'board' in key:
                    result['board'] = value
                elif 'build_type' in key:
                    result['build_type'] = value
        
        return result
    
    def _scan_directory(self, root_path: str) -> Tuple[Dict[str, str], Dict]:
        """
        Scan directory tree and read log files.
        
        Args:
            root_path: Root directory path
            
        Returns:
            Tuple of (logs dict, structure dict)
        """
        logs = {}
        structure = {}
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            rel_dir = os.path.relpath(dirpath, root_path)
            if rel_dir == '.':
                rel_dir = ''
            
            # Build structure
            dir_info = {
                'files': [],
                'subdirs': dirnames.copy()
            }
            
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
                
                # Skip binary files
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.BINARY_EXTENSIONS:
                    dir_info['files'].append({'name': filename, 'type': 'binary'})
                    continue
                
                # Handle symlinks
                if os.path.islink(filepath):
                    target = os.readlink(filepath)
                    dir_info['files'].append({
                        'name': filename,
                        'type': 'symlink',
                        'target': target
                    })
                    # Resolve the actual file
                    actual_path = os.path.join(dirpath, target)
                    if os.path.exists(actual_path):
                        filepath = actual_path
                
                # Read log file
                try:
                    content = self._read_log_file(filepath)
                    logs[rel_path] = content
                    dir_info['files'].append({
                        'name': filename,
                        'type': 'log',
                        'size': len(content)
                    })
                except Exception as e:
                    dir_info['files'].append({
                        'name': filename,
                        'type': 'error',
                        'error': str(e)
                    })
            
            structure[rel_dir if rel_dir else '.'] = dir_info
        
        return logs, structure
    
    def _read_log_file(self, filepath: str, max_size: int = 50 * 1024 * 1024) -> str:
        """
        Read log file with error handling.
        
        Args:
            filepath: Path to file
            max_size: Maximum file size to read (default 50MB)
            
        Returns:
            File content as string
        """
        # Check file size
        file_size = os.path.getsize(filepath)
        if file_size > max_size:
            # Read only first and last portions of large files
            with open(filepath, 'rb') as f:
                head = f.read(max_size // 2)
                f.seek(-max_size // 2, 2)
                tail = f.read()
            
            # Try to decode
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    head_str = head.decode(encoding)
                    tail_str = tail.decode(encoding)
                    return head_str + f"\n\n... [Truncated {file_size - max_size} bytes] ...\n\n" + tail_str
                except UnicodeDecodeError:
                    continue
            
            return f"[Binary or unreadable file: {file_size} bytes]"
        
        # Read entire file
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # Last resort: read as binary and decode ignoring errors
        with open(filepath, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')
    
    def get_vmlog_files(self, logs: Dict[str, str]) -> Dict[str, str]:
        """
        Extract vmlog files from logs dictionary.
        
        Args:
            logs: Dictionary of log file contents
            
        Returns:
            Dictionary with vmlog file contents
        """
        vmlog_files = {}
        for path, content in logs.items():
            filename = os.path.basename(path)
            if filename.startswith('vmlog'):
                vmlog_files[path] = content
        return vmlog_files
    
    def get_priority_logs(self, logs: Dict[str, str]) -> Dict[str, str]:
        """
        Get priority log files from logs dictionary.
        
        Args:
            logs: Dictionary of log file contents
            
        Returns:
            Dictionary with priority log contents
        """
        priority_logs = {}
        for path, content in logs.items():
            filename = os.path.basename(path)
            if filename in self.PRIORITY_LOGS:
                priority_logs[path] = content
            # Also check for vmlog with timestamps
            elif filename.startswith('vmlog.'):
                priority_logs[path] = content
        return priority_logs
    
    def cleanup(self):
        """Clean up temporary files."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)
            self._temp_dir = None
    
    def __del__(self):
        """Destructor to clean up temp files."""
        self.cleanup()
