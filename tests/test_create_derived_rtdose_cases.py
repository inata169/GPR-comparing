from pathlib import Path

import numpy as np
import pydicom
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRBigEndian, ExplicitVRLittleEndian, generate_uid

from scripts.create_derived_rtdose_cases import _write_shift_variant


def _source_rtdose(path: Path, transfer_syntax_uid: str) -> FileDataset:
    little_endian = transfer_syntax_uid == ExplicitVRLittleEndian
    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = transfer_syntax_uid
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds = FileDataset(
        str(path),
        {},
        file_meta=file_meta,
        preamble=b'\0' * 128,
        is_implicit_VR=False,
        is_little_endian=little_endian,
    )
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SeriesInstanceUID = generate_uid()
    ds.Modality = 'RTDOSE'
    ds.Rows = 2
    ds.Columns = 3
    ds.NumberOfFrames = 1
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.PixelSpacing = [1.0, 1.0]
    ds.DoseGridScaling = 1.0
    dtype = '<u2' if little_endian else '>u2'
    pixels = np.array([[[1, 2, 3], [4, 5, 6]]], dtype=dtype)
    ds.PixelData = pixels.tobytes()
    ds.save_as(path, write_like_original=False)
    return pydicom.dcmread(path)


@pytest.mark.parametrize(
    'transfer_syntax_uid',
    [ExplicitVRLittleEndian, ExplicitVRBigEndian],
)
def test_shift_variant_preserves_uncompressed_pixel_byte_order(
    tmp_path,
    transfer_syntax_uid,
):
    source = _source_rtdose(tmp_path / 'source.dcm', transfer_syntax_uid)
    output = tmp_path / 'shifted.dcm'

    _write_shift_variant(
        source,
        output,
        source_sha256='0' * 64,
        case_label='byte-order',
        shift_mm=1.0,
    )

    derived = pydicom.dcmread(output)
    assert derived.file_meta.TransferSyntaxUID == transfer_syntax_uid
    np.testing.assert_array_equal(
        derived.pixel_array,
        np.array([[0, 1, 2], [0, 4, 5]], dtype=np.uint16),
    )
