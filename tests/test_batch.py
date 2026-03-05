"""Tests for rtgamma.batch module."""

import csv
import json
import os

import numpy as np


def _make_synthetic_rtdose(path, shape=(3, 4, 4), dose_value=1.0, spacing=(2.5, 2.5)):
    """Create a minimal synthetic RTDOSE DICOM file for testing."""
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.uid import ExplicitVRLittleEndian

    ds = FileDataset(path, Dataset(), preamble=b"\x00" * 128, is_implicit_VR=False)
    ds.file_meta = Dataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    ds.file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.Modality = 'RTDOSE'
    ds.Rows = shape[1]
    ds.Columns = shape[2]
    ds.NumberOfFrames = shape[0]
    ds.BitsAllocated = 32
    ds.BitsStored = 32
    ds.HighBit = 31
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.ImagePositionPatient = [0.0, 0.0, 0.0]
    ds.PixelSpacing = [spacing[0], spacing[1]]
    ds.GridFrameOffsetVector = [float(i * spacing[0]) for i in range(shape[0])]
    ds.DoseGridScaling = 1.0
    ds.DoseUnits = 'GY'
    ds.DoseType = 'PHYSICAL'
    ds.DoseSummationType = 'PLAN'

    dose_array = (np.ones(shape, dtype=np.float64) * dose_value * 1e6).astype(np.uint32)
    ds.PixelData = dose_array.tobytes()
    ds.save_as(path, write_like_original=False)
    return path


class TestBatchBuildArgv:
    """Unit tests for _build_argv helper."""

    def test_minimal_row(self, tmp_path):
        from rtgamma.batch import _build_argv
        row = {'ref': '/path/to/ref.dcm', 'eval': '/path/to/eval.dcm'}
        argv, pid = _build_argv(row, str(tmp_path))
        assert '--ref' in argv
        assert '--eval' in argv
        assert '--report' in argv
        assert pid  # patient_id derived from ref basename

    def test_custom_params(self, tmp_path):
        from rtgamma.batch import _build_argv
        row = {
            'ref': '/ref.dcm', 'eval': '/eval.dcm',
            'patient_id': 'P001',
            'dta_mm': '1.0', 'dd_percent': '2.0',
            'cutoff_percent': '5.0', 'gamma_type': 'local',
        }
        argv, pid = _build_argv(row, str(tmp_path))
        assert pid == 'P001'
        assert argv[argv.index('--dta') + 1] == '1.0'
        assert argv[argv.index('--dd') + 1] == '2.0'
        assert argv[argv.index('--cutoff') + 1] == '5.0'
        assert argv[argv.index('--gamma-type') + 1] == 'local'

    def test_roi_semicolon_split(self, tmp_path):
        from rtgamma.batch import _build_argv
        row = {'ref': '/r.dcm', 'eval': '/e.dcm', 'rtstruct': '/rs.dcm', 'roi': 'PTV;CTV'}
        argv, _ = _build_argv(row, str(tmp_path))
        roi_indices = [i for i, v in enumerate(argv) if v == '--roi']
        assert len(roi_indices) == 2


class TestBatchSummaryWriters:
    """Unit tests for summary output writers."""

    def test_write_summary_csv(self, tmp_path):
        from rtgamma.batch import _write_summary_csv
        results = [
            {'patient_id': 'P1', 'ref': 'r1.dcm', 'eval': 'e1.dcm',
             'mode': '3d', 'dd_percent': 3.0, 'dta_mm': 2.0,
             'cutoff_percent': 10.0, 'gamma_type': 'global',
             'pass_rate_percent': 95.5, 'gamma_mean': 0.45,
             'gamma_median': 0.33, 'gamma_max': 2.1,
             'best_shift_mm': (0, 0, 0), 'warnings': '', 'status': 'OK'},
        ]
        out = str(tmp_path / 'summary.csv')
        _write_summary_csv(out, results)
        assert os.path.exists(out)
        with open(out, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['patient_id'] == 'P1'

    def test_write_summary_md(self, tmp_path):
        from rtgamma.batch import _write_summary_md
        results = [
            {'batch_index': 1, 'patient_id': 'P1', 'ref': 'r.dcm', 'eval': 'e.dcm',
             'pass_rate_percent': 90.0, 'gamma_mean': 0.5,
             'gamma_median': 0.4, 'gamma_max': 3.0,
             'best_shift_mm': (1, 2, 3), 'warnings': ''},
        ]
        out = str(tmp_path / 'summary.md')
        _write_summary_md(out, results, [], 1)
        assert os.path.exists(out)
        content = open(out, 'r', encoding='utf-8').read()
        assert 'P1' in content
        assert '90.00' in content

    def test_write_summary_json(self, tmp_path):
        from rtgamma.batch import _write_summary_json
        results = [
            {'patient_id': 'P1', 'pass_rate_percent': 95.0, 'best_shift_mm': (0, 0, 0)},
        ]
        out = str(tmp_path / 'summary.json')
        _write_summary_json(out, results, [])
        assert os.path.exists(out)
        data = json.loads(open(out, 'r', encoding='utf-8').read())
        assert data['succeeded'] == 1
        assert data['results'][0]['best_shift_mm'] == [0, 0, 0]  # tuple -> list


class TestBatchIntegration:
    """Integration test: run_batch with synthetic DICOM data."""

    def test_self_compare_batch(self, tmp_path):
        """Batch with 2 identical self-compare pairs should produce 100% GPR."""
        # Create synthetic RTDOSE
        dose_path = str(tmp_path / 'dose.dcm')
        _make_synthetic_rtdose(dose_path, shape=(3, 4, 4), dose_value=1.0)

        # Create CSV
        csv_path = str(tmp_path / 'batch.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'patient_id', 'ref', 'eval', 'dta_mm', 'dd_percent',
                'cutoff_percent', 'opt_shift', 'mode',
            ])
            writer.writeheader()
            writer.writerow({
                'patient_id': 'TestA',
                'ref': dose_path, 'eval': dose_path,
                'dta_mm': '3', 'dd_percent': '3',
                'cutoff_percent': '10', 'opt_shift': 'off', 'mode': '3d',
            })
            writer.writerow({
                'patient_id': 'TestB',
                'ref': dose_path, 'eval': dose_path,
                'dta_mm': '2', 'dd_percent': '2',
                'cutoff_percent': '10', 'opt_shift': 'off', 'mode': '3d',
            })

        out_dir = str(tmp_path / 'output')
        from rtgamma.batch import run_batch
        result = run_batch(csv_path, out_dir)

        assert len(result['results']) == 2
        assert len(result['errors']) == 0
        for r in result['results']:
            assert r['pass_rate_percent'] == 100.0

        # Check summary files exist
        assert os.path.exists(os.path.join(out_dir, 'batch_summary.csv'))
        assert os.path.exists(os.path.join(out_dir, 'batch_summary.md'))
        assert os.path.exists(os.path.join(out_dir, 'batch_summary.json'))

    def test_error_resilience(self, tmp_path):
        """Batch should skip rows with invalid paths and continue."""
        dose_path = str(tmp_path / 'dose.dcm')
        _make_synthetic_rtdose(dose_path, shape=(3, 4, 4), dose_value=1.0)

        csv_path = str(tmp_path / 'batch.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'patient_id', 'ref', 'eval', 'opt_shift', 'mode',
            ])
            writer.writeheader()
            # Row 1: invalid path (should fail)
            writer.writerow({
                'patient_id': 'Bad', 'ref': '/nonexistent.dcm',
                'eval': '/nonexistent.dcm', 'opt_shift': 'off', 'mode': '3d',
            })
            # Row 2: valid self-compare (should succeed)
            writer.writerow({
                'patient_id': 'Good', 'ref': dose_path,
                'eval': dose_path, 'opt_shift': 'off', 'mode': '3d',
            })

        out_dir = str(tmp_path / 'output')
        from rtgamma.batch import run_batch
        result = run_batch(csv_path, out_dir)

        assert len(result['errors']) == 1
        assert result['errors'][0]['patient_id'] == 'Bad'
        assert len(result['results']) == 1
        assert result['results'][0]['patient_id'] == 'Good'
