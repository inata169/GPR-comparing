"""Coordinate system round-trip tests for voxel_to_world / world_to_index.

Ensures that converting grid indices → world LPS → grid indices returns the
original indices to numerical precision, for both canonical and oblique
orientations as well as real DICOM data.
"""
from pathlib import Path

import numpy as np
import pytest

from rtgamma.io_dicom import load_rtdose, load_rtstruct, voxel_to_world, world_to_index
from rtgamma.mask import build_roi_masks

ROOT = Path(__file__).resolve().parents[1]


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_meta(ipp, v_col, v_row, v_slice, s_col, s_row, z_offsets):
    """Build a minimal meta dict for voxel_to_world / world_to_index."""
    return {
        'ipp': np.asarray(ipp, dtype=float),
        'v_col': np.asarray(v_col, dtype=float),
        'v_row': np.asarray(v_row, dtype=float),
        'v_slice': np.asarray(v_slice, dtype=float),
        's_col': float(s_col),
        's_row': float(s_row),
        'z_offsets': np.asarray(z_offsets, dtype=float),
    }


def _roundtrip(meta, ijk_orig, atol=1e-6):
    """Verify ijk → world → ijk round-trip."""
    world = voxel_to_world(
        meta['ipp'], meta['v_col'], meta['v_row'], meta['v_slice'],
        meta['s_col'], meta['s_row'], meta['z_offsets'], ijk_orig)
    ijk_back = world_to_index(
        meta['ipp'], meta['v_col'], meta['v_row'], meta['v_slice'],
        meta['s_col'], meta['s_row'], meta['z_offsets'], world)
    np.testing.assert_allclose(ijk_back, ijk_orig, atol=atol,
                               err_msg="Round-trip (ijk→world→ijk) mismatch")


# ── Test 1: Identity (canonical) orientation ─────────────────────────────────

def test_roundtrip_identity_orientation():
    """Canonical HFS orientation: v_col=[1,0,0], v_row=[0,1,0], v_slice=[0,0,1]."""
    meta = _make_meta(
        ipp=[-150.0, -200.0, -50.0],
        v_col=[1, 0, 0],
        v_row=[0, 1, 0],
        v_slice=[0, 0, 1],
        s_col=2.5,
        s_row=2.5,
        z_offsets=np.arange(20) * 3.0,
    )
    rng = np.random.default_rng(42)
    ijk = rng.uniform([0, 0, 0], [19, 79, 59], size=(50, 3))
    _roundtrip(meta, ijk)


# ── Test 2: Oblique orientation ──────────────────────────────────────────────

def test_roundtrip_oblique_orientation():
    """45-degree oblique orientation about the z-axis."""
    c45 = np.cos(np.radians(45))
    s45 = np.sin(np.radians(45))
    meta = _make_meta(
        ipp=[10.0, -20.0, 30.0],
        v_col=[c45, s45, 0],
        v_row=[-s45, c45, 0],
        v_slice=[0, 0, 1],
        s_col=1.5,
        s_row=1.5,
        z_offsets=np.arange(10) * 2.0,
    )
    rng = np.random.default_rng(123)
    ijk = rng.uniform([0, 0, 0], [9, 30, 30], size=(100, 3))
    _roundtrip(meta, ijk)


# ── Test 3: Real DICOM round-trip ────────────────────────────────────────────

@pytest.mark.parametrize("dose_subpath", [
    'PROSTATE/RTDOSE_2.16.840.1.114337.1.11224.1772428288.1.dcm',
    '2024101700/RTDOSE_2.16.840.1.114337.1.6420.1764295957.1',
])
def test_roundtrip_with_real_dicom(dose_subpath):
    """Round-trip on corners, center, and random points of a real dose grid."""
    p = ROOT / 'dicom' / dose_subpath
    if not p.exists():
        pytest.skip(f"Test data not present: {p}")
    meta = load_rtdose(str(p))
    nk, nj, ni = meta['shape']

    # Deterministic sample points: corners + center + random
    corners = np.array([
        [0, 0, 0],
        [nk - 1, 0, 0],
        [0, nj - 1, 0],
        [0, 0, ni - 1],
        [nk - 1, nj - 1, ni - 1],
        [nk / 2.0, nj / 2.0, ni / 2.0],
    ])
    rng = np.random.default_rng(99)
    rand_pts = rng.uniform([0, 0, 0], [nk - 1, nj - 1, ni - 1], size=(20, 3))
    ijk = np.vstack([corners, rand_pts])
    _roundtrip(meta, ijk, atol=1e-4)


# ── Test 4: Mask overlap self-compare ────────────────────────────────────────

_PROSTATE = ROOT / 'dicom' / 'PROSTATE'
_P_DOSE = _PROSTATE / 'RTDOSE_2.16.840.1.114337.1.11224.1772428288.1.dcm'
_P_STRUCT = _PROSTATE / 'RTSTRUCT_2.16.840.1.114337.1.11224.1772428287.0.dcm'


def test_mask_overlap_self_compare():
    """ROI mask must overlap with dose voxels above cutoff in self-compare."""
    if not (_P_DOSE.exists() and _P_STRUCT.exists()):
        pytest.skip("PROSTATE test data not present")
    meta = load_rtdose(str(_P_DOSE))
    rtstruct_meta = load_rtstruct(str(_P_STRUCT))

    # Find any ROI that exists
    roi_names = [r['name'] for r in rtstruct_meta['roi_list']]
    assert len(roi_names) > 0, "No ROIs found in RTSTRUCT"

    # Use first ROI
    target_roi = roi_names[0]
    masks = build_roi_masks(rtstruct_meta, meta, roi_names=[target_roi])
    mask = masks[target_roi]

    dose = meta['dose']
    cutoff = np.max(dose) * 0.1

    mask_count = int(np.sum(mask))
    above_cutoff = int(np.sum(dose >= cutoff))
    intersection = int(np.sum(mask & (dose >= cutoff)))

    assert mask_count > 0, f"ROI '{target_roi}' mask has 0 voxels"
    assert above_cutoff > 0, "No voxels above 10% cutoff"
    assert intersection > 0, (
        f"ROI '{target_roi}' mask ({mask_count} voxels) has ZERO overlap "
        f"with dose above cutoff ({above_cutoff} voxels) — spatial alignment bug"
    )
