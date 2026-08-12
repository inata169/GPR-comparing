from pathlib import Path

import numpy as np
import pydicom
import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian

from rtgamma.header_compare import summarize
from rtgamma.io_dicom import (
    RTDoseGeometryError,
    load_rtdose,
    validate_rtdose_pair_geometry,
)
from rtgamma.provenance import sha256_file


def _write_rtdose(
    path: Path,
    *,
    shape=(3, 4, 5),
    ipp=(0.0, 0.0, -10.0),
    iop=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    pixel_spacing=(2.0, 2.5),
    gfov=(0.0, 3.0, 6.0),
    units='GY',
    frame_of_reference_uid=None,
) -> Path:
    ds = FileDataset(
        str(path),
        Dataset(),
        preamble=b'\0' * 128,
        is_implicit_VR=False,
    )
    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    ds.file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    ds.SOPClassUID = ds.file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.Modality = 'RTDOSE'
    ds.Rows = shape[1]
    ds.Columns = shape[2]
    ds.NumberOfFrames = shape[0]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.ImagePositionPatient = list(ipp)
    ds.ImageOrientationPatient = list(iop)
    ds.PixelSpacing = list(pixel_spacing)
    ds.GridFrameOffsetVector = list(gfov)
    ds.DoseGridScaling = 0.001
    ds.DoseUnits = units
    if frame_of_reference_uid is not None:
        ds.FrameOfReferenceUID = frame_of_reference_uid
    ds.DoseType = 'PHYSICAL'
    ds.DoseSummationType = 'PLAN'
    pixels = np.arange(np.prod(shape), dtype=np.uint16).reshape(shape)
    ds.PixelData = pixels.tobytes()
    ds.save_as(path, write_like_original=False)
    return path


def test_descending_gfov_sorts_frames_and_offsets_together(tmp_path):
    path = _write_rtdose(tmp_path / 'descending.dcm', gfov=(6.0, 3.0, 0.0))
    meta = load_rtdose(str(path))

    np.testing.assert_array_equal(meta['z_offsets'], [0.0, 3.0, 6.0])
    assert meta['dose'][0, 0, 0] == pytest.approx(40 * 0.001)
    assert meta['dose'][2, 0, 0] == pytest.approx(0.0)


def test_loader_retains_digest_of_loaded_snapshot(tmp_path):
    path = _write_rtdose(tmp_path / 'snapshot.dcm')
    meta = load_rtdose(str(path))
    loaded_digest = meta['source_sha256']

    assert loaded_digest == sha256_file(path)
    path.write_bytes(b'replaced after loading')
    assert meta['source_sha256'] == loaded_digest
    assert meta['source_sha256'] != sha256_file(path)


def test_header_summary_uses_snapshot_source_path(tmp_path):
    path = _write_rtdose(tmp_path / 'summary.dcm')
    meta = load_rtdose(str(path))

    assert summarize(meta)['path'] == 'summary.dcm'


def test_absolute_axial_gfov_is_converted_to_offsets(tmp_path):
    path = _write_rtdose(
        tmp_path / 'absolute.dcm',
        ipp=(0.0, 0.0, -10.0),
        gfov=(-10.0, -7.0, -4.0),
    )
    meta = load_rtdose(str(path))
    np.testing.assert_array_equal(meta['z_offsets'], [0.0, 3.0, 6.0])


@pytest.mark.parametrize(
    ('field', 'value', 'message'),
    [
        ('PixelSpacing', [2.0, 0.0], 'PixelSpacing values must be positive'),
        (
            'ImageOrientationPatient',
            [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            'directions are not orthogonal',
        ),
        (
            'GridFrameOffsetVector',
            [0.0, 3.0, 2.0],
            'must be strictly monotonic',
        ),
    ],
)
def test_invalid_single_grid_geometry_fails_closed(
    tmp_path,
    field,
    value,
    message,
):
    path = _write_rtdose(tmp_path / 'invalid.dcm')
    ds = pydicom.dcmread(path)
    setattr(ds, field, value)
    ds.save_as(path, write_like_original=False)

    with pytest.raises(RTDoseGeometryError, match=message):
        load_rtdose(str(path))


def test_pair_allows_different_origin_and_spacing(tmp_path):
    ref = load_rtdose(str(_write_rtdose(tmp_path / 'ref.dcm')))
    evaluation = load_rtdose(str(_write_rtdose(
        tmp_path / 'eval.dcm',
        ipp=(1.0, -2.0, -9.0),
        pixel_spacing=(1.5, 3.0),
        gfov=(0.0, 2.0, 4.0),
    )))

    assert validate_rtdose_pair_geometry(ref, evaluation) == pytest.approx(1.0)


def test_pair_rejects_dose_units_mismatch(tmp_path):
    ref = load_rtdose(str(_write_rtdose(tmp_path / 'ref.dcm')))
    evaluation = load_rtdose(str(_write_rtdose(
        tmp_path / 'eval.dcm',
        units='RELATIVE',
    )))

    with pytest.raises(RTDoseGeometryError, match='DoseUnits mismatch'):
        validate_rtdose_pair_geometry(ref, evaluation)


def test_pair_rejects_different_orientation(tmp_path):
    ref = load_rtdose(str(_write_rtdose(tmp_path / 'ref.dcm')))
    evaluation = load_rtdose(str(_write_rtdose(
        tmp_path / 'eval.dcm',
        iop=(0.0, 1.0, 0.0, -1.0, 0.0, 0.0),
    )))

    with pytest.raises(
        RTDoseGeometryError,
        match='ImageOrientationPatient directions differ',
    ):
        validate_rtdose_pair_geometry(ref, evaluation)


def test_pair_warns_and_allows_frame_of_reference_mismatch(tmp_path, caplog):
    ref = load_rtdose(str(_write_rtdose(
        tmp_path / 'ref.dcm',
        frame_of_reference_uid=pydicom.uid.generate_uid(),
    )))
    evaluation = load_rtdose(str(_write_rtdose(
        tmp_path / 'eval.dcm',
        frame_of_reference_uid=pydicom.uid.generate_uid(),
    )))

    with caplog.at_level('WARNING'):
        orientation_min_dot = validate_rtdose_pair_geometry(ref, evaluation)

    assert orientation_min_dot == pytest.approx(1.0)
    assert 'FrameOfReferenceUID values differ' in caplog.text
    assert 'continuing with explicit DICOM patient coordinates' in caplog.text
