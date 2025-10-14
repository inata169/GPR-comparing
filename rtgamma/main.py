import os
import sys
import json
import argparse
import numpy as np
import logging

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
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filename='rtgamma.log', filemode='w')
    logging.info("Starting gamma analysis.")

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
    logging.info(f"Arguments: {args}")

    logging.info(f"Loading reference dose: {args.ref}")
    meta_ref = load_rtdose(args.ref)
    logging.info("Reference dose loaded.")

    logging.info(f"Loading evaluation dose: {args.eval}")
    meta_eval = load_rtdose(args.eval)
    logging.info("Evaluation dose loaded.")

    logging.info(f"Ref IPP: {meta_ref['ipp']}, Eval IPP: {meta_eval['ipp']}")
    logging.info(f"Ref Row Dir: {meta_ref['row_dir']}, Eval Row Dir: {meta_eval['row_dir']}")
    logging.info(f"Ref Col Dir: {meta_ref['col_dir']}, Eval Col Dir: {meta_eval['col_dir']}")
    logging.info(f"Ref PixelSpacing: {meta_ref['dataset'].PixelSpacing}, Eval PixelSpacing: {meta_eval['dataset'].PixelSpacing}")
    logging.info(f"Ref GridFrameOffsetVector (first 5): {meta_ref['dataset'].GridFrameOffsetVector[:5]}, Eval GridFrameOffsetVector (first 5): {meta_eval['dataset'].GridFrameOffsetVector[:5]}")
    logging.info(f"Ref DoseGridScaling: {meta_ref['dataset'].DoseGridScaling}, Eval DoseGridScaling: {meta_eval['dataset'].DoseGridScaling}")
    logging.info(f"Ref DoseUnits: {meta_ref['units']}, Eval DoseUnits: {meta_eval['units']}")

    dose_ref = meta_ref['dose']  # (z,y,x)
    dose_eval = meta_eval['dose']

    # --- GEMINI AGENT MODIFICATION ---
    # Per user instruction, disabling forced normalization of eval dose to ref max.
    # The user's data is a gold standard absolute dose comparison, and this
    # step was incorrectly altering the data before gamma analysis.
    # logging.info("Normalizing evaluation dose to reference max.")
    # eval_max = np.max(dose_eval)
    # ref_max = np.max(dose_ref)
    # if eval_max > 0 and ref_max > 0:
    #     dose_eval = dose_eval * (ref_max / eval_max)

    logging.info(f"Ref Dose Min/Max: {np.min(dose_ref)}, {np.max(dose_ref)}")
    logging.info(f"Eval Dose Min/Max (after normalization): {np.min(dose_eval)}, {np.max(dose_eval)}")

    logging.info("Building reference world coordinates.")
    Xw, Yw, Zw = build_ref_world_coords(meta_ref)
    logging.info("Reference world coordinates built.")

    def world_to_eval_ijk(points):
        ipp = meta_eval['ipp']
        r = meta_eval['row_dir']
        c = meta_eval['col_dir']
        s = meta_eval['slice_dir']
        return world_to_index(ipp, r, c, s, meta_eval['row_spacing'], meta_eval['col_spacing'], meta_eval['z_offsets'], points)

    # Default: resample eval onto ref grid without shift
    logging.info("Performing initial resampling of evaluation dose.")
    eval_on_ref = resample_eval_onto_ref(dose_eval, world_to_eval_ijk, (Xw, Yw, Zw), interp=args.interp, shift_mm=(0, 0, 0))
    logging.info("Initial resampling complete.")

    best_shift = (0.0, 0.0, 0.0)
    search_log = None
    if args.opt_shift == 'on':
        logging.info("Starting shift optimization.")
        ref_axes_mm_1d = (meta_ref['z_coords_mm'], meta_ref['y_coords_mm'], meta_ref['x_coords_mm'])
        eval_axes_mm_1d = (meta_eval['z_coords_mm'], meta_eval['y_coords_mm'], meta_eval['x_coords_mm'])

        # Correct for the difference in origins before searching for shift.
        # Project the LPS origin delta onto the reference axis directions so that
        # eval axes are expressed in the same coordinate frame (r,c,s of ref).
        origin_offset_vec = meta_ref['ipp'] - meta_eval['ipp']
        dz_ref = float(np.dot(origin_offset_vec, meta_ref['slice_dir']))
        dy_ref = float(np.dot(origin_offset_vec, meta_ref['row_dir']))
        dx_ref = float(np.dot(origin_offset_vec, meta_ref['col_dir']))
        logging.info(f"Correcting for origin offset projected onto ref axes: dx={dx_ref:.3f}, dy={dy_ref:.3f}, dz={dz_ref:.3f} mm")
        eval_axes_mm_1d_preshifted = (
            eval_axes_mm_1d[0] + dz_ref,  # Z along ref slice_dir
            eval_axes_mm_1d[1] + dy_ref,  # Y along ref row_dir
            eval_axes_mm_1d[2] + dx_ref   # X along ref col_dir
        )

        best_shift, best_pass, extras = grid_search_best_shift(
            ref_axes_mm_1d=ref_axes_mm_1d,
            dose_ref=dose_ref,
            eval_axes_mm_1d=eval_axes_mm_1d_preshifted,
            dose_eval=dose_eval,
            dd=args.dd,
            dta=args.dta,
            cutoff=args.cutoff,
            norm=args.norm,
            shift_spec=args.shift_range,
            refine=args.refine == 'coarse2fine',
        )
        search_log = extras['search_log']
        logging.info(f"Shift optimization complete. Best shift: {best_shift}, Pass rate: {best_pass}")
        
        # Convert best shift from ref axis components (dx along col_dir,
        # dy along row_dir, dz along slice_dir) into LPS vector components.
        if isinstance(best_shift, tuple) and len(best_shift) == 3:
            dx_axis, dy_axis, dz_axis = float(best_shift[0]), float(best_shift[1]), float(best_shift[2])
        else:
            dx_axis = dy_axis = dz_axis = 0.0
        shift_vec_lps = (dx_axis * meta_ref['col_dir']
                         + dy_axis * meta_ref['row_dir']
                         + dz_axis * meta_ref['slice_dir'])
        logging.info(f"Performing final resampling with best shift (axis)={best_shift} -> (LPS)={shift_vec_lps}")
        eval_on_ref = resample_eval_onto_ref(dose_eval, world_to_eval_ijk, (Xw, Yw, Zw), interp=args.interp,
                                             shift_mm=(float(shift_vec_lps[0]), float(shift_vec_lps[1]), float(shift_vec_lps[2])))
        logging.info("Final resampling complete.")

    # Final gamma calculation on the optimally shifted and resampled dose grid
    logging.info("Starting final gamma calculation.")
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
        use_pymedphys=False,
    )
    logging.info(f"Final gamma calculation complete. Pass rate: {pass_rate}")

    # Create output directories if they don't exist
    if args.save_gamma_map:
        d = os.path.dirname(args.save_gamma_map)
        if d:
            os.makedirs(d, exist_ok=True)
    if args.save_dose_diff:
        d = os.path.dirname(args.save_dose_diff)
        if d:
            os.makedirs(d, exist_ok=True)
    if args.report:
        d = os.path.dirname(args.report)
        if d:
            os.makedirs(d, exist_ok=True)

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
            logging.info(f"Saving 2D gamma map to {args.save_gamma_map}")
            save_gamma_map_2d(args.save_gamma_map, g2d, title=f'Gamma (shift {best_shift} mm)')
        if args.save_dose_diff:
            logging.info(f"Saving 2D dose difference map to {args.save_dose_diff}")
            nf = np.nanmax(dose_ref) if np.isfinite(dose_ref).any() else 1.0
            save_dose_diff_2d(args.save_dose_diff, r2d / nf * 100.0, e2d / nf * 100.0, title='Dose diff (%)')
    else:
        # 3D outputs: save as NPZ if paths provided
        if args.save_gamma_map:
            logging.info(f"Saving 3D gamma map to {args.save_gamma_map}")
            np.savez_compressed(args.save_gamma_map, gamma=gamma_map)
        if args.save_dose_diff:
            logging.info(f"Saving 3D dose difference map to {args.save_dose_diff}")
            nf = np.nanmax(dose_ref) if np.isfinite(dose_ref).any() else 1.0
            np.savez_compressed(args.save_dose_diff, dose_diff_pct=(eval_on_ref - dose_ref) / nf * 100.0)

    if args.report:
        logging.info(f"Saving report to {args.report}")
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
    
    logging.info("Gamma analysis finished.")

if __name__ == '__main__':
    main()
