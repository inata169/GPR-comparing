#!/usr/bin/env python
import os
from typing import List, Tuple

from rtgamma.io_dicom import load_rtdose
from scripts.compare_rtdose_headers import summarize, project_origin_delta, orientation_similarity  # reuse helpers


def summarize_pair(a_path: str, b_path: str):
    ma = load_rtdose(a_path)
    mb = load_rtdose(b_path)
    sa = summarize(ma)
    sb = summarize(mb)
    dx, dy, dz = project_origin_delta(ma, mb)
    mindot = orientation_similarity(ma, mb)
    return sa, sb, (dx, dy, dz), mindot


def hypothesis(sa, sb, dxyz, mindot) -> str:
    notes: List[str] = []
    # FoR differences
    if sa.get('for_uid') and sb.get('for_uid') and sa['for_uid'] != sb['for_uid']:
        notes.append('FoR differs')
    # Large translational delta
    if any(abs(v) > 50 for v in dxyz):
        notes.append('Large origin delta (>50 mm)')
    # Orientation mismatch
    if mindot < 0.99:
        notes.append('Orientation mismatch (min dot < 0.99)')
    # Dose unit mismatch
    if sa.get('dose_units') != sb.get('dose_units'):
        notes.append('DoseUnits differ')
    # SSD/SCD(SAD) hypothesis
    if 'Large origin delta (>50 mm)' in notes and mindot >= 0.99:
        notes.append('Likely SSD/SCD(SAD) setup discrepancy')
    return '; '.join(notes) if notes else ''


def main():
    pairs: List[Tuple[str, str, str]] = [
        ('dicom/Test01/RTDOSE_2.16.840.1.114337.1.2604.1760077605.3.dcm',
         'dicom/Test01/RTDOSE_2.16.840.1.114337.1.2604.1760079109.3.dcm', 'Test01'),
        ('dicom/Test02/PHITS_Iris_10_rtdose.dcm',
         'dicom/Test02/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm', 'Test02'),
        ('dicom/Test03/RTDOSE_2.16.840.1.114337.1.2604.1760077605.4.dcm',
         'dicom/Test03/RTDOSE_2.16.840.1.114337.1.2604.1760077605.5.dcm', 'Test03'),
        ('dicom/Test04/RTDOSE_2.16.840.1.114337.1.1224.1760489141.2-6x.dcm',
         'dicom/Test04/RTDOSE_2.16.840.1.114337.1.1224.1760489209.2-10x.dcm', 'Test04'),
    ]

    out_dir = 'phits-linac-validation/output/rtgamma'
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'headers_summary.md')

    lines: List[str] = []
    lines.append('# RTDOSE Header Summary (Test01–04)')
    lines.append('')
    lines.append('| Pair | FoR same | origin_delta_projected_mm (dx,dy,dz) | orientation_min_dot | Hypothesis |')
    lines.append('|---|---:|---|---:|---|')

    for a, b, label in pairs:
        sa, sb, dxyz, mindot = summarize_pair(a, b)
        same_for = (sa.get('for_uid') and sb.get('for_uid') and sa['for_uid'] == sb['for_uid'])
        hyp = hypothesis(sa, sb, dxyz, mindot)
        lines.append(f"| {label} | {str(bool(same_for))} | ({dxyz[0]:.1f}, {dxyz[1]:.1f}, {dxyz[2]:.1f}) | {mindot:.3f} | {hyp} |")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()

