"""
Tests for parser modules.
"""

import os
import pytest
from datetime import datetime

from src.parsers import VmlogParser, GeneratedLogsParser, UserFeedbackParser
from tests.fixtures import (
    SAMPLE_VMLOG, SAMPLE_VMLOG_NO_HEADER, SAMPLE_USER_FEEDBACK,
    SAMPLE_SYSLOG, SAMPLE_CHROME_LOG,
    create_temp_file, create_temp_dir_structure, cleanup_temp_dir
)


class TestVmlogParser:
    """Tests for VmlogParser."""
    
    def test_parse_content_with_header(self):
        """Test parsing vmlog content with header."""
        parser = VmlogParser(reference_year=2025)
        entries = parser.parse_content(SAMPLE_VMLOG)
        
        assert len(entries) == 5
        assert entries[0]['cpuusage'] == 0.02
        assert entries[0]['cpufreq0'] == 700000
        assert entries[0]['pgmajfault'] == 0
    
    def test_parse_content_without_header(self):
        """Test parsing vmlog content without header."""
        parser = VmlogParser(reference_year=2025)
        entries = parser.parse_content(SAMPLE_VMLOG_NO_HEADER)
        
        assert len(entries) == 2
        assert entries[0]['cpuusage'] == 0.02
    
    def test_parse_timestamp(self):
        """Test timestamp parsing."""
        parser = VmlogParser(reference_year=2025)
        dt = parser._parse_timestamp("[1027/151447]")
        
        assert dt is not None
        assert dt.month == 10
        assert dt.day == 27
        assert dt.hour == 15
        assert dt.minute == 14
        assert dt.second == 47
        assert dt.year == 2025
    
    def test_parse_timestamp_invalid(self):
        """Test invalid timestamp handling."""
        parser = VmlogParser()
        dt = parser._parse_timestamp("invalid")
        
        assert dt is None
    
    def test_parse_file(self):
        """Test parsing from file."""
        filepath = create_temp_file(SAMPLE_VMLOG, suffix='.log')
        try:
            parser = VmlogParser(reference_year=2025)
            entries = parser.parse_file(filepath)
            
            assert len(entries) == 5
        finally:
            os.unlink(filepath)
    
    def test_get_time_range(self):
        """Test time range extraction."""
        parser = VmlogParser(reference_year=2025)
        entries = parser.parse_content(SAMPLE_VMLOG)
        
        start, end = parser.get_time_range(entries)
        
        assert start is not None
        assert end is not None
        assert start <= end
    
    def test_get_metrics_summary(self):
        """Test metrics summary calculation."""
        parser = VmlogParser(reference_year=2025)
        entries = parser.parse_content(SAMPLE_VMLOG)
        
        summary = parser.get_metrics_summary(entries)
        
        assert 'cpuusage' in summary
        assert summary['cpuusage']['min'] == 0.02
        assert summary['cpuusage']['max'] == 0.25
        assert 'avg' in summary['cpuusage']


class TestGeneratedLogsParser:
    """Tests for GeneratedLogsParser."""
    
    def test_parse_directory(self):
        """Test parsing directory structure."""
        temp_dir = create_temp_dir_structure()
        try:
            parser = GeneratedLogsParser()
            result = parser.parse_directory(temp_dir)
            
            assert 'logs' in result
            assert 'metadata' in result
            assert 'structure' in result
            
            # Check logs were found
            log_names = list(result['logs'].keys())
            assert any('vmlog' in name for name in log_names)
            assert any('syslog' in name for name in log_names)
        finally:
            cleanup_temp_dir(temp_dir)
    
    def test_extract_metadata(self):
        """Test metadata extraction."""
        temp_dir = create_temp_dir_structure()
        try:
            parser = GeneratedLogsParser()
            result = parser.parse_directory(temp_dir)
            
            assert result['metadata'].get('chromeos_version') == '15633.0.0'
            assert result['metadata'].get('board') == 'volteer'
        finally:
            cleanup_temp_dir(temp_dir)
    
    def test_get_vmlog_files(self):
        """Test vmlog file extraction."""
        temp_dir = create_temp_dir_structure()
        try:
            parser = GeneratedLogsParser()
            result = parser.parse_directory(temp_dir)
            
            vmlog_files = parser.get_vmlog_files(result['logs'])
            
            assert len(vmlog_files) >= 1
            assert any('vmlog' in key for key in vmlog_files.keys())
        finally:
            cleanup_temp_dir(temp_dir)
    
    def test_get_priority_logs(self):
        """Test priority log extraction."""
        temp_dir = create_temp_dir_structure()
        try:
            parser = GeneratedLogsParser()
            result = parser.parse_directory(temp_dir)
            
            priority_logs = parser.get_priority_logs(result['logs'])
            
            assert len(priority_logs) >= 2  # vmlog and syslog at minimum
        finally:
            cleanup_temp_dir(temp_dir)


class TestUserFeedbackParser:
    """Tests for UserFeedbackParser."""
    
    def test_parse_content(self):
        """Test parsing user feedback content."""
        parser = UserFeedbackParser()
        result = parser.parse_content(SAMPLE_USER_FEEDBACK)
        
        assert 'metadata' in result
        assert 'sections' in result
        assert 'logs' in result
    
    def test_parse_metadata(self):
        """Test metadata extraction."""
        parser = UserFeedbackParser()
        result = parser.parse_content(SAMPLE_USER_FEEDBACK)
        
        assert result['metadata'].get('chromeos_version') == '15633.0.0'
        assert result['metadata'].get('board') == 'volteer'
    
    def test_parse_multiline_sections(self):
        """Test multiline section parsing."""
        parser = UserFeedbackParser()
        result = parser.parse_content(SAMPLE_USER_FEEDBACK)
        
        sections = result['sections']
        
        assert 'vmlog.LATEST' in sections
        assert 'syslog' in sections
        assert 'chrome_system_log' in sections
        
        # Check content is extracted correctly
        vmlog_content = sections['vmlog.LATEST']
        assert '[1027/151447]' in vmlog_content
    
    def test_parse_file(self):
        """Test parsing from file."""
        filepath = create_temp_file(SAMPLE_USER_FEEDBACK)
        try:
            parser = UserFeedbackParser()
            result = parser.parse_file(filepath)
            
            assert len(result['sections']) > 0
        finally:
            os.unlink(filepath)
    
    def test_get_vmlog_content(self):
        """Test vmlog content extraction."""
        parser = UserFeedbackParser()
        result = parser.parse_content(SAMPLE_USER_FEEDBACK)
        
        vmlog = parser.get_vmlog_content(result)
        
        assert vmlog is not None
        assert 'cpuusage' in vmlog or '[1027' in vmlog
    
    def test_get_section_names(self):
        """Test section names extraction."""
        parser = UserFeedbackParser()
        result = parser.parse_content(SAMPLE_USER_FEEDBACK)
        
        names = parser.get_section_names(result)
        
        assert 'vmlog.LATEST' in names
        assert 'syslog' in names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
