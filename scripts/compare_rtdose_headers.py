#!/usr/bin/env python
import argparse
import os
import numpy as np

from rtgamma.io_dicom import load_rtdose, load_rtplan


def summarize(meta):
    ds = meta['dataset']
    rows, cols = int(ds.Rows), int(ds.Columns)
    nframes = int(getattr(ds, 'NumberOfFrames', 1))
    ipp = meta['ipp']
    r, c, s = meta['row_dir'], meta['col_dir'], meta['slice_dir']
    row_spacing, col_spacing = meta['row_spacing'], meta['col_spacing']
    z_offsets = meta['z_offsets']
    x_mm, y_mm, z_mm = meta['x_coords_mm'], meta['y_coords_mm'], meta['z_coords_mm']

    # World-space extents (LPS) along each axis using corners
    def world_point(j, i, k):
        return ipp + j * row_spacing * r + i * col_spacing * c + z_offsets[k] * s

    corners = [
        world_point(0, 0, 0),
        world_point(rows - 1, 0, 0),
        world_point(0, cols - 1, 0),
        world_point(0, 0, z_offsets.size - 1),
        world_point(rows - 1, cols - 1, 0),
        world_point(rows - 1, 0, z_offsets.size - 1),
        world_point(0, cols - 1, z_offsets.size - 1),
        world_point(rows - 1, cols - 1, z_offsets.size - 1),
    ]
    corners = np.stack(corners, axis=0)
    mins = corners.min(axis=0)
    maxs = corners.max(axis=0)
    center = (mins + maxs) / 2.0

    out = {
        'path': os.path.basename(getattr(ds, 'filename', '')),
        'modality': getattr(ds, 'Modality', ''),
        'dose_units': getattr(ds, 'DoseUnits', ''),
        'dose_grid_scaling': float(getattr(ds, 'DoseGridScaling', 1.0)),
        'shape_zyx': (z_offsets.size, rows, cols),
        'pixel_spacing_rc_mm': (row_spacing, col_spacing),
        'z_offsets_stats_mm': (float(z_offsets.min()), float(z_offsets.max()), float(np.median(np.diff(z_offsets)) if z_offsets.size > 1 else 0.0)),
        'ipp_lps_mm': tuple(map(float, ipp)),
        'row_dir': tuple(map(float, r)),
        'col_dir': tuple(map(float, c)),
        'slice_dir': tuple(map(float, s)),
        'for_uid': str(getattr(ds, 'FrameOfReferenceUID', '')) or None,
        'ref_plan_uid': str(getattr(getattr(ds, 'ReferencedRTPlanSequence', [{}])[0], 'ReferencedSOPInstanceUID', '')) if hasattr(ds, 'ReferencedRTPlanSequence') else None,
        'world_bbox_min_lps_mm': tuple(map(float, mins)),
        'world_bbox_max_lps_mm': tuple(map(float, maxs)),
        'world_center_lps_mm': tuple(map(float, center)),
    }
    return out


def project_origin_delta(meta_a, meta_b):
    # delta from b to a in ref (a) axes
    d = meta_a['ipp'] - meta_b['ipp']
    dx = float(np.dot(d, meta_a['col_dir']))
    dy = float(np.dot(d, meta_a['row_dir']))
    dz = float(np.dot(d, meta_a['slice_dir']))
    return dx, dy, dz


def orientation_similarity(meta_a, meta_b):
    dot_row = float(abs(np.dot(meta_a['row_dir'], meta_b['row_dir'])))
    dot_col = float(abs(np.dot(meta_a['col_dir'], meta_b['col_dir'])))
    dot_sli = float(abs(np.dot(meta_a['slice_dir'], meta_b['slice_dir'])))
    return min(dot_row, dot_col, dot_sli)


def render_markdown(a, b, dxdyz, mindot, plan_a=None, plan_b=None):
    lines = []
    lines.append("# RTDOSE Header Comparison")
    lines.append("")
    lines.append("| Key | A (ref) | B (eval) |")
    lines.append("|---|---|---|")
    def row(k, fa, fb):
        lines.append(f"| {k} | {fa} | {fb} |")

    row('path', a['path'], b['path'])
    row('modality', a['modality'], b['modality'])
    row('dose_units', a['dose_units'], b['dose_units'])
    row('dose_grid_scaling', a['dose_grid_scaling'], b['dose_grid_scaling'])
    row('shape_zyx', a['shape_zyx'], b['shape_zyx'])
    row('pixel_spacing_rc_mm', a['pixel_spacing_rc_mm'], b['pixel_spacing_rc_mm'])
    row('z_offsets_stats_mm (min,max,median_step)', a['z_offsets_stats_mm'], b['z_offsets_stats_mm'])
    row('FrameOfReferenceUID', a['for_uid'], b['for_uid'])
    row('ReferencedRTPlanUID', a['ref_plan_uid'], b['ref_plan_uid'])
    row('IPP (LPS mm)', a['ipp_lps_mm'], b['ipp_lps_mm'])
    row('row_dir', a['row_dir'], b['row_dir'])
    row('col_dir', a['col_dir'], b['col_dir'])
    row('slice_dir', a['slice_dir'], b['slice_dir'])
    row('world_bbox_min_lps_mm', a['world_bbox_min_lps_mm'], b['world_bbox_min_lps_mm'])
    row('world_bbox_max_lps_mm', a['world_bbox_max_lps_mm'], b['world_bbox_max_lps_mm'])
    row('world_center_lps_mm', a['world_center_lps_mm'], b['world_center_lps_mm'])

    lines.append("")
    lines.append("## Derived")
    lines.append("")
    row('origin_delta_projected_mm (dx,dy,dz) along A', dxdyz, '')
    row('orientation_min_dot', mindot, '')
    # Optional plan-derived info
    if plan_a is not None or plan_b is not None:
        lines.append("")
        lines.append("## RTPLAN (Optional)")
        lines.append("")
        def fmt_iso(p):
            v = p.get('isocenter_mean_lps_mm') if p else None
            return tuple(map(float, v)) if v is not None else None
        def fmt_mean(x):
            return float(x) if x is not None else None
        a_iso = fmt_iso(plan_a)
        b_iso = fmt_iso(plan_b)
        row('plan_isocenter_mean_lps_mm', a_iso, b_iso)
        row('plan_sad_mm_mean', fmt_mean(plan_a.get('sad_mm_mean') if plan_a else None), fmt_mean(plan_b.get('sad_mm_mean') if plan_b else None))
        row('plan_ssd_mm_mean', fmt_mean(plan_a.get('ssd_mm_mean') if plan_a else None), fmt_mean(plan_b.get('ssd_mm_mean') if plan_b else None))
        # Deltas
        if a_iso is not None and b_iso is not None:
            delta = tuple(float(ai - bi) for ai, bi in zip(a_iso, b_iso))
            mag = float(np.sqrt(sum((ai - bi)**2 for ai, bi in zip(a_iso, b_iso))))
            row('plan_isocenter_delta_lps_mm (A-B)', delta, '')
            row('plan_isocenter_delta_mag_mm', mag, '')
    lines.append("")
    # Heuristic notes
    notes = []
    if a['for_uid'] and b['for_uid'] and a['for_uid'] != b['for_uid']:
        notes.append("FoR UID differs: suspected different geometry frames.")
    if abs(dxdyz[0]) > 50 or abs(dxdyz[1]) > 50 or abs(dxdyz[2]) > 50:
        notes.append("Large origin delta (>50 mm): check SSD/SAD/iso setup and plan alignment.")
    if mindot < 0.99:
        notes.append("Orientation mismatch (min dot < 0.99): check IOP.")
    if a['dose_units'] != b['dose_units']:
        notes.append("DoseUnits differ: absolute scaling comparison may be invalid.")
    if notes:
        lines.append("### Notes")
        for n in notes:
            lines.append(f"- {n}")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description='Compare two RTDOSE DICOM headers and geometry')
    ap.add_argument('--a', required=True, help='Path to reference RTDOSE DICOM')
    ap.add_argument('--b', required=True, help='Path to evaluation RTDOSE DICOM')
    ap.add_argument('--out', required=True, help='Output markdown path')
    ap.add_argument('--plan-a', help='Optional: Path to reference RTPLAN DICOM')
    ap.add_argument('--plan-b', help='Optional: Path to evaluation RTPLAN DICOM')
    args = ap.parse_args()

    meta_a = load_rtdose(args.a)
    meta_b = load_rtdose(args.b)

    summ_a = summarize(meta_a)
    summ_b = summarize(meta_b)
    dxdyz = project_origin_delta(meta_a, meta_b)
    mindot = orientation_similarity(meta_a, meta_b)
    plan_a = load_rtplan(args.plan_a) if args.plan_a else None
    plan_b = load_rtplan(args.plan_b) if args.plan_b else None
    md = render_markdown(summ_a, summ_b, dxdyz, mindot, plan_a=plan_a, plan_b=plan_b)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(md)


if __name__ == '__main__':
    main()
