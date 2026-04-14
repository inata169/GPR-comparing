import argparse
import json
import logging
import os
import sys

import numpy as np

from .db import save_summary_db
from .dvh import calculate_dvh_stats
from .gamma import compute_gamma
from .header_compare import run_header_comparison
from .io_dicom import load_rtdose, load_rtstruct, world_to_index
from .mask import build_roi_masks
from .optimize import grid_search_best_shift
from .pdf_report import save_summary_pdf
from .report import save_summary_csv, save_summary_json, save_summary_markdown
from .resample import resample_eval_onto_ref
from .viz import save_dose_diff_2d, save_gamma_map_2d


def build_ref_world_coords(meta_ref):
    # Build world coordinate arrays (LPS) for each voxel center in reference grid
    i_mm = meta_ref['x_coords_mm'] # i-axis values (columns)
    j_mm = meta_ref['y_coords_mm'] # j-axis values (rows)
    k_mm = meta_ref['z_coords_mm'] # k-axis values (slices)

    ipp = meta_ref['ipp']
    v_col = meta_ref['v_col']
    v_row = meta_ref['v_row']
    v_slice = meta_ref['v_slice']

    # Meshgrid with indexing='ij' -> shapes (nj, ni, nk)
    J, I, K = np.meshgrid(j_mm, i_mm, k_mm, indexing='ij')

    # Pw(j,i,k) = IPP + j*v_row + i*v_col + k*v_slice
    Pw = (ipp[None, None, None, :]
          + J[..., None] * v_row[None, None, None, :]
          + I[..., None] * v_col[None, None, None, :]
          + K[..., None] * v_slice[None, None, None, :])

    # Reorder to (k,j,i) to match dose array shape
    Pw = np.moveaxis(Pw, 2, 0)  # (k,j,i,3)
    Xw = Pw[..., 0]
    Yw = Pw[..., 1]
    Zw = Pw[..., 2]
    return Xw, Yw, Zw


def build_plane_world_coords(meta_ref, plane: str, sl: int):
    """Build world-coordinate grids for a single plane slice."""
    k_mm = meta_ref['z_coords_mm']
    j_mm = meta_ref['y_coords_mm']
    i_mm = meta_ref['x_coords_mm']
    ipp = meta_ref['ipp']
    v_col = meta_ref['v_col']
    v_row = meta_ref['v_row']
    v_slice = meta_ref['v_slice']

    if plane == 'axial':
        # k fixed, vary j and i -> (1, j, i)
        J, I = np.meshgrid(j_mm, i_mm, indexing='ij')
        K = np.full_like(J, fill_value=float(k_mm[sl]))
        Pw = (ipp[None, None, :] + J[..., None] * v_row[None, None, :]
              + I[..., None] * v_col[None, None, :] + K[..., None] * v_slice[None, None, :])
        Xw = Pw[..., 0][None, ...]
        Yw = Pw[..., 1][None, ...]
        Zw = Pw[..., 2][None, ...]
        ax_z = np.array([float(k_mm[sl])], dtype=float)
        ax_y = j_mm
        ax_x = i_mm
    elif plane == 'sagittal':
        # i fixed, vary k and j -> build (k, j), then expand to (k, j, 1)
        K, J = np.meshgrid(k_mm, j_mm, indexing='ij')
        I = np.full_like(K, fill_value=float(i_mm[sl]))
        Pw = (ipp[None, None, :] + J[..., None] * v_row[None, None, :]
              + I[..., None] * v_col[None, None, :] + K[..., None] * v_slice[None, None, :])
        Xw = Pw[..., 0][..., None]
        Yw = Pw[..., 1][..., None]
        Zw = Pw[..., 2][..., None]
        ax_z = k_mm
        ax_y = j_mm
        ax_x = np.array([float(i_mm[sl])], dtype=float)
    else:  # coronal
        # j fixed, vary k and i -> build (k, i), then expand to (k, 1, i)
        K, I = np.meshgrid(k_mm, i_mm, indexing='ij')
        J = np.full_like(K, fill_value=float(j_mm[sl]))
        Pw = (ipp[None, None, :] + J[..., None] * v_row[None, None, :]
              + I[..., None] * v_col[None, None, :] + K[..., None] * v_slice[None, None, :])
        Xw = Pw[..., 0][:, None, :]
        Yw = Pw[..., 1][:, None, :]
        Zw = Pw[..., 2][:, None, :]
        ax_z = k_mm
        ax_y = np.array([float(j_mm[sl])], dtype=float)
        ax_x = i_mm
    return (Xw, Yw, Zw), (ax_z, ax_y, ax_x)


def main(argv=None):
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filename='rtgamma.log', filemode='w')
    logging.info("Starting gamma analysis.")

    parser = argparse.ArgumentParser(description='DICOM RTDOSE gamma analysis (2D/3D) with shift optimization')
    parser.add_argument('--ref', required=True, help='Reference RTDOSE (DICOM)')
    parser.add_argument('--eval', required=True, help='Evaluation RTDOSE (DICOM)')
    parser.add_argument('--mode', choices=['3d', '2d', 'header'], default='3d')
    parser.add_argument('--plane', choices=['axial', 'sagittal', 'coronal'])
    # Allow 'auto' to pick the central slice for the chosen plane
    parser.add_argument('--plane-index', type=str, default='auto')

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
    parser.add_argument('--fine-range-mm', type=float, default=10.0,
                        help='Fine search half-range in mm (default 10)')
    parser.add_argument('--fine-step-mm', type=float, default=1.0,
                        help='Fine search step in mm (default 1)')
    parser.add_argument('--early-stop-epsilon', type=float, default=0.05,
                        help='Early stop threshold (pass rate delta)')
    parser.add_argument('--early-stop-patience', type=int, default=100,
                        help='Number of consecutive non-improving steps to stop')
    parser.add_argument('--prescan-2d', choices=['on', 'off'], default='on',
                        help='Enable 2D central-slice prescan to narrow XY range')

    parser.add_argument('--spacing', help='Override spacing sx,sy,sz in mm (unused default: ref grid)')
    parser.add_argument('--interp', choices=['linear', 'bspline', 'nearest'], default='linear')

    parser.add_argument('--save-gamma-map')
    parser.add_argument('--save-dose-diff')
    parser.add_argument('--report')
    parser.add_argument('--no-pdf', action='store_true', help='Disable PDF report generation (PDF is enabled by default)')
    parser.add_argument('--log-level', choices=['INFO', 'DEBUG'], default='INFO')
    parser.add_argument('--warn-large-shift-mm', type=float, default=20.0,
                        help='Warn if |best_shift| exceeds this magnitude (mm)')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--threads', type=int)
    parser.add_argument('--profile', type=str,
                        help='Preset profile name from config/presets.json (overrides dta/dd/cutoff/norm)')
    parser.add_argument('--db', type=str, nargs='?', const='rtgamma.db',
                        help='Save result to SQLite database (default: rtgamma.db in current directory if flag passed without value)')
    parser.add_argument('--gpu', choices=['on', 'off'], default='off')
    parser.add_argument('--tolerance', type=float, default=1e-6)
    parser.add_argument('--rtstruct', help='RTSTRUCT DICOM file for per-structure GPR')
    parser.add_argument('--roi', action='append', dest='roi_names',
                        help='ROI name(s) to evaluate (repeatable). Omit for all ROIs.')
    parser.add_argument('--interp-fraction', type=int, default=10,
                        help='Sub-voxel interpolation fraction for 3D/2D search. (default: 10)\n'
                             'Higher values (e.g. 10) enable trilinear sub-voxel search within DTA sphere '
                             'at dta/interp_fraction mm resolution. 1 disables sub-voxel interpolation.')

    args = parser.parse_args(argv)
    # Add console (stdout) logging handler for on-screen feedback
    try:
        root_logger = logging.getLogger()
        stream_levels = {'INFO': logging.INFO, 'DEBUG': logging.DEBUG}
        sh = logging.StreamHandler(stream=sys.stdout)
        sh.setLevel(stream_levels.get(args.log_level, logging.INFO))
        sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(sh)
    except Exception:
        pass

    if args.profile:
        preset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'presets.json')
        if os.path.exists(preset_path):
            try:
                with open(preset_path, 'r', encoding='utf-8') as f:
                    presets = json.load(f)
                if args.profile in presets:
                    p = presets[args.profile]
                    if 'dta' in p: args.dta = float(p['dta'])
                    if 'dd' in p: args.dd = float(p['dd'])
                    if 'cutoff' in p: args.cutoff = float(p['cutoff'])
                    if 'norm' in p: args.norm = str(p['norm'])
                    # We output this after logging is configured properly.
                else:
                    pass # Will log below
            except Exception as e:
                pass


    logging.info(f"Arguments: {args}")

    if args.mode == 'header':
        logging.info("Running header comparison mode.")
        if not args.report:
            raise SystemExit('--report is required for header comparison mode')
        run_header_comparison(args.ref, args.eval, args.report)
        logging.info(f"Header comparison report saved to {args.report}")
        return

    logging.info(f"Loading reference dose: {args.ref}")
    meta_ref = load_rtdose(args.ref)
    logging.info("Reference dose loaded.")

    logging.info(f"Loading evaluation dose: {args.eval}")
    meta_eval = load_rtdose(args.eval)
    logging.info("Evaluation dose loaded.")

    logging.info(f"Ref IPP: {meta_ref['ipp']}, Eval IPP: {meta_eval['ipp']}")
    logging.info(f"Ref v_col: {meta_ref['v_col']}, Eval v_col: {meta_eval['v_col']}")
    logging.info(f"Ref v_row: {meta_ref['v_row']}, Eval v_row: {meta_eval['v_row']}")
    logging.info(f"Ref PixelSpacing: {meta_ref['dataset'].PixelSpacing}, Eval PixelSpacing: {meta_eval['dataset'].PixelSpacing}")
    logging.info(f"Ref GridFrameOffsetVector (first 5): {meta_ref['dataset'].GridFrameOffsetVector[:5]}, Eval GridFrameOffsetVector (first 5): {meta_eval['dataset'].GridFrameOffsetVector[:5]}")
    logging.info(f"Ref DoseGridScaling: {meta_ref['dataset'].DoseGridScaling}, Eval DoseGridScaling: {meta_eval['dataset'].DoseGridScaling}")
    logging.info(f"Ref DoseUnits: {meta_ref['units']}, Eval DoseUnits: {meta_eval['units']}")
    # FrameOfReferenceUIDs (may be absent on some files)
    ref_for_uid = str(getattr(meta_ref['dataset'], 'FrameOfReferenceUID', ''))
    eval_for_uid = str(getattr(meta_eval['dataset'], 'FrameOfReferenceUID', ''))
    logging.info(f"Ref FoR UID: {ref_for_uid or 'N/A'}, Eval FoR UID: {eval_for_uid or 'N/A'}")

    # Orientation similarity checks (cosine of angle between ref and eval axes)
    try:
        dot_col = float(abs(np.dot(meta_ref['v_col'], meta_eval['v_col'])))
        dot_row = float(abs(np.dot(meta_ref['v_row'], meta_eval['v_row'])))
        dot_sli = float(abs(np.dot(meta_ref['v_slice'], meta_eval['v_slice'])))
        orientation_min_dot = min(dot_row, dot_col, dot_sli)
        if orientation_min_dot < 0.99:
            logging.warning(f"Orientation mismatch suspected (min dot = {orientation_min_dot:.6f}). Check IOP consistency.")
    except Exception:
        orientation_min_dot = float('nan')

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
        v_col = meta_eval['v_col']
        v_row = meta_eval['v_row']
        v_slice = meta_eval['v_slice']
        return world_to_index(ipp, v_col, v_row, v_slice, meta_eval['s_col'], meta_eval['s_row'], meta_eval['z_offsets'], points)

    # Lazy resampling: only computed when eval_on_ref is actually needed
    # (e.g. --save-dose-diff output or 2D+opt_shift=on slice extraction)
    _eval_on_ref_cache = [None]  # mutable container for closure
    _eval_on_ref_shift = [(0.0, 0.0, 0.0)]  # track which shift was applied
    def get_eval_on_ref(shift_mm=(0.0, 0.0, 0.0)):
        if _eval_on_ref_cache[0] is None or _eval_on_ref_shift[0] != shift_mm:
            logging.info(f"Resampling evaluation dose (shift_mm={shift_mm}).")
            _eval_on_ref_cache[0] = resample_eval_onto_ref(
                dose_eval, world_to_eval_ijk, (Xw, Yw, Zw),
                interp=args.interp, shift_mm=shift_mm)
            _eval_on_ref_shift[0] = shift_mm
            logging.info("Resampling complete.")
        return _eval_on_ref_cache[0]

    # Correct for the difference in origins to express eval axes in the reference coordinate frame.
    # To align eval to ref, the physical point P_eval must be represented in ref's coordinate system.
    # P_eval_physical = IPP_eval + x_eval * v_col
    # P_ref_equivalent = P_eval_physical - IPP_ref = x_eval * v_col + (IPP_eval - IPP_ref)
    origin_offset_vec = meta_eval['ipp'] - meta_ref['ipp']
    dz_ref = float(np.dot(origin_offset_vec, meta_ref['v_slice']))
    dy_ref = float(np.dot(origin_offset_vec, meta_ref['v_row']))
    dx_ref = float(np.dot(origin_offset_vec, meta_ref['v_col']))
    logging.info(f"Origin offset projected onto ref axes: di={dx_ref:.3f}, dj={dy_ref:.3f}, dk={dz_ref:.3f} mm")
    eval_axes_mm_1d = (meta_eval['z_coords_mm'], meta_eval['y_coords_mm'], meta_eval['x_coords_mm'])
    eval_axes_mm_1d_preshifted = (
        eval_axes_mm_1d[0] + dz_ref,  # k along ref v_slice
        eval_axes_mm_1d[1] + dy_ref,  # j along ref v_row
        eval_axes_mm_1d[2] + dx_ref   # i along ref v_col
    )

    best_shift = (0.0, 0.0, 0.0)
    di_axis = dj_axis = dk_axis = 0.0
    search_log = None

    # Bypass optimization if Ref and Eval are the same file
    if os.path.exists(args.ref) and os.path.exists(args.eval):
        if os.path.abspath(args.ref) == os.path.abspath(args.eval):
            logging.info("Identity comparison detected (Ref==Eval). Bypassing shift optimization.")
            args.opt_shift = 'off'

    if args.opt_shift == 'on':
        logging.info("Starting shift optimization.")
        ref_axes_mm_1d = (meta_ref['z_coords_mm'], meta_ref['y_coords_mm'], meta_ref['x_coords_mm'])

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
            gamma_type=args.gamma_type,
            refine=args.refine == 'coarse2fine',
            fine_range_mm=float(args.fine_range_mm),
            fine_step_mm=float(args.fine_step_mm),
            early_stop_epsilon=float(args.early_stop_epsilon),
            early_stop_patience=int(args.early_stop_patience),
            prescan_2d=(args.prescan_2d == 'on'),
        )
        search_log = extras['search_log']
        logging.info(f"Shift optimization complete. Best shift: {best_shift}, Pass rate: {best_pass}")

        # Convert best shift from ref axis components (dx along col_dir,
        # dy along row_dir, dz along slice_dir) into LPS vector components.
        if isinstance(best_shift, tuple) and len(best_shift) == 3:
            di_axis, dj_axis, dk_axis = float(best_shift[0]), float(best_shift[1]), float(best_shift[2])
        shift_vec_lps = (di_axis * meta_ref['v_col']
                         + dj_axis * meta_ref['v_row']
                         + dk_axis * meta_ref['v_slice'])
        # Store the LPS shift so that lazy resampling uses the correct shift when needed
        _eval_on_ref_shift[0] = (float(shift_vec_lps[0]), float(shift_vec_lps[1]), float(shift_vec_lps[2]))
        _eval_on_ref_cache[0] = None  # invalidate cache so next get_eval_on_ref uses new shift
        logging.info(f"Best shift (axis)={best_shift} -> (LPS)={shift_vec_lps}. Resampling deferred until needed.")

    # Final gamma calculation on the optimally shifted and resampled dose grid
    # Fast path: 2D mode without shift optimization computes only the selected slice
    if args.mode == '2d' and args.opt_shift == 'off':
        # Determine slice index early
        sz, sy, sx = dose_ref.shape
        if isinstance(args.plane_index, str) and args.plane_index.lower() == 'auto':
            if args.plane == 'axial':
                sl = int(sz // 2)
            elif args.plane == 'sagittal':
                sl = int(sx // 2)
            else:
                sl = int(sy // 2)
        else:
            try:
                sl = int(args.plane_index)
            except Exception:
                raise SystemExit('--plane-index must be an integer or "auto"')
        # Build world coords only for this plane slice and resample eval
        (Xw1, Yw1, Zw1), (ax_z, ax_y, ax_x) = build_plane_world_coords(meta_ref, args.plane, sl)
        def world_to_eval_ijk(xyz):
            return world_to_index(meta_eval['ipp'], meta_eval['v_col'], meta_eval['v_row'], meta_eval['v_slice'],
                                  meta_eval['s_col'], meta_eval['s_row'], meta_eval['z_offsets'], xyz)
        eval_on_ref_slice = resample_eval_onto_ref(dose_eval, world_to_eval_ijk, (Xw1, Yw1, Zw1), interp=args.interp, shift_mm=(0, 0, 0))
        # Extract ref slice
        if args.plane == 'axial':
            ref_slice = dose_ref[sl:sl+1, :, :]
        elif args.plane == 'sagittal':
            ref_slice = dose_ref[:, :, sl:sl+1]  # shape (z,y,1)
        else:  # coronal
            ref_slice = dose_ref[:, sl:sl+1, :]  # shape (z,1,x)
        logging.info("Starting 2D slice gamma calculation (fast path).")
        # Ensure 2D fast path uses the full-volume reference max for normalization
        full_ref_max = float(np.nanmax(dose_ref)) if np.isfinite(dose_ref).any() else 1.0
        gamma_map, pass_rate, gstats = compute_gamma(
            axes_ref_mm=(ax_z, ax_y, ax_x),
            dose_ref=ref_slice,
            axes_eval_mm=(ax_z, ax_y, ax_x),
            dose_eval=eval_on_ref_slice,
            dd_percent=args.dd,
            dta_mm=args.dta,
            cutoff_percent=args.cutoff,
            gamma_type=args.gamma_type,
            norm=args.norm,
            use_pymedphys=False,
            norm_factor_override=full_ref_max if args.norm in ('global_max','max_ref') else None,
            interp_fraction=args.interp_fraction,
        )
        logging.info(f"2D gamma calculation complete. Slice pass rate: {pass_rate}")
    else:
        logging.info("Starting final gamma calculation.")
        axes_ref_mm = (meta_ref['z_coords_mm'], meta_ref['y_coords_mm'], meta_ref['x_coords_mm'])

        # We use the un-resampled original eval dose and its correctly shifted axes.
        # This prevents interpolation blur and preserves sub-voxel gamma resolution!
        axes_eval_mm_final = (
            eval_axes_mm_1d_preshifted[0] + dk_axis,
            eval_axes_mm_1d_preshifted[1] + dj_axis,
            eval_axes_mm_1d_preshifted[2] + di_axis
        )

        gamma_map, pass_rate, gstats = compute_gamma(
            axes_ref_mm=axes_ref_mm,
            dose_ref=dose_ref,
            axes_eval_mm=axes_eval_mm_final, # Eval is explicitly offset to sub-grid physical coordinates
            dose_eval=dose_eval,             # ORIGINAL un-blurred dose!
            dd_percent=args.dd,
            dta_mm=args.dta,
            cutoff_percent=args.cutoff,
            gamma_type=args.gamma_type,
            norm=args.norm,
            use_pymedphys=False,
            interp_fraction=args.interp_fraction,
        )
        logging.info(f"Final gamma calculation complete. Pass rate: {pass_rate}")

    # --- Per-structure gamma analysis ---
    per_structure = []
    if args.rtstruct:
        logging.info(f"Loading RTSTRUCT: {args.rtstruct}")
        rtstruct_meta = load_rtstruct(args.rtstruct)
        logging.info(f"RTSTRUCT loaded. ROIs: {[r['name'] for r in rtstruct_meta['roi_list']]}")
        roi_masks = build_roi_masks(rtstruct_meta, meta_ref, roi_names=args.roi_names)
        for roi_name, roi_mask in roi_masks.items():
            # In 2D fast path, gamma_map is a thin slice (1, Y, X), etc.
            # We must slice the 3D roi_mask to match.
            current_roi_mask = roi_mask
            if args.mode == '2d' and args.opt_shift == 'off':
                if args.plane == 'axial':
                    current_roi_mask = roi_mask[sl:sl+1, :, :]
                elif args.plane == 'sagittal':
                    current_roi_mask = roi_mask[:, :, sl:sl+1]
                else: # coronal
                    current_roi_mask = roi_mask[:, sl:sl+1, :]

            # Apply mask to gamma_map
            masked_gamma = gamma_map[current_roi_mask]
            finite = np.isfinite(masked_gamma)
            if finite.any():
                roi_pr = float(np.sum(masked_gamma[finite] <= 1.0) / np.sum(finite) * 100.0)
                roi_mean = float(np.nanmean(masked_gamma[finite]))
                roi_median = float(np.nanmedian(masked_gamma[finite]))
                roi_max = float(np.nanmax(masked_gamma[finite]))
            else:
                roi_pr = float('nan')
                roi_mean = roi_median = roi_max = float('nan')
            
            n_voxels = int(np.sum(current_roi_mask))
            n_evaluated = int(np.sum(finite))

            # --- DVH calculation ---
            # Use resampled eval dose to match ref mask
            eor = get_eval_on_ref(_eval_on_ref_shift[0])
            # Ref DVH
            ref_dvh_stats = calculate_dvh_stats(dose_ref, current_roi_mask)
            # Eval DVH
            eval_dvh_stats = calculate_dvh_stats(eor, current_roi_mask)

            logging.info(f"ROI '{roi_name}': GPR={roi_pr:.2f}%, voxels={n_voxels}, evaluated={n_evaluated}")
            per_structure.append({
                'roi_name': roi_name,
                'voxel_count': n_voxels,
                'evaluated_count': n_evaluated,
                'pass_rate_percent': roi_pr,
                'gamma_mean': roi_mean,
                'gamma_median': roi_median,
                'gamma_max': roi_max,
                'ref_dvh': ref_dvh_stats,
                'eval_dvh': eval_dvh_stats,
            })

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
    pass_rate_out = None
    if args.mode == '2d':
        if not args.plane:
            raise SystemExit('--plane is required in 2d mode')

        # In fast 2D path, gamma_map may be (1,y,x) or similar; normalize indexing
        if args.opt_shift == 'off':
            # We already selected slice; extract 2D arrays from computed slice gamma
            if args.plane == 'axial':
                g2d = gamma_map[0, :, :]
                r2d = dose_ref[sl, :, :]
                e2d = eval_on_ref_slice[0, :, :]
            elif args.plane == 'sagittal':
                g2d = gamma_map[:, :, 0] if gamma_map.shape[2] == 1 else gamma_map[0, :, :]
                r2d = dose_ref[:, :, sl]
                e2d = eval_on_ref_slice[:, :, 0] if eval_on_ref_slice.shape[2] == 1 else eval_on_ref_slice[0, :, :]
            else:  # coronal
                g2d = gamma_map[:, 0, :] if gamma_map.shape[1] == 1 else gamma_map[0, :, :]
                r2d = dose_ref[:, sl, :]
                e2d = eval_on_ref_slice[:, 0, :] if eval_on_ref_slice.shape[1] == 1 else eval_on_ref_slice[0, :, :]
        else:
            # Original indexing from full 3D map
            # Determine slice index: support 'auto' (central slice) or explicit integer
            sz, sy, sx = dose_ref.shape  # (z, y, x)
            if isinstance(args.plane_index, str) and args.plane_index.lower() == 'auto':
                if args.plane == 'axial':
                    sl = int(sz // 2)
                elif args.plane == 'sagittal':
                    sl = int(sx // 2)
                else:  # coronal
                    sl = int(sy // 2)
            else:
                try:
                    sl = int(args.plane_index)
                except Exception:
                    raise SystemExit('--plane-index must be an integer or "auto"')
            if args.plane == 'axial':
                g2d = gamma_map[sl, :, :]
                r2d = dose_ref[sl, :, :]
                e2d = get_eval_on_ref(_eval_on_ref_shift[0])[sl, :, :]
            elif args.plane == 'sagittal':
                g2d = gamma_map[:, :, sl]
                r2d = dose_ref[:, :, sl]
                e2d = get_eval_on_ref(_eval_on_ref_shift[0])[:, :, sl]
            else:  # coronal
                g2d = gamma_map[:, sl, :]
                r2d = dose_ref[:, sl, :]
                e2d = get_eval_on_ref(_eval_on_ref_shift[0])[:, sl, :]

        # Compute 2D pass rate on the selected slice (exclude NaN/inf and cutoff-excluded voxels)
        finite_mask = np.isfinite(g2d)
        if finite_mask.any():
            pass_rate_out = float(np.sum((g2d <= 1.0) & finite_mask) / np.sum(finite_mask) * 100.0)
        else:
            pass_rate_out = float('nan')
        logging.info(f"2D slice pass rate ({args.plane} index {sl}): {pass_rate_out}")
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
            eor = get_eval_on_ref(_eval_on_ref_shift[0])
            np.savez_compressed(args.save_dose_diff, dose_diff_pct=(eor - dose_ref) / nf * 100.0)

    # Build warnings and flags (always, for return value)
    warnings_list = []
    same_for = (ref_for_uid != '' and eval_for_uid != '' and ref_for_uid == eval_for_uid)
    if (ref_for_uid and eval_for_uid) and (ref_for_uid != eval_for_uid):
        msg = f"FrameOfReferenceUID differs (ref={ref_for_uid}, eval={eval_for_uid})"
        warnings_list.append(msg)
        logging.warning(msg)
    # Large shift warning (applies when optimization was enabled)
    try:
        dx_, dy_, dz_ = float(best_shift[0]), float(best_shift[1]), float(best_shift[2])
        shift_mag = float(np.sqrt(dx_**2 + dy_**2 + dz_**2))
    except Exception:
        shift_mag = float(0.0)
    large_shift_threshold = float(getattr(args, 'warn_large_shift_mm', 20.0))
    if args.opt_shift == 'on' and shift_mag > large_shift_threshold:
        msg = f"Large best shift magnitude {shift_mag:.3f} mm (> {large_shift_threshold} mm)"
        warnings_list.append(msg)
        logging.warning(msg)

    absolute_geometry_only = (args.opt_shift == 'off' and args.norm == 'none')

    summary = {
        'ref': os.path.basename(args.ref),
        'eval': os.path.basename(args.eval),
        'profile': getattr(args, 'profile', None),
        'mode': args.mode,
        'plane': getattr(args, 'plane', None),
        'plane_index': int(sl) if args.mode == '2d' else None,
        'dd_percent': args.dd,
        'dta_mm': args.dta,
        'cutoff_percent': args.cutoff,
        'gamma_type': args.gamma_type,
        'norm': args.norm,
        'interp_fraction': args.interp_fraction,
        'pass_rate_percent': pass_rate_out if args.mode == '2d' else pass_rate,
        'best_shift_mm': best_shift,
        'best_shift_mag_mm': shift_mag,
        'absolute_geometry_only': absolute_geometry_only,
        'ref_for_uid': ref_for_uid or None,
        'eval_for_uid': eval_for_uid or None,
        'same_for_uid': bool(same_for),
        'orientation_min_dot': orientation_min_dot,
        'warnings': "; ".join(warnings_list) if warnings_list else "",
        'gamma_mean': gstats.get('gamma_mean', float('nan')),
        'gamma_median': gstats.get('gamma_median', float('nan')),
        'gamma_max': gstats.get('gamma_max', float('nan')),
        'gamma_p95': gstats.get('gamma_p95', float('nan')),
        'gamma_p99': gstats.get('gamma_p99', float('nan')),
        'histogram': gstats.get('histogram', None),
        'save_gamma_map_path': args.save_gamma_map,
    }
    if per_structure:
        summary['per_structure'] = per_structure

    if args.report:
        logging.info(f"Saving report to {args.report}")
        base = os.path.splitext(args.report)[0]
        save_summary_csv(base + '.csv', summary)
        save_summary_json(base + '.json', summary)
        save_summary_markdown(base + '.md', summary)
        if not args.no_pdf:
            try:
                save_summary_pdf(base + '.pdf', summary)
                logging.info(f"Saved PDF report to {base}.pdf")
            except Exception as e:
                logging.error(f"Failed to save PDF report: {e}")

        if search_log is not None:
            with open(base + '_search_log.json', 'w', encoding='utf-8') as f:
                json.dump(search_log, f, ensure_ascii=False, indent=2)

    if args.db:
        save_summary_db(args.db, summary)

    logging.info("Gamma analysis finished.")
    return summary

if __name__ == '__main__':
    main()
