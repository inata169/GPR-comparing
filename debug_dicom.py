import pydicom
import numpy as np
import sys

def compare_dicom_files(file1, file2):
    ds1 = pydicom.dcmread(file1, force=True)
    ds2 = pydicom.dcmread(file2, force=True)

    # Workaround for files with missing TransferSyntaxUID
    if not hasattr(ds1.file_meta, 'TransferSyntaxUID'):
        ds1.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
    if not hasattr(ds2.file_meta, 'TransferSyntaxUID'):
        ds2.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

    tags_to_compare = [
        'ImagePositionPatient',
        'ImageOrientationPatient',
        'PixelSpacing',
        'Rows',
        'Columns',
        'NumberOfFrames',
        'DoseGridScaling',
        'DoseUnits',
    ]

    print(f"Comparing {file1} and {file2}\n")

    for tag in tags_to_compare:
        try:
            val1 = getattr(ds1, tag, 'N/A')
            val2 = getattr(ds2, tag, 'N/A')
            print(f"{tag}:")
            print(f"  File 1: {val1}")
            print(f"  File 2: {val2}")
            if str(val1) != str(val2):
                print("  --> MISMATCH")
            print("-"*20)
        except Exception as e:
            print(f"Could not compare tag {tag}: {e}")

    print("GridFrameOffsetVector:")
    gfov1 = ds1.GridFrameOffsetVector
    gfov2 = ds2.GridFrameOffsetVector
    print(f"  File 1 (len {len(gfov1)}): {gfov1[:5]}...")
    print(f"  File 2 (len {len(gfov2)}): {gfov2[:5]}...")
    if not np.allclose(np.array(gfov1, dtype=float), np.array(gfov2, dtype=float)):
        print("  --> MISMATCH")
    print("-"*20)

    # Compare dose arrays
    dose1 = ds1.pixel_array.astype(np.float64) * ds1.DoseGridScaling
    dose2 = ds2.pixel_array.astype(np.float64) * ds2.DoseGridScaling

    print("Dose Array Comparison:")
    print(f"  File 1 - Min: {np.min(dose1):.4f}, Max: {np.max(dose1):.4f}, Mean: {np.mean(dose1):.4f}")
    print(f"  File 2 - Min: {np.min(dose2):.4f}, Max: {np.max(dose2):.4f}, Mean: {np.mean(dose2):.4f}")
    print("-"*20)

    print("First 5 dose values of first frame:")
    print(f"  File 1: {dose1[0, 0, :5]}")
    print(f"  File 2: {dose2[0, 0, :5]}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python debug_dicom.py <file1> <file2>")
        sys.exit(1)
    
    compare_dicom_files(sys.argv[1], sys.argv[2])
