import os
import sys
import json
import argparse
import numpy as np

from .io_dicom import load_rtdose, world_to_index
from .resample import resample_eval_onto_ref
from .gamma import compute_gamma
from .optimize import grid_search_best_shift
from .report import save_summary_csv, save_summary_json, save_summary_markdown
from .viz import save_gamma_map_2d, save_dose_diff_2d


def build_ref_world_coords(meta_ref):
    # Build world coordinate arrays (LPS) for each voxel center in reference grid
    z_mm = meta_ref['z_coords_mm']
    y_mm = meta_ref['y_coords_mm']
    x_mm = meta_ref['x_coords_mm']
    # Construct 3D world coordinate for each grid point: IPP + r*y + c*x + s*z
    ipp = meta_ref['ipp']
    r = meta_ref['row_dir']
    c = meta_ref['col_dir']
    s = meta_ref['slice_dir']
    Y, X, Z = np.meshgrid(y_mm, x_mm, z_mm, indexing='ij')  # shapes: (y,x,z)
    # Reorder later to (z,y,x)
    Pw = (ipp[None, None, None, :]
          + Y[..., None] * r[None, None, None, :]
          + X[..., None] * c[None, None, None, :]
          + Z[..., None] * s[None, None, None, :])
    # Return in array order (z,y,x)
    Pw = np.moveaxis(Pw, 2, 0)  # (z,y,x,3)
    Xw = Pw[..., 0]
    Yw = Pw[..., 1]
    Zw = Pw[..., 2]
    return Xw, Yw, Zw


def main(argv=None):
    parser = argparse.ArgumentParser(description='DICOM RTDOSE gamma analysis (2D/3D) with shift optimization')
    parser.add_argument('--ref', required=True, help='Reference RTDOSE (DICOM)')
    parser.add_argument('--eval', required=True, help='Evaluation RTDOSE (DICOM)')
    parser.add_argument('--mode', choices=['3d', '2d'], default='3d')
    parser.add_argument('--plane', choices=['axial', 'sagittal', 'coronal'])
    parser.add_argument('--plane-index', type=int)

    parser.add_argument('--dd', type=float, default=3.0)
    parser.add_argument('--dta', type=float, default=2.0)
    parser.add_argument('--cutoff', type=float, default=10.0)
    parser.add_argument('--gamma-type', choices=['global', 'local'], default='global')
    parser.add_argument('--norm', choices=['global_max', 'max_ref', 'none'], default='global_max')
    parser.add_argument('--cutoff-mask', choices=['ref', 'eval'], default='ref')
    parser.add_argument('--low-dose-exclusion', type=float)

    parser.add_argument('--opt-shift', choices=['on', 'off'], default='on')
    parser.add_argument('--shift-range', default='x:-3:3:1,y:-3:3:1,z:-3:3:1')
    parser.add_argument('--refine', choices=['none', 'coarse2fine'], default='coarse2fine')

    parser.add_argument('--spacing', help='Override spacing sx,sy,sz in mm (unused default: ref grid)')
    parser.add_argument('--interp', choices=['linear', 'bspline', 'nearest'], default='linear')

    parser.add_argument('--save-gamma-map')
    parser.add_argument('--save-dose-diff')
    parser.add_argument('--report')
    parser.add_argument('--log-level', choices=['INFO', 'DEBUG'], default='INFO')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--threads', type=int)
    parser.add_argument('--gpu', choices=['on', 'off'], default='off')
    parser.add_argument('--tolerance', type=float, default=1e-6)

    args = parser.parse_args(argv)

    meta_ref = load_rtdose(args.ref)
    meta_eval = load_rtdose(args.eval)

    dose_ref = meta_ref['dose']  # (z,y,x)
    dose_eval = meta_eval['dose']

    Xw, Yw, Zw = build_ref_world_coords(meta_ref)

    def world_to_eval_ijk(points):
        ipp = meta_eval['ipp']
        r = meta_eval['row_dir']
        c = meta_eval['col_dir']
        s = meta_eval['slice_dir']
        return world_to_index(ipp, r, c, s, meta_eval['row_spacing'], meta_eval['col_spacing'], meta_eval['z_offsets'], points)

    # Default: resample eval onto ref grid without shift
    eval_on_ref = resample_eval_onto_ref(dose_eval, world_to_eval_ijk, (Xw, Yw, Zw), interp=args.interp, shift_mm=(0, 0, 0))

    best_shift = (0.0, 0.0, 0.0)
    search_log = None
    if args.opt_shift == 'on':
        ref_axes_mm_1d = (meta_ref['z_coords_mm'], meta_ref['y_coords_mm'], meta_ref['x_coords_mm'])
        eval_axes_mm_1d = (meta_eval['z_coords_mm'], meta_eval['y_coords_mm'], meta_eval['x_coords_mm'])

        best_shift, best_pass, extras = grid_search_best_shift(
            ref_axes_mm_1d=ref_axes_mm_1d,
            dose_ref=dose_ref,
            eval_axes_mm_1d=eval_axes_mm_1d,
            dose_eval=dose_eval,
            dd=args.dd,
            dta=args.dta,
            cutoff=args.cutoff,
            norm=args.norm,
            shift_spec=args.shift_range,
        )
        search_log = extras['search_log']
        # After finding the best shift, do a final resampling for map generation
        eval_on_ref = resample_eval_onto_ref(dose_eval, world_to_eval_ijk, (Xw, Yw, Zw), interp=args.interp, shift_mm=best_shift)

    # Final gamma calculation on the optimally shifted and resampled dose grid
    axes_ref_mm = (meta_ref['z_coords_mm'], meta_ref['y_coords_mm'], meta_ref['x_coords_mm'])
    gamma_map, pass_rate, gstats = compute_gamma(
        axes_ref_mm=axes_ref_mm,
        dose_ref=dose_ref,
        axes_eval_mm=axes_ref_mm,  # Now eval is on the ref grid
        dose_eval=eval_on_ref,
        dd_percent=args.dd,
        dta_mm=args.dta,
        cutoff_percent=args.cutoff,
        gamma_type=args.gamma_type,
        norm=args.norm,
        use_pymedphys=True,
    )

    # Outputs
    if args.mode == '2d':
        if not args.plane or args.plane_index is None:
            raise SystemExit('--plane and --plane-index are required in 2d mode')
        if args.plane == 'axial':
            sl = args.plane_index
            g2d = gamma_map[sl, :, :]
            r2d = dose_ref[sl, :, :]
            e2d = eval_on_ref[sl, :, :]
        elif args.plane == 'sagittal':
            sl = args.plane_index
            g2d = gamma_map[:, :, sl]
            r2d = dose_ref[:, :, sl]
            e2d = eval_on_ref[:, :, sl]
        else:  # coronal
            sl = args.plane_index
            g2d = gamma_map[:, sl, :]
            r2d = dose_ref[:, sl, :]
            e2d = eval_on_ref[:, sl, :]
        if args.save_gamma_map:
            save_gamma_map_2d(args.save_gamma_map, g2d, title=f'Gamma (shift {best_shift} mm)')
        if args.save_dose_diff:
            # Use percent doses for diff visualization
            nf = np.nanmax(dose_ref) if np.isfinite(dose_ref).any() else 1.0
            save_dose_diff_2d(args.save_dose_diff, r2d / nf * 100.0, e2d / nf * 100.0, title='Dose diff (%)')
    else:
        # 3D outputs: save as NPZ if paths provided
        if args.save_gamma_map:
            np.savez_compressed(args.save_gamma_map, gamma=gamma_map)
        if args.save_dose_diff:
            nf = np.nanmax(dose_ref) if np.isfinite(dose_ref).any() else 1.0
            np.savez_compressed(args.save_dose_diff, dose_diff_pct=(eval_on_ref - dose_ref) / nf * 100.0)

    if args.report:
        base = os.path.splitext(args.report)[0]
        summary = {
            'ref': os.path.basename(args.ref),
            'eval': os.path.basename(args.eval),
            'mode': args.mode,
            'plane': getattr(args, 'plane', None),
            'plane_index': getattr(args, 'plane_index', None),
            'dd_percent': args.dd,
            'dta_mm': args.dta,
            'cutoff_percent': args.cutoff,
            'gamma_type': args.gamma_type,
            'norm': args.norm,
            'pass_rate_percent': pass_rate,
            'best_shift_mm': best_shift,
            'gamma_mean': gstats['gamma_mean'],
            'gamma_median': gstats['gamma_median'],
            'gamma_max': gstats['gamma_max'],
        }
        save_summary_csv(base + '.csv', summary)
        save_summary_json(base + '.json', summary)
        save_summary_markdown(base + '.md', summary)
        if search_log is not None:
            with open(base + '_search_log.json', 'w', encoding='utf-8') as f:
                json.dump(search_log, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
