# ChromeOS Log Analyzer - Architecture

## Overview

The ChromeOS Log Analyzer is a Python-based tool that parses, analyzes, and visualizes ChromeOS logs from two sources: generated_logs archives and user feedback files. It produces self-contained HTML reports with interactive charts and error summaries.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLI Entry Point                            │
│                            (src/main.py)                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Input Detection                             │
│              (ZIP archive / Directory / Text file)                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ Generated │   │   User    │   │  Vmlog    │
            │   Logs    │   │ Feedback  │   │  Parser   │
            │  Parser   │   │  Parser   │   │           │
            └───────────┘   └───────────┘   └───────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Structured Data                               │
│                   (Logs, Metadata, Vmlog entries)                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌───────────────┐               ┌───────────────┐
            │    Error      │               │   Metrics     │
            │   Detector    │               │   Analyzer    │
            └───────────────┘               └───────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Analyzed Data                                 │
│                  (Errors, Statistics, Anomalies)                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌───────────────┐               ┌───────────────┐
            │    Chart      │               │     HTML      │
            │  Generator    │               │    Builder    │
            └───────────────┘               └───────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      HTML Report Output                              │
│            (Self-contained with embedded JS/CSS)                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Structure

### 1. Parser Layer (`src/parsers/`)

Responsible for reading and normalizing log data from various input formats.

| Module | Purpose | Input | Output |
|--------|---------|-------|--------|
| [`GeneratedLogsParser`](../src/parsers/generated_logs_parser.py) | Parse directory structures from generated_logs archives | ZIP file or directory path | Dict with logs, metadata |
| [`UserFeedbackParser`](../src/parsers/user_feedback_parser.py) | Parse multiline sections from feedback files | Text file path | Dict with sections, metadata |
| [`VmlogParser`](../src/parsers/vmlog_parser.py) | Parse vmlog time-series data | Vmlog content string | List of timestamped entries |
| [`TempLoggerParser`](../src/parsers/temp_logger_parser.py) | Parse thermal zone temperature data | Temp logger content | List of thermal entries |

### 2. Analyzer Layer (`src/analyzers/`)

Processes parsed data to extract insights and detect issues.

| Module | Purpose | Input | Output |
|--------|---------|-------|--------|
| [`ErrorDetector`](../src/analyzers/error_detector.py) | Scan logs for error patterns | All log contents | List of errors with metadata |
| [`MetricsAnalyzer`](../src/analyzers/metrics_analyzer.py) | Calculate statistics and detect anomalies | Vmlog data | Stats summary, anomalies |

### 3. Visualizer Layer (`src/visualizers/`)

Generates the final HTML report with embedded visualizations.

| Module | Purpose | Input | Output |
|--------|---------|-------|--------|
| [`ChartGenerator`](../src/visualizers/chart_generator.py) | Create Chart.js configurations | Vmlog data, errors | Chart.js config JSON |
| [`HTMLBuilder`](../src/visualizers/html_builder.py) | Assemble complete HTML report | All data, charts | Self-contained HTML |

## Data Flow

```
Input (ZIP/Directory/Text)
         │
         ▼
┌─────────────────┐
│  Parser Layer   │  ─── Normalization & Extraction
└─────────────────┘
         │
         ▼
   Structured Data
   {
     metadata: {...},
     logs: {...},
     vmlog_entries: [...]
   }
         │
         ▼
┌─────────────────┐
│ Analyzer Layer  │  ─── Pattern Detection & Statistics
└─────────────────┘
         │
         ▼
   Analyzed Data
   {
     errors: [...],
     stats: {...},
     anomalies: [...]
   }
         │
         ▼
┌─────────────────┐
│Visualizer Layer │  ─── Chart Generation & HTML Assembly
└─────────────────┘
         │
         ▼
   HTML Report
   (Single file, <10MB)
```

## Key Design Decisions

### 1. Self-Contained Output
- Single HTML file with embedded CSS, JavaScript, and data
- Uses CDN links for Chart.js and Bootstrap (fallback to inline)
- No server required for viewing reports

### 2. Input Format Abstraction
- Common internal data structure regardless of input source
- Auto-detection of input type (ZIP, directory, text file)
- Graceful handling of missing or corrupted logs

### 3. Segment-Based Processing
- Vmlog data split into segments based on time gaps
- Each segment generates a separate chart
- Prevents memory issues with large datasets

### 4. Error Mapping
- Errors detected in logs are mapped to vmlog timeline
- Displayed as annotations on time-series charts
- Context lines preserved for debugging

## External Dependencies

### Runtime
- Python 3.8+
- Standard library only (no required external packages)

### Embedded in Output
- Chart.js 4.x (time-series visualization)
- Bootstrap 5 (responsive layout)
- Chart.js plugins: zoom, annotation, date-fns adapter

## Configuration

Configuration is loaded from [`config.json`](../config.json) at the repository root:

```json
{
  "chart": {
    "max_duration_minutes": 10,
    "max_data_points": 5000
  },
  "parsing": {
    "time_gap_threshold_seconds": 5
  }
}
```

CLI arguments can override these settings.

## Error Handling Strategy

1. **Input Validation**: Check file formats before parsing
2. **Graceful Degradation**: Continue if some logs are corrupted
3. **Error Collection**: Parser errors collected separately from log errors
4. **User Feedback**: Parsing issues displayed in the report

## Performance Considerations

- **Data Sampling**: Charts limited to configurable max data points
- **Segment Splitting**: Large vmlog files split by time gaps
- **Lazy Reading**: Large logs processed incrementally
- **Target**: Process typical logs in <60 seconds

## Testing Strategy

```
tests/
├── fixtures.py          # Sample log data for testing
├── test_parsers.py      # Parser unit tests
└── test_analyzers.py    # Analyzer unit tests
```

Run tests with:
```bash
pytest tests/ -v
```

## File Size Targets

| Component | Target |
|-----------|--------|
| HTML Report | <10MB |
| Input Logs | Up to 500MB |
| Processing Time | <60 seconds |