"""Privacy-conscious, versioned runtime provenance for gamma reports."""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from .settings import REPORT_SCHEMA_VERSION, GammaSettings


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _git_value(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ['git', '-C', str(root), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


def _application_identity() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    explicit_version = os.environ.get('GPR_COMPARING_VERSION', '').strip()
    if explicit_version:
        version = explicit_version
        version_source = 'environment'
    else:
        try:
            version = importlib.metadata.version('GPR-comparing')
            version_source = 'installed-package'
        except importlib.metadata.PackageNotFoundError:
            version = _git_value(root, 'describe', '--tags', '--always') or 'unknown'
            version_source = 'git-describe' if version != 'unknown' else 'unavailable'

    status = _git_value(root, 'status', '--porcelain', '--untracked-files=no')
    return {
        'name': 'GPR-comparing',
        'version': version,
        'version_source': version_source,
        'git_commit': _git_value(root, 'rev-parse', 'HEAD'),
        'git_dirty': bool(status) if status is not None else None,
    }


def _float_list(values: Any) -> list[float]:
    return [float(value) for value in values]


def _finite_or_none(value: float) -> float | None:
    numeric = float(value)
    return numeric if np.isfinite(numeric) else None


def dicom_grid_summary(meta: dict[str, Any]) -> dict[str, Any]:
    dataset = meta['dataset']
    offsets = np.asarray(meta['z_offsets'], dtype=float)
    return {
        'shape_kji': [int(value) for value in meta['dose'].shape],
        'dose_units': str(meta.get('units', '')),
        'image_position_patient': _float_list(meta['ipp']),
        'image_orientation_patient': _float_list(dataset.ImageOrientationPatient),
        'pixel_spacing_mm': _float_list(dataset.PixelSpacing),
        'grid_frame_offset_vector': {
            'count': int(offsets.size),
            'first_mm': float(offsets[0]) if offsets.size else None,
            'last_mm': float(offsets[-1]) if offsets.size else None,
            'strictly_increasing': bool(np.all(np.diff(offsets) > 0)),
        },
        'frame_of_reference_uid_present': bool(str(getattr(dataset, 'FrameOfReferenceUID', ''))),
    }


def build_provenance(
    *,
    started_utc: str,
    ended_utc: str,
    elapsed_seconds: float,
    ref_path: str,
    eval_path: str,
    meta_ref: dict[str, Any],
    meta_eval: dict[str, Any],
    settings: GammaSettings,
    engine_version: str,
    mode: str,
    plane: str | None,
    plane_index: int | None,
    normalisation_value: float,
    best_shift_mm: tuple[float, float, float],
    best_shift_lps_mm: tuple[float, float, float],
    shift_candidate_count: int,
    warnings: list[str],
    rtstruct_supplied: bool,
    roi_names: list[str] | None,
    threads: int | None,
    gpu: str,
    seed: int | None,
    cutoff_mask: str,
    low_dose_exclusion: float | None,
    spacing_override: str | None,
    tolerance: float,
    orientation_min_dot: float,
) -> dict[str, Any]:
    resolved_ref_path = meta_ref.get('source_path', ref_path)
    resolved_eval_path = meta_eval.get('source_path', eval_path)
    return {
        'schema_version': REPORT_SCHEMA_VERSION,
        'application': _application_identity(),
        'execution': {
            'started_utc': started_utc,
            'ended_utc': ended_utc,
            'elapsed_seconds': float(elapsed_seconds),
        },
        'runtime': {
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'os': platform.system(),
            'os_release': platform.release(),
            'architecture': platform.machine(),
        },
        'engine': {'name': settings.engine, 'version': engine_version},
        'inputs': {
            'reference': {
                'role': 'reference',
                'basename': Path(resolved_ref_path).name,
                'sha256': sha256_file(resolved_ref_path),
            },
            'evaluation': {
                'role': 'evaluation',
                'basename': Path(resolved_eval_path).name,
                'sha256': sha256_file(resolved_eval_path),
            },
            'rtstruct_supplied': bool(rtstruct_supplied),
            'roi_names': list(roi_names) if roi_names else [],
        },
        'analysis': {
            'mode': mode,
            'plane': plane,
            'plane_index': plane_index,
            'gamma': settings.as_dict(),
            'resolved_normalisation': float(normalisation_value),
            'selected_shift_axis_mm': [float(value) for value in best_shift_mm],
            'selected_shift_lps_mm': [float(value) for value in best_shift_lps_mm],
            'shift_candidate_count': int(shift_candidate_count),
            'execution_controls': {
                'threads_requested': threads,
                'threads_applied': False,
                'gpu_requested': gpu,
                'gpu_applied': False,
                'seed_requested': seed,
                'seed_applied': False,
            },
            'parsed_but_not_applied': {
                'cutoff_mask': cutoff_mask,
                'low_dose_exclusion': low_dose_exclusion,
                'spacing_override': spacing_override,
                'tolerance': float(tolerance),
            },
        },
        'geometry': {
            'reference': dicom_grid_summary(meta_ref),
            'evaluation': dicom_grid_summary(meta_eval),
            'orientation_min_dot': _finite_or_none(orientation_min_dot),
        },
        'warnings': list(warnings),
        'privacy': {
            'absolute_paths_recorded': False,
            'dicom_demographics_recorded': False,
            'input_identity': 'basename-and-sha256',
        },
    }
