#!/usr/bin/env python
"""Offline installation smoke test using synthetic, non-patient DICOM data."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import struct
import subprocess
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def run(command: list[str], label: str, env: dict[str, str]) -> None:
    print(f"[RUN] {label}")
    completed = subprocess.run(
        command,
        cwd=APP_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")
    print(f"[OK ] {label}")


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Expected output is missing or empty: {path}")


def require_gamma_report(path: Path, engine: str, engine_version: str) -> None:
    require_file(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    rate = float(data["pass_rate_percent"])
    if rate < 99.99:
        raise RuntimeError(f"Unexpected pass rate in {path.name}: {rate}")
    if data.get("gamma_engine") != engine:
        raise RuntimeError(
            f"Unexpected engine in {path.name}: {data.get('gamma_engine')}"
        )
    if data.get("gamma_engine_version") != engine_version:
        raise RuntimeError(
            f"Unexpected engine version in {path.name}: "
            f"{data.get('gamma_engine_version')}"
        )


def check_runtime() -> None:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(f"Python 3.12 is required; found {sys.version}")
    if struct.calcsize("P") != 8:
        raise RuntimeError("64-bit Python is required")

    modules = [
        "pydicom",
        "numpy",
        "scipy",
        "numba",
        "matplotlib",
        "reportlab",
        "pymedphys",
        "PySide6",
        "pyqtgraph",
        "rtgamma.main",
        "scripts.gamma_viewer_fast",
    ]
    for name in modules:
        importlib.import_module(name)
        print(f"[OK ] import {name}")

    if version("pymedphys") != "0.41.0":
        raise RuntimeError(
            f"PyMedPhys 0.41.0 is required; found {version('pymedphys')}"
        )

    viewer = importlib.import_module("scripts.gamma_viewer_fast")
    qt_core, qt_widgets, pyqtgraph = viewer._import_qtgraph()
    if qt_core is None or qt_widgets is None or pyqtgraph is None:
        raise RuntimeError("Fast Viewer Qt dependency probe failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Parent directory for smoke-test results")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(args.output).resolve() / timestamp
    data_dir = output / "synthetic_dicom"
    reports = output / "reports"
    reports.mkdir(parents=True, exist_ok=False)
    mpl_config = output / "matplotlib_config"
    mpl_config.mkdir()

    os.environ.update(
        {
            "MPLBACKEND": "Agg",
            "QT_QPA_PLATFORM": "offscreen",
            "NUMBA_NUM_THREADS": "1",
            "MPLCONFIGDIR": str(mpl_config),
        }
    )
    check_runtime()

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(APP_ROOT),
            "PYTHONUTF8": "1",
            "MPLBACKEND": "Agg",
            "QT_QPA_PLATFORM": "offscreen",
            "NUMBA_NUM_THREADS": "1",
            "MPLCONFIGDIR": str(mpl_config),
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_CONFIG_FILE": os.devnull,
        }
    )

    run(
        [
            sys.executable,
            str(APP_ROOT / "scripts" / "create_synthetic_dicom_rt_dataset.py"),
            "--out",
            str(data_dir),
            "--identical-eval",
        ],
        "generate synthetic CT/RTDOSE/RTSTRUCT",
        env,
    )

    ref = data_dir / "RTDOSE_REF.dcm"
    evaluation = data_dir / "RTDOSE_EVAL.dcm"
    rtstruct = data_dir / "RTSTRUCT_SYNTH.dcm"
    ct_dir = data_dir / "CT"
    for path in (ref, evaluation, rtstruct):
        require_file(path)
    if len(list(ct_dir.glob("*.dcm"))) < 2:
        raise RuntimeError("Synthetic CT series was not generated")

    from rtgamma.io_dicom import load_ct, load_rtdose, load_rtstruct

    if load_rtdose(str(ref))["dose"].ndim != 3:
        raise RuntimeError("Synthetic RTDOSE load failed")
    if load_ct(str(ct_dir))["ct_hu"].ndim != 3:
        raise RuntimeError("Synthetic CT load failed")
    if not load_rtstruct(str(rtstruct))["roi_list"]:
        raise RuntimeError("Synthetic RTSTRUCT load failed")
    print("[OK ] synthetic DICOM I/O")

    header_report = reports / "header_compare.md"
    run(
        [
            sys.executable,
            "-m",
            "rtgamma.main",
            "--ref",
            str(ref),
            "--eval",
            str(evaluation),
            "--mode",
            "header",
            "--report",
            str(header_report),
        ],
        "RTDOSE header comparison",
        env,
    )
    require_file(header_report)

    report_2d = reports / "gamma_2d"
    gamma_png = reports / "gamma_2d.png"
    diff_png = reports / "dose_diff_2d.png"
    run(
        [
            sys.executable,
            "-m",
            "rtgamma.main",
            "--ref",
            str(ref),
            "--eval",
            str(evaluation),
            "--mode",
            "2d",
            "--plane",
            "axial",
            "--plane-index",
            "auto",
            "--opt-shift",
            "off",
            "--engine",
            "pymedphys",
            "--interp-fraction",
            "1",
            "--save-gamma-map",
            str(gamma_png),
            "--save-dose-diff",
            str(diff_png),
            "--report",
            str(report_2d),
        ],
        "2D PyMedPhys gamma analysis and image/PDF reports",
        env,
    )
    require_gamma_report(report_2d.with_suffix(".json"), "pymedphys", "0.41.0")
    for path in (report_2d.with_suffix(".md"), report_2d.with_suffix(".pdf"), gamma_png, diff_png):
        require_file(path)

    report_3d = reports / "gamma_3d"
    run(
        [
            sys.executable,
            "-m",
            "rtgamma.main",
            "--ref",
            str(ref),
            "--eval",
            str(evaluation),
            "--mode",
            "3d",
            "--opt-shift",
            "off",
            "--engine",
            "pymedphys",
            "--interp-fraction",
            "1",
            "--no-pdf",
            "--report",
            str(report_3d),
        ],
        "3D PyMedPhys gamma analysis",
        env,
    )
    require_gamma_report(report_3d.with_suffix(".json"), "pymedphys", "0.41.0")

    report_numba = reports / "gamma_3d_numba_legacy"
    run(
        [
            sys.executable,
            "-m",
            "rtgamma.main",
            "--ref",
            str(ref),
            "--eval",
            str(evaluation),
            "--mode",
            "3d",
            "--opt-shift",
            "off",
            "--engine",
            "numba",
            "--interp-fraction",
            "1",
            "--no-pdf",
            "--report",
            str(report_numba),
        ],
        "3D explicit Numba legacy gamma analysis",
        env,
    )
    require_gamma_report(
        report_numba.with_suffix(".json"),
        "numba",
        version("numba"),
    )

    summary = {
        "status": "PASS",
        "python": sys.version,
        "application_root": str(APP_ROOT),
        "output": str(output),
        "checks": [
            "Python 3.12 x64 and runtime imports",
            "Fast Viewer dependency import",
            "synthetic non-patient CT/RTDOSE/RTSTRUCT generation and load",
            "RTDOSE header comparison",
            "2D PyMedPhys 0.41.0 gamma with JSON/Markdown/PDF/PNG outputs",
            "3D PyMedPhys 0.41.0 gamma analysis",
            "3D explicit Numba legacy gamma analysis",
        ],
    }
    (output / "SMOKE_TEST_RESULT.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[PASS] Offline smoke test completed: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
