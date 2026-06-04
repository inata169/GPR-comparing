#!/usr/bin/env python
"""Interactive 3D Multi-plane Gamma Viewer (Axial/Sagittal/Coronal) with 3D Cursor.
Optimized for high performance with many structures and large volumes.
"""
import argparse
import json
import logging
import os
import sys

import matplotlib
import numpy as np

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
from matplotlib.widgets import CheckButtons, RadioButtons, Slider, TextBox

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

ROI_COLORS = [
    '#FF4444', '#4488FF', '#44DD44', '#FFAA00', '#FF44FF',
    '#44FFFF', '#FFFF44', '#AA44FF', '#FF8888', '#88AAFF',
]
_PASS_FAIL_CMAP = ListedColormap(['#00CC00', '#FF2222'])

class MultiPlaneViewer:
    def __init__(self, ct, gamma, dose_meta, ref_dose=None, eval_dose=None,
                 rtstruct_meta=None, roi_names=None, per_structure_stats=None,
                 gpr_cond=None, ref_label='', eval_label='', cache_radius=15):
        self.ct = ct        # (z, y, x)
        self.gamma = gamma  # (z, y, x)
        self.dose_meta = dose_meta
        self.ref_dose = ref_dose
        self.eval_dose = eval_dose
        self.rtstruct_meta = rtstruct_meta
        self.roi_names = roi_names or []
        self.per_structure_stats = per_structure_stats or []
        self.gpr_cond = gpr_cond
        self.ref_label = ref_label
        self.eval_label = eval_label
        self.cache_radius = max(0, int(cache_radius))

        self.nz, self.ny, self.nx = self.ct.shape
        self.cur_z = self.nz // 2
        self.cur_y = self.ny // 2
        self.cur_x = self.nx // 2

        # Spacings
        self.sx = float(dose_meta['s_col'])
        self.sy = float(dose_meta['s_row'])
        z_mm = dose_meta['z_coords_mm']
        self.sz = abs(float(z_mm[1] - z_mm[0])) if len(z_mm) > 1 else 1.0

        self.visible = {'CT': True, 'Structure': True}
        self.roi_visible = {name: True for name in self.roi_names}
        self.overlay_mode = 'Gamma'
        self.show_help = False
        self._last_active_plane = 'axial'

        self._load_state()

        # Precompute dose vmax
        self._dose_vmax = 1.0
        for d in [ref_dose, eval_dose]:
            if d is not None:
                self._dose_vmax = max(self._dose_vmax, float(np.nanmax(d)))
        
        self.dose_ratio = None
        if ref_dose is not None and eval_dose is not None:
            with np.errstate(divide='ignore', invalid='ignore'):
                self.dose_ratio = np.where(ref_dose > 0, eval_dose / ref_dose, np.nan)

        self.roi_contours = {}
        if rtstruct_meta:
            for roi in rtstruct_meta['roi_list']:
                if roi['name'] in self.roi_names:
                    self.roi_contours[roi['name']] = roi['contours']

        self._overlay_cache = {}
        self._structure_cache = {}

        self._init_plots()

    def _init_plots(self):
        self.fig = plt.figure(figsize=(15, 10), facecolor='#111111')
        self.fig.canvas.manager.set_window_title('rtgamma 3D Multi-Plane Viewer (Optimized)')
        self.fig.subplots_adjust(left=0.08, right=0.82, top=0.92, bottom=0.08, wspace=0.2, hspace=0.2)
        
        self.ax_ax = self.fig.add_subplot(221, facecolor='black')
        self.ax_sag = self.fig.add_subplot(222, facecolor='black')
        self.ax_cor = self.fig.add_subplot(223, facecolor='black')
        self.fig.subplots_adjust(left=0.08, right=0.82, top=0.92, bottom=0.10, wspace=0.25, hspace=0.35)

        self.axes_map = {
            'axial': self.ax_ax,
            'sagittal': self.ax_sag,
            'coronal': self.ax_cor
        }
        
        # Physical coordinates for display
        self.coords_mm = {
            'axial': self.dose_meta['z_coords_mm'],
            'sagittal': self.dose_meta['x_coords_mm'],
            'coronal': self.dose_meta['y_coords_mm']
        }
        
        # Artist storage to avoid ax.clear()
        self.ims = {} # imshow objects
        self.lines = {} # crosshairs
        self.roi_artists = {} # LineCollection objects per plane per ROI
        self.text_artists = {}
        self.widgets = {} # Store widgets to prevent garbage collection

        self.cax = self.fig.add_axes([0.48, 0.1, 0.01, 0.35])
        self.cax.set_visible(False)

        # --- CRITICAL: First draw creation MUST happen before widget setup
        # because Slider.set_val triggers _on_widget_change -> _update_display
        self._first_draw()
        
        self._setup_widgets()
        
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key)
        self.fig.canvas.mpl_connect('close_event', lambda e: self._save_state())

    def _setup_widgets(self):
        modes = ['Gamma', 'Pass/Fail', 'Ref Dose', 'Eval Dose', 'Dose Ratio']
        active_idx = modes.index(self.overlay_mode) if self.overlay_mode in modes else 0

        ax_modes = self.fig.add_axes([0.84, 0.32, 0.14, 0.16], facecolor='#222222')
        self.w_modes = RadioButtons(ax_modes, modes, active=active_idx)
        self.w_modes.on_clicked(self._on_mode_change)
        for l in self.w_modes.labels: l.set_color('white'); l.set_fontsize(8)

        ax_vis = self.fig.add_axes([0.84, 0.52, 0.14, 0.43], facecolor='#222222')
        vis_labels = ['CT', 'Structure'] + self.roi_names
        actives = [self.visible.get(l, self.roi_visible.get(l, True)) for l in vis_labels]
        self.w_vis = CheckButtons(ax_vis, vis_labels, actives)
        self.w_vis.on_clicked(self._on_visibility_change)
        for l in self.w_vis.labels:
            l.set_color('black')
            l.set_fontsize(7)
        
        def style_checkboxes(w):
            try:
                w.ax.set_facecolor('#CCCCCC')
                if hasattr(w, 'rectangles'):
                    for r in w.rectangles:
                        r.set_facecolor('white')
                        r.set_edgecolor('black')
                        r.set_linewidth(1.5)
                if hasattr(w, 'lines'):
                    for line_pair in w.lines:
                        for line in line_pair:
                            line.set_color('#00AA00')
                            line.set_linewidth(3)
                w.ax.figure.canvas.draw_idle()
            except Exception: pass
            
        style_checkboxes(self.w_vis)
        self.w_vis.on_clicked(lambda label: style_checkboxes(self.w_vis))

        self.t_filenames = self.fig.text(0.08, 0.97, f"Ref : {self.ref_label}\nEval: {self.eval_label}",
                                         color='#AAAAAA', family='monospace', fontsize=8, va='top')
        self.t_stats = self.fig.text(0.84, 0.30, self._get_stats_text(), color='#00FF00', family='monospace', fontsize=8, va='top')
        
        # --- Slice Navigation (Sliders + TextBoxes) ---
        def add_ctrl(plane, x, y, w, max_val):
            ax_sl = self.fig.add_axes([x, y, w * 0.65, 0.015], facecolor='#333333')
            sl = Slider(ax_sl, f'{plane[:1].upper()} ', 0, max_val, valinit=0, valstep=1, color='#00AA00')
            sl.label.set_color('white'); sl.label.set_fontsize(8); sl.valtext.set_visible(False)
            
            ax_txt = self.fig.add_axes([x + w * 0.72, y - 0.005, w * 0.28, 0.025], facecolor='#222222')
            txt = TextBox(ax_txt, '', initial='0', color='#222222', hovercolor='#333333')
            txt.label.set_color('white'); txt.text_disp.set_color('white'); txt.text_disp.set_fontsize(8)
            
            # Events
            sl.on_changed(lambda v: self._on_widget_change(plane, 'slider', v))
            txt.on_submit(lambda s: self._on_widget_change(plane, 'text', s))
            
            self.widgets[plane] = {'slider': sl, 'text': txt}

        # Positions below each subplot (tuned for hspace=0.35)
        # 221 (top-left) -> [0.08, 0.52, 0.35, 0.35]
        # 222 (top-right) -> [0.48, 0.52, 0.35, 0.35]
        # 223 (bot-left) -> [0.08, 0.10, 0.35, 0.35]
        add_ctrl('axial', 0.10, 0.49, 0.30, self.nz - 1)
        self.widgets['axial']['slider'].set_val(self.cur_z)
        
        add_ctrl('sagittal', 0.50, 0.49, 0.30, self.nx - 1)
        self.widgets['sagittal']['slider'].set_val(self.cur_x)
        
        add_ctrl('coronal', 0.10, 0.06, 0.30, self.ny - 1)
        self.widgets['coronal']['slider'].set_val(self.cur_y)

        help_txt = ("--- Help ---\nL-Click: Move Cursor\nScroll: Change Slice\nH: Toggle Help | Q: Quit\nInput: Enter Index or '12.3mm'")
        self.t_help = self.fig.text(0.5, 0.5, help_txt, color='white', family='monospace', fontsize=10, ha='center', va='center',
                                    bbox=dict(boxstyle='round,pad=1', fc='#333333', alpha=0.9, ec='#00FF00'))
        self.t_help.set_visible(False)

    def _on_widget_change(self, plane, source, val):
        self._last_active_plane = plane
        if source == 'slider':
            idx = int(val)
        else:
            try:
                s = val.strip().lower()
                if s.endswith('mm'):
                    v_mm = float(s[:-2].strip())
                    idx = np.argmin(np.abs(self.coords_mm[plane] - v_mm))
                else:
                    idx = int(s)
            except Exception: return
        
        idx = np.clip(idx, 0, (self.nz if plane=='axial' else (self.nx if plane=='sagittal' else self.ny)) - 1)
        if plane == 'axial': self.cur_z = idx
        elif plane == 'sagittal': self.cur_x = idx
        elif plane == 'coronal': self.cur_y = idx
        self._update_display()

    def _get_stats_text(self):
        txt = ""
        if self.gpr_cond:
            txt += f"Criteria: {self.gpr_cond['dta']:.1f}mm / {self.gpr_cond['dd']:.1f}%\n"
            txt += f"Cutoff  : {self.gpr_cond['cutoff']:.1f}%\n"
        txt += "--------------------\n"
        txt += "ROI GPR[%]\n"
        for s in self.per_structure_stats:
            val = s['pass_rate_percent']
            val_str = f"{val:5.1f}%" if np.isfinite(val) else "  N/A"
            txt += f"{s['roi_name'][:12]:12}: {val_str}\n"
        return txt

    def _on_mode_change(self, label):
        self.overlay_mode = label
        self._invalidate_overlay_cache()
        self._update_display(full=True)

    def _on_visibility_change(self, label):
        if label in self.visible: self.visible[label] = not self.visible[label]
        else: self.roi_visible[label] = not self.roi_visible[label]
        self._update_display(full=True)

    def _on_click(self, event):
        if event.inaxes in self.axes_map.values(): self._update_cursor(event); self._update_display()

    def _on_mouse_move(self, event):
        if event.button == 1 and event.inaxes in self.axes_map.values(): self._update_cursor(event); self._update_display()

    def _on_scroll(self, event):
        ax, step = event.inaxes, (1 if event.button == 'up' else -1)
        if ax == self.ax_ax:
            self._last_active_plane = 'axial'
            self.cur_z = np.clip(self.cur_z + step, 0, self.nz - 1)
        elif ax == self.ax_sag:
            self._last_active_plane = 'sagittal'
            self.cur_x = np.clip(self.cur_x + step, 0, self.nx - 1)
        elif ax == self.ax_cor:
            self._last_active_plane = 'coronal'
            self.cur_y = np.clip(self.cur_y + step, 0, self.ny - 1)
        else:
            self._last_active_plane = 'axial'
            self.cur_z = np.clip(self.cur_z + step, 0, self.nz - 1)
        self._update_display()

    def _on_key(self, event):
        if event.key in ['h', 'H']: self.t_help.set_visible(not self.t_help.get_visible()); self.fig.canvas.draw_idle()
        elif event.key in ['q', 'Q']: plt.close(self.fig)

    def _update_cursor(self, event):
        ix, iy = int(round(event.xdata)), int(round(event.ydata))
        if event.inaxes == self.ax_ax:
            self._last_active_plane = 'axial'
            self.cur_x, self.cur_y = np.clip(ix, 0, self.nx-1), np.clip(iy, 0, self.ny-1)
        elif event.inaxes == self.ax_sag:
            self._last_active_plane = 'sagittal'
            self.cur_y, self.cur_z = np.clip(ix, 0, self.ny-1), np.clip(iy, 0, self.nz-1)
        elif event.inaxes == self.ax_cor:
            self._last_active_plane = 'coronal'
            self.cur_x, self.cur_z = np.clip(ix, 0, self.nx-1), np.clip(iy, 0, self.nz-1)

    def _first_draw(self):
        """Initial creation of all artists."""
        for plane in ['axial', 'sagittal', 'coronal']:
            ax = self.axes_map[plane]
            # Axial: usually top is Anterior (index 0). S/C: Superior (index N) is top.
            origin = 'upper' if plane == 'axial' else 'lower'
            self.ims[(plane, 'ct')] = ax.imshow(np.zeros((1,1)), cmap='gray', vmin=-200, vmax=300, origin=origin)
            self.ims[(plane, 'ovl')] = ax.imshow(np.zeros((1,1)), alpha=0.5, origin=origin)
            self.lines[(plane, 'h')] = ax.axhline(0, color='yellow', lw=0.5, alpha=0.6)
            self.lines[(plane, 'v')] = ax.axvline(0, color='yellow', lw=0.5, alpha=0.6)
            self.text_artists[plane] = ax.text(0.03, 0.05, "", transform=ax.transAxes, color='#00FF00',
                                              fontsize=8, fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', fc='black', alpha=0.6, ec='#333333'))
            
            for ci, name in enumerate(self.roi_names):
                lc = LineCollection([], colors=ROI_COLORS[ci % len(ROI_COLORS)], linewidths=1.2, alpha=0.9)
                ax.add_collection(lc)
                self.roi_artists[(plane, name)] = lc
        
        self._set_aspects()
        self._update_display(full=True)

    def _set_aspects(self):
        self.ax_ax.set_aspect(self.sy / self.sx)
        self.ax_sag.set_aspect(self.sz / self.sy)
        self.ax_cor.set_aspect(self.sz / self.sx)
        
        # Standard orientation check: Superior is Up for Sagittal/Coronal
        # origin='lower' handles this if index Z increases Superiorly.

    def _update_display(self, full=False):
        """Update existings artists with new data. Very fast."""
        v_ct = self.visible['CT']
        v_str = self.visible['Structure']
        mode = self.overlay_mode

        # Update slices
        self._update_plane('axial', self.cur_z, v_ct, v_str, mode)
        self._update_plane('sagittal', self.cur_x, v_ct, v_str, mode)
        self._update_plane('coronal', self.cur_y, v_ct, v_str, mode)

        # Update crosshairs
        self.lines[('axial', 'h')].set_ydata([self.cur_y, self.cur_y])
        self.lines[('axial', 'v')].set_xdata([self.cur_x, self.cur_x])
        self.lines[('sagittal', 'h')].set_ydata([self.cur_z, self.cur_z])
        self.lines[('sagittal', 'v')].set_xdata([self.cur_y, self.cur_y])
        self.lines[('coronal', 'h')].set_ydata([self.cur_z, self.cur_z])
        self.lines[('coronal', 'v')].set_xdata([self.cur_x, self.cur_x])

        # Sync Widgets (only if initialized)
        def sync(plane, idx):
            if plane not in self.widgets: return
            w = self.widgets[plane]
            w['slider'].eventson = False
            w['slider'].set_val(idx)
            w['slider'].eventson = True
            pos_mm = self.coords_mm[plane][idx]
            w['text'].set_val(f"{idx} ({pos_mm:+.1f}mm)")
        
        sync('axial', self.cur_z)
        sync('sagittal', self.cur_x)
        sync('coronal', self.cur_y)

        self._prefetch_neighbors()
        self._trim_caches()
        self.fig.canvas.draw_idle()

    def _overlay_cache_key(self, plane, idx, mode):
        return (plane, int(idx), mode)

    def _structure_cache_key(self, plane, idx, name):
        return (plane, int(idx), name)

    def _expected_shape(self, plane):
        if plane == 'axial':
            return (self.ny, self.nx)
        if plane == 'sagittal':
            return (self.nz, self.ny)
        return (self.nz, self.nx)

    def _slice_for_plane(self, volume, plane, idx):
        if volume is None:
            return None
        if plane == 'axial':
            return volume[idx, :, :]
        if plane == 'sagittal':
            return volume[:, :, idx]
        return volume[:, idx, :]

    def _slice_gpr_text(self, g2d):
        valid = np.isfinite(g2d) & (g2d > 0)
        if not np.any(valid):
            return None
        n_v, n_ok = np.sum(valid), np.sum(g2d[valid] <= 1.0)
        sgpr = n_ok / n_v * 100.0
        return f"Slice GPR: {sgpr:.1f}% ({n_ok}/{n_v})"

    def _compute_pass_fail_entry(self, g2d):
        pf = np.full_like(g2d, np.nan)
        v = np.isfinite(g2d) & (g2d != 0)
        pf[v & (g2d <= 1.0)] = 0
        pf[v & (g2d > 1.0)] = 1
        return {'data': pf, 'mask': ~v, 'cmap': _PASS_FAIL_CMAP, 'clim': (0, 1)}

    def _compute_overlay_entry(self, plane, idx, mode):
        g2d = self._slice_for_plane(self.gamma, plane, idx)
        ref2d = self._slice_for_plane(self.ref_dose, plane, idx)
        eval2d = self._slice_for_plane(self.eval_dose, plane, idx)
        ratio2d = self._slice_for_plane(self.dose_ratio, plane, idx)
        stats_text = self._slice_gpr_text(g2d)

        if mode == 'Gamma':
            entry = {
                'data': g2d,
                'mask': ~np.isfinite(g2d) | (g2d == 0),
                'cmap': 'turbo',
                'clim': (0, 2),
            }
        elif mode == 'Pass/Fail':
            entry = self._compute_pass_fail_entry(g2d)
        elif mode == 'Ref Dose' and ref2d is not None:
            entry = {
                'data': ref2d,
                'mask': ref2d < self._dose_vmax*0.1,
                'cmap': 'jet',
                'clim': (0, self._dose_vmax),
            }
        elif mode == 'Eval Dose' and eval2d is not None:
            entry = {
                'data': eval2d,
                'mask': eval2d < self._dose_vmax*0.1,
                'cmap': 'jet',
                'clim': (0, self._dose_vmax),
            }
        elif mode == 'Dose Ratio' and ratio2d is not None:
            entry = {
                'data': ratio2d,
                'mask': ~np.isfinite(ratio2d),
                'cmap': 'bwr',
                'clim': (0.8, 1.2),
            }
        else:
            entry = {'visible': False}

        entry['visible'] = entry.get('visible', True)
        entry['stats_text'] = stats_text
        return entry

    def _entry_shape_matches(self, entry, expected_shape):
        if not entry.get('visible', True):
            return True
        data = entry.get('data')
        mask = entry.get('mask')
        if data is None or data.shape != expected_shape:
            return False
        return mask is None or mask.shape == expected_shape

    def _get_overlay_entry(self, plane, idx, mode):
        if self.cache_radius == 0:
            return self._compute_overlay_entry(plane, idx, mode)

        key = self._overlay_cache_key(plane, idx, mode)
        expected_shape = self._expected_shape(plane)
        entry = self._overlay_cache.get(key)
        if entry is not None:
            if self._entry_shape_matches(entry, expected_shape):
                return entry
            self._overlay_cache.pop(key, None)

        entry = self._compute_overlay_entry(plane, idx, mode)
        if self._entry_shape_matches(entry, expected_shape):
            self._overlay_cache[key] = entry
        return entry

    def _apply_overlay_entry(self, im_ovl, entry, expected_shape):
        if not entry.get('visible', True):
            im_ovl.set_visible(False)
            return

        if not self._entry_shape_matches(entry, expected_shape):
            im_ovl.set_visible(False)
            return

        data = entry['data']
        mask = entry.get('mask')
        im_ovl.set_data(np.ma.array(data, mask=mask) if mask is not None else data)
        im_ovl.set_cmap(entry['cmap'])
        im_ovl.set_clim(*entry['clim'])
        im_ovl.set_visible(True)

    def _invalidate_overlay_cache(self):
        self._overlay_cache.clear()

    def _invalidate_structure_cache(self):
        self._structure_cache.clear()

    def _plane_index(self, plane):
        if plane == 'axial':
            return int(self.cur_z)
        if plane == 'sagittal':
            return int(self.cur_x)
        return int(self.cur_y)

    def _prefetch_neighbors(self):
        if self.cache_radius == 0:
            return
        plane = self._last_active_plane
        idx = self._plane_index(plane)
        max_idx = (self.nz if plane == 'axial' else (self.nx if plane == 'sagittal' else self.ny)) - 1
        max_new = 2
        new_count = 0
        for nidx in (idx - 1, idx + 1):
            if new_count >= max_new or nidx < 0 or nidx > max_idx:
                continue
            key = self._overlay_cache_key(plane, nidx, self.overlay_mode)
            if key not in self._overlay_cache:
                self._get_overlay_entry(plane, nidx, self.overlay_mode)
                new_count += 1

    def _trim_caches(self):
        if self.cache_radius == 0:
            self._overlay_cache.clear()
            self._structure_cache.clear()
            return

        cur = {'axial': int(self.cur_z), 'sagittal': int(self.cur_x), 'coronal': int(self.cur_y)}
        for key in list(self._overlay_cache):
            plane, idx, _mode = key
            if abs(idx - cur[plane]) > self.cache_radius:
                self._overlay_cache.pop(key, None)
        for key in list(self._structure_cache):
            plane, idx, _name = key
            if abs(idx - cur[plane]) > self.cache_radius:
                self._structure_cache.pop(key, None)

    def _update_plane(self, plane, idx, v_ct, v_str, mode):
        ax = self.axes_map[plane]
        ct2d = self._slice_for_plane(self.ct, plane, idx)

        # CT
        im_ct = self.ims[(plane, 'ct')]
        if v_ct:
            im_ct.set_data(ct2d)
            im_ct.set_visible(True)
            im_ct.set_extent([0, ct2d.shape[1], ct2d.shape[0], 0] if plane=='axial' else [0, ct2d.shape[1], 0, ct2d.shape[0]])
        else:
            im_ct.set_visible(False)

        # Overlay
        im_ovl = self.ims[(plane, 'ovl')]
        entry = self._get_overlay_entry(plane, idx, mode)
        self._apply_overlay_entry(im_ovl, entry, self._expected_shape(plane))
        im_ovl.set_extent(im_ct.get_extent())

        # Stats text
        if entry.get('stats_text'):
            self.text_artists[plane].set_text(entry['stats_text'])
            self.text_artists[plane].set_visible(True)
        else:
            self.text_artists[plane].set_visible(False)

        # Structures
        if v_str and self.rtstruct_meta:
            self._update_structures(plane, idx)
        else:
            for name in self.roi_names: self.roi_artists[(plane, name)].set_segments([])

        ax.set_title(f"{plane.capitalize()} (idx {idx})", color='white', fontsize=9)

    def _update_structures(self, plane, idx):
        for name in self.roi_names:
            if not self.roi_visible.get(name, True):
                self.roi_artists[(plane, name)].set_segments([])
                continue
            self.roi_artists[(plane, name)].set_segments(self._get_structure_segments(plane, idx, name))

    def _compute_structure_segments(self, plane, idx, name):
        ipp = self.dose_meta['ipp']
        s_col, s_row = self.dose_meta['s_col'], self.dose_meta['s_row']
        v_col, v_row, v_slice = self.dose_meta['v_col'], self.dose_meta['v_row'], self.dose_meta['v_slice']
        segments = []
        if plane == 'axial':
            from rtgamma.mask import _world_xy_to_grid_rc
            z_w = ipp[2] + self.dose_meta['z_coords_mm'][idx] * v_slice[2]
            for c_pts_dict in self.roi_contours.get(name, []):
                if abs(c_pts_dict['z'] - z_w) < self.sz * 0.51:
                    rc = _world_xy_to_grid_rc(c_pts_dict['points'], self.dose_meta)
                    # Convert to list of segments for LineCollection consistency or just plot
                    # For Axial, we use segments of (x,y)
                    pts = rc[:, [1, 0]]
                    for i in range(len(pts)):
                        segments.append([pts[i], pts[(i+1)%len(pts)]])

        elif plane == 'sagittal':
            x_w = ipp[0] + self.dose_meta['x_coords_mm'][idx] * v_col[0]
            for c_pts_dict in self.roi_contours.get(name, []):
                pts = c_pts_dict['points']
                z_grid = (c_pts_dict['z'] - ipp[2]) / (self.sz * v_slice[2])
                inters = []
                for k in range(len(pts)):
                    p1, p2 = pts[k], pts[(k+1)%len(pts)]
                    if (p1[0]-x_w)*(p2[0]-x_w) <= 0 and p1[0] != p2[0]:
                        inters.append((p1[1] + (x_w-p1[0])/(p2[0]-p1[0])*(p2[1]-p1[1]) - ipp[1]) / (s_row * v_row[1]))
                if len(inters) >= 2:
                    inters.sort()
                    for i in range(0, (len(inters)//2)*2, 2): segments.append([(inters[i], z_grid), (inters[i+1], z_grid)])

        elif plane == 'coronal':
            y_w = ipp[1] + self.dose_meta['y_coords_mm'][idx] * v_row[1]
            for c_pts_dict in self.roi_contours.get(name, []):
                pts = c_pts_dict['points']
                z_grid = (c_pts_dict['z'] - ipp[2]) / (self.sz * v_slice[2])
                inters = []
                for k in range(len(pts)):
                    p1, p2 = pts[k], pts[(k+1)%len(pts)]
                    if (p1[1]-y_w)*(p2[1]-y_w) <= 0 and p1[1] != p2[1]:
                        inters.append((p1[0] + (y_w-p1[1])/(p2[1]-p1[1])*(p2[0]-p1[0]) - ipp[0]) / (s_col * v_col[0]))
                if len(inters) >= 2:
                    inters.sort()
                    for i in range(0, (len(inters)//2)*2, 2): segments.append([(inters[i], z_grid), (inters[i+1], z_grid)])
        return segments

    def _get_structure_segments(self, plane, idx, name):
        if self.cache_radius == 0:
            return self._compute_structure_segments(plane, idx, name)
        key = self._structure_cache_key(plane, idx, name)
        if key not in self._structure_cache:
            self._structure_cache[key] = self._compute_structure_segments(plane, idx, name)
        return self._structure_cache[key]

    def _get_state_path(self):
        return os.path.join(ROOT, 'scripts', 'viewer_settings.json')

    def _save_state(self):
        state = {
            'cur_z': int(self.cur_z), 'cur_y': int(self.cur_y), 'cur_x': int(self.cur_x),
            'visible': self.visible, 'roi_visible': self.roi_visible, 'overlay_mode': self.overlay_mode,
        }
        try:
            win = self.fig.canvas.manager.window
            state['geometry'] = win.geometry()
            state['is_maximized'] = (win.state() == 'zoomed')
        except Exception: pass
        try:
            with open(self._get_state_path(), 'w') as f: json.dump(state, f)
        except Exception: pass

    def _load_state(self):
        path = self._get_state_path()
        if not os.path.exists(path): return
        try:
            with open(path, 'r') as f: state = json.load(f)
            self.cur_z = min(state.get('cur_z', self.cur_z), self.nz - 1)
            self.cur_y = min(state.get('cur_y', self.cur_y), self.ny - 1)
            self.cur_x = min(state.get('cur_x', self.cur_x), self.nx - 1)
            self.visible.update(state.get('visible', {}))
            self.roi_visible.update(state.get('roi_visible', {}))
            self.overlay_mode = state.get('overlay_mode', self.overlay_mode)
        except Exception: pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ct', required=True)
    parser.add_argument('--ref', required=True)
    parser.add_argument('--eval')
    parser.add_argument('--gamma-npz')
    parser.add_argument('--rtstruct')
    parser.add_argument('--roi')
    parser.add_argument('--dd', type=float, default=3.0)
    parser.add_argument('--dta', type=float, default=2.0)
    parser.add_argument('--cutoff', type=float, default=10.0)
    parser.add_argument('--gamma-type', choices=['global', 'local'], default='global')
    parser.add_argument('--norm', choices=['global_max', 'max_ref', 'none'], default='global_max')
    parser.add_argument('--cache-radius', type=int, default=15)
    args = parser.parse_args()

    ct_meta = load_ct(args.ct)
    dose_meta = load_rtdose(args.ref)
    ct_on_dose = resample_ct_onto_dose(ct_meta, dose_meta)
    
    eval_on_ref = None
    if args.gamma_npz:
        gamma_map = np.load(args.gamma_npz)['gamma']
        if args.eval:
            eval_meta = load_rtdose(args.eval)
            from rtgamma.io_dicom import world_to_index
            from rtgamma.main import build_ref_world_coords
            from rtgamma.resample import resample_eval_onto_ref
            Xw, Yw, Zw = build_ref_world_coords(dose_meta)
            w2i = lambda pts: world_to_index(eval_meta['ipp'], eval_meta['v_col'], eval_meta['v_row'], eval_meta['v_slice'], eval_meta['s_col'], eval_meta['s_row'], eval_meta['z_offsets'], pts)
            eval_on_ref = resample_eval_onto_ref(eval_meta['dose'], w2i, (Xw, Yw, Zw), interp='linear', shift_mm=(0, 0, 0))
    else:
        eval_meta = load_rtdose(args.eval)
        from rtgamma.io_dicom import world_to_index
        from rtgamma.main import build_ref_world_coords
        from rtgamma.resample import resample_eval_onto_ref
        Xw, Yw, Zw = build_ref_world_coords(dose_meta)
        w2i = lambda pts: world_to_index(eval_meta['ipp'], eval_meta['v_col'], eval_meta['v_row'], eval_meta['v_slice'], eval_meta['s_col'], eval_meta['s_row'], eval_meta['z_offsets'], pts)
        eval_on_ref = resample_eval_onto_ref(eval_meta['dose'], w2i, (Xw, Yw, Zw), interp='linear', shift_mm=(0, 0, 0))
        axes = (dose_meta['z_coords_mm'], dose_meta['y_coords_mm'], dose_meta['x_coords_mm'])
        gamma_map, _, _ = compute_gamma(axes, dose_meta['dose'], axes, eval_on_ref, args.dd, args.dta, args.cutoff, args.gamma_type, args.norm)

    rtstruct_meta = load_rtstruct(args.rtstruct) if args.rtstruct else None
    roi_names = [n.strip() for n in args.roi.split(',')] if args.roi else ([r['name'] for r in rtstruct_meta['roi_list']] if rtstruct_meta else [])
    
    per_structure = []
    roi_masks = build_roi_masks(rtstruct_meta, dose_meta, roi_names=roi_names) if rtstruct_meta else {}
    for name, mask in roi_masks.items():
        masked_g = gamma_map[mask]; finite = np.isfinite(masked_g)
        pr = float(np.sum(masked_g[finite] <= 1.0) / np.sum(finite) * 100.0) if finite.any() else float('nan')
        per_structure.append({'roi_name': name, 'pass_rate_percent': pr})

    viewer = MultiPlaneViewer(ct_on_dose, gamma_map, dose_meta, dose_meta['dose'], eval_on_ref, rtstruct_meta, roi_names, per_structure,
                             {'dd': args.dd, 'dta': args.dta, 'cutoff': args.cutoff},
                             os.path.basename(args.ref), os.path.basename(args.eval) if args.eval else '',
                             cache_radius=args.cache_radius)
    plt.show()

if __name__ == '__main__':
    main()
