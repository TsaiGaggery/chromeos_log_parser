"""
ChartGenerator - Generate Chart.js configuration for vmlog and thermal visualization.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional


class ChartGenerator:
    """Generates Chart.js configuration for vmlog and thermal visualization."""
    
    # Dark theme colors
    DARK_THEME = {
        'text_primary': '#e6edf3',
        'text_secondary': '#8b949e',
        'grid_color': 'rgba(48, 54, 61, 0.8)',
        'border_color': '#30363d',
    }
    
    # Color scheme for different metrics (brighter for dark theme)
    METRIC_COLORS = {
        'cpuusage': {'border': 'rgb(88, 166, 255)', 'background': 'rgba(88, 166, 255, 0.15)'},
        'cpufreq0': {'border': 'rgb(255, 107, 129)', 'background': 'rgba(255, 107, 129, 0.15)'},
        'cpufreq1': {'border': 'rgb(63, 185, 80)', 'background': 'rgba(63, 185, 80, 0.15)'},
        'cpufreq2': {'border': 'rgb(210, 153, 34)', 'background': 'rgba(210, 153, 34, 0.15)'},
        'cpufreq3': {'border': 'rgb(163, 113, 247)', 'background': 'rgba(163, 113, 247, 0.15)'},
        'pgmajfault': {'border': 'rgb(255, 159, 64)', 'background': 'rgba(255, 159, 64, 0.15)'},
        'pswpin': {'border': 'rgb(201, 203, 207)', 'background': 'rgba(201, 203, 207, 0.15)'},
        'pswpout': {'border': 'rgb(139, 148, 158)', 'background': 'rgba(139, 148, 158, 0.15)'},
    }
    
    # Color palette for thermal sensors (brighter for dark theme)
    THERMAL_COLORS = [
        {'border': 'rgb(255, 107, 129)', 'background': 'rgba(255, 107, 129, 0.15)'},   # red
        {'border': 'rgb(88, 166, 255)', 'background': 'rgba(88, 166, 255, 0.15)'},     # blue
        {'border': 'rgb(210, 153, 34)', 'background': 'rgba(210, 153, 34, 0.15)'},     # yellow
        {'border': 'rgb(57, 197, 207)', 'background': 'rgba(57, 197, 207, 0.15)'},     # cyan
        {'border': 'rgb(163, 113, 247)', 'background': 'rgba(163, 113, 247, 0.15)'},   # purple
        {'border': 'rgb(255, 159, 64)', 'background': 'rgba(255, 159, 64, 0.15)'},     # orange
        {'border': 'rgb(139, 148, 158)', 'background': 'rgba(139, 148, 158, 0.15)'},   # gray
        {'border': 'rgb(99, 102, 255)', 'background': 'rgba(99, 102, 255, 0.15)'},     # indigo
        {'border': 'rgb(255, 110, 199)', 'background': 'rgba(255, 110, 199, 0.15)'},   # pink
        {'border': 'rgb(63, 185, 80)', 'background': 'rgba(63, 185, 80, 0.15)'},       # green
    ]
    
    # Error severity colors
    SEVERITY_COLORS = {
        1: 'rgba(139, 148, 158, 0.8)',   # info - gray
        2: 'rgba(210, 153, 34, 0.8)',    # warning - yellow
        3: 'rgba(248, 81, 73, 0.8)',     # error - red
        4: 'rgba(163, 113, 247, 0.8)',   # critical - purple
    }
    
    def __init__(self):
        """Initialize the chart generator."""
        pass
    
    def _get_dark_scale_options(self) -> Dict:
        """Get dark theme options for scales."""
        return {
            'ticks': {
                'color': self.DARK_THEME['text_secondary'],
            },
            'title': {
                'color': self.DARK_THEME['text_primary'],
            },
            'grid': {
                'color': self.DARK_THEME['grid_color'],
            },
        }
    
    def create_chart_config(self, vmlog_data: List[Dict], errors: List[Dict] = None,
                            metrics: List[str] = None) -> Dict:
        """
        Create complete Chart.js configuration.
        
        Args:
            vmlog_data: Parsed vmlog entries
            errors: Error entries with timestamps
            metrics: Specific metrics to include (default: all)
            
        Returns:
            Chart.js configuration dictionary
        """
        if not vmlog_data:
            return self._empty_chart_config()
        
        # Default metrics if not specified
        if metrics is None:
            metrics = ['cpuusage', 'cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3']
        
        # Create datasets
        datasets = []
        for metric in metrics:
            dataset = self._create_dataset(vmlog_data, metric)
            if dataset:
                datasets.append(dataset)
        
        # Create error annotations
        annotations = {}
        if errors:
            annotations = self._create_error_annotations(errors)
        
        # Build complete config
        config = {
            'type': 'line',
            'data': {
                'datasets': datasets
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'interaction': {
                    'mode': 'index',
                    'intersect': False,
                },
                'plugins': {
                    'title': {
                        'display': True,
                        'text': 'ChromeOS vmlog Metrics Timeline',
                        'color': self.DARK_THEME['text_primary'],
                    },
                    'legend': {
                        'position': 'top',
                        'labels': {
                            'color': self.DARK_THEME['text_primary'],
                        },
                    },
                    'tooltip': {
                        'callbacks': {}
                    },
                    'zoom': {
                        'pan': {
                            'enabled': True,
                            'mode': 'x',
                        },
                        'zoom': {
                            'wheel': {
                                'enabled': True,
                            },
                            'pinch': {
                                'enabled': True,
                            },
                            'mode': 'x',
                        }
                    },
                    'annotation': {
                        'annotations': annotations
                    }
                },
                'scales': self._create_scales(metrics),
            }
        }
        
        return config
    
    def _create_dataset(self, vmlog_data: List[Dict], metric: str) -> Optional[Dict]:
        """
        Create single Chart.js dataset for one metric.
        
        Args:
            vmlog_data: Parsed vmlog entries
            metric: Metric name
            
        Returns:
            Chart.js dataset configuration
        """
        # Extract data points
        data_points = []
        for entry in vmlog_data:
            value = entry.get(metric)
            timestamp = entry.get('timestamp')
            
            if value is not None and timestamp is not None:
                # Convert cpuusage from 0-1 to 0-100%
                if metric == 'cpuusage':
                    value = value * 100
                # Format timestamp for Chart.js time axis
                data_points.append({
                    'x': timestamp.isoformat(),
                    'y': value
                })
        
        if not data_points:
            return None
        
        # Get colors
        colors = self.METRIC_COLORS.get(metric, {
            'border': 'rgb(128, 128, 128)',
            'background': 'rgba(128, 128, 128, 0.1)'
        })
        
        # Determine which y-axis to use
        y_axis_id = 'y'
        if metric.startswith('cpufreq'):
            y_axis_id = 'y1'
        elif metric in ['pgmajfault', 'pswpin', 'pswpout']:
            y_axis_id = 'y2'
        
        dataset = {
            'label': self._format_metric_label(metric),
            'data': data_points,
            'borderColor': colors['border'],
            'backgroundColor': colors['background'],
            'fill': False,
            'tension': 0.1,
            'pointRadius': 0,
            'borderWidth': 1.5,
            'yAxisID': y_axis_id,
        }
        
        return dataset
    
    def _create_error_annotations(self, errors: List[Dict]) -> Dict:
        """
        Create Chart.js annotation objects for errors.
        Shows vertical lines for Critical (severity 4) and Error (severity 3) events.
        
        Args:
            errors: List of error dictionaries
            
        Returns:
            Dictionary of annotation configurations
        """
        annotations = {}
        
        # Limit annotations to avoid performance issues
        max_annotations = 100
        
        # Prioritize critical errors, then regular errors
        critical_errors = [e for e in errors if e.get('severity', 0) == 4]
        regular_errors = [e for e in errors if e.get('severity', 0) == 3]
        
        # Take critical first, then fill with regular errors
        selected_errors = critical_errors[:max_annotations]
        remaining_slots = max_annotations - len(selected_errors)
        if remaining_slots > 0:
            selected_errors.extend(regular_errors[:remaining_slots])
        
        for i, error in enumerate(selected_errors):
            timestamp = error.get('timestamp') or error.get('vmlog_timestamp')
            if not timestamp:
                continue
            
            severity = error.get('severity', 3)
            color = self.SEVERITY_COLORS.get(severity, self.SEVERITY_COLORS[3])
            
            # Critical errors get thicker lines and label on hover
            is_critical = severity == 4
            
            # Get error message for hover display
            error_message = error.get('message', 'Unknown error')[:80]
            error_source = error.get('source', 'unknown')
            severity_name = 'CRITICAL' if is_critical else 'ERROR'
            
            annotation_id = f'error_{i}'
            annotations[annotation_id] = {
                'type': 'line',
                'xMin': timestamp.isoformat(),
                'xMax': timestamp.isoformat(),
                'borderColor': color,
                'borderWidth': 3 if is_critical else 2,
                'borderDash': [6, 4] if is_critical else [4, 4],  # All dashed, critical slightly longer dashes
                'label': {
                    'display': True,
                    'content': 'CRITICAL' if is_critical else 'ERR',
                    'position': 'start',
                    'backgroundColor': color,
                    'color': '#ffffff',
                    'font': {
                        'size': 9,
                        'weight': 'bold' if is_critical else 'normal',
                    },
                    'padding': 2,
                },
                # Store error details for hover tooltip
                'errorDetails': {
                    'message': error_message,
                    'source': error_source,
                    'severity': severity_name,
                    'severityLevel': severity,  # Add numeric level for filtering
                    'time': timestamp.strftime('%H:%M:%S') if hasattr(timestamp, 'strftime') else str(timestamp),
                }
            }
        
        return annotations
    
    def _create_scales(self, metrics: List[str]) -> Dict:
        """
        Create multi-axis scale configuration.
        
        Args:
            metrics: List of metrics being displayed
            
        Returns:
            Scale configuration dictionary
        """
        dark_opts = self._get_dark_scale_options()
        
        scales = {
            'x': {
                'type': 'time',
                'time': {
                    'unit': 'minute',
                    'displayFormats': {
                        'minute': 'HH:mm',
                        'hour': 'HH:mm',
                    }
                },
                'title': {
                    'display': True,
                    'text': 'Time',
                    'color': self.DARK_THEME['text_primary'],
                },
                'ticks': {
                    'color': self.DARK_THEME['text_secondary'],
                },
                'grid': {
                    'color': self.DARK_THEME['grid_color'],
                },
            },
            'y': {
                'type': 'linear',
                'display': True,
                'position': 'left',
                'title': {
                    'display': True,
                    'text': 'CPU Usage (%)',
                    'color': self.DARK_THEME['text_primary'],
                },
                'min': 0,
                'max': 100,
                'ticks': {
                    'color': self.DARK_THEME['text_secondary'],
                },
                'grid': {
                    'color': self.DARK_THEME['grid_color'],
                },
            }
        }
        
        # Add frequency axis if needed
        if any(m.startswith('cpufreq') for m in metrics):
            scales['y1'] = {
                'type': 'linear',
                'display': True,
                'position': 'right',
                'title': {
                    'display': True,
                    'text': 'CPU Frequency (MHz)',
                    'color': self.DARK_THEME['text_primary'],
                },
                'ticks': {
                    'color': self.DARK_THEME['text_secondary'],
                },
                'grid': {
                    'drawOnChartArea': False,
                    'color': self.DARK_THEME['grid_color'],
                },
                # Scale will be determined by data
            }
        
        # Add page fault axis if needed
        if any(m in ['pgmajfault', 'pswpin', 'pswpout'] for m in metrics):
            scales['y2'] = {
                'type': 'linear',
                'display': True,
                'position': 'right',
                'title': {
                    'display': True,
                    'text': 'Page Operations',
                    'color': self.DARK_THEME['text_primary'],
                },
                'ticks': {
                    'color': self.DARK_THEME['text_secondary'],
                },
                'grid': {
                    'drawOnChartArea': False,
                    'color': self.DARK_THEME['grid_color'],
                },
                'offset': True,
            }
        
        return scales
    
    def _format_metric_label(self, metric: str) -> str:
        """
        Format metric name for display.
        
        Args:
            metric: Metric name
            
        Returns:
            Formatted label
        """
        labels = {
            'cpuusage': 'CPU Usage',
            'cpufreq0': 'CPU 0 Freq',
            'cpufreq1': 'CPU 1 Freq',
            'cpufreq2': 'CPU 2 Freq',
            'cpufreq3': 'CPU 3 Freq',
            'pgmajfault': 'Page Faults',
            'pgmajfault_f': 'Page Faults (File)',
            'pgmajfault_a': 'Page Faults (Anon)',
            'pswpin': 'Swap In',
            'pswpout': 'Swap Out',
        }
        return labels.get(metric, metric)
    
    def _empty_chart_config(self, message: str = "No data available") -> Dict:
        """Return empty chart configuration."""
        return {
            'type': 'line',
            'data': {'datasets': []},
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': message
                    }
                }
            }
        }
    
    def create_cpu_usage_chart(self, vmlog_data: List[Dict], errors: List[Dict] = None,
                               chart_id: str = "cpu_chart", 
                               title: str = "CPU Usage & Frequency") -> Dict:
        """
        Create chart focusing on CPU usage and frequency.
        
        Args:
            vmlog_data: Parsed vmlog entries
            errors: Error entries with timestamps
            chart_id: Unique ID for this chart
            title: Chart title
            
        Returns:
            Chart.js configuration dictionary with id and title
        """
        if not vmlog_data:
            return {
                'id': chart_id,
                'title': title,
                'config': self._empty_chart_config("No vmlog data available")
            }
        
        metrics = ['cpuusage', 'cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3']
        
        # Create datasets
        datasets = []
        for metric in metrics:
            dataset = self._create_dataset(vmlog_data, metric)
            if dataset:
                datasets.append(dataset)
        
        # Create error annotations
        annotations = {}
        if errors:
            annotations = self._create_error_annotations(errors)
        
        config = {
            'type': 'line',
            'data': {
                'datasets': datasets
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'interaction': {
                    'mode': 'index',
                    'intersect': False,
                },
                'plugins': {
                    'title': {
                        'display': True,
                        'text': title,
                        'color': self.DARK_THEME['text_primary'],
                    },
                    'legend': {
                        'position': 'top',
                        'labels': {
                            'color': self.DARK_THEME['text_primary'],
                        },
                    },
                    'zoom': {
                        'pan': {
                            'enabled': True,
                            'mode': 'x',
                        },
                        'zoom': {
                            'wheel': {
                                'enabled': True,
                            },
                            'pinch': {
                                'enabled': True,
                            },
                            'mode': 'x',
                        }
                    },
                    'annotation': {
                        'annotations': annotations
                    }
                },
                'scales': self._create_scales(metrics),
            }
        }
        
        return {
            'id': chart_id,
            'title': title,
            'config': config
        }
    
    def create_cpu_frequency_chart(self, vmlog_data: List[Dict], errors: List[Dict] = None) -> Dict:
        """Create chart focusing on CPU frequencies."""
        return self.create_chart_config(vmlog_data, errors, 
                                        metrics=['cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3'])
    
    def create_memory_chart(self, vmlog_data: List[Dict], errors: List[Dict] = None) -> Dict:
        """Create chart focusing on memory metrics."""
        return self.create_chart_config(vmlog_data, errors,
                                        metrics=['pgmajfault', 'pswpin', 'pswpout'])
    
    def to_json(self, config: Dict) -> str:
        """
        Convert chart config to JSON string.
        
        Args:
            config: Chart configuration dictionary
            
        Returns:
            JSON string
        """
        return json.dumps(config, default=str, indent=2)
    
    def sample_data(self, vmlog_data: List[Dict], max_points: int = 5000) -> List[Dict]:
        """
        Sample vmlog data if it exceeds max_points.
        
        Args:
            vmlog_data: Original vmlog data
            max_points: Maximum data points to keep
            
        Returns:
            Sampled or original data
        """
        if len(vmlog_data) <= max_points:
            return vmlog_data
        
        # Calculate sampling interval
        step = len(vmlog_data) / max_points
        sampled = []
        
        i = 0.0
        while i < len(vmlog_data):
            sampled.append(vmlog_data[int(i)])
            i += step
        
        return sampled
    
    def create_thermal_chart(self, temp_data: List[Dict], 
                             chart_id: str = "thermal_chart",
                             title: str = "Thermal & Fan") -> Dict:
        """
        Create chart for thermal temperature and fan speed data.
        Uses dual Y-axis: left for temperature (°C), right for fan speed (RPM).
        
        Args:
            temp_data: List of temp_logger entries
            chart_id: Unique ID for this chart
            title: Chart title
            
        Returns:
            Chart.js configuration dictionary with id and title
        """
        if not temp_data:
            return {
                'id': chart_id,
                'title': title,
                'config': self._empty_chart_config("No thermal data available")
            }
        
        # Collect all sensor names
        all_temp_sensors = set()
        all_fan_sensors = set()
        for entry in temp_data:
            all_temp_sensors.update(entry.get('temperatures', {}).keys())
            all_fan_sensors.update(entry.get('fans', {}).keys())
        
        temp_sensors = sorted(all_temp_sensors)
        fan_sensors = sorted(all_fan_sensors)
        
        datasets = []
        color_idx = 0
        
        # Create datasets for temperature sensors (left Y axis)
        for sensor in temp_sensors:
            data_points = []
            for entry in temp_data:
                timestamp = entry.get('timestamp')
                temp = entry.get('temperatures', {}).get(sensor)
                
                if timestamp and temp is not None:
                    data_points.append({
                        'x': timestamp.isoformat(),
                        'y': temp
                    })
            
            if data_points:
                colors = self.THERMAL_COLORS[color_idx % len(self.THERMAL_COLORS)]
                color_idx += 1
                datasets.append({
                    'label': f'{sensor} (°C)',
                    'data': data_points,
                    'borderColor': colors['border'],
                    'backgroundColor': colors['background'],
                    'fill': False,
                    'tension': 0.1,
                    'pointRadius': 0,
                    'borderWidth': 1.5,
                    'yAxisID': 'y',  # Left Y axis for temperature
                })
        
        # Create datasets for fan sensors (right Y axis)
        for sensor in fan_sensors:
            data_points = []
            for entry in temp_data:
                timestamp = entry.get('timestamp')
                rpm = entry.get('fans', {}).get(sensor)
                
                if timestamp and rpm is not None:
                    data_points.append({
                        'x': timestamp.isoformat(),
                        'y': rpm
                    })
            
            if data_points:
                # Use distinct colors for fan (darker/different shades)
                fan_colors = {
                    'border': 'rgb(128, 128, 128)',  # Gray
                    'background': 'rgba(128, 128, 128, 0.1)'
                }
                if color_idx < len(self.THERMAL_COLORS):
                    fan_colors = self.THERMAL_COLORS[color_idx % len(self.THERMAL_COLORS)]
                color_idx += 1
                
                datasets.append({
                    'label': f'{sensor} (RPM)',
                    'data': data_points,
                    'borderColor': fan_colors['border'],
                    'backgroundColor': fan_colors['background'],
                    'fill': False,
                    'tension': 0.1,
                    'pointRadius': 0,
                    'borderWidth': 2,
                    'borderDash': [5, 5],  # Dashed line to distinguish from temperature
                    'yAxisID': 'y1',  # Right Y axis for fan speed
                })
        
        # Build scales config - always include both axes
        scales = {
            'x': {
                'type': 'time',
                'time': {
                    'unit': 'minute',
                    'displayFormats': {
                        'minute': 'HH:mm',
                        'hour': 'HH:mm',
                    }
                },
                'title': {
                    'display': True,
                    'text': 'Time',
                    'color': self.DARK_THEME['text_primary'],
                },
                'ticks': {
                    'color': self.DARK_THEME['text_secondary'],
                },
                'grid': {
                    'color': self.DARK_THEME['grid_color'],
                },
            },
            'y': {
                'type': 'linear',
                'display': True,
                'position': 'left',
                'title': {
                    'display': True,
                    'text': 'Temperature (°C)',
                    'color': self.DARK_THEME['text_primary'],
                },
                'min': 0,
                'ticks': {
                    'color': self.DARK_THEME['text_secondary'],
                },
                'grid': {
                    'color': self.DARK_THEME['grid_color'],
                },
            }
        }
        
        # Add right Y axis for fan speed if we have fan data
        if fan_sensors:
            scales['y1'] = {
                'type': 'linear',
                'display': True,
                'position': 'right',
                'title': {
                    'display': True,
                    'text': 'Fan Speed (RPM)',
                    'color': self.DARK_THEME['text_primary'],
                },
                'min': 0,
                'ticks': {
                    'color': self.DARK_THEME['text_secondary'],
                },
                'grid': {
                    'drawOnChartArea': False,  # Don't draw grid lines on chart area
                    'color': self.DARK_THEME['grid_color'],
                },
            }
        
        config = {
            'type': 'line',
            'data': {
                'datasets': datasets
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'interaction': {
                    'mode': 'index',
                    'intersect': False,
                },
                'plugins': {
                    'title': {
                        'display': True,
                        'text': title,
                        'color': self.DARK_THEME['text_primary'],
                    },
                    'legend': {
                        'position': 'top',
                        'labels': {
                            'color': self.DARK_THEME['text_primary'],
                        },
                    },
                    'zoom': {
                        'pan': {
                            'enabled': True,
                            'mode': 'x',
                        },
                        'zoom': {
                            'wheel': {
                                'enabled': True,
                            },
                            'pinch': {
                                'enabled': True,
                            },
                            'mode': 'x',
                        }
                    },
                },
                'scales': scales,
            }
        }
        
        return {
            'id': chart_id,
            'title': title,
            'config': config
        }
    
    def create_vmlog_cpu_chart(self, vmlog_data: List[Dict], errors: List[Dict] = None,
                               title: str = "CPU Usage & Frequency") -> Dict:
        """
        Create combined CPU usage and frequency chart.
        
        Args:
            vmlog_data: Parsed vmlog entries
            errors: Error entries with timestamps
            title: Chart title
            
        Returns:
            Chart.js configuration dictionary
        """
        if not vmlog_data:
            return self._empty_chart_config("No vmlog data available")
        
        metrics = ['cpuusage', 'cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3']
        
        # Create datasets
        datasets = []
        for metric in metrics:
            dataset = self._create_dataset(vmlog_data, metric)
            if dataset:
                datasets.append(dataset)
        
        # Create error annotations
        annotations = {}
        if errors:
            annotations = self._create_error_annotations(errors)
        
        config = {
            'type': 'line',
            'data': {
                'datasets': datasets
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'interaction': {
                    'mode': 'index',
                    'intersect': False,
                },
                'plugins': {
                    'title': {
                        'display': True,
                        'text': title,
                        'color': self.DARK_THEME['text_primary'],
                    },
                    'legend': {
                        'position': 'top',
                        'labels': {
                            'color': self.DARK_THEME['text_primary'],
                        },
                    },
                    'zoom': {
                        'pan': {
                            'enabled': True,
                            'mode': 'x',
                        },
                        'zoom': {
                            'wheel': {
                                'enabled': True,
                            },
                            'pinch': {
                                'enabled': True,
                            },
                            'mode': 'x',
                        }
                    },
                    'annotation': {
                        'annotations': annotations
                    }
                },
                'scales': self._create_scales(metrics),
            }
        }
        
        return config
    
    def create_multiple_vmlog_charts(self, vmlog_by_file: Dict[str, List[Dict]], 
                                      errors: List[Dict] = None) -> Dict[str, Dict]:
        """
        Create separate charts for each vmlog file segment.
        
        Args:
            vmlog_by_file: Dictionary mapping vmlog filename to parsed entries
            errors: Error entries with timestamps
            
        Returns:
            Dictionary mapping chart ID to Chart.js configuration
        """
        charts = {}
        
        for filename, vmlog_data in vmlog_by_file.items():
            if not vmlog_data:
                continue
            
            # Get time range for this segment
            timestamps = [e.get('timestamp') for e in vmlog_data if e.get('timestamp')]
            if timestamps:
                start = min(timestamps).strftime('%m/%d %H:%M')
                end = max(timestamps).strftime('%H:%M')
                title = f"{filename} ({start} - {end})"
            else:
                title = filename
            
            # Filter errors for this time range
            segment_errors = []
            if errors and timestamps:
                min_ts = min(timestamps)
                max_ts = max(timestamps)
                segment_errors = [e for e in errors 
                                 if e.get('timestamp') and min_ts <= e['timestamp'] <= max_ts]
            
            chart_id = filename.replace('.', '_').replace('/', '_')
            charts[chart_id] = self.create_vmlog_cpu_chart(vmlog_data, segment_errors, title)
        
        return charts
