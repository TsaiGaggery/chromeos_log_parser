# ChromeOS Log Analyzer

A Python tool for parsing, analyzing, and visualizing ChromeOS logs. Generates interactive HTML reports with time-series charts and error markers.

## Features

- **Multi-format Support**: Parse both `generated_logs` directory structures and user feedback text files
- **vmlog Visualization**: Interactive time-series charts for CPU usage and frequencies
  - Separate charts for each vmlog segment (LATEST, PREVIOUS, etc.)
  - CPU frequency values converted from kHz to MHz for readability
- **Thermal Monitoring**: Parse temp_logger from `/var/log/messages` for thermal temperature visualization
- **Error Detection**: Automatically scan logs for errors, warnings, and critical issues
- **Error Timeline**: Mark detected errors on the vmlog timeline chart
- **Self-contained HTML**: Generate single-file HTML reports with embedded data and charts
- **Search & Browse**: Search through all log files directly in the report

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd chromeos_log_parser

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Analyze extracted generated_logs directory
python -m src.main -i ./generated_logs/ -o report.html

# Analyze user feedback text file
python -m src.main -i feedback.txt -o report.html

# Analyze ZIP archive directly
python -m src.main -i logs.zip -o report.html

# With verbose output
python -m src.main -i logs/ -o report.html --verbose
```

### Command Line Options

```
-i, --input      Input path: directory, ZIP file, or text file (required)
-o, --output     Output HTML report path (default: chromeos_log_report.html)
-t, --type       Log type: auto, generated, or feedback (default: auto)
-v, --verbose    Enable verbose output
--max-points     Maximum chart data points (default: 5000)
--year           Reference year for timestamps (default: current year)
```

## Generated Report

The HTML report includes:

1. **CPU Charts**: One chart per vmlog segment showing:
   - CPU usage percentage
   - CPU frequencies (cpufreq0-3) in MHz

2. **Thermal Chart**: Temperature data from all thermal zones:
   - x86_pkg_temp, INT3400_Thermal, TSR0, TSR1, etc.

3. **Error Summary**: Grouped by severity (Critical, Error, Warning, Info)

4. **Log Browser**: Search and view all parsed log files

## Supported Log Formats

### Generated Logs Structure

```
generated_logs/
├── feedback/
│   ├── vmlog.1.LATEST
│   ├── vmlog.1.PREVIOUS
│   ├── vmlog.1.3
│   ├── syslog
│   ├── chrome_system_log
│   └── ...
├── var/log/
│   ├── messages
│   ├── messages.1
│   └── ...
└── home/chronos/user/log/
    └── ...
```

### vmlog Format

```
time pgmajfault pgmajfault_f pgmajfault_a pswpin pswpout cpuusage cpufreq0 cpufreq1 cpufreq2 cpufreq3
[1027/124537] 0 0 0 0 0 0.02 700000 700000 700000 1246034
```

- Timestamp `[MMDD/HHMMSS]`: 10月27日 12:45:37 UTC
- cpufreq values in kHz: 700000 = 700 MHz, 1246034 = 1246.034 MHz

### temp_logger Format (from /var/log/messages)

```
2025-10-27T07:44:13.519238Z NOTICE temp_logger[4157]: x86_pkg_temp:55C INT3400_Thermal:20C TSR0:44C TSR1:56C
```

### User Feedback Format

Single text file with sections:

```
CHROMEOS_RELEASE_VERSION=15633.0.0
CHROMEOS_RELEASE_BOARD=volteer

vmlog.LATEST=<multiline>
---------- START ----------
time pgmajfault pgmajfault_f pgmajfault_a pswpin pswpout cpuusage cpufreq0 cpufreq1 cpufreq2 cpufreq3
[1027/151447] 0 0 0 0 0 0.02 700000 700000 698611 1263820
---------- END ----------

syslog=<multiline>
---------- START ----------
...log content...
---------- END ----------
```

## Project Structure

```
chromeos_log_parser/
├── src/
│   ├── parsers/
│   │   ├── vmlog_parser.py       # Parse vmlog time-series data
│   │   ├── generated_logs_parser.py  # Parse directory structures
│   │   └── user_feedback_parser.py   # Parse feedback text files
│   ├── analyzers/
│   │   ├── error_detector.py     # Scan for error patterns
│   │   └── metrics_analyzer.py   # Analyze vmlog statistics
│   ├── visualizers/
│   │   ├── chart_generator.py    # Generate Chart.js config
│   │   └── html_builder.py       # Build HTML report
│   └── main.py                   # CLI entry point
├── tests/
│   ├── fixtures.py               # Test data
│   ├── test_parsers.py           # Parser tests
│   └── test_analyzers.py         # Analyzer tests
├── docs/
│   └── specs/                    # Specification documents
├── requirements.txt
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## HTML Report Features

The generated HTML report includes:

1. **Header Section**: ChromeOS version, board info, and generation timestamp
2. **Timeline Chart**: Interactive vmlog metrics visualization
   - CPU usage (percentage)
   - CPU frequencies (MHz)
   - Error markers as vertical lines
   - Zoom and pan controls
3. **Error Summary**: Table of all detected errors with:
   - Severity levels (Critical, Error, Warning, Info)
   - Timestamps and source files
   - Click to expand for context
4. **Log Browser**: Searchable list of all log files
   - Click to view full content
   - File size information

## Error Patterns Detected

- `ERROR`, `FATAL`, `CRASH`
- `WARNING`, `WARN`
- `FAILED`, `failure`
- `timeout`, `refused`, `denied`
- `panic`, `OOM`, `Out of memory`
- `killed`, `CRITICAL`

## License

MIT License
