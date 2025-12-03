"""
Test fixtures for ChromeOS Log Analyzer tests.
"""

import os
import tempfile
from pathlib import Path

# Sample vmlog content
SAMPLE_VMLOG = """time pgmajfault pgmajfault_f pgmajfault_a pswpin pswpout cpuusage cpufreq0 cpufreq1 cpufreq2 cpufreq3
[1027/151447] 0 0 0 0 0 0.02 700000 700000 698611 1263820
[1027/151448] 0 0 0 0 0 0.05 800000 750000 700000 1300000
[1027/151449] 5 3 2 0 0 0.15 1200000 1100000 1000000 1500000
[1027/151450] 0 0 0 0 0 0.08 900000 850000 800000 1400000
[1027/151451] 10 8 2 1 1 0.25 1500000 1400000 1300000 1800000
"""

# Sample vmlog without header
SAMPLE_VMLOG_NO_HEADER = """[1027/151447] 0 0 0 0 0 0.02 700000 700000 698611 1263820
[1027/151448] 0 0 0 0 0 0.05 800000 750000 700000 1300000
"""

# Sample syslog content
SAMPLE_SYSLOG = """Oct 31 11:58:18 localhost kernel: [    0.000000] Linux version 5.10.0
Oct 31 11:58:19 localhost kernel: [    0.100000] Memory: 8192MB available
Oct 31 11:58:20 localhost systemd[1]: Started Session 1 of user chronos.
Oct 31 11:58:21 localhost systemd[1]: ERROR: Failed to start service xyz.service
Oct 31 11:58:22 localhost kernel: [   10.500000] WARNING: CPU frequency scaling limited
Oct 31 11:58:23 localhost chronos[1234]: Normal operation message
Oct 31 11:58:24 localhost chronos[1234]: CRITICAL: Out of memory situation detected
"""

# Sample chrome_system_log content  
SAMPLE_CHROME_LOG = """2025-10-31T11:37:00.003226Z ERROR chrome[12345]: Failed to load extension
2025-10-31T11:37:01.123456Z INFO chrome[12345]: Starting browser
2025-10-31T11:37:02.234567Z WARNING chrome[12345]: Deprecated API usage
2025-10-31T11:37:03.345678Z ERROR chrome[12345]: Network request timeout
2025-10-31T11:37:04.456789Z INFO chrome[12345]: Tab created
"""

# Sample user feedback content
SAMPLE_USER_FEEDBACK = """CHROMEOS_RELEASE_VERSION=15633.0.0
CHROMEOS_RELEASE_BOARD=volteer
description=User reported issue with WiFi

vmlog.LATEST=<multiline>
---------- START ----------
time pgmajfault pgmajfault_f pgmajfault_a pswpin pswpout cpuusage cpufreq0 cpufreq1 cpufreq2 cpufreq3
[1027/151447] 0 0 0 0 0 0.02 700000 700000 698611 1263820
[1027/151448] 0 0 0 0 0 0.05 800000 750000 700000 1300000
---------- END ----------

syslog=<multiline>
---------- START ----------
Oct 31 11:58:18 localhost kernel: [    0.000000] Linux version 5.10.0
Oct 31 11:58:21 localhost systemd[1]: ERROR: Failed to start service
---------- END ----------

chrome_system_log=<multiline>
---------- START ----------
2025-10-31T11:37:00.003226Z ERROR chrome[12345]: Failed to load extension
---------- END ----------
"""


def create_temp_file(content: str, suffix: str = '.txt') -> str:
    """Create a temporary file with given content."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


def create_temp_dir_structure() -> str:
    """Create a temporary directory structure mimicking generated_logs."""
    temp_dir = tempfile.mkdtemp(prefix='chromeos_test_')
    
    # Create feedback directory
    feedback_dir = os.path.join(temp_dir, 'feedback')
    os.makedirs(feedback_dir)
    
    # Create vmlog files
    with open(os.path.join(feedback_dir, 'vmlog.LATEST'), 'w') as f:
        f.write(SAMPLE_VMLOG)
    
    # Create syslog
    with open(os.path.join(feedback_dir, 'syslog'), 'w') as f:
        f.write(SAMPLE_SYSLOG)
    
    # Create chrome_system_log
    with open(os.path.join(feedback_dir, 'chrome_system_log'), 'w') as f:
        f.write(SAMPLE_CHROME_LOG)
    
    # Create lsb-release
    with open(os.path.join(feedback_dir, 'lsb-release'), 'w') as f:
        f.write("CHROMEOS_RELEASE_VERSION=15633.0.0\n")
        f.write("CHROMEOS_RELEASE_BOARD=volteer\n")
    
    return temp_dir


def cleanup_temp_dir(temp_dir: str):
    """Clean up temporary directory."""
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
