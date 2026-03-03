import pydicom
import glob
import sys
import traceback

with open('temp/_info_2024.txt', 'w', encoding='utf-8') as f:
    sys.stdout = f
    try:
        print('=== RTSTRUCT ===')
        for path in glob.glob('dicom/2024101700/RTSTRUCT*'):
            try:
                rs = pydicom.dcmread(path, force=True)
                print('File:', path)
                for r in getattr(rs, 'StructureSetROISequence', []):
                    print(f'  [{r.ROINumber}] {r.ROIName}')
            except Exception as e:
                print(f'Error reading {path}: {e}')

        print('\n=== RTDOSE ===')
        for path in glob.glob('dicom/2024101700/RTDOSE*'):
            try:
                rd = pydicom.dcmread(path, force=True)
                dt = getattr(rd, 'DoseSummationType', '?')
                print(f'File: {path} | DoseType: {dt} | Frames: {getattr(rd, "NumberOfFrames", 1)}')
            except Exception as e:
                print(f'Error reading {path}: {e}')
    except Exception as exc:
        traceback.print_exc()
