"""
HTMLBuilder - Build complete HTML report with embedded data.
"""

import json
import html
import re
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


def natural_sort_key(s: str):
    """
    Generate a key for natural sorting (e.g., part2 before part10).
    Splits the string into text and numeric parts for proper ordering.
    """
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', s)]


class HTMLBuilder:
    """Builds complete HTML report with embedded data."""
    
    # Chart.js CDN URL
    CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
    CHARTJS_ADAPTER_CDN = "https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"
    CHARTJS_ZOOM_CDN = "https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"
    CHARTJS_ANNOTATION_CDN = "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"
    
    # Bootstrap CDN
    BOOTSTRAP_CSS_CDN = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
    BOOTSTRAP_JS_CDN = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize the HTML builder.
        
        Args:
            template_path: Path to custom HTML template (optional)
        """
        self.template_path = template_path
    
    def build_report(self, parsed_data: Dict, chart_config: Dict, 
                     errors: List[Dict], metadata: Dict = None) -> str:
        """
        Generate complete HTML file (legacy single chart).
        
        Args:
            parsed_data: All parsed log data
            chart_config: Chart.js configuration
            errors: List of detected errors
            metadata: Additional metadata
            
        Returns:
            Complete HTML string
        """
        # Convert single chart to multi-chart format (list)
        charts = [{'id': 'main', 'title': 'Main', 'config': chart_config, 'type': 'cpu'}]
        return self.build_multi_chart_report(parsed_data, charts, errors, metadata)
    
    def build_multi_chart_report(self, parsed_data: Dict, charts: List[Dict],
                                  errors: List[Dict], metadata: Dict = None,
                                  thermal_chart: Dict = None) -> str:
        """
        Generate complete HTML file with multiple charts.
        
        Args:
            parsed_data: All parsed log data
            charts: List of chart configs with 'id', 'title', 'config', 'type'
            errors: List of detected errors
            metadata: Additional metadata
            thermal_chart: Legacy thermal temperature chart config
            
        Returns:
            Complete HTML string
        """
        # Build sections
        head_section = self._build_head()
        header_section = self._build_header(metadata or parsed_data.get('metadata', {}))
        chart_section = self._build_multi_chart_section(charts, thermal_chart)
        error_summary_section = self._build_error_summary(errors)
        log_browser_section = self._build_log_browser(parsed_data.get('logs', {}))
        scripts_section = self._build_multi_chart_scripts(charts, thermal_chart)
        
        # Combine into full HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
{head_section}
<body>
    <div class="container-fluid">
        {header_section}
        
        {chart_section}
        
        <div class="row mt-4">
            <div class="col-md-6">
                {error_summary_section}
            </div>
            <div class="col-md-6">
                {log_browser_section}
            </div>
        </div>
        
        <!-- Full Log Modal -->
        <div class="modal fade" id="logModal" tabindex="-1">
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="logModalTitle">Log Content</h5>
                        <div class="ms-auto me-3 d-flex align-items-center gap-2">
                            <input type="text" class="form-control form-control-sm" id="logContentSearch" 
                                   placeholder="Search in content..." style="width: 200px;"
                                   oninput="highlightInLog(this.value)">
                            <span id="searchResultCount" class="text-muted small"></span>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre id="logModalContent" class="log-content"></pre>
                    </div>
                    <div class="modal-footer justify-content-between">
                        <div>
                            <button class="btn btn-sm btn-outline-secondary" onclick="navigateHighlight(-1)">← Prev</button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="navigateHighlight(1)">Next →</button>
                        </div>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    {scripts_section}
</body>
</html>"""
        
        return html_content
    
    def _build_head(self) -> str:
        """Build HTML head section."""
        return f"""<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChromeOS Log Analysis Report</title>
    <link href="{self.BOOTSTRAP_CSS_CDN}" rel="stylesheet">
    <style>
        {self._get_custom_css()}
    </style>
</head>"""
    
    def _get_custom_css(self) -> str:
        """Get custom CSS styles with dark tech theme."""
        return """
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --bg-card: #1a1f29;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-blue: #58a6ff;
            --accent-cyan: #39c5cf;
            --accent-green: #3fb950;
            --accent-orange: #d29922;
            --accent-red: #f85149;
            --accent-purple: #a371f7;
            --border-color: #30363d;
            --glow-blue: rgba(88, 166, 255, 0.15);
        }
        
        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
        }
        
        .chart-container {
            position: relative;
            height: 400px;
            background: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
            border: 1px solid var(--border-color);
        }
        
        .error-card {
            max-height: 500px;
            overflow-y: auto;
            background: var(--bg-card);
        }
        
        .log-browser {
            max-height: 500px;
            overflow-y: auto;
            background: var(--bg-secondary);
            border-radius: 12px;
        }
        
        .log-content {
            max-height: 600px;
            overflow: auto;
            font-size: 12px;
            white-space: pre-wrap;
            word-wrap: break-word;
            background: var(--bg-primary);
            color: var(--accent-green);
            padding: 10px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
            border: 1px solid var(--border-color);
        }
        
        .severity-critical { 
            color: var(--accent-purple); 
            font-weight: bold; 
            text-shadow: 0 0 8px rgba(163, 113, 247, 0.4);
        }
        .severity-error { color: var(--accent-red); }
        .severity-warning { color: var(--accent-orange); }
        .severity-info { color: var(--text-secondary); }
        
        .log-item {
            cursor: pointer;
            transition: all 0.2s ease;
            border-bottom: 1px solid var(--border-color) !important;
        }
        
        .log-item:hover {
            background-color: var(--bg-tertiary);
            border-left: 3px solid var(--accent-blue);
        }
        
        .badge-critical { background-color: var(--accent-purple); }
        .badge-error { background-color: var(--accent-red); }
        .badge-warning { background-color: var(--accent-orange); color: #000; }
        
        .metadata-value {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            background: var(--bg-tertiary);
            color: var(--accent-cyan);
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }
        
        #searchInput {
            margin-bottom: 10px;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 8px;
        }
        
        #searchInput:focus {
            background: var(--bg-primary);
            border-color: var(--accent-blue);
            color: var(--text-primary);
            box-shadow: 0 0 0 3px var(--glow-blue);
        }
        
        #searchInput::placeholder {
            color: var(--text-muted);
        }
        
        .error-context {
            font-size: 11px;
            background: var(--bg-primary);
            color: var(--text-secondary);
            padding: 8px;
            border-left: 3px solid var(--accent-purple);
            margin-top: 5px;
            display: none;
            border-radius: 0 4px 4px 0;
        }
        
        .error-row.expanded .error-context {
            display: block;
        }
        
        .error-row {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .error-row:hover {
            background-color: var(--bg-tertiary) !important;
        }
        
        .chart-section {
            margin-bottom: 20px;
        }
        
        .chart-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            border: 1px solid var(--border-color);
            margin-bottom: 15px;
        }
        
        .chart-card h6 {
            margin-bottom: 10px;
            color: var(--accent-cyan);
            font-weight: 600;
        }
        
        /* Override Bootstrap for dark theme */
        .bg-white {
            background-color: var(--bg-card) !important;
        }
        
        .text-muted {
            color: var(--text-secondary) !important;
        }
        
        .shadow-sm {
            box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        }
        
        .rounded {
            border: 1px solid var(--border-color);
        }
        
        .table {
            color: var(--text-primary);
        }
        
        .table-hover tbody tr:hover {
            background-color: var(--bg-tertiary);
            color: var(--text-primary);
        }
        
        .table thead th {
            background-color: var(--bg-tertiary);
            color: var(--accent-cyan);
            border-bottom: 2px solid var(--border-color);
        }
        
        .table td, .table th {
            border-color: var(--border-color);
        }
        
        .modal-content {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }
        
        .modal-header {
            border-bottom-color: var(--border-color);
        }
        
        .btn-close {
            filter: invert(1);
        }
        
        .btn-secondary {
            background-color: var(--bg-tertiary);
            border-color: var(--border-color);
            color: var(--text-primary);
        }
        
        .btn-secondary:hover {
            background-color: var(--border-color);
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary);
        }
        
        strong {
            color: var(--text-primary);
        }
        
        small.text-muted {
            color: var(--text-muted) !important;
        }
        
        /* Tech glow effect on hover */
        .chart-container:hover,
        .chart-card:hover {
            box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 20px var(--glow-blue);
            border-color: var(--accent-blue);
            transition: all 0.3s ease;
        }
        
        /* Search highlight styles */
        .search-highlight {
            background-color: rgba(255, 213, 0, 0.4);
            color: inherit;
            padding: 1px 2px;
            border-radius: 2px;
        }
        
        .search-highlight.current-highlight {
            background-color: rgba(255, 140, 0, 0.8);
            box-shadow: 0 0 4px rgba(255, 140, 0, 0.6);
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }
        
        /* Zoom hint */
        .zoom-hint {
            position: absolute;
            bottom: 5px;
            right: 10px;
            font-size: 10px;
            color: var(--text-muted);
            opacity: 0.7;
        }
        
        /* Stats card */
        .stats-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            border: 1px solid var(--border-color);
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: var(--accent-cyan);
            text-shadow: 0 0 10px rgba(57, 197, 207, 0.3);
        }
"""
    
    def _build_header(self, metadata: Dict) -> str:
        """Build page header with metadata."""
        version = metadata.get('chromeos_version', 'Unknown')
        board = metadata.get('board', 'Unknown')
        timestamp = metadata.get('timestamp', datetime.now().isoformat())
        
        return f"""
        <div class="row">
            <div class="col-12">
                <div class="bg-white rounded p-3 shadow-sm">
                    <h1 class="h3 mb-3">
                        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-file-earmark-text me-2" viewBox="0 0 16 16">
                            <path d="M5.5 7a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1h-5zM5 9.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5z"/>
                            <path d="M9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.5L9.5 0zm0 1v2A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5z"/>
                        </svg>
                        ChromeOS Log Analysis Report
                    </h1>
                    <div class="row">
                        <div class="col-auto">
                            <span class="text-muted">ChromeOS Version:</span>
                            <span class="metadata-value">{html.escape(str(version))}</span>
                        </div>
                        <div class="col-auto">
                            <span class="text-muted">Board:</span>
                            <span class="metadata-value">{html.escape(str(board))}</span>
                        </div>
                        <div class="col-auto">
                            <span class="text-muted">Generated:</span>
                            <span class="metadata-value">{html.escape(str(timestamp))}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>"""
    
    def _build_chart_section(self, chart_config: Dict) -> str:
        """Build chart container section (legacy single chart)."""
        return self._build_multi_chart_section([{'id': 'main', 'title': 'Main', 'config': chart_config, 'type': 'cpu'}])
    
    def _build_multi_chart_section(self, charts: List[Dict], thermal_chart: Dict = None) -> str:
        """
        Build multiple chart containers.
        Groups CPU and Thermal charts by their segment.
        
        Args:
            charts: List of chart configs, each with 'id', 'title', 'config', 'type', 'segment'
            thermal_chart: Optional separate thermal chart (deprecated, use charts list)
        """
        sections_html = ""
        
        # Group charts by segment
        segments = {}
        for chart in charts:
            segment = chart.get('segment', 'unknown')
            if segment not in segments:
                segments[segment] = {'cpu': None, 'thermal': None}
            
            chart_type = chart.get('type', 'cpu')
            if chart_type == 'cpu':
                segments[segment]['cpu'] = chart
            elif chart_type == 'thermal':
                segments[segment]['thermal'] = chart
        
        # Build section for each vmlog segment
        sections_html += """
        <div class="row mt-4">
            <div class="col-12">
                <div class="mb-2 d-flex gap-2 align-items-center flex-wrap">
                    <button class="btn btn-sm btn-outline-secondary" onclick="resetAllZoom()">Reset All Zoom</button>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" id="errorMarkerDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-exclamation-triangle me-1" viewBox="0 0 16 16">
                                <path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.146.146 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.163.163 0 0 1-.054.06.116.116 0 0 1-.066.017H1.146a.115.115 0 0 1-.066-.017.163.163 0 0 1-.054-.06.176.176 0 0 1 .002-.183L7.884 2.073a.147.147 0 0 1 .054-.057zm1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566z"/>
                                <path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995z"/>
                            </svg>
                            <span id="errorMarkerBtnText">Error Markers: Off</span>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-dark" aria-labelledby="errorMarkerDropdown">
                            <li><a class="dropdown-item" href="#" onclick="setErrorMarkerLevel('none'); return false;">Hide All</a></li>
                            <li><a class="dropdown-item" href="#" onclick="setErrorMarkerLevel('critical'); return false;">Critical Only</a></li>
                            <li><a class="dropdown-item" href="#" onclick="setErrorMarkerLevel('error'); return false;">Error & Critical</a></li>
                            <li><a class="dropdown-item" href="#" onclick="setErrorMarkerLevel('all'); return false;">All (incl. Warning)</a></li>
                        </ul>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary" id="ecEventsBtn" onclick="toggleEcEvents()">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-cpu me-1" viewBox="0 0 16 16">
                            <path d="M5 0a.5.5 0 0 1 .5.5V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2A2.5 2.5 0 0 1 14 4.5h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14a2.5 2.5 0 0 1-2.5 2.5v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14A2.5 2.5 0 0 1 2 11.5H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2A2.5 2.5 0 0 1 4.5 2V.5A.5.5 0 0 1 5 0zm-.5 3A1.5 1.5 0 0 0 3 4.5v7A1.5 1.5 0 0 0 4.5 13h7a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 11.5 3h-7zM5 6.5A1.5 1.5 0 0 1 6.5 5h3A1.5 1.5 0 0 1 11 6.5v3A1.5 1.5 0 0 1 9.5 11h-3A1.5 1.5 0 0 1 5 9.5v-3zM6.5 6a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3z"/>
                        </svg>
                        <span id="ecEventsBtnText">EC Events: Off</span>
                    </button>
                </div>
            </div>
        </div>"""
        
        for segment_name in sorted(segments.keys(), key=natural_sort_key):
            segment_charts = segments[segment_name]
            cpu_chart = segment_charts.get('cpu')
            thermal_chart_info = segment_charts.get('thermal')
            
            # Build segment card
            sections_html += f"""
        <div class="row mt-4">
            <div class="col-12">
                <div class="chart-card">
                    <h5 class="mb-3">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-graph-up me-2" viewBox="0 0 16 16">
                            <path fill-rule="evenodd" d="M0 0h1v15h15v1H0V0Zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07Z"/>
                        </svg>
                        vmlog.{html.escape(str(segment_name))}
                    </h5>"""
            
            # Add CPU chart
            if cpu_chart:
                chart_id = cpu_chart.get('id', 'unknown')
                title = cpu_chart.get('title', 'CPU Usage & Frequency')
                sections_html += f"""
                    <div class="chart-section">
                        <h6>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-cpu me-1" viewBox="0 0 16 16">
                                <path d="M5 0a.5.5 0 0 1 .5.5V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2A2.5 2.5 0 0 1 14 4.5h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14a2.5 2.5 0 0 1-2.5 2.5v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14A2.5 2.5 0 0 1 2 11.5H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2A2.5 2.5 0 0 1 4.5 2V.5A.5.5 0 0 1 5 0zm-.5 3A1.5 1.5 0 0 0 3 4.5v7A1.5 1.5 0 0 0 4.5 13h7a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 11.5 3h-7zM5 6.5A1.5 1.5 0 0 1 6.5 5h3A1.5 1.5 0 0 1 11 6.5v3A1.5 1.5 0 0 1 9.5 11h-3A1.5 1.5 0 0 1 5 9.5v-3zM6.5 6a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3z"/>
                            </svg>
                            CPU Usage & Frequency
                        </h6>
                        <div class="chart-container">
                            <canvas id="chart_{chart_id}"></canvas>
                            <span class="zoom-hint">📊 Scroll to zoom • Drag to pan • Double-click to reset</span>
                        </div>
                    </div>"""
            
            # Add Thermal chart (right below CPU chart in same card)
            if thermal_chart_info:
                chart_id = thermal_chart_info.get('id', 'thermal')
                title = thermal_chart_info.get('title', 'Thermal & Fan')
                sections_html += f"""
                    <div class="chart-section mt-4">
                        <h6>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-thermometer-half me-1" viewBox="0 0 16 16">
                                <path d="M9.5 12.5a1.5 1.5 0 1 1-2-1.415V6.5a.5.5 0 0 1 1 0v4.585a1.5 1.5 0 0 1 1 1.415z"/>
                                <path d="M5.5 2.5a2.5 2.5 0 0 1 5 0v7.55a3.5 3.5 0 1 1-5 0V2.5zM8 1a1.5 1.5 0 0 0-1.5 1.5v7.987l-.167.15a2.5 2.5 0 1 0 3.333 0l-.166-.15V2.5A1.5 1.5 0 0 0 8 1z"/>
                            </svg>
                            Thermal & Fan Speed
                        </h6>
                        <div class="chart-container">
                            <canvas id="chart_{chart_id}"></canvas>
                            <span class="zoom-hint">📊 Scroll to zoom • Drag to pan • Double-click to reset</span>
                        </div>
                    </div>"""
            
            sections_html += """
                </div>
            </div>
        </div>"""
        
        return sections_html
    
    def _build_error_summary(self, errors: List[Dict]) -> str:
        """Build error summary table."""
        # Group by severity
        by_severity = {4: [], 3: [], 2: [], 1: []}
        for error in errors:
            sev = error.get('severity', 3)
            by_severity.setdefault(sev, []).append(error)
        
        severity_names = {4: 'Critical', 3: 'Error', 2: 'Warning', 1: 'Info'}
        severity_badges = {4: 'badge-critical', 3: 'badge-error', 2: 'badge-warning', 1: 'bg-secondary'}
        severity_classes = {4: 'severity-critical', 3: 'severity-error', 2: 'severity-warning', 1: 'severity-info'}
        
        # Build summary counts
        summary_html = """<div class="d-flex gap-2 mb-3">"""
        for sev in [4, 3, 2, 1]:
            count = len(by_severity.get(sev, []))
            badge_class = severity_badges[sev]
            summary_html += f'<span class="badge {badge_class}">{severity_names[sev]}: {count}</span>'
        summary_html += "</div>"
        
        # Build error table
        rows_html = ""
        for error in errors[:100]:  # Limit to first 100 errors
            sev = error.get('severity', 3)
            sev_class = severity_classes[sev]
            source = html.escape(error.get('source', 'unknown'))
            msg = html.escape(error.get('message', '')[:100])
            timestamp = error.get('timestamp')
            ts_str = timestamp.strftime('%H:%M:%S') if timestamp else 'N/A'
            
            context_html = ""
            if error.get('context'):
                context = '\n'.join(html.escape(line) for line in error['context'][:5])
                context_html = f'<div class="error-context"><pre>{context}</pre></div>'
            
            rows_html += f"""
            <tr class="error-row" onclick="this.classList.toggle('expanded')">
                <td><span class="{sev_class}">{severity_names[sev]}</span></td>
                <td><code>{ts_str}</code></td>
                <td><small>{source}</small></td>
                <td><small>{msg}</small>{context_html}</td>
            </tr>"""
        
        if len(errors) > 100:
            rows_html += f'<tr><td colspan="4" class="text-center text-muted">... and {len(errors) - 100} more errors</td></tr>'
        
        return f"""
        <div class="bg-white rounded p-3 shadow-sm error-card">
            <h5 class="mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-exclamation-triangle me-2" viewBox="0 0 16 16">
                    <path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.146.146 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.163.163 0 0 1-.054.06.116.116 0 0 1-.066.017H1.146a.115.115 0 0 1-.066-.017.163.163 0 0 1-.054-.06.176.176 0 0 1 .002-.183L7.884 2.073a.147.147 0 0 1 .054-.057zm1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566z"/>
                    <path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995z"/>
                </svg>
                Error Summary ({len(errors)} total)
            </h5>
            {summary_html}
            <div class="mb-2">
                <input type="text" class="form-control form-control-sm" id="errorSearchInput" placeholder="Search errors..." oninput="filterErrors(this.value)">
            </div>
            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                <table class="table table-sm table-hover" id="errorTable">
                    <thead style="position: sticky; top: 0; z-index: 1;">
                        <tr>
                            <th>Severity</th>
                            <th>Time</th>
                            <th>Source</th>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html if rows_html else '<tr><td colspan="4" class="text-center text-muted">No errors detected</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>"""
    
    def _build_log_browser(self, logs: Dict[str, str]) -> str:
        """Build log file browser section."""
        # Create log items
        items_html = ""
        for i, (log_name, content) in enumerate(sorted(logs.items())):
            size = len(content)
            size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} B"
            preview = html.escape(content[:200].replace('\n', ' '))
            
            items_html += f"""
            <div class="log-item p-2 border-bottom" onclick="showLog({i})">
                <div class="d-flex justify-content-between">
                    <strong>{html.escape(log_name)}</strong>
                    <small class="text-muted">{size_str}</small>
                </div>
                <small class="text-muted">{preview}...</small>
            </div>"""
        
        # Store log data as JSON
        log_data_json = json.dumps({str(i): {'name': name, 'content': content} 
                                    for i, (name, content) in enumerate(sorted(logs.items()))},
                                   default=str)
        
        return f"""
        <div class="bg-white rounded p-3 shadow-sm log-browser">
            <h5 class="mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-folder me-2" viewBox="0 0 16 16">
                    <path d="M.54 3.87.5 3a2 2 0 0 1 2-2h3.672a2 2 0 0 1 1.414.586l.828.828A2 2 0 0 0 9.828 3H14a2 2 0 0 1 2 2v2H0V3.87a1.5 1.5 0 0 1 .54-1.13zM0 7v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7H0z"/>
                </svg>
                Log Files ({len(logs)} files)
            </h5>
            <input type="text" class="form-control form-control-sm" id="searchInput" placeholder="Search logs..." oninput="filterLogs(this.value)">
            <div id="logList">
                {items_html if items_html else '<p class="text-muted text-center">No log files available</p>'}
            </div>
        </div>
        <script>
            const logData = {log_data_json};
        </script>"""
    
    def _build_scripts(self, chart_config: Dict) -> str:
        """Build JavaScript section (legacy single chart)."""
        return self._build_multi_chart_scripts([{'id': 'main', 'title': 'Main', 'config': chart_config, 'type': 'cpu'}])
    
    def _build_multi_chart_scripts(self, charts: List[Dict], thermal_chart: Dict = None) -> str:
        """
        Build JavaScript section for multiple charts.
        
        Args:
            charts: List of chart configs, each with 'id', 'title', 'config', 'type'
            thermal_chart: Legacy thermal chart parameter
        """
        # Build chart configs dictionary for JavaScript
        chart_configs_dict = {}
        for chart_info in charts:
            chart_id = chart_info.get('id', 'unknown')
            config = chart_info.get('config', {})
            chart_configs_dict[chart_id] = config
        
        charts_json = json.dumps(chart_configs_dict, default=str)
        thermal_json = json.dumps(thermal_chart, default=str) if thermal_chart else 'null'
        
        return f"""
    <script src="{self.CHARTJS_CDN}"></script>
    <script src="{self.CHARTJS_ADAPTER_CDN}"></script>
    <script src="{self.CHARTJS_ZOOM_CDN}"></script>
    <script src="{self.CHARTJS_ANNOTATION_CDN}"></script>
    <script src="{self.BOOTSTRAP_JS_CDN}"></script>
    <script>
        // Chart configurations
        const chartConfigs = {charts_json};
        const thermalConfig = {thermal_json};
        const chartInstances = {{}};
        const originalAnnotations = {{}};  // Store original annotations for filtering
        const originalEcAnnotations = {{}};  // Store EC event annotations separately
        let currentErrorLevel = 'none';  // Default: hide all error markers
        let ecEventsEnabled = false;  // Default: hide EC events
        
        // Create custom tooltip element for error annotations
        function createErrorTooltip() {{
            const tooltip = document.createElement('div');
            tooltip.id = 'errorTooltip';
            tooltip.style.cssText = `
                position: fixed;
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid #a371f7;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                color: #e6edf3;
                z-index: 10000;
                pointer-events: none;
                display: none;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
            `;
            document.body.appendChild(tooltip);
            return tooltip;
        }}
        
        const errorTooltip = createErrorTooltip();
        
        // Setup hover handlers for annotation tooltips
        function setupAnnotationHover(chart, chartId) {{
            const canvas = chart.canvas;
            
            canvas.addEventListener('mousemove', function(e) {{
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                // Check if hovering over any annotation
                const annotations = chart.options.plugins.annotation?.annotations || {{}};
                let foundAnnotation = null;
                
                for (const [key, annotation] of Object.entries(annotations)) {{
                    // Skip annotations without details
                    if (!annotation.errorDetails && !annotation.ecDetails) continue;
                    
                    // Get the x position of the annotation line
                    const xScale = chart.scales.x;
                    const annotationX = xScale.getPixelForValue(new Date(annotation.xMin));
                    
                    // Check if mouse is near the annotation line (within 8 pixels)
                    if (Math.abs(x - annotationX) < 8 && y > chart.chartArea.top && y < chart.chartArea.bottom) {{
                        foundAnnotation = annotation;
                        break;
                    }}
                }}
                
                if (foundAnnotation) {{
                    let tooltipContent = '';
                    
                    if (foundAnnotation.errorDetails) {{
                        const details = foundAnnotation.errorDetails;
                        tooltipContent = `
                            <div style="margin-bottom: 6px; color: ${{details.severity === 'CRITICAL' ? '#a371f7' : '#f85149'}}; font-weight: bold;">
                                ${{details.severity}} @ ${{details.time}}
                            </div>
                            <div style="margin-bottom: 4px; color: #8b949e;">
                                Source: ${{details.source}}
                            </div>
                            <div style="word-wrap: break-word;">
                                ${{details.message}}
                            </div>
                        `;
                    }} else if (foundAnnotation.ecDetails) {{
                        const details = foundAnnotation.ecDetails;
                        const levelColors = {{1: '#8b949e', 2: '#d29922', 3: '#39c5cf', 4: '#f85149'}};
                        const levelNames = {{1: 'INFO', 2: 'NOTICE', 3: 'NOTABLE', 4: 'CRITICAL'}};
                        tooltipContent = `
                            <div style="margin-bottom: 6px; color: ${{levelColors[details.level] || '#39c5cf'}}; font-weight: bold;">
                                EC: ${{details.type}} @ ${{details.time}}
                            </div>
                            <div style="margin-bottom: 4px; color: #8b949e;">
                                Level: ${{levelNames[details.level] || 'INFO'}}
                            </div>
                            <div style="word-wrap: break-word;">
                                ${{details.message}}
                            </div>
                        `;
                    }}
                    
                    errorTooltip.innerHTML = tooltipContent;
                    errorTooltip.style.display = 'block';
                    errorTooltip.style.left = (e.clientX + 15) + 'px';
                    errorTooltip.style.top = (e.clientY - 10) + 'px';
                    
                    // Adjust position if tooltip goes off screen
                    const tooltipRect = errorTooltip.getBoundingClientRect();
                    if (tooltipRect.right > window.innerWidth) {{
                        errorTooltip.style.left = (e.clientX - tooltipRect.width - 15) + 'px';
                    }}
                    if (tooltipRect.bottom > window.innerHeight) {{
                        errorTooltip.style.top = (e.clientY - tooltipRect.height - 10) + 'px';
                    }}
                }} else {{
                    errorTooltip.style.display = 'none';
                }}
            }});
            
            canvas.addEventListener('mouseleave', function() {{
                errorTooltip.style.display = 'none';
            }});
        }}
        
        // Filter annotations by severity level
        function filterAnnotationsByLevel(annotations, level) {{
            if (level === 'none') return {{}};
            if (level === 'all') return annotations;
            
            const filtered = {{}};
            for (const [key, annotation] of Object.entries(annotations)) {{
                // Skip EC annotations - they are handled separately
                if (key.startsWith('ec_')) continue;
                
                const sevLevel = annotation.errorDetails?.severityLevel;
                if (sevLevel === undefined) continue;
                
                if (level === 'critical' && sevLevel === 4) {{
                    filtered[key] = annotation;
                }} else if (level === 'error' && sevLevel >= 3) {{
                    filtered[key] = annotation;
                }}
            }}
            return filtered;
        }}
        
        // Filter EC annotations
        function filterEcAnnotations(annotations) {{
            const filtered = {{}};
            for (const [key, annotation] of Object.entries(annotations)) {{
                if (key.startsWith('ec_') && annotation.ecDetails) {{
                    filtered[key] = annotation;
                }}
            }}
            return filtered;
        }}
        
        // Combine error and EC annotations based on current settings
        function getCombinedAnnotations(chartId) {{
            const errorAnnotations = filterAnnotationsByLevel(originalAnnotations[chartId] || {{}}, currentErrorLevel);
            const ecAnnotations = ecEventsEnabled ? filterEcAnnotations(originalAnnotations[chartId] || {{}}) : {{}};
            return {{...errorAnnotations, ...ecAnnotations}};
        }}
        
        // Toggle EC events on/off
        function toggleEcEvents() {{
            ecEventsEnabled = !ecEventsEnabled;
            const btnText = document.getElementById('ecEventsBtnText');
            const btn = document.getElementById('ecEventsBtn');
            
            // Update button text and style
            btnText.textContent = ecEventsEnabled ? 'EC Events: On' : 'EC Events: Off';
            btn.classList.remove('btn-outline-secondary', 'btn-outline-info');
            btn.classList.add(ecEventsEnabled ? 'btn-outline-info' : 'btn-outline-secondary');
            
            // Update annotations on all charts
            for (const [chartId, chart] of Object.entries(chartInstances)) {{
                if (chart.options.plugins.annotation) {{
                    chart.options.plugins.annotation.annotations = getCombinedAnnotations(chartId);
                    chart.update('none');  // Update without animation
                }}
            }}
        }}
        
        // Set error marker level from dropdown
        function setErrorMarkerLevel(level) {{
            currentErrorLevel = level;
            const btnText = document.getElementById('errorMarkerBtnText');
            const btn = document.getElementById('errorMarkerDropdown');
            
            // Update button text and style
            const levelLabels = {{
                'none': 'Error Markers: Off',
                'critical': 'Critical Only',
                'error': 'Error & Critical',
                'all': 'All Errors'
            }};
            btnText.textContent = levelLabels[level] || 'Error Markers: Off';
            
            // Update button style based on level
            btn.classList.remove('btn-outline-secondary', 'btn-outline-danger', 'btn-outline-warning', 'btn-outline-info');
            if (level === 'none') {{
                btn.classList.add('btn-outline-secondary');
            }} else if (level === 'critical') {{
                btn.classList.add('btn-outline-danger');
            }} else if (level === 'error') {{
                btn.classList.add('btn-outline-warning');
            }} else {{
                btn.classList.add('btn-outline-info');
            }}
            
            // Update annotations on all charts (combined with EC events)
            for (const [chartId, chart] of Object.entries(chartInstances)) {{
                if (chart.options.plugins.annotation) {{
                    chart.options.plugins.annotation.annotations = getCombinedAnnotations(chartId);
                    chart.update('none');  // Update without animation
                }}
            }}
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            // Initialize all charts from config
            for (const [chartId, config] of Object.entries(chartConfigs)) {{
                const canvas = document.getElementById('chart_' + chartId);
                if (canvas) {{
                    // Store original annotations before creating chart
                    if (config.options?.plugins?.annotation?.annotations) {{
                        originalAnnotations[chartId] = JSON.parse(JSON.stringify(config.options.plugins.annotation.annotations));
                        // Default: hide all error markers
                        config.options.plugins.annotation.annotations = {{}};
                    }}
                    
                    chartInstances[chartId] = new Chart(canvas.getContext('2d'), config);
                    
                    // Setup hover handlers for annotations
                    setupAnnotationHover(chartInstances[chartId], chartId);
                    
                    // Add double-click to reset zoom
                    canvas.addEventListener('dblclick', function() {{
                        if (chartInstances[chartId] && chartInstances[chartId].resetZoom) {{
                            chartInstances[chartId].resetZoom();
                        }}
                    }});
                }}
            }}
            
            // Initialize legacy thermal chart (if separate)
            if (thermalConfig) {{
                const thermalCanvas = document.getElementById('chart_thermal');
                if (thermalCanvas && !chartInstances['thermal']) {{
                    chartInstances['thermal'] = new Chart(thermalCanvas.getContext('2d'), thermalConfig);
                    
                    // Add double-click to reset zoom
                    thermalCanvas.addEventListener('dblclick', function() {{
                        if (chartInstances['thermal'] && chartInstances['thermal'].resetZoom) {{
                            chartInstances['thermal'].resetZoom();
                        }}
                    }});
                }}
            }}
        }});
        
        function resetAllZoom() {{
            for (const chart of Object.values(chartInstances)) {{
                if (chart && chart.resetZoom) {{
                    chart.resetZoom();
                }}
            }}
        }}
        
        function showLog(index) {{
            const data = logData[index];
            if (data) {{
                document.getElementById('logModalTitle').textContent = data.name;
                document.getElementById('logModalContent').textContent = data.content;
                document.getElementById('logContentSearch').value = '';
                document.getElementById('searchResultCount').textContent = '';
                currentHighlightIndex = -1;
                
                // If there's a search query in the log list, auto-search in content
                const listSearchQuery = document.getElementById('searchInput').value;
                if (listSearchQuery) {{
                    document.getElementById('logContentSearch').value = listSearchQuery;
                    setTimeout(() => highlightInLog(listSearchQuery), 100);
                }}
                
                const modal = new bootstrap.Modal(document.getElementById('logModal'));
                modal.show();
            }}
        }}
        
        let currentHighlightIndex = -1;
        let totalHighlights = 0;
        let originalLogContent = '';
        
        function highlightInLog(query) {{
            const contentEl = document.getElementById('logModalContent');
            const countEl = document.getElementById('searchResultCount');
            
            // Store original content on first call or restore it
            if (!originalLogContent || !query) {{
                originalLogContent = contentEl.textContent;
            }}
            
            if (!query || query.length < 2) {{
                contentEl.textContent = originalLogContent;
                countEl.textContent = '';
                currentHighlightIndex = -1;
                totalHighlights = 0;
                return;
            }}
            
            // Escape special HTML characters in original content
            const escaped = originalLogContent
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            // Escape regex special characters in query
            const escapedQuery = query.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
            const regex = new RegExp(`(${{escapedQuery}})`, 'gi');
            
            // Count matches
            const matches = originalLogContent.match(new RegExp(escapedQuery, 'gi'));
            totalHighlights = matches ? matches.length : 0;
            
            if (totalHighlights === 0) {{
                contentEl.textContent = originalLogContent;
                countEl.textContent = 'No matches';
                currentHighlightIndex = -1;
                return;
            }}
            
            // Highlight matches
            let matchIndex = 0;
            const highlighted = escaped.replace(regex, (match) => {{
                return `<mark class="search-highlight" data-index="${{matchIndex++}}">${{match}}</mark>`;
            }});
            
            contentEl.innerHTML = highlighted;
            countEl.textContent = `${{totalHighlights}} matches`;
            
            // Navigate to first match
            currentHighlightIndex = -1;
            navigateHighlight(1);
        }}
        
        function navigateHighlight(direction) {{
            if (totalHighlights === 0) return;
            
            const highlights = document.querySelectorAll('.search-highlight');
            
            // Remove current highlight
            if (currentHighlightIndex >= 0 && highlights[currentHighlightIndex]) {{
                highlights[currentHighlightIndex].classList.remove('current-highlight');
            }}
            
            // Calculate new index
            currentHighlightIndex += direction;
            if (currentHighlightIndex >= totalHighlights) currentHighlightIndex = 0;
            if (currentHighlightIndex < 0) currentHighlightIndex = totalHighlights - 1;
            
            // Highlight current and scroll to it
            if (highlights[currentHighlightIndex]) {{
                highlights[currentHighlightIndex].classList.add('current-highlight');
                highlights[currentHighlightIndex].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }}
            
            // Update count display
            document.getElementById('searchResultCount').textContent = 
                `${{currentHighlightIndex + 1}} / ${{totalHighlights}}`;
        }}
        
        function filterLogs(query) {{
            const items = document.querySelectorAll('.log-item');
            const lowerQuery = query.toLowerCase();
            
            if (!query) {{
                // Show all if no query
                items.forEach(item => item.style.display = '');
                return;
            }}
            
            // Search in both displayed text AND full content
            items.forEach((item, index) => {{
                const displayText = item.textContent.toLowerCase();
                const fullContent = logData[index]?.content?.toLowerCase() || '';
                const matches = displayText.includes(lowerQuery) || fullContent.includes(lowerQuery);
                item.style.display = matches ? '' : 'none';
                
                // Add indicator if match is in content but not visible in preview
                const matchBadge = item.querySelector('.content-match-badge');
                if (matches && !displayText.includes(lowerQuery) && fullContent.includes(lowerQuery)) {{
                    if (!matchBadge) {{
                        const badge = document.createElement('span');
                        badge.className = 'content-match-badge badge bg-info ms-2';
                        badge.textContent = 'match in content';
                        badge.style.fontSize = '10px';
                        item.querySelector('strong').appendChild(badge);
                    }}
                }} else if (matchBadge) {{
                    matchBadge.remove();
                }}
            }});
        }}
        
        function filterErrors(query) {{
            const rows = document.querySelectorAll('#errorTable tbody tr.error-row');
            const lowerQuery = query.toLowerCase();
            
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(lowerQuery) ? '' : 'none';
            }});
        }}
    </script>"""
    
    def save_report(self, filepath: str, parsed_data: Dict, chart_config: Dict,
                    errors: List[Dict], metadata: Dict = None) -> str:
        """
        Generate and save HTML report to file (legacy single chart).
        
        Args:
            filepath: Output file path
            parsed_data: All parsed log data
            chart_config: Chart.js configuration
            errors: List of detected errors
            metadata: Additional metadata
            
        Returns:
            Path to saved file
        """
        html_content = self.build_report(parsed_data, chart_config, errors, metadata)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def save_multi_chart_report(self, filepath: str, parsed_data: Dict, 
                                 charts: List[Dict], errors: List[Dict],
                                 metadata: Dict = None, thermal_chart: Dict = None) -> str:
        """
        Generate and save HTML report with multiple charts.
        
        Args:
            filepath: Output file path
            parsed_data: All parsed log data
            charts: List of chart configs with 'id', 'title', 'config', 'type'
            errors: List of detected errors
            metadata: Additional metadata
            thermal_chart: Legacy thermal temperature chart config
            
        Returns:
            Path to saved file
        """
        html_content = self.build_multi_chart_report(
            parsed_data, charts, errors, metadata, thermal_chart
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
