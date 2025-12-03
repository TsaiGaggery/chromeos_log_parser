"""
Tests for analyzer modules.
"""

import pytest
from datetime import datetime

from src.parsers import VmlogParser
from src.analyzers import ErrorDetector, MetricsAnalyzer
from tests.fixtures import SAMPLE_VMLOG, SAMPLE_SYSLOG, SAMPLE_CHROME_LOG


class TestErrorDetector:
    """Tests for ErrorDetector."""
    
    def test_scan_logs(self):
        """Test scanning logs for errors."""
        detector = ErrorDetector(reference_year=2025)
        
        logs = {
            'syslog': SAMPLE_SYSLOG,
            'chrome_system_log': SAMPLE_CHROME_LOG,
        }
        
        errors = detector.scan_logs(logs)
        
        assert len(errors) > 0
        
        # Check we found different severity levels
        severities = {e['severity'] for e in errors}
        assert 3 in severities  # ERROR
        assert 2 in severities or 4 in severities  # WARNING or CRITICAL
    
    def test_extract_timestamp_iso(self):
        """Test ISO timestamp extraction."""
        detector = ErrorDetector(reference_year=2025)
        
        line = "2025-10-31T11:37:00.003226Z ERROR chrome[12345]: Failed"
        ts = detector._extract_timestamp(line)
        
        assert ts is not None
        assert ts.year == 2025
        assert ts.month == 10
        assert ts.day == 31
        assert ts.hour == 11
    
    def test_extract_timestamp_syslog(self):
        """Test syslog timestamp extraction."""
        detector = ErrorDetector(reference_year=2025)
        
        line = "Oct 31 11:58:18 localhost kernel: ERROR message"
        ts = detector._extract_timestamp(line)
        
        assert ts is not None
        assert ts.month == 10
        assert ts.day == 31
    
    def test_error_severity_levels(self):
        """Test error severity detection."""
        detector = ErrorDetector()
        
        logs = {
            'test': """
ERROR: This is an error
WARNING: This is a warning
CRASH: This is a crash
INFO: This is info
"""
        }
        
        errors = detector.scan_logs(logs)
        
        # Find errors by type
        by_type = {e['type']: e['severity'] for e in errors}
        
        assert by_type.get('ERROR') == 3
        assert by_type.get('WARNING') == 2
        assert by_type.get('CRASH') == 4
    
    def test_get_context(self):
        """Test context extraction."""
        detector = ErrorDetector(context_lines=2)
        
        lines = ['line1', 'line2', 'line3', 'line4', 'line5']
        context = detector._get_context(lines, 2, 2)
        
        assert len(context) == 5
        assert 'line1' in context
        assert 'line5' in context
    
    def test_map_to_vmlog_timeline(self):
        """Test mapping errors to vmlog timeline."""
        detector = ErrorDetector(reference_year=2025)
        
        # Parse vmlog
        vmlog_parser = VmlogParser(reference_year=2025)
        vmlog_data = vmlog_parser.parse_content(SAMPLE_VMLOG)
        
        # Create errors with timestamps
        errors = [
            {'timestamp': datetime(2025, 10, 27, 15, 14, 48), 'message': 'test error'}
        ]
        
        mapped_errors = detector.map_to_vmlog_timeline(errors, vmlog_data)
        
        assert len(mapped_errors) == 1
        assert 'vmlog_index' in mapped_errors[0]
    
    def test_get_error_summary(self):
        """Test error summary generation."""
        detector = ErrorDetector(reference_year=2025)
        
        logs = {'syslog': SAMPLE_SYSLOG}
        errors = detector.scan_logs(logs)
        
        summary = detector.get_error_summary(errors)
        
        assert 'total_count' in summary
        assert 'by_severity' in summary
        assert 'by_type' in summary
        assert 'by_source' in summary
        assert summary['total_count'] == len(errors)


class TestMetricsAnalyzer:
    """Tests for MetricsAnalyzer."""
    
    def setup_method(self):
        """Set up test data."""
        vmlog_parser = VmlogParser(reference_year=2025)
        self.vmlog_data = vmlog_parser.parse_content(SAMPLE_VMLOG)
    
    def test_calculate_stats(self):
        """Test statistics calculation."""
        analyzer = MetricsAnalyzer()
        stats = analyzer.calculate_stats(self.vmlog_data)
        
        assert 'cpuusage' in stats
        assert 'min' in stats['cpuusage']
        assert 'max' in stats['cpuusage']
        assert 'mean' in stats['cpuusage']
        assert stats['cpuusage']['min'] <= stats['cpuusage']['max']
    
    def test_detect_spikes(self):
        """Test spike detection."""
        analyzer = MetricsAnalyzer(spike_threshold=1.5)
        
        # Our sample has some variation in cpuusage
        spikes = analyzer.detect_spikes(self.vmlog_data, 'cpuusage')
        
        # Should detect the 0.25 value as a spike
        assert isinstance(spikes, list)
    
    def test_detect_all_anomalies(self):
        """Test anomaly detection across all metrics."""
        analyzer = MetricsAnalyzer()
        anomalies = analyzer.detect_all_anomalies(self.vmlog_data)
        
        assert isinstance(anomalies, dict)
    
    def test_detect_swap_activity(self):
        """Test swap activity detection."""
        analyzer = MetricsAnalyzer()
        activities = analyzer.detect_swap_activity(self.vmlog_data)
        
        # Our sample has swap activity in one entry
        assert isinstance(activities, list)
        assert len(activities) >= 1  # Entry with pswpin=1, pswpout=1
    
    def test_detect_page_fault_bursts(self):
        """Test page fault burst detection."""
        analyzer = MetricsAnalyzer()
        bursts = analyzer.detect_page_fault_bursts(self.vmlog_data, threshold=5)
        
        assert isinstance(bursts, list)
        # Our sample has entries with pgmajfault >= 5
        assert len(bursts) >= 1
    
    def test_generate_summary_report(self):
        """Test summary report generation."""
        analyzer = MetricsAnalyzer()
        report = analyzer.generate_summary_report(self.vmlog_data)
        
        assert 'data_points' in report
        assert 'time_range' in report
        assert 'statistics' in report
        assert 'anomalies' in report
        assert 'summary' in report
        
        assert report['data_points'] == len(self.vmlog_data)
    
    def test_empty_data(self):
        """Test handling of empty data."""
        analyzer = MetricsAnalyzer()
        
        stats = analyzer.calculate_stats([])
        assert stats == {}
        
        report = analyzer.generate_summary_report([])
        assert 'error' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
