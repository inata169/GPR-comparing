import os
import sys
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cli_help_runs():
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT)
    cp = subprocess.run([sys.executable, '-m', 'rtgamma.main', '--help'], env=env, text=True, capture_output=True)
    assert cp.returncode == 0
    # Basic sanity in help text
    assert 'usage' in (cp.stdout.lower() + cp.stderr.lower())

