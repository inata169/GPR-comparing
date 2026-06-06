#!/usr/bin/env python
"""Create a local synthetic DICOM-RT dataset for Fast Viewer smoke checks.

The generated files contain only dummy patient/study values and are intended for
local manual testing. By default they are written under test_data_local/, which
is ignored by git.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, RTDoseStorage, RTStructureSetStorage


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "test_data_local" / "synthetic_rt_fast_viewer"
UID_PREFIX = "1.2.826.0.1.3680043.10.54321."


def _uid(suffix: str) -> str:
    return UID_PREFIX + suffix


def _file_dataset(path: Path, sop_class_uid: str, sop_instance_uid: str) -> FileDataset:
    meta = FileMetaDataset()
    meta.FileMetaInformationVersion = b"\x00\x01"
    meta.MediaStorageSOPClassUID = sop_class_uid
    meta.MediaStorageSOPInstanceUID = sop_instance_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = _uid("999")
    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.SOPClassUID = sop_class_uid
    ds.SOPInstanceUID = sop_instance_uid
    return ds


def _common_patient_study(ds: Dataset, study_uid: str, frame_uid: str, series_uid: str) -> None:
    now = datetime.now()
    ds.PatientName = "SYNTHETIC^FASTVIEWER"
    ds.PatientID = "SYNTH_FAST_VIEWER_001"
    ds.PatientBirthDate = ""
    ds.PatientSex = "O"
    ds.StudyInstanceUID = study_uid
    ds.FrameOfReferenceUID = frame_uid
    ds.StudyID = "SYNTH001"
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.AccessionNumber = ""
    ds.SeriesInstanceUID = series_uid
    ds.Manufacturer = "Synthetic"
    ds.InstitutionName = "Synthetic Local Test"


def _dose_array(shape: tuple[int, int, int], eval_delta: bool) -> np.ndarray:
    nz, ny, nx = shape
    z, y, x = np.indices(shape, dtype=np.float32)
    cx = (nx - 1) / 2.0
    cy = (ny - 1) / 2.0
    cz = (nz - 1) / 2.0
    r2 = ((x - cx) / 18.0) ** 2 + ((y - cy) / 18.0) ** 2 + ((z - cz) / 5.0) ** 2
    dose = 2.0 * np.exp(-r2).astype(np.float32)
    if eval_delta:
        dose = dose + 0.04 * np.exp(-(((x - cx - 5) / 10.0) ** 2 + ((y - cy) / 10.0) ** 2))
    return dose.astype(np.float32)


def write_ct_series(out_dir: Path, study_uid: str, frame_uid: str, shape: tuple[int, int, int], spacing: tuple[float, float, float]) -> list[str]:
    ct_dir = out_dir / "CT"
    ct_dir.mkdir(parents=True, exist_ok=True)
    nz, ny, nx = shape
    sx, sy, sz = spacing
    origin = np.array([-sx * nx / 2.0, -sy * ny / 2.0, -sz * nz / 2.0], dtype=float)
    series_uid = _uid("10")
    sop_uids = []

    z, y, x = np.indices(shape, dtype=np.float32)
    body = (((x - nx / 2) / 24.0) ** 2 + ((y - ny / 2) / 24.0) ** 2 + ((z - nz / 2) / 8.0) ** 2) < 1.0
    ct = np.where(body, 40.0, -900.0).astype(np.int16)

    for k in range(nz):
        sop_uid = _uid(f"10.{k + 1}")
        sop_uids.append(sop_uid)
        path = ct_dir / f"CT_{k + 1:03d}.dcm"
        ds = _file_dataset(path, CTImageStorage, sop_uid)
        _common_patient_study(ds, study_uid, frame_uid, series_uid)
        ds.Modality = "CT"
        ds.SeriesNumber = 1
        ds.InstanceNumber = k + 1
        ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]
        ds.Rows = ny
        ds.Columns = nx
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.ImagePositionPatient = [float(origin[0]), float(origin[1]), float(origin[2] + k * sz)]
        ds.PixelSpacing = [sy, sx]
        ds.SliceThickness = sz
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.RescaleSlope = 1
        ds.RescaleIntercept = 0
        ds.RescaleType = "HU"
        ds.PixelData = ct[k].tobytes()
        ds.save_as(path, write_like_original=False)
    return sop_uids


def write_rtdose(path: Path, study_uid: str, frame_uid: str, series_uid: str, instance_uid: str, dose: np.ndarray, spacing: tuple[float, float, float]) -> None:
    nz, ny, nx = dose.shape
    sx, sy, sz = spacing
    origin = [-sx * nx / 2.0, -sy * ny / 2.0, -sz * nz / 2.0]
    scale = 0.001
    stored = np.clip(np.round(dose / scale), 0, np.iinfo(np.uint32).max).astype(np.uint32)

    ds = _file_dataset(path, RTDoseStorage, instance_uid)
    _common_patient_study(ds, study_uid, frame_uid, series_uid)
    ds.Modality = "RTDOSE"
    ds.SeriesNumber = 20
    ds.InstanceNumber = 1
    ds.ImageType = ["DERIVED", "PRIMARY", "DOSE"]
    ds.Rows = ny
    ds.Columns = nx
    ds.NumberOfFrames = nz
    ds.FrameIncrementPointer = [0x3004000C]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.ImagePositionPatient = origin
    ds.PixelSpacing = [sy, sx]
    ds.SliceThickness = sz
    ds.GridFrameOffsetVector = [float(k * sz) for k in range(nz)]
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 32
    ds.BitsStored = 32
    ds.HighBit = 31
    ds.PixelRepresentation = 0
    ds.DoseGridScaling = scale
    ds.DoseUnits = "GY"
    ds.DoseType = "PHYSICAL"
    ds.DoseSummationType = "PLAN"
    ds.PixelData = stored.tobytes()
    ds.save_as(path, write_like_original=False)


def write_rtstruct(path: Path, study_uid: str, frame_uid: str, ct_sop_uids: list[str], spacing: tuple[float, float, float], shape: tuple[int, int, int]) -> None:
    nz, ny, nx = shape
    sx, sy, sz = spacing
    origin = np.array([-sx * nx / 2.0, -sy * ny / 2.0, -sz * nz / 2.0], dtype=float)
    series_uid = _uid("30")
    ds = _file_dataset(path, RTStructureSetStorage, _uid("30.1"))
    _common_patient_study(ds, study_uid, frame_uid, series_uid)
    ds.Modality = "RTSTRUCT"
    ds.SeriesNumber = 30
    ds.InstanceNumber = 1
    ds.StructureSetLabel = "SYNTH_RTSTRUCT"
    ds.StructureSetName = "Synthetic Fast Viewer Structure Set"
    ds.StructureSetDate = ds.StudyDate
    ds.StructureSetTime = ds.StudyTime

    roi = Dataset()
    roi.ROINumber = 1
    roi.ReferencedFrameOfReferenceUID = frame_uid
    roi.ROIName = "SYNTH_ROI"
    roi.ROIGenerationAlgorithm = "MANUAL"
    ds.StructureSetROISequence = Sequence([roi])

    z_index = nz // 2
    z_mm = float(origin[2] + z_index * sz)
    x0, x1 = -18.0, 18.0
    y0, y1 = -18.0, 18.0
    contour_points = [
        x0, y0, z_mm,
        x1, y0, z_mm,
        x1, y1, z_mm,
        x0, y1, z_mm,
    ]
    contour = Dataset()
    contour.ContourGeometricType = "CLOSED_PLANAR"
    contour.NumberOfContourPoints = 4
    contour.ContourData = [float(v) for v in contour_points]
    if ct_sop_uids:
        img_ref = Dataset()
        img_ref.ReferencedSOPClassUID = CTImageStorage
        img_ref.ReferencedSOPInstanceUID = ct_sop_uids[z_index]
        contour.ContourImageSequence = Sequence([img_ref])

    roi_contour = Dataset()
    roi_contour.ReferencedROINumber = 1
    roi_contour.ROIDisplayColor = [255, 64, 64]
    roi_contour.ContourSequence = Sequence([contour])
    ds.ROIContourSequence = Sequence([roi_contour])

    obs = Dataset()
    obs.ObservationNumber = 1
    obs.ReferencedROINumber = 1
    obs.RTROIInterpretedType = "ORGAN"
    obs.ROIInterpreter = ""
    ds.RTROIObservationsSequence = Sequence([obs])

    ref_for = Dataset()
    ref_for.FrameOfReferenceUID = frame_uid
    ds.ReferencedFrameOfReferenceSequence = Sequence([ref_for])
    ds.save_as(path, write_like_original=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create local synthetic CT/RTDOSE/RTSTRUCT files for Fast Viewer.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory. Default: test_data_local/synthetic_rt_fast_viewer")
    parser.add_argument("--identical-eval", action="store_true", help="Make Eval dose identical to Ref dose.")
    parser.add_argument("--no-rtstruct", action="store_true", help="Skip synthetic RTSTRUCT generation.")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    shape = (16, 64, 64)
    spacing = (2.0, 2.0, 3.0)
    study_uid = _uid("1")
    frame_uid = _uid("2")

    ct_sop_uids = write_ct_series(out_dir, study_uid, frame_uid, shape, spacing)
    ref = _dose_array(shape, eval_delta=False)
    eval_dose = ref.copy() if args.identical_eval else _dose_array(shape, eval_delta=True)
    ref_path = out_dir / "RTDOSE_REF.dcm"
    eval_path = out_dir / "RTDOSE_EVAL.dcm"
    write_rtdose(ref_path, study_uid, frame_uid, _uid("20.1"), _uid("20.1.1"), ref, spacing)
    write_rtdose(eval_path, study_uid, frame_uid, _uid("20.2"), _uid("20.2.1"), eval_dose, spacing)

    rtstruct_path = out_dir / "RTSTRUCT_SYNTH.dcm"
    if not args.no_rtstruct:
        write_rtstruct(rtstruct_path, study_uid, frame_uid, ct_sop_uids, spacing, shape)

    print("Synthetic DICOM-RT dataset created.")
    print(f"  CT dir:    {out_dir / 'CT'}")
    print(f"  Ref dose:  {ref_path}")
    print(f"  Eval dose: {eval_path}")
    if not args.no_rtstruct:
        print(f"  RTSTRUCT:  {rtstruct_path}")
    print()
    cmd = [
        ".\\.venv\\Scripts\\python.exe",
        "scripts\\gamma_viewer_fast.py",
        "--ct", str(out_dir / "CT"),
        "--ref", str(ref_path),
        "--eval", str(eval_path),
        "--dd", "3",
        "--dta", "2",
        "--cutoff", "10",
    ]
    if not args.no_rtstruct:
        cmd += ["--rtstruct", str(rtstruct_path), "--roi", "SYNTH_ROI"]
    print("Fast Viewer command:")
    print(" ".join(f'"{part}"' if " " in part else part for part in cmd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
