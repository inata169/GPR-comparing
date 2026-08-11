#!/usr/bin/env python
"""Create deterministic evaluation RTDOSE files from anonymized phantom RTDOSE.

The source file is never modified or copied. Generated files are intended for
local engine-comparison research and should stay under a git-ignored directory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import uuid
from pathlib import Path

import numpy as np
import pydicom
from scipy.ndimage import shift as ndimage_shift

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "test_data_local" / "monaco_derived_gamma_cases"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _derived_uid(source_sha256: str, case_label: str, variant: str, role: str) -> str:
    value = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"gpr-comparing:{source_sha256}:{case_label}:{variant}:{role}",
    )
    return f"2.25.{value.int}"


def _clear_identity(ds: pydicom.dataset.Dataset) -> None:
    ds.remove_private_tags()
    ds.PatientName = "DERIVED^ANONYMIZED_PHANTOM"
    ds.PatientID = "DERIVED_ANONYMIZED_PHANTOM"
    ds.PatientBirthDate = ""
    ds.PatientSex = "O"
    ds.PatientIdentityRemoved = "YES"
    ds.DeidentificationMethod = "Derived from anonymized phantom; identity fields cleared"
    ds.AccessionNumber = ""
    ds.StudyID = "DERIVED_GAMMA"
    ds.StudyDate = "20000101"
    ds.StudyTime = "000000"
    ds.SeriesDate = "20000101"
    ds.SeriesTime = "000000"
    ds.ContentDate = "20000101"
    ds.ContentTime = "000000"
    for keyword in (
        "OtherPatientIDs",
        "OtherPatientIDsSequence",
        "PatientAddress",
        "PatientTelephoneNumbers",
        "ReferringPhysicianName",
        "PerformingPhysicianName",
        "OperatorsName",
        "InstitutionName",
        "InstitutionAddress",
        "InstitutionalDepartmentName",
        "StationName",
    ):
        if keyword in ds:
            del ds[keyword]


def _prepare_derived(
    source: pydicom.dataset.Dataset,
    source_sha256: str,
    case_label: str,
    variant: str,
) -> pydicom.dataset.Dataset:
    ds = copy.deepcopy(source)
    _clear_identity(ds)
    ds.SOPInstanceUID = _derived_uid(source_sha256, case_label, variant, "sop")
    ds.SeriesInstanceUID = _derived_uid(source_sha256, case_label, variant, "series")
    if getattr(ds, "file_meta", None) is not None:
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.ImageType = ["DERIVED", "SECONDARY", "DOSE"]
    ds.SeriesDescription = f"GPR test {case_label} {variant}"
    ds.DerivationDescription = (
        f"Deterministic local research derivative: {variant}. "
        "Not for clinical use."
    )
    ds.InstanceCreationDate = "20000101"
    ds.InstanceCreationTime = "000000"
    return ds


def _write_scale_variant(
    source: pydicom.dataset.Dataset,
    output_path: Path,
    source_sha256: str,
    case_label: str,
    factor: float,
) -> dict:
    variant = f"dose_scale_{factor:.6f}"
    ds = _prepare_derived(source, source_sha256, case_label, variant)
    ds.DoseGridScaling = float(source.DoseGridScaling) * factor
    ds.DoseComment = f"DoseGridScaling x{factor:.6f}; stored pixels unchanged"
    ds.save_as(output_path, write_like_original=False)
    return {
        "name": variant,
        "operation": "multiply_physical_dose",
        "factor": factor,
        "output": output_path.name,
        "sha256": _sha256(output_path),
    }


def _write_shift_variant(
    source: pydicom.dataset.Dataset,
    output_path: Path,
    source_sha256: str,
    case_label: str,
    shift_mm: float,
) -> dict:
    if int(source.PixelRepresentation) != 0 or int(source.BitsAllocated) != 16:
        raise ValueError("Shift variant currently requires unsigned 16-bit RTDOSE pixels")
    if source.file_meta.TransferSyntaxUID.is_compressed:
        raise ValueError("Shift variant requires an uncompressed transfer syntax")

    col_spacing_mm = float(source.PixelSpacing[1])
    shift_columns = shift_mm / col_spacing_mm
    physical_dose = source.pixel_array.astype(np.float64) * float(source.DoseGridScaling)
    shifted_dose = ndimage_shift(
        physical_dose,
        shift=(0.0, 0.0, shift_columns),
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )
    stored = np.rint(shifted_dose / float(source.DoseGridScaling))
    stored = np.clip(stored, 0, np.iinfo(np.uint16).max).astype("<u2")

    variant = f"shift_col_plus_{shift_mm:.3f}mm"
    ds = _prepare_derived(source, source_sha256, case_label, variant)
    ds.PixelData = stored.tobytes()
    ds.DoseComment = f"+{shift_mm:.3f} mm column shift; linear; 0 Gy outside"
    if "SmallestImagePixelValue" in ds:
        ds.SmallestImagePixelValue = int(stored.min())
    if "LargestImagePixelValue" in ds:
        ds.LargestImagePixelValue = int(stored.max())
    ds.save_as(output_path, write_like_original=False)
    return {
        "name": variant,
        "operation": "shift_dose_along_positive_column_direction",
        "shift_mm": shift_mm,
        "pixel_spacing_mm": col_spacing_mm,
        "shift_pixels": shift_columns,
        "interpolation": "linear",
        "outside_fill_dose": 0.0,
        "output": output_path.name,
        "sha256": _sha256(output_path),
    }


def create_case(case_label: str, source_path: Path, output_root: Path) -> dict:
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    source = pydicom.dcmread(source_path)
    if str(source.get("Modality", "")) != "RTDOSE":
        raise ValueError(f"Source is not RTDOSE: {source_path}")

    source_sha256 = _sha256(source_path)
    case_dir = output_root / case_label
    case_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        _write_scale_variant(
            source,
            case_dir / "eval_dose_scale_102.dcm",
            source_sha256,
            case_label,
            1.02,
        ),
        _write_shift_variant(
            source,
            case_dir / "eval_shift_col_plus_1mm.dcm",
            source_sha256,
            case_label,
            1.0,
        ),
    ]
    manifest = {
        "schema_version": 1,
        "purpose": "Local research comparison of gamma engines; not clinical validation",
        "case_label": case_label,
        "source": {
            "basename": source_path.name,
            "sha256": source_sha256,
            "modality": "RTDOSE",
            "shape": [
                int(source.NumberOfFrames),
                int(source.Rows),
                int(source.Columns),
            ],
            "pixel_spacing_mm": [float(value) for value in source.PixelSpacing],
            "dose_units": str(source.DoseUnits),
        },
        "variants": variants,
    }
    manifest_path = case_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _parse_case(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("case must use LABEL=SOURCE_PATH")
    label, source = value.split("=", 1)
    if not label.strip() or not source.strip():
        raise argparse.ArgumentTypeError("case must use LABEL=SOURCE_PATH")
    return label.strip(), Path(source.strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create deterministic local RTDOSE derivatives from anonymized phantom dose"
    )
    parser.add_argument(
        "--case",
        action="append",
        required=True,
        type=_parse_case,
        help="Repeatable LABEL=SOURCE_PATH definition",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    output_root = args.out.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    manifests = [create_case(label, source, output_root) for label, source in args.case]
    index = {
        "schema_version": 1,
        "purpose": "Derived anonymized phantom RTDOSE gamma-engine comparison cases",
        "cases": [
            {
                "case_label": item["case_label"],
                "manifest": f"{item['case_label']}/manifest.json",
            }
            for item in manifests
        ],
    }
    (output_root / "index.json").write_text(
        json.dumps(index, indent=2),
        encoding="utf-8",
    )
    print(f"Created {len(manifests)} case(s) under {output_root}")
    for item in manifests:
        print(f"  {item['case_label']}: {len(item['variants'])} derived RTDOSE files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
