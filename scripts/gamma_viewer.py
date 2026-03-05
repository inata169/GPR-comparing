#!/usr/bin/env python
"""Interactive 3D Gamma Viewer with CT background, Dose overlay, and Structure overlay.

Usage:
    python scripts/gamma_viewer.py \
        --ct dicom/PROSTATE/ \
        --ref dicom/PROSTATE/RTDOSE_*.dcm \
        --eval dicom/PROSTATE/RTDOSE_*.dcm \
        --rtstruct dicom/PROSTATE/RTSTRUCT_*.dcm \
        --dd 3 --dta 2 --cutoff 10

    # Or with pre-computed gamma NPZ:
    python scripts/gamma_viewer.py \
        --ct dicom/PROSTATE/ \
        --ref dicom/PROSTATE/RTDOSE_*.dcm \
        --eval dicom/PROSTATE/RTDOSE_*.dcm \
        --gamma-npz output/gamma3d.npz \
        --rtstruct dicom/PROSTATE/RTSTRUCT_*.dcm
"""
import argparse
import logging
import os
import sys

import matplotlib
import numpy as np

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Polygon
from matplotlib.widgets import CheckButtons, RadioButtons, Slider

# Ensure repo root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rtgamma.gamma import compute_gamma
from rtgamma.io_dicom import load_ct, load_rtdose, load_rtstruct
from rtgamma.mask import build_roi_masks
from rtgamma.resample import resample_ct_onto_dose

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -- Predefined ROI colors -----------------------------------------------
ROI_COLORS = [
    '#FF4444',  # red
    '#4488FF',  # blue
    '#44DD44',  # green
    '#FFAA00',  # orange
    '#FF44FF',  # magenta
    '#44FFFF',  # cyan
    '#FFFF44',  # yellow
    '#AA44FF',  # purple
    '#FF8888',  # light red
    '#88AAFF',  # light blue
]

# -- Pass/Fail colormap (green=OK, red=NG) --------------------------------
_PASS_FAIL_CMAP = ListedColormap(['#00CC00', '#FF2222'])


def get_contours_for_slice(roi_contours, z_world, z_tol):
    """Return list of contour point arrays matching a given world Z."""
    matched = []
    for c in roi_contours:
        if abs(c['z'] - z_world) <= z_tol:
            matched.append(c['points'])
    return matched


def compute_dose_z_world(dose_meta, k):
    """World Z coordinate of dose slice k."""
    ipp = dose_meta['ipp']
    v_slice = dose_meta['v_slice']
    z_off = dose_meta['z_coords_mm'][k]
    return float(ipp[2] + z_off * v_slice[2])


class GammaViewer:
    def __init__(self, ct_on_dose, gamma_map, dose_meta,
                 ref_dose=None, eval_dose=None,
                 rtstruct_meta=None,
                 roi_names=None, roi_masks=None, per_structure_stats=None,
                 gpr_cond=None, ref_label='', eval_label=''):
        self.ct = ct_on_dose  # (z, y, x) HU
        self.gamma = gamma_map  # (z, y, x)
        self.dose_meta = dose_meta
        self.ref_dose = ref_dose    # (z, y, x) Gy
        self.eval_dose = eval_dose  # (z, y, x) Gy resampled onto ref grid
        self.rtstruct_meta = rtstruct_meta
        self.roi_names = roi_names or []
        self.per_structure_stats = per_structure_stats or []
        self.gpr_cond = gpr_cond
        self.ref_label = ref_label
        self.eval_label = eval_label

        self.plane = 'axial'
        self.nz, self.ny, self.nx = self.ct.shape
        self.slice_idx = self.nz // 2

        self.visible = {'CT': True, 'Structure': True}
        self.roi_visible = {name: True for name in self.roi_names}

        # Overlay mode
        self.overlay_mode = 'Gamma'

        # Precompute dose vmax for consistent color scaling
        self._dose_vmax = 0.0
        if ref_dose is not None:
            self._dose_vmax = max(self._dose_vmax, float(np.nanmax(ref_dose)))
        if eval_dose is not None:
            self._dose_vmax = max(self._dose_vmax, float(np.nanmax(eval_dose)))
        if self._dose_vmax == 0:
            self._dose_vmax = 1.0

        # Precompute dose ratio (Eval / Ref)
        self.dose_ratio = None
        if ref_dose is not None and eval_dose is not None:
            with np.errstate(divide='ignore', invalid='ignore'):
                ratio = np.where(ref_dose > 0, eval_dose / ref_dose, np.nan)
            self.dose_ratio = ratio

        # Precompute world Z for dose slices
        self.dose_z_world = np.array([compute_dose_z_world(dose_meta, k) for k in range(self.nz)])
        if self.nz > 1:
            self.z_tol = abs(float(self.dose_z_world[1] - self.dose_z_world[0])) * 0.5
        else:
            self.z_tol = 1.0

        self.roi_contour_data = {}
        if rtstruct_meta:
            for roi in rtstruct_meta['roi_list']:
                if roi['name'] in self.roi_names:
                    self.roi_contour_data[roi['name']] = roi['contours']

        self._build_ui()

    def _get_slice(self, vol):
        s = self.slice_idx
        if self.plane == 'axial': return vol[s, :, :]
        if self.plane == 'sagittal': return vol[:, :, s]
        return vol[:, s, :]

    def _build_ui(self):
        self.fig = plt.figure(figsize=(14, 9), facecolor='#111111')
        self.fig.canvas.manager.set_window_title('rtgamma 3D Viewer')
        self.ax = self.fig.add_axes([0.05, 0.13, 0.62, 0.78])
        self.ax.set_facecolor('#000000')
        self._cbar_ax = self.fig.add_axes([0.68, 0.13, 0.012, 0.78])
        self._cbar_ax.set_visible(False)

        # -- File info text (top-left) --
        info_lines = []
        if self.ref_label:
            info_lines.append(f"Ref : {self.ref_label}")
        if self.eval_label:
            info_lines.append(f"Eval: {self.eval_label}")
        if info_lines:
            self.fig.text(0.05, 0.97, '\n'.join(info_lines),
                          color='#AAAAAA', family='monospace', fontsize=7,
                          va='top', ha='left')

        # Slider
        ax_slider = self.fig.add_axes([0.05, 0.04, 0.62, 0.03], facecolor='#222222')
        self.slider = Slider(ax_slider, 'Slice', 0, self.nz-1,
                             valinit=self.slice_idx, valstep=1, color='#4466FF')
        self.slider.on_changed(self._on_slider_move)

        # -- Right panel layout --
        # CheckButtons: CT / Structure / ROIs
        toggle_labels = ['CT', 'Structure'] + self.roi_names
        toggle_defaults = [True] * len(toggle_labels)
        n_toggles = len(toggle_labels)
        toggle_h = min(0.28, 0.04 * n_toggles + 0.04)
        ax_toggles = self.fig.add_axes([0.75, 0.96 - toggle_h, 0.22, toggle_h], facecolor='#222222')
        self.check = CheckButtons(ax_toggles, toggle_labels, toggle_defaults)
        self.check.on_clicked(self._on_toggle)
        for lbl in self.check.labels:
            lbl.set_color('#FFFFFF')
            lbl.set_fontsize(8)

        # Style checkboxes
        if hasattr(self.check, 'set_frame_props'):
            self.check.set_frame_props({'edgecolor': '#AAAAAA', 'facecolor': '#222222', 'linewidths': 1.0})
            self.check.set_check_props({'color': '#00FF00', 'linewidths': 2.0})
            self._update_check_sizes()
        else:
            if hasattr(self.check, 'rectangles'):
                for rect in self.check.rectangles:
                    rect.set_edgecolor('#AAAAAA')
                    rect.set_facecolor('#222222')
                    rect.set_linewidth(1.5)
            if hasattr(self.check, 'lines'):
                for line in self.check.lines:
                    for l in line:
                        l.set_color('#00FF00')
                        l.set_linewidth(2.0)

        # Overlay mode RadioButtons
        overlay_labels = ['Gamma', 'Pass/Fail', 'Ref Dose', 'Eval Dose', 'Dose Ratio']
        overlay_top = 0.96 - toggle_h - 0.02
        overlay_h = 0.22
        ax_overlay = self.fig.add_axes([0.75, overlay_top - overlay_h, 0.22, overlay_h], facecolor='#222222')
        self.overlay_radio = RadioButtons(ax_overlay, overlay_labels, active=0)
        self.overlay_radio.on_clicked(self._on_overlay_mode)
        for lbl in self.overlay_radio.labels:
            lbl.set_color('#EEEEEE')
            lbl.set_fontsize(9)

        # Plane RadioButtons
        plane_top = overlay_top - overlay_h - 0.02
        plane_h = 0.12
        ax_plane = self.fig.add_axes([0.75, plane_top - plane_h, 0.22, plane_h], facecolor='#222222')
        self.radio = RadioButtons(ax_plane, ('axial', 'sagittal', 'coronal'), active=0)
        self.radio.on_clicked(self._on_plane)
        for lbl in self.radio.labels:
            lbl.set_color('#EEEEEE')
            lbl.set_fontsize(9)

        # GPR / info text
        txt_top = plane_top - plane_h - 0.02
        self.txt = self.fig.text(0.75, txt_top, self._gpr_text(),
                                 color='#00FF00', family='monospace', fontsize=8, va='top')

        self._draw()
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)

    def _gpr_text(self):
        if self.gpr_cond:
            res = f"Criteria: {self.gpr_cond['dta']}mm / {self.gpr_cond['dd']}%\n"
            res += f"Cutoff  : {self.gpr_cond['cutoff']}%\n"
            res += "-"*22 + "\n"
        else:
            res = ""

        res += "ROI GPR[%]\n" + "-"*15 + "\n"
        for ps in self.per_structure_stats:
            v = ps['pass_rate_percent']
            status = f"{v:5.1f}%" if np.isfinite(v) else "  N/A"
            res += f"{ps['roi_name'][:10]:10}: {status}\n"
        return res

    def _on_slider_move(self, val):
        idx = int(val)
        if idx != self.slice_idx:
            self.slice_idx = idx
            self._draw()

    def _on_scroll(self, event):
        step = 1 if event.button == 'up' else -1
        mx = int(self.slider.valmax)
        new_idx = max(0, min(self.slice_idx + step, mx))
        if new_idx != self.slice_idx:
            self.slice_idx = new_idx
            self.slider.set_val(new_idx)
            self._draw()

    def _on_toggle(self, label):
        if label in self.visible:
            self.visible[label] = not self.visible[label]
        else:
            self.roi_visible[label] = not self.roi_visible[label]
        self._update_check_sizes()
        self._draw()

    def _update_check_sizes(self):
        """Manually update sizes to ensure toggling works with custom styles."""
        if not hasattr(self.check, 'set_check_props'):
            return
        try:
            status = self.check.get_status()
            if hasattr(self.check, 'checks'):
                sizes = [70 if s else 0 for s in status]
                self.check.checks.set_sizes(sizes)
            elif hasattr(self.check, '_checks'):
                colors = ['#00FF00' if s else 'none' for s in status]
                self.check._checks.set_facecolor(colors)
                self.check._checks.set_edgecolor(colors)
        except Exception:
            pass
        self.fig.canvas.draw_idle()

    def _on_overlay_mode(self, label):
        self.overlay_mode = label
        self._draw()

    def _on_plane(self, label):
        self.plane = label
        mx = self.nz-1 if label == 'axial' else (self.nx-1 if label == 'sagittal' else self.ny-1)
        self.slider.valmax = mx
        self.slice_idx = min(self.slice_idx, mx)
        self.slider.set_val(self.slice_idx)
        self.slider.ax.set_xlim(0, mx)
        self._draw()

    def _draw(self):
        self.ax.clear()

        # -- CT background --
        if self.visible['CT']:
            ct2d = self._get_slice(self.ct)
            self.ax.imshow(ct2d, cmap='gray', vmin=-200, vmax=300,
                           aspect='auto', origin='lower')

        # -- Overlay --
        self._cbar_ax.clear()
        self._cbar_ax.set_visible(False)

        mode = self.overlay_mode

        if mode == 'Gamma':
            g2d = self._get_slice(self.gamma)
            gm = np.ma.masked_where(~np.isfinite(g2d) | (g2d == 0), g2d)
            im = self.ax.imshow(gm, cmap='turbo', vmin=0, vmax=2,
                                alpha=0.5, aspect='auto', origin='lower')
            self._cbar_ax.set_visible(True)
            self.fig.colorbar(im, cax=self._cbar_ax)
            self._cbar_ax.yaxis.set_tick_params(colors='white', labelsize=7)
            self._cbar_ax.set_ylabel('Gamma Index', color='white', fontsize=8)

        elif mode == 'Pass/Fail':
            g2d = self._get_slice(self.gamma)
            # Build pass/fail: 0 = pass (gamma <= 1), 1 = fail (gamma > 1)
            pf = np.full_like(g2d, np.nan)
            valid = np.isfinite(g2d) & (g2d != 0)
            pf[valid & (g2d <= 1.0)] = 0.0  # OK
            pf[valid & (g2d > 1.0)] = 1.0   # NG
            pfm = np.ma.masked_where(~valid, pf)
            self.ax.imshow(pfm, cmap=_PASS_FAIL_CMAP, vmin=0, vmax=1,
                           alpha=0.55, aspect='auto', origin='lower',
                           interpolation='nearest')
            # Count pass/fail for this slice
            n_pass = int(np.sum(pf[valid] == 0))
            n_fail = int(np.sum(pf[valid] == 1))
            n_total = n_pass + n_fail
            if n_total > 0:
                slice_gpr = n_pass / n_total * 100.0
                self.ax.text(0.02, 0.02,
                             f"Slice GPR: {slice_gpr:.1f}%  (OK:{n_pass} / NG:{n_fail})",
                             transform=self.ax.transAxes, color='white', fontsize=9,
                             bbox=dict(boxstyle='round,pad=0.3', fc='#000000', alpha=0.7))

        elif mode == 'Ref Dose' and self.ref_dose is not None:
            d2d = self._get_slice(self.ref_dose)
            cutoff_abs = self._dose_vmax * (self.gpr_cond['cutoff'] / 100.0) if self.gpr_cond else 0
            dm = np.ma.masked_where(d2d < cutoff_abs, d2d)
            im = self.ax.imshow(dm, cmap='jet', vmin=0, vmax=self._dose_vmax,
                                alpha=0.5, aspect='auto', origin='lower')
            self._cbar_ax.set_visible(True)
            self.fig.colorbar(im, cax=self._cbar_ax)
            self._cbar_ax.yaxis.set_tick_params(colors='white', labelsize=7)
            self._cbar_ax.set_ylabel('Dose [Gy]', color='white', fontsize=8)

        elif mode == 'Eval Dose' and self.eval_dose is not None:
            d2d = self._get_slice(self.eval_dose)
            cutoff_abs = self._dose_vmax * (self.gpr_cond['cutoff'] / 100.0) if self.gpr_cond else 0
            dm = np.ma.masked_where(d2d < cutoff_abs, d2d)
            im = self.ax.imshow(dm, cmap='jet', vmin=0, vmax=self._dose_vmax,
                                alpha=0.5, aspect='auto', origin='lower')
            self._cbar_ax.set_visible(True)
            self.fig.colorbar(im, cax=self._cbar_ax)
            self._cbar_ax.yaxis.set_tick_params(colors='white', labelsize=7)
            self._cbar_ax.set_ylabel('Dose [Gy]', color='white', fontsize=8)

        elif mode == 'Dose Ratio' and self.dose_ratio is not None:
            r2d = self._get_slice(self.dose_ratio)
            # Mask where ref dose is below cutoff (ratio is meaningless)
            cutoff_abs = self._dose_vmax * (self.gpr_cond['cutoff'] / 100.0) if self.gpr_cond else 0
            ref2d = self._get_slice(self.ref_dose)
            rm = np.ma.masked_where(~np.isfinite(r2d) | (ref2d < cutoff_abs), r2d)
            im = self.ax.imshow(rm, cmap='bwr', vmin=0.8, vmax=1.2,
                                alpha=0.55, aspect='auto', origin='lower')
            self._cbar_ax.set_visible(True)
            self.fig.colorbar(im, cax=self._cbar_ax)
            self._cbar_ax.yaxis.set_tick_params(colors='white', labelsize=7)
            self._cbar_ax.set_ylabel('Eval / Ref', color='white', fontsize=8)

        # -- Structure contours --
        if self.visible['Structure'] and self.plane == 'axial' and self.rtstruct_meta:
            z_w = self.dose_z_world[self.slice_idx]
            from rtgamma.mask import _world_xy_to_grid_rc
            for i, name in enumerate(self.roi_names):
                if not self.roi_visible[name]:
                    continue
                for pts in get_contours_for_slice(self.roi_contour_data[name], z_w, self.z_tol):
                    rc = _world_xy_to_grid_rc(pts, self.dose_meta)
                    self.ax.add_patch(Polygon(rc[:, [1, 0]], closed=True, fill=False,
                                             edgecolor=ROI_COLORS[i % len(ROI_COLORS)], lw=1))

        # -- Title --
        self.ax.set_title(f"{self.plane} view - slice {self.slice_idx}  [{mode}]",
                          color='white', fontsize=10)
        self.fig.canvas.draw_idle()


def main():
    parser = argparse.ArgumentParser(description='3D Gamma Viewer with CT + Dose + Structure overlay')
    parser.add_argument('--ct', required=True, help='Directory containing CT DICOM slices')
    parser.add_argument('--ref', required=True, help='Reference RTDOSE DICOM file')
    parser.add_argument('--eval', help='Evaluation RTDOSE DICOM file (omit if using --gamma-npz only)')
    parser.add_argument('--gamma-npz', help='Pre-computed gamma NPZ file (skip gamma calculation)')
    parser.add_argument('--rtstruct', help='RTSTRUCT DICOM file or directory')
    parser.add_argument('--roi', help='Comma-separated ROI names (default: all)')
    parser.add_argument('--dd', type=float, default=3.0)
    parser.add_argument('--dta', type=float, default=2.0)
    parser.add_argument('--cutoff', type=float, default=10.0)
    parser.add_argument('--gamma-type', choices=['global', 'local'], default='global')
    parser.add_argument('--norm', choices=['global_max', 'max_ref', 'none'], default='global_max')
    args = parser.parse_args()

    # Extract filenames for display
    ref_label = os.path.basename(args.ref) if args.ref else ''
    eval_label = os.path.basename(args.eval) if args.eval else ''

    # Load CT
    logger.info(f'Loading CT from: {args.ct}')
    ct_meta = load_ct(args.ct)
    logger.info(f'CT loaded: {ct_meta["shape"]}')

    # Load reference DOSE
    logger.info(f'Loading reference DOSE: {args.ref}')
    dose_meta = load_rtdose(args.ref)
    logger.info(f'DOSE loaded: {dose_meta["shape"]}')
    ref_dose = dose_meta['dose']  # (z, y, x)

    # Resample CT onto DOSE grid
    logger.info('Resampling CT onto DOSE grid...')
    ct_on_dose = resample_ct_onto_dose(ct_meta, dose_meta)
    logger.info(f'CT resampled: {ct_on_dose.shape}')

    # Eval dose (resampled onto ref grid)
    eval_on_ref = None

    # Gamma map: compute or load
    if args.gamma_npz:
        logger.info(f'Loading pre-computed gamma from: {args.gamma_npz}')
        npz = np.load(args.gamma_npz)
        gamma_map = npz['gamma']

        # If --eval is also provided, load and resample for dose display
        if args.eval:
            logger.info(f'Loading evaluation DOSE for display: {args.eval}')
            eval_meta = load_rtdose(args.eval)
            from rtgamma.main import build_ref_world_coords
            Xw, Yw, Zw = build_ref_world_coords(dose_meta)
            from rtgamma.io_dicom import world_to_index
            def world_to_eval_ijk(pts):
                return world_to_index(eval_meta['ipp'], eval_meta['v_col'], eval_meta['v_row'],
                                      eval_meta['v_slice'], eval_meta['s_col'], eval_meta['s_row'],
                                      eval_meta['z_offsets'], pts)
            from rtgamma.resample import resample_eval_onto_ref
            logger.info('Resampling eval onto ref grid for display...')
            eval_on_ref = resample_eval_onto_ref(eval_meta['dose'], world_to_eval_ijk,
                                                  (Xw, Yw, Zw), interp='linear', shift_mm=(0, 0, 0))
    else:
        if not args.eval:
            parser.error('--eval is required when --gamma-npz is not provided')
        logger.info(f'Loading evaluation DOSE: {args.eval}')
        eval_meta = load_rtdose(args.eval)

        # Build world coords
        from rtgamma.main import build_ref_world_coords
        Xw, Yw, Zw = build_ref_world_coords(dose_meta)

        from rtgamma.io_dicom import world_to_index
        def world_to_eval_ijk(pts):
            return world_to_index(eval_meta['ipp'], eval_meta['v_col'], eval_meta['v_row'],
                                  eval_meta['v_slice'], eval_meta['s_col'], eval_meta['s_row'],
                                  eval_meta['z_offsets'], pts)

        from rtgamma.resample import resample_eval_onto_ref
        logger.info('Resampling eval onto ref grid...')
        eval_on_ref = resample_eval_onto_ref(eval_meta['dose'], world_to_eval_ijk,
                                              (Xw, Yw, Zw), interp='linear', shift_mm=(0, 0, 0))

        logger.info('Computing 3D gamma...')
        axes = (dose_meta['z_coords_mm'], dose_meta['y_coords_mm'], dose_meta['x_coords_mm'])
        gamma_map, pass_rate, gstats = compute_gamma(
            axes_ref_mm=axes, dose_ref=dose_meta['dose'],
            axes_eval_mm=axes, dose_eval=eval_on_ref,
            dd_percent=args.dd, dta_mm=args.dta, cutoff_percent=args.cutoff,
            gamma_type=args.gamma_type, norm=args.norm, use_pymedphys=False,
        )
        logger.info(f'Gamma computed. Global GPR: {pass_rate:.2f}%')

    # Load RTSTRUCT
    rtstruct_meta = None
    roi_names = []
    roi_masks = {}
    per_structure = []
    if args.rtstruct:
        logger.info(f'Loading RTSTRUCT: {args.rtstruct}')
        rtstruct_meta = load_rtstruct(args.rtstruct)
        if args.roi:
            roi_names = [r.strip() for r in args.roi.split(',')]
        else:
            roi_names = [r['name'] for r in rtstruct_meta['roi_list']]
        logger.info(f'Building ROI masks for: {roi_names}')
        roi_masks = build_roi_masks(rtstruct_meta, dose_meta, roi_names=roi_names)

        # Compute per-structure GPR
        for name, mask in roi_masks.items():
            masked_g = gamma_map[mask]
            finite = np.isfinite(masked_g)
            if finite.any():
                pr = float(np.sum(masked_g[finite] <= 1.0) / np.sum(finite) * 100.0)
            else:
                pr = float('nan')
            per_structure.append({'roi_name': name, 'pass_rate_percent': pr,
                                  'voxel_count': int(np.sum(mask))})

    # Launch viewer
    logger.info('Launching viewer...')
    gpr_cond = {'dd': args.dd, 'dta': args.dta, 'cutoff': args.cutoff}
    viewer = GammaViewer(ct_on_dose, gamma_map, dose_meta,
                         ref_dose=ref_dose, eval_dose=eval_on_ref,
                         rtstruct_meta=rtstruct_meta, roi_names=roi_names,
                         roi_masks=roi_masks, per_structure_stats=per_structure,
                         gpr_cond=gpr_cond,
                         ref_label=ref_label, eval_label=eval_label)
    plt.show()


if __name__ == '__main__':
    main()
