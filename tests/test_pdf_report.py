"""Tests for rtgamma.pdf_report module."""

import os

from rtgamma.pdf_report import save_summary_pdf


def test_pdf_report_generation(tmp_path):
    """Test standard PDF report generation without errors."""
    summary = {
        'ref': 'ref_dummy.dcm',
        'eval': 'eval_dummy.dcm',
        'patient_id': 'Test_Pat_001',
        'pass_rate_percent': 98.76,
        'dta_mm': 2.0,
        'dd_percent': 3.0,
        'cutoff_percent': 10.0,
        'cutoff_qualified_points': 1200,
        'common_spatial_points': 1100,
        'spatially_excluded_points': 100,
        'evaluated_points': 1100,
        'mode': '3d',
        'best_shift_mm': (1.0, 0.5, -0.5),
        'warnings': 'None',
        'per_structure': [
            {
                'roi_name': 'PTV',
                'pass_rate_percent': 99.1,
                'voxel_count': 1000,
                'gamma_mean': 0.3,
                'gamma_median': 0.25,
                'gamma_max': 1.2
            }
        ],
        'save_gamma_map_path': None
    }

    out_pdf = str(tmp_path / 'test_report.pdf')
    save_summary_pdf(out_pdf, summary)

    assert os.path.exists(out_pdf)
    assert os.path.getsize(out_pdf) > 1000  # Should be easily > 1KB
