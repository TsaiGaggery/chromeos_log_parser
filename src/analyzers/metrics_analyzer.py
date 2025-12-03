"""
MetricsAnalyzer - Analyze vmlog metrics for statistics and anomalies.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import statistics


class MetricsAnalyzer:
    """Analyzes vmlog metrics for statistics and anomalies."""
    
    # Metric definitions with expected ranges
    METRIC_DEFINITIONS = {
        'cpuusage': {'min': 0, 'max': 1, 'unit': '%', 'description': 'CPU Usage'},
        'pgmajfault': {'min': 0, 'max': None, 'unit': 'count', 'description': 'Major Page Faults'},
        'pgmajfault_f': {'min': 0, 'max': None, 'unit': 'count', 'description': 'Major Page Faults (File)'},
        'pgmajfault_a': {'min': 0, 'max': None, 'unit': 'count', 'description': 'Major Page Faults (Anonymous)'},
        'pswpin': {'min': 0, 'max': None, 'unit': 'pages', 'description': 'Pages Swapped In'},
        'pswpout': {'min': 0, 'max': None, 'unit': 'pages', 'description': 'Pages Swapped Out'},
        'cpufreq0': {'min': 0, 'max': None, 'unit': 'kHz', 'description': 'CPU 0 Frequency'},
        'cpufreq1': {'min': 0, 'max': None, 'unit': 'kHz', 'description': 'CPU 1 Frequency'},
        'cpufreq2': {'min': 0, 'max': None, 'unit': 'kHz', 'description': 'CPU 2 Frequency'},
        'cpufreq3': {'min': 0, 'max': None, 'unit': 'kHz', 'description': 'CPU 3 Frequency'},
    }
    
    def __init__(self, spike_threshold: float = 2.0):
        """
        Initialize the analyzer.
        
        Args:
            spike_threshold: Standard deviations to consider a spike
        """
        self.spike_threshold = spike_threshold
    
    def calculate_stats(self, vmlog_data: List[Dict]) -> Dict:
        """
        Calculate statistics for all vmlog metrics.
        
        Args:
            vmlog_data: List of parsed vmlog entries
            
        Returns:
            Dictionary with statistics for each metric
        """
        if not vmlog_data:
            return {}
        
        stats = {}
        metrics = list(self.METRIC_DEFINITIONS.keys())
        
        for metric in metrics:
            values = [entry.get(metric) for entry in vmlog_data if entry.get(metric) is not None]
            if not values:
                continue
            
            metric_stats = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
            }
            
            if len(values) >= 2:
                metric_stats['stdev'] = statistics.stdev(values)
                metric_stats['median'] = statistics.median(values)
            else:
                metric_stats['stdev'] = 0
                metric_stats['median'] = values[0]
            
            if len(values) >= 4:
                sorted_values = sorted(values)
                n = len(sorted_values)
                metric_stats['p25'] = sorted_values[n // 4]
                metric_stats['p75'] = sorted_values[3 * n // 4]
                metric_stats['p90'] = sorted_values[int(n * 0.9)]
                metric_stats['p99'] = sorted_values[int(n * 0.99)]
            
            # Add metadata
            metric_stats['unit'] = self.METRIC_DEFINITIONS[metric]['unit']
            metric_stats['description'] = self.METRIC_DEFINITIONS[metric]['description']
            
            stats[metric] = metric_stats
        
        return stats
    
    def detect_spikes(self, vmlog_data: List[Dict], metric: str) -> List[Dict]:
        """
        Detect unusual spikes in a metric.
        
        Args:
            vmlog_data: List of parsed vmlog entries
            metric: Metric name to analyze
            
        Returns:
            List of spike events
        """
        values = [(i, entry.get(metric), entry.get('timestamp')) 
                  for i, entry in enumerate(vmlog_data) 
                  if entry.get(metric) is not None]
        
        if len(values) < 10:
            return []
        
        # Calculate mean and stdev
        metric_values = [v[1] for v in values]
        mean = statistics.mean(metric_values)
        stdev = statistics.stdev(metric_values) if len(metric_values) >= 2 else 0
        
        if stdev == 0:
            return []
        
        threshold_upper = mean + (self.spike_threshold * stdev)
        threshold_lower = mean - (self.spike_threshold * stdev)
        
        spikes = []
        for idx, value, timestamp in values:
            if value > threshold_upper or value < threshold_lower:
                spikes.append({
                    'index': idx,
                    'timestamp': timestamp,
                    'metric': metric,
                    'value': value,
                    'mean': mean,
                    'deviation': abs(value - mean) / stdev if stdev else 0,
                    'direction': 'high' if value > mean else 'low'
                })
        
        return spikes
    
    def detect_all_anomalies(self, vmlog_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Detect anomalies across all metrics.
        
        Args:
            vmlog_data: List of parsed vmlog entries
            
        Returns:
            Dictionary mapping metric names to list of anomalies
        """
        anomalies = {}
        
        for metric in self.METRIC_DEFINITIONS.keys():
            spikes = self.detect_spikes(vmlog_data, metric)
            if spikes:
                anomalies[metric] = spikes
        
        return anomalies
    
    def detect_cpu_frequency_changes(self, vmlog_data: List[Dict]) -> List[Dict]:
        """
        Detect significant CPU frequency changes.
        
        Args:
            vmlog_data: List of parsed vmlog entries
            
        Returns:
            List of frequency change events
        """
        changes = []
        freq_metrics = ['cpufreq0', 'cpufreq1', 'cpufreq2', 'cpufreq3']
        
        for i in range(1, len(vmlog_data)):
            prev = vmlog_data[i - 1]
            curr = vmlog_data[i]
            
            for metric in freq_metrics:
                prev_val = prev.get(metric, 0)
                curr_val = curr.get(metric, 0)
                
                if prev_val > 0:
                    change_pct = abs(curr_val - prev_val) / prev_val
                    if change_pct > 0.5:  # 50% change
                        changes.append({
                            'index': i,
                            'timestamp': curr.get('timestamp'),
                            'metric': metric,
                            'from_value': prev_val,
                            'to_value': curr_val,
                            'change_pct': change_pct * 100
                        })
        
        return changes
    
    def detect_swap_activity(self, vmlog_data: List[Dict]) -> List[Dict]:
        """
        Detect periods of swap activity.
        
        Args:
            vmlog_data: List of parsed vmlog entries
            
        Returns:
            List of swap activity periods
        """
        activities = []
        
        for i, entry in enumerate(vmlog_data):
            pswpin = entry.get('pswpin', 0)
            pswpout = entry.get('pswpout', 0)
            
            if pswpin > 0 or pswpout > 0:
                activities.append({
                    'index': i,
                    'timestamp': entry.get('timestamp'),
                    'pswpin': pswpin,
                    'pswpout': pswpout,
                    'total': pswpin + pswpout
                })
        
        return activities
    
    def detect_page_fault_bursts(self, vmlog_data: List[Dict], threshold: int = 100) -> List[Dict]:
        """
        Detect bursts of page faults.
        
        Args:
            vmlog_data: List of parsed vmlog entries
            threshold: Minimum page faults to consider a burst
            
        Returns:
            List of page fault burst events
        """
        bursts = []
        
        for i, entry in enumerate(vmlog_data):
            pgmajfault = entry.get('pgmajfault', 0)
            
            if pgmajfault >= threshold:
                bursts.append({
                    'index': i,
                    'timestamp': entry.get('timestamp'),
                    'pgmajfault': pgmajfault,
                    'pgmajfault_f': entry.get('pgmajfault_f', 0),
                    'pgmajfault_a': entry.get('pgmajfault_a', 0),
                })
        
        return bursts
    
    def generate_summary_report(self, vmlog_data: List[Dict]) -> Dict:
        """
        Generate comprehensive summary report.
        
        Args:
            vmlog_data: List of parsed vmlog entries
            
        Returns:
            Summary report dictionary
        """
        if not vmlog_data:
            return {'error': 'No vmlog data'}
        
        # Get time range
        timestamps = [e.get('timestamp') for e in vmlog_data if e.get('timestamp')]
        time_range = {
            'start': min(timestamps) if timestamps else None,
            'end': max(timestamps) if timestamps else None,
            'duration_seconds': (max(timestamps) - min(timestamps)).total_seconds() if len(timestamps) >= 2 else 0
        }
        
        report = {
            'data_points': len(vmlog_data),
            'time_range': time_range,
            'statistics': self.calculate_stats(vmlog_data),
            'anomalies': {
                'spikes': self.detect_all_anomalies(vmlog_data),
                'freq_changes': self.detect_cpu_frequency_changes(vmlog_data),
                'swap_activity': self.detect_swap_activity(vmlog_data),
                'page_fault_bursts': self.detect_page_fault_bursts(vmlog_data),
            },
            'summary': {
                'total_anomalies': 0,
                'has_swap_activity': False,
                'has_page_fault_bursts': False,
            }
        }
        
        # Calculate summary
        for metric_spikes in report['anomalies']['spikes'].values():
            report['summary']['total_anomalies'] += len(metric_spikes)
        
        report['summary']['has_swap_activity'] = len(report['anomalies']['swap_activity']) > 0
        report['summary']['has_page_fault_bursts'] = len(report['anomalies']['page_fault_bursts']) > 0
        
        return report
