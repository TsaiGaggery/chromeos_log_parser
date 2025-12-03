# ChromeOS Log Analyzer - Specification

## Project Overview
A web-based ChromeOS log analysis tool that parses, visualizes, and analyzes ChromeOS logs from two different sources: generated_logs archives and user feedback files.

## Core Requirements

### 1. Log Source Support
- **Generated Logs**: Extract and parse directory structure from generate_logs archives
- **User Feedback**: Parse single text file containing all logs with section markers

### 2. vmlog Data Extraction
Extract vmlog time series data with the following fields:
- time (format: [MMDD/HHMMSS])
- pgmajfault, pgmajfault_f, pgmajfault_a
- pswpin, pswpout
- cpuusage
- cpufreq0, cpufreq1, cpufreq2, cpufreq3

### 3. Data Visualization
- Generate interactive time-series charts for vmlog metrics
- Support multiple metric overlays on the same timeline
- Zoom and pan capabilities for detailed analysis

### 4. Error Detection and Marking
- Scan all log files for error patterns (ERROR, WARNING, FAILED, etc.)
- Mark error occurrences on the timeline chart
- Associate errors with their source log files
- Display error details on hover/click

### 5. HTML Report Generation
- Single-file HTML output with embedded CSS/JavaScript
- Responsive design for different screen sizes
- Interactive charts with tooltips
- Log file browser with search capability
- Error summary section

## Input Formats

### Generated Logs Structure
```
├── feedback/
│   ├── vmlog.LATEST
│   ├── vmlog.PREVIOUS
│   ├── syslog
│   ├── chrome_system_log
│   └── [other log files]
├── var/log/
│   └── [system logs]
└── home/chronos/user/log/
    └── [user logs]
```

### User Feedback Format
Single text file with sections marked as:
```
SECTION_NAME=<multiline>
---------- START ----------
[content]
---------- END ----------
```

## Output Requirements

### HTML Report Components
1. **Header**: Metadata (collection time, device info, ChromeOS version)
2. **Timeline Chart**: Interactive vmlog metrics visualization
3. **Error Markers**: Overlay on timeline with popup details
4. **Log Browser**: Filterable list of all log files
5. **Error Summary**: Categorized list of all errors found
6. **Search Functionality**: Full-text search across all logs

## Technical Constraints
- Pure Python backend for log parsing
- JavaScript/HTML5 for visualization (Chart.js or D3.js)
- No external dependencies in the generated HTML
- Support files up to 500MB
- Parse and generate report in under 60 seconds for typical logs

## Success Criteria
1. Successfully parse both log formats with 100% accuracy
2. Extract all vmlog entries with correct timestamps
3. Detect at least 95% of common error patterns
4. Generate self-contained HTML file under 10MB
5. Charts render smoothly with 10,000+ data points