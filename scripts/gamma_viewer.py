#!/usr/bin/env python
"""Interactive 3D Gamma Viewer with CT background and Structure overlay.

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
        --gamma-npz output/gamma3d.npz \
        --rtstruct dicom/PROSTATE/RTSTRUCT_*.dcm
"""
import os
import sys
import argparse
import logging
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons, CheckButtons
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

# Ensure repo root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rtgamma.io_dicom import load_rtdose, load_ct, load_rtstruct
from rtgamma.resample import resample_ct_onto_dose
from rtgamma.mask import build_roi_masks
from rtgamma.gamma import compute_gamma

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── Predefined ROI colors ────────────────────────────────────────────────────
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
    def __init__(self, ct_on_dose, gamma_map, dose_meta, rtstruct_meta=None,
                 roi_names=None, roi_masks=None, per_structure_stats=None,
                 gpr_cond=None):
        self.ct = ct_on_dose  # (z, y, x) HU
        self.gamma = gamma_map  # (z, y, x)
        self.dose_meta = dose_meta
        self.rtstruct_meta = rtstruct_meta
        self.roi_names = roi_names or []
        self.per_structure_stats = per_structure_stats or []
        self.gpr_cond = gpr_cond
        
        self.plane = 'axial'
        self.nz, self.ny, self.nx = self.ct.shape
        self.slice_idx = self.nz // 2
        
        self.visible = {'CT': True, 'Gamma': True, 'Structure': True}
        self.roi_visible = {name: True for name in self.roi_names}

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
        self.fig = plt.figure(figsize=(12, 8), facecolor='#111111')
        self.fig.canvas.manager.set_window_title('rtgamma 3D Viewer')
        self.ax = self.fig.add_axes([0.05, 0.15, 0.70, 0.80])
        self.ax.set_facecolor('#000000')

        # Slider
        ax_slider = self.fig.add_axes([0.05, 0.05, 0.70, 0.03], facecolor='#222222')
        self.slider = Slider(ax_slider, 'Slice', 0, self.nz-1, valinit=self.slice_idx, valstep=1, color='#4466FF')
        # Use a wrapper to avoid recursion
        self.slider.on_changed(self._on_slider_move)

        # Toggles (Layer & ROIs)
        ax_toggles = self.fig.add_axes([0.80, 0.60, 0.15, 0.35], facecolor='#222222')
        self.check = CheckButtons(ax_toggles, ['CT', 'Gamma', 'Structure'] + self.roi_names, 
                                 [True] * (3 + len(self.roi_names)))
        self.check.on_clicked(self._on_toggle)
        for lbl in self.check.labels:
            lbl.set_color('#FFFFFF') # White text
            lbl.set_fontsize(8)
        
        # Checkbox visibility and size adaptations
            # Matplotlib >= 3.7: Use props dictionary to modify color/linewidth
            self.check.set_frame_props({'edgecolor': '#AAAAAA', 'facecolor': '#222222', 'linewidths': 1.0})
            self.check.set_check_props({'color': '#00FF00', 'linewidths': 2.0})
            # To have larger checkboxes that actually toggle, we must update sizes manually
            self._update_check_sizes()
        else:
            # Older Matplotlib versions using rectangles/lines
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

        # Plane
        ax_plane = self.fig.add_axes([0.80, 0.45, 0.15, 0.12], facecolor='#222222')
        self.radio = RadioButtons(ax_plane, ('axial', 'sagittal', 'coronal'), active=0)
        self.radio.on_clicked(self._on_plane)
        for lbl in self.radio.labels: lbl.set_color('#EEEEEE'); lbl.set_fontsize(9)

        # GPR Table
        self.txt = self.fig.text(0.80, 0.30, self._gpr_text(), color='#00FF00', family='monospace', fontsize=8, va='top')

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
            self.slider.set_val(new_idx) # This triggers _on_slider_move but guards prevent recursion
            self._draw()

    def _on_toggle(self, label):
        if label in self.visible: self.visible[label] = not self.visible[label]
        else: self.roi_visible[label] = not self.roi_visible[label]
        self._update_check_sizes()
        self._draw()

    def _update_check_sizes(self):
        """Manually update sizes to ensure toggling works with custom styles."""
        if not hasattr(self.check, 'set_check_props'): return
        # In newer Matplotlib, CheckButtons uses a scatter (PathCollection) for checks
        try:
            status = self.check.get_status()
            # The 'checks' property is the scatter collection (usually named 'checks')
            if hasattr(self.check, 'checks'):
                # Size 70 if checked, 0 if unchecked
                sizes = [70 if s else 0 for s in status]
                self.check.checks.set_sizes(sizes)
        except: pass

    def _on_plane(self, label):
        self.plane = label
        mx = self.nz-1 if label=='axial' else (self.nx-1 if label=='sagittal' else self.ny-1)
        self.slider.valmax = mx
        self.slice_idx = min(self.slice_idx, mx)
        # Update slider without recursive trigger if possible, or just set_val
        self.slider.set_val(self.slice_idx)
        self.slider.ax.set_xlim(0, mx)
        self._draw()

    def _draw(self):
        self.ax.clear()
        if self.visible['CT']:
            ct2d = self._get_slice(self.ct)
            self.ax.imshow(ct2d, cmap='gray', vmin=-200, vmax=300, aspect='auto', origin='lower')
        
        if self.visible['Gamma']:
            g2d = self._get_slice(self.gamma)
            gm = np.ma.masked_where(~np.isfinite(g2d) | (g2d == 0), g2d)
            self.ax.imshow(gm, cmap='turbo', vmin=0, vmax=2, alpha=0.5, aspect='auto', origin='lower')

        if self.visible['Structure'] and self.plane == 'axial' and self.rtstruct_meta:
            z_w = self.dose_z_world[self.slice_idx]
            from rtgamma.mask import _world_xy_to_grid_rc
            for i, name in enumerate(self.roi_names):
                if not self.roi_visible[name]: continue
                for pts in get_contours_for_slice(self.roi_contour_data[name], z_w, self.z_tol):
                    rc = _world_xy_to_grid_rc(pts, self.dose_meta)
                    self.ax.add_patch(Polygon(rc[:, [1, 0]], closed=True, fill=False, 
                                            edgecolor=ROI_COLORS[i % len(ROI_COLORS)], lw=1))
        
        self.ax.set_title(f"{self.plane} view - slice {self.slice_idx}", color='white', fontsize=10)
        self.fig.canvas.draw()


def main():
    parser = argparse.ArgumentParser(description='3D Gamma Viewer with CT + Structure overlay')
    parser.add_argument('--ct', required=True, help='Directory containing CT DICOM slices')
    parser.add_argument('--ref', required=True, help='Reference RTDOSE DICOM file')
    parser.add_argument('--eval', help='Evaluation RTDOSE DICOM file (omit if using --gamma-npz)')
    parser.add_argument('--gamma-npz', help='Pre-computed gamma NPZ file (skip gamma calculation)')
    parser.add_argument('--rtstruct', help='RTSTRUCT DICOM file or directory')
    parser.add_argument('--roi', help='Comma-separated ROI names (default: all)')
    parser.add_argument('--dd', type=float, default=3.0)
    parser.add_argument('--dta', type=float, default=2.0)
    parser.add_argument('--cutoff', type=float, default=10.0)
    parser.add_argument('--gamma-type', choices=['global', 'local'], default='global')
    parser.add_argument('--norm', choices=['global_max', 'max_ref', 'none'], default='global_max')
    args = parser.parse_args()

    # Load CT
    logger.info(f'Loading CT from: {args.ct}')
    ct_meta = load_ct(args.ct)
    logger.info(f'CT loaded: {ct_meta["shape"]}')

    # Load reference DOSE
    logger.info(f'Loading reference DOSE: {args.ref}')
    dose_meta = load_rtdose(args.ref)
    logger.info(f'DOSE loaded: {dose_meta["shape"]}')

    # Resample CT onto DOSE grid
    logger.info('Resampling CT onto DOSE grid...')
    ct_on_dose = resample_ct_onto_dose(ct_meta, dose_meta)
    logger.info(f'CT resampled: {ct_on_dose.shape}')

    # Gamma map: compute or load
    if args.gamma_npz:
        logger.info(f'Loading pre-computed gamma from: {args.gamma_npz}')
        npz = np.load(args.gamma_npz)
        gamma_map = npz['gamma']
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
                         rtstruct_meta=rtstruct_meta, roi_names=roi_names,
                         roi_masks=roi_masks, per_structure_stats=per_structure,
                         gpr_cond=gpr_cond)
    plt.show()


if __name__ == '__main__':
    main()
