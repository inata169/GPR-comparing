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
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def test_preflight_allows_no_candidates(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected-python.txt"
    result = run_preflight(
        "-BundledPythonDir",
        str(tmp_path / "runtime" / "python312"),
        "-SelectedPythonPathFile",
        str(selected_path),
        "-SkipSystemDiscovery",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No external Python 3.12" in result.stdout
    assert not selected_path.exists()


def test_preflight_ignores_python_inside_bundled_runtime(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected-python.txt"
    result = run_preflight(
        "-BundledPythonDir",
        str(Path(sys.executable).parent),
        "-SelectedPythonPathFile",
        str(selected_path),
        "-CandidatePath",
        sys.executable,
        "-SkipSystemDiscovery",
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(sys.version_info[:2] != (3, 12), reason="requires a Python 3.12 test interpreter")
def test_preflight_selects_external_python312_without_modifying_it(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected-python.txt"
    result = run_preflight(
        "-BundledPythonDir",
        str(tmp_path / "runtime" / "python312"),
        "-SelectedPythonPathFile",
        str(selected_path),
        "-CandidatePath",
        sys.executable,
        "-SkipSystemDiscovery",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Compatible external Python 3.12 x64" in result.stdout
    assert "global packages will not be changed" in result.stdout
    assert selected_path.read_text(encoding="utf-8") == str(Path(sys.executable).resolve())


@pytest.mark.skipif(sys.version_info[:2] != (3, 12), reason="requires a Python 3.12 test interpreter")
def test_preflight_creates_venv_when_python_path_contains_unicode(
    tmp_path: Path,
) -> None:
    selected_path = tmp_path / "selected-python.txt"
    venv_dir = tmp_path / "日本語ユーザー" / ".venv"
    source_python = Path(sys.executable).resolve()
    source_mtime = source_python.stat().st_mtime_ns

    result = run_preflight(
        "-BundledPythonDir",
        str(tmp_path / "runtime" / "python312"),
        "-SelectedPythonPathFile",
        str(selected_path),
        "-VenvDir",
        str(venv_dir),
        "-CandidatePath",
        str(source_python),
        "-SkipSystemDiscovery",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (venv_dir / "Scripts" / "python.exe").is_file()
    assert selected_path.read_text(encoding="utf-8") == str(source_python)
    assert source_python.stat().st_mtime_ns == source_mtime
