# ChromeOS Log Analyzer

A Python tool for parsing, analyzing, and visualizing ChromeOS logs. Generates interactive HTML reports with time-series charts, error markers, and log browsing capabilities.

## Features

- **Multiple Input Formats**: Supports generated_logs directories, ZIP archives, and user feedback text files
- **Auto-Detection**: Automatically identifies input format
- **Interactive Charts**: Time-series visualization of CPU, memory, swap, and thermal data using Chart.js
- **Error Detection**: Identifies critical errors, warnings, and failures with timeline markers
- **Log Browser**: Searchable log viewer with keyword highlighting
- **Self-Contained Output**: Single HTML file with embedded CSS, JavaScript, and data
- **Configurable**: JSON-based configuration with CLI overrides

## Installation

```bash
# Clone the repository
git clone https://github.com/user/chromeos_log_parser.git
cd chromeos_log_parser

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

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
-i, --input       Input path: directory, ZIP file, or text file (required)
-o, --output      Output HTML report path (default: chromeos_log_report.html)
-t, --type        Log type: auto, generated, or feedback (default: auto)
-v, --verbose     Enable verbose output
--max-points      Maximum chart data points (default: from config.json)
--max-duration    Maximum chart duration in minutes (default: from config.json)
--year            Reference year for timestamps (default: current year)
--config          Path to config.json file (default: auto-detect)
```

### Configuration

Settings can be customized via `config.json`:

```json
{
    "chart": {
        "max_duration_minutes": 10,
        "max_data_points": 5000
    },
    "parsing": {
        "time_gap_threshold_seconds": 5
    },
    "error_detection": {
        "default_marker_level": "none"
    }
}
```

CLI arguments override config file settings.

## Generated Report

The HTML report includes:

1. **System Info**: ChromeOS version, board, and metadata
2. **Error Summary**: Categorized errors with search and filter capabilities
3. **Time-Series Charts**: 
   - CPU usage (0-100%)
   - Memory usage
   - Swap usage
   - Thermal data (temperature zones)
4. **Log Browser**: Full log content with search and keyword highlighting
5. **Interactive Features**:
   - Chart zoom and pan
   - Error marker toggle (on/off)
   - Error level filter (none/error/critical/all)
   - Hover tooltips for error details

## Supported Log Formats

### Generated Logs Format

Directory structure from ChromeOS feedback:

```
generated_logs/
├── var_log/
│   ├── messages
│   ├── vmlog/
│   │   ├── vmlog.LATEST
│   │   └── vmlog.PREVIOUS
│   └── temp_logger/
│       └── temp_logger
├── lsb-release
└── etc/
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

## Architecture

```
Input (ZIP/Directory/Text)
         │
         ▼
┌─────────────────┐
│  Parser Layer   │  ─── Normalization & Extraction
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Analyzer Layer  │  ─── Pattern Detection & Statistics
└─────────────────┘
         │
         ▼
┌─────────────────┐
│Visualizer Layer │  ─── Chart Generation & HTML Assembly
└─────────────────┘
         │
         ▼
   HTML Report (Single file)
```

See [docs/specs/architecture.md](docs/specs/architecture.md) for detailed architecture documentation.

## Project Structure

```
chromeos_log_parser/
├── src/
│   ├── main.py                   # CLI entry point
│   ├── parsers/
│   │   ├── generated_logs_parser.py
│   │   ├── user_feedback_parser.py
│   │   ├── vmlog_parser.py
│   │   └── temp_logger_parser.py
│   ├── analyzers/
│   │   ├── error_detector.py
│   │   └── metrics_analyzer.py
│   └── visualizers/
│       ├── chart_generator.py
│       └── html_builder.py
├── tests/
│   ├── fixtures.py               # Sample log data
│   ├── test_parsers.py
│   └── test_analyzers.py
├── docs/
│   └── specs/                    # Specification documents
├── config.json                   # Default configuration
├── requirements.txt
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_parsers.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## HTML Report Features

### Chart Interactions
- **Zoom**: Mouse wheel or pinch gesture
- **Pan**: Click and drag
- **Reset**: Double-click to reset view
- **Error Markers**: Toggle visibility with dropdown selector

### Search Features
- **Error Summary**: Filter errors by keyword
- **Log Browser**: Search within log content with match highlighting
- **Navigation**: Previous/Next buttons to jump between matches

### Error Level Filter
- **None**: Hide all error markers on charts
- **Error**: Show ERROR and WARNING level markers
- **Critical**: Show only CRITICAL and FATAL markers
- **All**: Show all detected error markers

## Error Patterns Detected

The analyzer detects the following error patterns in logs:

| Level | Patterns |
|-------|----------|
| Critical | `FATAL`, `CRASH`, `panic`, `OOM`, `Out of memory`, `killed`, `CRITICAL` |
| Error | `ERROR`, `FAILED`, `failure`, `timeout`, `refused`, `denied` |
| Warning | `WARNING`, `WARN` |

## Performance

- **Target Processing Time**: <60 seconds for typical logs
- **Input Size**: Up to 500MB
- **Output Size**: <10MB HTML file
- **Data Sampling**: Automatic sampling for large datasets

## License

MIT License