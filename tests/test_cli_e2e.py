"""End-to-end tests for rtgamma CLI and report generation."""

import json
import os
import subprocess

import pytest
from jsonschema import validate

from tests.test_batch import _make_synthetic_rtdose

# Define the expected JSON report schema
REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "ref": {"type": "string"},
        "eval": {"type": "string"},
        "mode": {"type": "string"},
        "pass_rate_percent": {"type": ["number", "string"]},
        "dta_mm": {"type": "number"},
        "dd_percent": {"type": "number"},
        "cutoff_percent": {"type": "number"},
        "best_shift_mm": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3
        },
        "gamma_mean": {"type": "number"},
    },
    "required": ["ref", "eval", "pass_rate_percent", "dta_mm", "dd_percent", "best_shift_mm", "gamma_mean"]
}


@pytest.fixture
def synthetic_doses(tmp_path):
    ref_path = str(tmp_path / "ref_dose.dcm")
    eval_path = str(tmp_path / "eval_dose.dcm")
    _make_synthetic_rtdose(ref_path, shape=(5, 10, 10), dose_value=2.0)
    _make_synthetic_rtdose(eval_path, shape=(5, 10, 10), dose_value=2.0)
    return ref_path, eval_path


def test_cli_e2e_full_reports(synthetic_doses, tmp_path):
    """Run full E2E test via CLI: generates all formats including PDF and validates."""
    ref_path, eval_path = synthetic_doses
    out_dir = tmp_path / "e2e_output"
    out_dir.mkdir()
    
    report_base = str(out_dir / "e2e_report")
    
    # Execute CLI
    cmd = [
        "python", "-m", "rtgamma.main",
        "--ref", ref_path,
        "--eval", eval_path,
        "--report", report_base,
        "--opt-shift", "off",
        "--mode", "3d"
    ]
    
    # We use subprocess to simulate true CLI invocation
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    
    # Verify report files
    json_path = report_base + ".json"
    csv_path = report_base + ".csv"
    md_path = report_base + ".md"
    pdf_path = report_base + ".pdf"
    
    assert os.path.exists(json_path), "JSON missing"
    assert os.path.exists(csv_path), "CSV missing"
    assert os.path.exists(md_path), "Markdown missing"
    # PDF generation should succeed
    assert os.path.exists(pdf_path), "PDF missing"
    
    # Validate JSON Schema
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate(instance=data, schema=REPORT_SCHEMA)
    
    # Ensure PASS since they are identical
    assert data["pass_rate_percent"] == 100.0
