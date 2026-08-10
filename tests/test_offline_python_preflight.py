"""Windows checks for the offline Python 3.12 safety preflight."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "offline" / "check_existing_python.ps1"
POWERSHELL = shutil.which("powershell.exe") if sys.platform == "win32" else None


pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="Windows PowerShell is required")


def run_preflight(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PREFLIGHT),
            *arguments,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_preflight_allows_no_candidates(tmp_path: Path) -> None:
    result = run_preflight(
        "-BundledPythonDir",
        str(tmp_path / "runtime" / "python312"),
        "-SkipSystemDiscovery",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No external Python 3.12" in result.stdout


def test_preflight_ignores_python_inside_bundled_runtime() -> None:
    result = run_preflight(
        "-BundledPythonDir",
        str(Path(sys.executable).parent),
        "-CandidatePath",
        sys.executable,
        "-SkipSystemDiscovery",
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(sys.version_info[:2] != (3, 12), reason="requires a Python 3.12 test interpreter")
def test_preflight_blocks_external_python312(tmp_path: Path) -> None:
    result = run_preflight(
        "-BundledPythonDir",
        str(tmp_path / "runtime" / "python312"),
        "-CandidatePath",
        sys.executable,
        "-SkipSystemDiscovery",
    )
    assert result.returncode == 12, result.stdout + result.stderr
    assert "SAFETY STOP" in result.stdout
    assert "installer was not started" in result.stdout
