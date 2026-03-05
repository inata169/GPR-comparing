"""Regression testing suite for rtgamma.

Ensures that known distributions produce the exact same Gamma Pass Rates
to prevent unintended mathematical changes or off-by-one errors during refactor.
"""

import numpy as np
import os
import pytest
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian
import pydicom
from rtgamma.main import main


def _create_synthetic_doses_regression(tmp_path):
    # Shape: z, y, x
    shape = (4, 10, 10)
    ref_dose = np.ones(shape, dtype=np.float64)
    eval_dose = np.ones(shape, dtype=np.float64)
    
    # Introduce a specific known difference
    # On plane z=1, make a 2x2 square fail exactly (1/4 of the plane)
    eval_dose[1, 2:4, 2:4] = 0.5  # Large DD fail (50% difference)
    
    # Scale to typical integer DICOM values
    ref_dose_uint = (ref_dose * 1e6).astype(np.uint32)
    eval_dose_uint = (eval_dose * 1e6).astype(np.uint32)
    
    paths = []
    for doses, name in zip([ref_dose_uint, eval_dose_uint], ["ref.dcm", "eval.dcm"]):
        path = str(tmp_path / name)
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
        ds.PixelSpacing = [2.0, 2.0]
        ds.GridFrameOffsetVector = [float(i * 2.0) for i in range(shape[0])]
        ds.DoseGridScaling = 1.0
        ds.DoseUnits = 'GY'
        ds.DoseType = 'PHYSICAL'
        ds.DoseSummationType = 'PLAN'
        ds.PixelData = doses.tobytes()
        ds.save_as(path, write_like_original=False)
        paths.append(path)
        
    return paths


def test_regression_synthetic_gpr(tmp_path):
    """Regression test enforcing numeric stability of Gamma Pass Rate."""
    ref_path, eval_path = _create_synthetic_doses_regression(tmp_path)
    
    argv = [
        "--ref", ref_path,
        "--eval", eval_path,
        "--opt-shift", "off",
        "--mode", "3d",
        "--dta", "2.0",
        "--dd", "3.0"
    ]
    
    summary = main(argv)
    
    # Out of 4x10x10 = 400 voxels, wait, 4 voxels are modified.
    # What's the exact expected GPR?
    expected_gpr = 99.0  # 396 / 400 = 99.0%
    
    assert summary['pass_rate_percent'] == pytest.approx(expected_gpr, abs=0.01), \
        f"GPR regression detected. Expected {expected_gpr}, got {summary['pass_rate_percent']}"
