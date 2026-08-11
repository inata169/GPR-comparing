"""End-to-end tests for rtgamma CLI and report generation."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import validate

from rtgamma.provenance import sha256_file
from tests.test_batch import _make_synthetic_rtdose

# Define the expected JSON report schema
REPORT_SCHEMA = {
    'type': 'object',
    'properties': {
        'ref': {'type': 'string'},
        'eval': {'type': 'string'},
        'mode': {'type': 'string'},
        'pass_rate_percent': {'type': ['number', 'string']},
        'dta_mm': {'type': 'number'},
        'dd_percent': {'type': 'number'},
        'cutoff_percent': {'type': 'number'},
        'gamma_engine': {'enum': ['numba', 'pymedphys']},
        'gamma_engine_version': {'type': 'string'},
        'report_schema_version': {'const': 2},
        'provenance': {'type': 'object'},
        'best_shift_mm': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3},
        'gamma_mean': {'type': 'number'},
    },
    'required': [
        'ref',
        'eval',
        'pass_rate_percent',
        'dta_mm',
        'dd_percent',
        'best_shift_mm',
        'gamma_mean',
        'gamma_engine',
        'gamma_engine_version',
        'report_schema_version',
        'provenance',
    ],
}


@pytest.fixture
def synthetic_doses(tmp_path):
    ref_path = str(tmp_path / 'ref_dose.dcm')
    eval_path = str(tmp_path / 'eval_dose.dcm')
    _make_synthetic_rtdose(ref_path, shape=(5, 10, 10), dose_value=2.0)
    _make_synthetic_rtdose(eval_path, shape=(5, 10, 10), dose_value=2.0)
    return ref_path, eval_path


def test_cli_e2e_full_reports(synthetic_doses, tmp_path):
    """Run full E2E test via CLI: generates all formats including PDF and validates."""
    ref_path, eval_path = synthetic_doses
    out_dir = tmp_path / 'e2e_output'
    out_dir.mkdir()

    report_base = str(out_dir / 'e2e_report')

    # Execute CLI
    cmd = [
        sys.executable,
        '-m',
        'rtgamma.main',
        '--ref',
        ref_path,
        '--eval',
        eval_path,
        '--report',
        report_base,
        '--opt-shift',
        'off',
        '--mode',
        '3d',
        '--db',
        str(out_dir / 'results.db'),
    ]

    # We use subprocess to simulate true CLI invocation
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f'CLI failed: {result.stderr}'
    assert '--engine was omitted; the standard default is now PyMedPhys' in result.stdout

    # Verify report files
    json_path = report_base + '.json'
    csv_path = report_base + '.csv'
    md_path = report_base + '.md'
    pdf_path = report_base + '.pdf'

    assert os.path.exists(json_path), 'JSON missing'
    assert os.path.exists(csv_path), 'CSV missing'
    assert os.path.exists(md_path), 'Markdown missing'
    # PDF generation should succeed
    assert os.path.exists(pdf_path), 'PDF missing'

    # Validate JSON Schema
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    validate(instance=data, schema=REPORT_SCHEMA)
    repository_schema = json.loads(
        (Path(__file__).parents[1] / 'docs' / 'openspec' / 'report.schema.json').read_text(encoding='utf-8')
    )
    validate(instance=data, schema=repository_schema)
    assert 'NaN' not in Path(json_path).read_text(encoding='utf-8')

    # Ensure PASS since they are identical
    assert data['pass_rate_percent'] == 100.0
    assert data['gamma_engine'] == 'pymedphys'
    provenance = data['provenance']
    assert provenance['schema_version'] == 2
    assert provenance['engine'] == {
        'name': 'pymedphys',
        'version': '0.41.0',
    }
    assert provenance['runtime']['python_version'] == '.'.join(
        str(part) for part in sys.version_info[:3]
    )
    assert provenance['privacy']['absolute_paths_recorded'] is False
    assert provenance['inputs']['reference']['sha256']
    assert ref_path not in json.dumps(data)
    assert eval_path not in json.dumps(data)
    assert provenance['analysis']['execution_controls'] == {
        'threads_requested': None,
        'threads_applied': False,
        'gpu_requested': 'off',
        'gpu_applied': False,
        'seed_requested': None,
        'seed_applied': False,
    }

    with sqlite3.connect(out_dir / 'results.db') as connection:
        row = connection.execute('SELECT report_schema_version, provenance_json FROM gamma_results').fetchone()
    assert row[0] == 2
    assert json.loads(row[1])['engine']['name'] == 'pymedphys'


def test_cli_explicit_pymedphys_engine_records_provenance(synthetic_doses, tmp_path):
    """The explicit PyMedPhys path records the selected engine."""
    ref_path, eval_path = synthetic_doses
    report_base = str(tmp_path / 'pymedphys_report')
    cmd = [
        sys.executable,
        '-m',
        'rtgamma.main',
        '--ref',
        ref_path,
        '--eval',
        eval_path,
        '--report',
        report_base,
        '--opt-shift',
        'off',
        '--mode',
        '3d',
        '--engine',
        'pymedphys',
        '--interp-fraction',
        '1',
        '--no-pdf',
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f'CLI failed: {result.stderr}'
    assert '--engine was omitted' not in result.stdout

    with open(report_base + '.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data['pass_rate_percent'] == 100.0
    assert data['gamma_engine'] == 'pymedphys'
    assert data['gamma_engine_version'] == '0.41.0'


def test_cli_directory_inputs_hash_resolved_rtdose(synthetic_doses, tmp_path):
    ref_path, eval_path = (Path(path) for path in synthetic_doses)
    ref_dir = tmp_path / 'reference_input'
    eval_dir = tmp_path / 'evaluation_input'
    ref_dir.mkdir()
    eval_dir.mkdir()
    resolved_ref = ref_path.replace(ref_dir / ref_path.name)
    resolved_eval = eval_path.replace(eval_dir / eval_path.name)
    report_base = tmp_path / 'directory_input_report'

    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'rtgamma.main',
            '--ref',
            str(ref_dir),
            '--eval',
            str(eval_dir),
            '--report',
            str(report_base),
            '--opt-shift',
            'off',
            '--mode',
            '3d',
            '--interp-fraction',
            '1',
            '--no-pdf',
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f'CLI failed: {result.stderr}'
    data = json.loads(report_base.with_suffix('.json').read_text(encoding='utf-8'))
    inputs = data['provenance']['inputs']
    assert inputs['reference']['basename'] == resolved_ref.name
    assert inputs['reference']['sha256'] == sha256_file(resolved_ref)
    assert inputs['evaluation']['basename'] == resolved_eval.name
    assert inputs['evaluation']['sha256'] == sha256_file(resolved_eval)
