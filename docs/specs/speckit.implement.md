# ChromeOS Log Analyzer - Implementation Guide

## Module Implementation Details

### 1. vmlog_parser.py
```python
# Implementation structure for GitHub Copilot

class VmlogParser:
    """
    Parses vmlog files from ChromeOS logs.
    
    Expected format:
    time pgmajfault pgmajfault_f pgmajfault_a pswpin pswpout cpuusage cpufreq0 cpufreq1 cpufreq2 cpufreq3
    [1027/151447] 0 0 0 0 0 0.02 700000 700000 698611 1263820
    """
    
    def parse_file(self, filepath: str) -> List[Dict]:
        """
        Parse a single vmlog file.
        
        Returns: List of dictionaries with keys:
        - timestamp: datetime object
        - pgmajfault, pgmajfault_f, pgmajfault_a: int
        - pswpin, pswpout: int
        - cpuusage: float
        - cpufreq0-3: int
        """
        pass
    
    def parse_timestamp(self, time_str: str) -> datetime:
        """
        Convert [MMDD/HHMMSS] to datetime object.
        Handle year wraparound (use current year or log collection year).
        """
        pass
    
    def parse_line(self, line: str, columns: List[str]) -> Dict:
        """
        Parse single vmlog data line.
        Return None if line is malformed.
        """
        pass
```

**Key Implementation Points**:
1. Handle header line separately from data lines
2. Timestamp format is [MMDD/HHMMSS] - parse to datetime with year inference
3. All numeric values except cpuusage are integers
4. cpuusage is a float (e.g., 0.02)
5. cpufreq values are in kHz (e.g., 700000 = 700 MHz)

---

### 2. generated_logs_parser.py
```python
class GeneratedLogsParser:
    """
    Parses extracted generated_logs directory structure.
    """
    
    def parse_directory(self, root_path: str) -> Dict:
        """
        Scan directory and read all log files.
        
        Returns: Dictionary structure:
        {
            'metadata': {...},  # ChromeOS version info
            'logs': {
                'feedback/vmlog.LATEST': 'content...',
                'feedback/syslog': 'content...',
                ...
            },
            'structure': {...}  # Directory tree
        }
        """
        pass
    
    def extract_metadata(self, root_path: str) -> Dict:
        """
        Parse CHROMEOS_* files in feedback/ directory.
        Extract version, board, build info.
        """
        pass
    
    def read_log_file(self, filepath: str) -> str:
        """
        Read log file with error handling.
        Try UTF-8, fall back to latin-1.
        """
        pass
```

**Key Implementation Points**:
1. Handle symlinks (e.g., vmlog.LATEST -> vmlog.20251031-113706)
2. Some files may be binary or corrupted - handle gracefully
3. Priority log files: vmlog.*, syslog, chrome_system_log, dmesg
4. Metadata files start with CHROMEOS_ prefix

---

### 3. user_feedback_parser.py
```python
class UserFeedbackParser:
    """
    Parses user feedback text file with multiline sections.
    """
    
    SECTION_PATTERN = re.compile(
        r'^(\w+)=<multiline>\n'
        r'---------- START ----------\n'
        r'(.*?)\n'
        r'---------- END ----------',
        re.MULTILINE | re.DOTALL
    )
    
    def parse_file(self, filepath: str) -> Dict:
        """
        Parse entire feedback file into sections.
        
        Returns:
        {
            'metadata': {...},
            'sections': {
                'vmlog.LATEST': 'content...',
                'syslog': 'content...',
                ...
            }
        }
        """
        pass
    
    def split_sections(self, content: str) -> Dict[str, str]:
        """
        Split file into named sections.
        Handle simple and multiline formats.
        """
        pass
```

**Key Implementation Points**:
1. Two section formats: simple (key=value) and multiline (with START/END)
2. Section names map to log file names (e.g., 'syslog' section)
3. Some sections may be empty: "<not available>" or "<empty>"
4. Handle nested markers gracefully

---

### 4. error_detector.py
```python
class ErrorDetector:
    """
    Scans logs for error patterns and maps to timeline.
    """
    
    ERROR_PATTERNS = [
        (re.compile(r'\bERROR\b', re.IGNORECASE), 'ERROR', 3),
        (re.compile(r'\bWARNING\b', re.IGNORECASE), 'WARNING', 2),
        (re.compile(r'\bFAILED\b', re.IGNORECASE), 'FAILED', 3),
        (re.compile(r'\bCRASH\b', re.IGNORECASE), 'CRASH', 4),
        # (pattern, label, severity)
    ]
    
    def scan_logs(self, logs: Dict[str, str]) -> List[Dict]:
        """
        Scan all logs for error patterns.
        
        Returns: List of error dictionaries:
        {
            'source': 'syslog',
            'timestamp': datetime or None,
            'line_number': 123,
            'severity': 3,
            'type': 'ERROR',
            'message': 'error line content',
            'context': ['line before', 'error line', 'line after']
        }
        """
        pass
    
    def extract_timestamp(self, line: str) -> Optional[datetime]:
        """
        Try to extract timestamp from log line.
        Support multiple formats (syslog, Chrome, kernel).
        """
        pass
    
    def map_to_vmlog_timeline(self, errors: List[Dict], 
                               vmlog_data: List[Dict]) -> List[Dict]:
        """
        Find nearest vmlog entry for each error.
        """
        pass
```

**Key Implementation Points**:
1. Multiple timestamp formats in different logs
2. Context should include ±5 lines around error
3. Severity scale: 1=info, 2=warning, 3=error, 4=critical
4. Map errors to vmlog timeline using nearest timestamp

---

### 5. chart_generator.py
```python
class ChartGenerator:
    """
    Generates Chart.js configuration for vmlog visualization.
    """
    
    def create_chart_config(self, vmlog_data: List[Dict],
                            errors: List[Dict]) -> Dict:
        """
        Create complete Chart.js configuration.
        
        Returns: Chart.js config dictionary with:
        - Multiple datasets (CPU usage, frequencies, page faults)
        - Time-based x-axis
        - Multiple y-axes
        - Error annotations
        - Zoom/pan configuration
        """
        pass
    
    def create_dataset(self, vmlog_data: List[Dict],
                       metric: str) -> Dict:
        """
        Create single Chart.js dataset for one metric.
        """
        pass
    
    def create_error_annotations(self, errors: List[Dict]) -> List[Dict]:
        """
        Create Chart.js annotation objects for errors.
        Use vertical lines or points on timeline.
        """
        pass
```

**Key Implementation Points**:
1. Use line charts for continuous metrics
2. Multiple y-axes: left for percentages (CPU), right for frequencies
3. Color coding: CPU=blue, freq0=red, freq1=green, etc.
4. Error markers as vertical lines with tooltips
5. Enable zoom plugin for detail view

---

### 6. html_builder.py
```python
class HTMLBuilder:
    """
    Builds complete HTML report with embedded data.
    """
    
    def build_report(self, parsed_data: Dict,
                     chart_config: Dict,
                     errors: List[Dict]) -> str:
        """
        Generate complete HTML file.
        
        Returns: HTML string with:
        - Embedded Chart.js library
        - Inline CSS styles
        - Chart configuration as JSON
        - Log browser section
        - Error summary table
        - Search functionality
        """
        pass
    
    def embed_chart_js(self) -> str:
        """
        Return Chart.js library code.
        Use CDN or inline minified version.
        """
        pass
    
    def build_log_browser(self, logs: Dict[str, str]) -> str:
        """
        Create HTML for searchable log file browser.
        Use accordion or tabs for organization.
        """
        pass
    
    def build_error_summary(self, errors: List[Dict]) -> str:
        """
        Create HTML table of all errors.
        Sortable by severity, time, source.
        """
        pass
```

**Key Implementation Points**:
1. Single self-contained HTML file
2. Bootstrap 5 for responsive layout
3. Search uses JavaScript filter (no backend)
4. Log content in collapsible sections
5. Error table links to chart timeline
6. Total file size target: <10MB

---

## Main Application Flow
```python
# main.py structure

def main():
    # 1. Parse arguments
    args = parse_arguments()
    
    # 2. Detect input type and parse
    if is_generated_logs(args.input):
        parser = GeneratedLogsParser()
        data = parser.parse_directory(args.input)
    else:
        parser = UserFeedbackParser()
        data = parser.parse_file(args.input)
    
    # 3. Parse vmlog specifically
    vmlog_parser = VmlogParser()
    vmlog_data = vmlog_parser.parse_from_data(data)
    
    # 4. Detect errors
    detector = ErrorDetector()
    errors = detector.scan_logs(data['logs'])
    errors = detector.map_to_vmlog_timeline(errors, vmlog_data)
    
    # 5. Analyze metrics (optional)
    analyzer = MetricsAnalyzer()
    stats = analyzer.calculate_stats(vmlog_data)
    anomalies = analyzer.detect_anomalies(vmlog_data)
    
    # 6. Generate chart configuration
    chart_gen = ChartGenerator()
    chart_config = chart_gen.create_chart_config(vmlog_data, errors)
    
    # 7. Build HTML report
    builder = HTMLBuilder()
    html = builder.build_report(data, chart_config, errors)
    
    # 8. Write output
    with open(args.output, 'w') as f:
        f.write(html)
    
    print(f"Report generated: {args.output}")
```

## Testing Guidelines

### Unit Test Example
```python
def test_vmlog_timestamp_parsing():
    parser = VmlogParser()
    # Test normal case
    dt = parser.parse_timestamp("[1027/151447]")
    assert dt.month == 10
    assert dt.day == 27
    assert dt.hour == 15
    assert dt.minute == 14
    assert dt.second == 47
    
    # Test edge cases
    dt = parser.parse_timestamp("[1231/235959]")
    assert dt.month == 12
    assert dt.day == 31
```

### Integration Test Example
```python
def test_end_to_end_generated_logs():
    # Create minimal test log structure
    test_dir = create_test_log_structure()
    
    # Run full pipeline
    parser = GeneratedLogsParser()
    data = parser.parse_directory(test_dir)
    
    # Verify results
    assert 'vmlog.LATEST' in data['logs']
    assert len(data['logs']) > 0
    assert data['metadata']['version'] is not None
```

## Error Patterns Reference

Common error patterns to detect:
- `ERROR`: General errors
- `WARNING`: Warnings
- `FAILED`: Operation failures
- `CRASH`: System crashes
- `panic`: Kernel panics
- `Out of memory`: OOM errors
- `timeout`: Timeout errors
- `refused`: Connection refused
- `killed`: Process killed

Timestamp formats to support:
- `2025-10-31T11:58:18.896902Z`: ISO format
- `[27268.556000]`: Kernel timestamp
- `1027/151447`: vmlog format
- `Oct 31 11:58:18`: syslog format