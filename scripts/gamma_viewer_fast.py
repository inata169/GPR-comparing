#!/usr/bin/env python
"""PyQtGraph-based fast 3D viewer proof of concept.

This PoC intentionally avoids changing scripts/gamma_viewer.py. It focuses on
three synchronized voxel-index planes, CT display, Gamma overlay, and cursor
values for HU / Ref / Eval.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rtgamma.gamma import compute_gamma
from rtgamma.io_dicom import load_ct, load_rtdose, load_rtstruct, world_to_index
from rtgamma.main import build_ref_world_coords
from rtgamma.mask import build_roi_masks
from rtgamma.resample import resample_ct_onto_dose, resample_eval_onto_ref

logger = logging.getLogger(__name__)


def _import_qtgraph():
    try:
        import pyqtgraph as pg
        from PySide6 import QtCore, QtWidgets
    except ImportError as exc:
        print("[ERROR] Fast Viewer dependencies are missing.")
        print("Install them with:")
        print("  pip install -r requirements-fast-viewer.txt")
        print(f"Import error: {exc}")
        return None, None, None
    return QtCore, QtWidgets, pg


def _format_dose_unit(unit: str | None) -> str:
    unit = str(unit or "").strip()
    if unit.upper() == "GY":
        return "Gy"
    return unit or "Gy"


def _safe_voxel_value(volume: np.ndarray | None, z: int, y: int, x: int) -> float | None:
    if volume is None or getattr(volume, "ndim", None) != 3:
        return None
    if not (0 <= z < volume.shape[0] and 0 <= y < volume.shape[1] and 0 <= x < volume.shape[2]):
        return None
    value = volume[z, y, x]
    if not np.isfinite(value):
        return None
    return float(value)


def _strict_voxel_value(volume: np.ndarray | None, ct: np.ndarray, z: int, y: int, x: int) -> float | None:
    if volume is None or getattr(volume, "ndim", None) != 3:
        return None
    if volume.shape != ct.shape:
        return None
    return _safe_voxel_value(volume, z, y, x)


def _load_gamma_npz(path: str | None) -> np.ndarray | None:
    if not path:
        return None
    try:
        with np.load(path) as npz:
            if "gamma" not in npz:
                logger.warning("Gamma NPZ has no 'gamma' key: %s (keys=%s)", path, list(npz.keys()))
                return None
            return np.asarray(npz["gamma"])
    except Exception as exc:
        logger.warning("Failed to load Gamma NPZ '%s': %s", path, exc)
        return None


def _resample_eval(eval_path: str | None, dose_meta: dict) -> tuple[np.ndarray | None, str]:
    if not eval_path:
        return None, ""
    eval_meta = load_rtdose(eval_path)
    Xw, Yw, Zw = build_ref_world_coords(dose_meta)
    w2i = lambda pts: world_to_index(
        eval_meta["ipp"],
        eval_meta["v_col"],
        eval_meta["v_row"],
        eval_meta["v_slice"],
        eval_meta["s_col"],
        eval_meta["s_row"],
        eval_meta["z_offsets"],
        pts,
    )
    eval_on_ref = resample_eval_onto_ref(
        eval_meta["dose"],
        w2i,
        (Xw, Yw, Zw),
        interp="linear",
        shift_mm=(0, 0, 0),
    )
    return eval_on_ref, eval_meta.get("units", "")


def _compute_gamma_if_needed(args, dose_meta: dict, eval_on_ref: np.ndarray | None) -> np.ndarray | None:
    gamma = _load_gamma_npz(args.gamma_npz)
    if gamma is not None:
        return gamma
    if not args.gamma_npz and eval_on_ref is not None:
        logger.info("No --gamma-npz supplied. Computing Gamma map for PoC display.")
        axes = (dose_meta["z_coords_mm"], dose_meta["y_coords_mm"], dose_meta["x_coords_mm"])
        gamma_map, _, _ = compute_gamma(
            axes,
            dose_meta["dose"],
            axes,
            eval_on_ref,
            args.dd,
            args.dta,
            args.cutoff,
            args.gamma_type,
            args.norm,
        )
        return gamma_map
    return None


@dataclass
class PlaneState:
    plane: str
    title: object
    view: object
    ct_item: object
    gamma_item: object
    hline: object
    vline: object
    label: object
    slider: object
    slider_label: object
    structure_items: dict[str, object]


class FastPlaneViewer:
    def __init__(
        self,
        ct: np.ndarray,
        ref_dose: np.ndarray,
        eval_dose: np.ndarray | None,
        gamma: np.ndarray | None,
        dose_meta: dict,
        rtstruct_meta: dict | None,
        roi_names: list[str],
        per_structure_stats: list[dict],
        gpr_cond: dict,
        ref_label: str,
        eval_label: str,
        ref_unit: str,
        eval_unit: str,
        QtCore,
        QtWidgets,
        pg,
    ):
        self.ct = ct
        self.ref_dose = ref_dose
        self.eval_dose = eval_dose
        self.gamma = gamma if gamma is not None and gamma.shape == ref_dose.shape else None
        self.dose_meta = dose_meta
        self.rtstruct_meta = rtstruct_meta
        self.roi_names = roi_names
        self.per_structure_stats = per_structure_stats
        self.gpr_cond = gpr_cond
        self.ref_label = ref_label
        self.eval_label = eval_label
        self.gamma_warning = ""
        if gamma is None:
            self.gamma_warning = "Gamma overlay: N/A"
        elif gamma.shape != ref_dose.shape:
            self.gamma_warning = f"Gamma overlay disabled: shape {gamma.shape} != ref {ref_dose.shape}"

        self.ref_unit = _format_dose_unit(ref_unit)
        self.eval_unit = _format_dose_unit(eval_unit)
        self.QtCore = QtCore
        self.QtWidgets = QtWidgets
        self.pg = pg

        self.nz, self.ny, self.nx = self.ct.shape
        self.cur_z = self.nz // 2
        self.cur_y = self.ny // 2
        self.cur_x = self.nx // 2
        self.overlay_alpha = 128
        self.overlay_visible = self.gamma is not None
        self.overlay_mode = "Gamma"
        self.visible = {"CT": True, "Structure": True}
        self.roi_visible = {name: True for name in self.roi_names}
        self.ct_levels = self._ct_levels()
        z_mm = dose_meta["z_coords_mm"]
        self.sz = abs(float(z_mm[1] - z_mm[0])) if len(z_mm) > 1 else 1.0
        self._dose_vmax = self._compute_dose_vmax()
        self.roi_contours = {}
        if self.rtstruct_meta:
            for roi in self.rtstruct_meta["roi_list"]:
                if roi["name"] in self.roi_names:
                    self.roi_contours[roi["name"]] = roi["contours"]
        self._syncing = False

        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("rtgamma Fast 3D Viewer PoC")
        self.plane_states: dict[str, PlaneState] = {}
        self._viewport_click_filters = []
        self._build_ui()
        self._update_all_images()
        self._sync_crosshair_labels_sliders()

    def show(self):
        self.window.resize(1400, 900)
        self.window.show()

    def _build_ui(self):
        QtCore, QtWidgets, pg = self.QtCore, self.QtWidgets, self.pg
        pg.setConfigOptions(imageAxisOrder="row-major")
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        grid = QtWidgets.QGridLayout()
        root.addLayout(grid, stretch=1)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Overlay alpha"))
        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(50)
        self.alpha_slider.valueChanged.connect(self._on_alpha_changed)
        controls.addWidget(self.alpha_slider, stretch=1)

        self.status_label = QtWidgets.QLabel(self.gamma_warning)
        controls.addWidget(self.status_label, stretch=2)
        root.addLayout(controls)

        grid.addWidget(self._make_plane_widget("axial", "Axial"), 0, 0)
        grid.addWidget(self._make_plane_widget("sagittal", "Sagittal"), 0, 1)
        grid.addWidget(self._make_plane_widget("coronal", "Coronal"), 1, 0)
        grid.addWidget(self._make_sidebar(), 1, 1)
        self.window.setCentralWidget(central)

    def _make_sidebar(self):
        QtWidgets = self.QtWidgets
        side = QtWidgets.QWidget()
        side.setStyleSheet(
            """
            QWidget {
                background: #222222; color: #DDDDDD;
                font-family: Consolas, monospace; font-size: 10px;
            }
            QCheckBox, QRadioButton { spacing: 5px; padding: 1px; }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 10px; height: 10px; border: 1px solid #AAAAAA; background: #111111;
            }
            QCheckBox::indicator:checked {
                background: #2ECC71; border: 1px solid #2ECC71;
            }
            QRadioButton::indicator { border-radius: 6px; }
            QRadioButton::indicator:checked {
                background: #2D7DFF; border: 1px solid #BFD6FF;
            }
            QGroupBox {
                border: 1px solid #555555; margin-top: 6px; padding-top: 6px;
                font-family: Consolas, monospace; font-size: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            """
        )
        layout = QtWidgets.QVBoxLayout(side)
        layout.setContentsMargins(12, 12, 12, 12)

        note = QtWidgets.QLabel("Fast Viewer: click=cursor, wheel=slice, sliders=slice.")
        note.setStyleSheet("color: #DDEEFF; font-family: Consolas, monospace; font-size: 10px;")
        layout.addWidget(note)

        files = QtWidgets.QLabel(f"Ref : {self.ref_label}\nEval: {self.eval_label}")
        files.setStyleSheet("font-family: Consolas, monospace; color: #AAAAAA; font-size: 10px;")
        files.setWordWrap(True)
        layout.addWidget(files)

        self.ct_check = QtWidgets.QCheckBox("CT")
        self.ct_check.setChecked(True)
        self.ct_check.toggled.connect(lambda checked: self._on_visibility_changed("CT", checked))
        layout.addWidget(self.ct_check)

        self.structure_check = QtWidgets.QCheckBox("Structure")
        self.structure_check.setChecked(bool(self.roi_names))
        self.structure_check.setEnabled(bool(self.roi_names))
        self.structure_check.toggled.connect(lambda checked: self._on_visibility_changed("Structure", checked))
        layout.addWidget(self.structure_check)

        self.roi_checks = {}
        for name in self.roi_names:
            check = QtWidgets.QCheckBox(name)
            check.setChecked(True)
            check.toggled.connect(lambda checked, roi=name: self._on_roi_visibility_changed(roi, checked))
            self.roi_checks[name] = check
            layout.addWidget(check)

        mode_box = QtWidgets.QGroupBox("Overlay")
        mode_layout = QtWidgets.QVBoxLayout(mode_box)
        self.mode_group = QtWidgets.QButtonGroup(mode_box)
        for i, mode in enumerate(["Gamma", "Pass/Fail", "Ref Dose", "Eval Dose", "Dose Ratio"]):
            button = QtWidgets.QRadioButton(mode)
            button.setChecked(mode == self.overlay_mode)
            self.mode_group.addButton(button, i)
            mode_layout.addWidget(button)
        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        layout.addWidget(mode_box)

        stats = QtWidgets.QLabel(self._stats_text())
        stats.setStyleSheet("font-family: Consolas, monospace; color: #00FF00; font-size: 10px;")
        layout.addWidget(stats)
        layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setWidget(side)
        return scroll

    def _make_plane_widget(self, plane: str, title: str):
        QtWidgets, pg = self.QtWidgets, self.pg
        wrap = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(wrap)
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        graph = pg.GraphicsLayoutWidget()
        view = self._make_viewbox(plane)
        view.setAspectLocked(True)
        if plane == "axial":
            view.invertY(True)
        graph.ci.addItem(view, row=0, col=0)
        click_filter = self._make_viewport_click_filter(plane, view, graph)
        graph.viewport().installEventFilter(click_filter)
        self._viewport_click_filters.append(click_filter)
        graph.scene().sigMouseClicked.connect(
            lambda ev, p=plane, v=view: self._on_scene_clicked(p, v, ev)
        )

        ct_item = self._make_clickable_image_item(plane)
        gamma_item = self._make_clickable_image_item(plane)
        view.addItem(ct_item)
        view.addItem(gamma_item)

        structure_items = {}
        for i, name in enumerate(self.roi_names):
            color = self._roi_color(i)
            item = pg.PlotDataItem(pen=pg.mkPen(color, width=1.2))
            view.addItem(item)
            structure_items[name] = item

        hline = pg.InfiniteLine(angle=0, pen=pg.mkPen("y", width=1))
        vline = pg.InfiniteLine(angle=90, pen=pg.mkPen("y", width=1))
        view.addItem(hline)
        view.addItem(vline)
        label = pg.TextItem(color="w", anchor=(0, 1), fill=pg.mkBrush(0, 0, 0, 160))
        view.addItem(label)

        layout.addWidget(graph, stretch=1)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Slice"))
        slider = QtWidgets.QSlider(self.QtCore.Qt.Orientation.Horizontal)
        slider.setRange(0, self._max_index(plane))
        slider.setValue(self._plane_index(plane))
        slider.valueChanged.connect(lambda value, p=plane: self._on_slider_changed(p, value))
        slider_label = QtWidgets.QLabel("")
        row.addWidget(slider, stretch=1)
        row.addWidget(slider_label)
        layout.addLayout(row)

        self.plane_states[plane] = PlaneState(
            plane=plane,
            title=title_label,
            view=view,
            ct_item=ct_item,
            gamma_item=gamma_item,
            hline=hline,
            vline=vline,
            label=label,
            slider=slider,
            slider_label=slider_label,
            structure_items=structure_items,
        )
        return wrap

    def _make_viewport_click_filter(self, plane: str, view, graph):
        QtCore = self.QtCore

        class ViewportClickFilter(QtCore.QObject):
            def __init__(self, parent, plane_name, plane_view, graph_widget):
                super().__init__()
                self.parent = parent
                self.plane_name = plane_name
                self.plane_view = plane_view
                self.graph_widget = graph_widget

            def eventFilter(self, obj, event):
                if event.type() != QtCore.QEvent.Type.MouseButtonPress:
                    return False
                if event.button() != QtCore.Qt.MouseButton.LeftButton:
                    return False
                scene_pos = self.graph_widget.mapToScene(event.position().toPoint())
                if not self.plane_view.sceneBoundingRect().contains(scene_pos):
                    return False
                view_pos = self.plane_view.mapSceneToView(scene_pos)
                self.parent._on_plane_click(self.plane_name, view_pos.x(), view_pos.y())
                return True

        return ViewportClickFilter(self, plane, view, graph)

    def _make_clickable_image_item(self, plane: str):
        pg = self.pg

        class BoundImageItem(pg.ImageItem):
            def __init__(self, parent, plane_name):
                super().__init__()
                self.parent = parent
                self.plane_name = plane_name
                self.setAcceptedMouseButtons(parent.QtCore.Qt.MouseButton.LeftButton)

            def mouseClickEvent(self, ev):
                if ev.button() == self.parent.QtCore.Qt.MouseButton.LeftButton:
                    pos = ev.pos()
                    self.parent._on_plane_click(self.plane_name, pos.x(), pos.y())
                    ev.accept()
                    return
                ev.ignore()

            def mousePressEvent(self, ev):
                if ev.button() == self.parent.QtCore.Qt.MouseButton.LeftButton:
                    pos = ev.pos()
                    self.parent._on_plane_click(self.plane_name, pos.x(), pos.y())
                    ev.accept()
                    return
                super().mousePressEvent(ev)

        return BoundImageItem(self, plane)

    def _make_viewbox(self, plane: str):
        pg = self.pg

        class BoundViewBox(pg.ViewBox):
            def __init__(self, parent, plane_name):
                super().__init__(enableMenu=False)
                self.parent = parent
                self.plane_name = plane_name
                self.setMouseEnabled(x=False, y=False)

            def mouseClickEvent(self, ev):
                if ev.button() == self.parent.QtCore.Qt.MouseButton.LeftButton:
                    pos = self.mapSceneToView(ev.scenePos())
                    self.parent._on_plane_click(self.plane_name, pos.x(), pos.y())
                    ev.accept()
                    return
                ev.ignore()

            def mousePressEvent(self, ev):
                if ev.button() == self.parent.QtCore.Qt.MouseButton.LeftButton:
                    pos = self.mapSceneToView(ev.scenePos())
                    self.parent._on_plane_click(self.plane_name, pos.x(), pos.y())
                    ev.accept()
                    return
                super().mousePressEvent(ev)

            def wheelEvent(self, ev, axis=None):
                delta = ev.delta() if hasattr(ev, "delta") else ev.angleDelta().y()
                self.parent._on_plane_wheel(self.plane_name, self.parent._wheel_step(self.plane_name, delta))
                ev.accept()

        return BoundViewBox(self, plane)

    def _wheel_step(self, plane: str, delta: int) -> int:
        step = 1 if delta > 0 else -1
        if plane in {"sagittal", "coronal"}:
            return -step
        return step

    def _on_scene_clicked(self, plane: str, view, ev):
        if ev.button() != self.QtCore.Qt.MouseButton.LeftButton:
            return
        scene_pos = ev.scenePos()
        if not view.sceneBoundingRect().contains(scene_pos):
            return
        view_pos = view.mapSceneToView(scene_pos)
        self._on_plane_click(plane, view_pos.x(), view_pos.y())
        ev.accept()

    def _max_index(self, plane: str) -> int:
        if plane == "axial":
            return self.nz - 1
        if plane == "sagittal":
            return self.nx - 1
        return self.ny - 1

    def _plane_index(self, plane: str) -> int:
        if plane == "axial":
            return int(self.cur_z)
        if plane == "sagittal":
            return int(self.cur_x)
        return int(self.cur_y)

    def _set_plane_index(self, plane: str, idx: int):
        idx = int(np.clip(idx, 0, self._max_index(plane)))
        if plane == "axial":
            self.cur_z = idx
        elif plane == "sagittal":
            self.cur_x = idx
        else:
            self.cur_y = idx

    def _slice_for_plane(self, volume: np.ndarray | None, plane: str) -> np.ndarray | None:
        if volume is None:
            return None
        if plane == "axial":
            return volume[self.cur_z, :, :]
        if plane == "sagittal":
            return volume[:, :, self.cur_x]
        return volume[:, self.cur_y, :]

    def _plane_size(self, plane: str) -> tuple[int, int]:
        if plane == "axial":
            return self.nx, self.ny
        if plane == "sagittal":
            return self.ny, self.nz
        return self.nx, self.nz

    def _cursor_xy_for_plane(self, plane: str) -> tuple[int, int]:
        if plane == "axial":
            return int(self.cur_x), int(self.cur_y)
        if plane == "sagittal":
            return int(self.cur_y), int(self.cur_z)
        return int(self.cur_x), int(self.cur_z)

    def _ct_levels(self) -> tuple[float, float]:
        finite = self.ct[np.isfinite(self.ct)]
        if finite.size == 0:
            return -200.0, 300.0
        lo = float(np.nanpercentile(finite, 1))
        hi = float(np.nanpercentile(finite, 99))
        if hi <= lo:
            return -200.0, 300.0
        return max(lo, -1000.0), min(hi, 1500.0)

    def _compute_dose_vmax(self) -> float:
        vmax = 1.0
        for dose in (self.ref_dose, self.eval_dose):
            if dose is None:
                continue
            finite = dose[np.isfinite(dose)]
            if finite.size:
                vmax = max(vmax, float(np.nanmax(finite)))
        return vmax

    def _stats_text(self) -> str:
        text = ""
        if self.gpr_cond:
            text += f"Criteria: {self.gpr_cond['dta']:.1f}mm / {self.gpr_cond['dd']:.1f}%\n"
            text += f"Cutoff  : {self.gpr_cond['cutoff']:.1f}%\n"
        text += "--------------------\n"
        text += "ROI GPR[%]\n"
        for stat in self.per_structure_stats:
            val = stat["pass_rate_percent"]
            val_text = f"{val:5.1f}%" if np.isfinite(val) else "  N/A"
            text += f"{stat['roi_name'][:12]:12}: {val_text}\n"
        return text

    def _roi_color(self, index: int) -> tuple[int, int, int]:
        colors = [
            (255, 68, 68),
            (68, 136, 255),
            (68, 221, 68),
            (255, 170, 0),
            (255, 68, 255),
            (68, 255, 255),
            (255, 255, 68),
            (170, 68, 255),
        ]
        return colors[index % len(colors)]

    def _slice_gpr_text(self, gamma2d: np.ndarray | None) -> str:
        if gamma2d is None:
            return ""
        valid = np.isfinite(gamma2d)
        if not np.any(valid):
            return ""
        ok = np.sum(gamma2d[valid] <= 1.0)
        return f"Slice GPR: {ok / np.sum(valid) * 100.0:.1f}% ({ok}/{np.sum(valid)})"

    def _scalar_rgba(
        self,
        data: np.ndarray | None,
        clim: tuple[float, float],
        valid: np.ndarray | None = None,
        palette: str = "heat",
    ) -> np.ndarray | None:
        if data is None or not self.overlay_visible:
            return None
        lo, hi = clim
        if hi <= lo:
            hi = lo + 1.0
        if valid is None:
            valid = np.isfinite(data)
        t = np.clip((data.astype(np.float32) - lo) / (hi - lo), 0.0, 1.0)
        t = np.nan_to_num(t, nan=0.0, posinf=1.0, neginf=0.0)
        rgba = np.zeros(data.shape + (4,), dtype=np.uint8)
        if palette == "blue_red":
            rgba[..., 0] = (255 * t).astype(np.uint8)
            rgba[..., 1] = (255 * (1.0 - np.abs(t - 0.5) * 2.0)).astype(np.uint8)
            rgba[..., 2] = (255 * (1.0 - t)).astype(np.uint8)
        else:
            rgba[..., 0] = (255 * np.clip((t - 0.25) * 2.0, 0.0, 1.0)).astype(np.uint8)
            rgba[..., 1] = (255 * np.clip(1.0 - np.abs(t - 0.5) * 2.0, 0.0, 1.0)).astype(np.uint8)
            rgba[..., 2] = (255 * np.clip((0.5 - t) * 2.0, 0.0, 1.0)).astype(np.uint8)
        rgba[..., 3] = np.where(valid, self.overlay_alpha, 0).astype(np.uint8)
        return rgba

    def _pass_fail_rgba(self, gamma2d: np.ndarray | None) -> np.ndarray | None:
        if gamma2d is None or not self.overlay_visible:
            return None
        valid = np.isfinite(gamma2d)
        rgba = np.zeros(gamma2d.shape + (4,), dtype=np.uint8)
        passed = valid & (gamma2d <= 1.0)
        failed = valid & (gamma2d > 1.0)
        rgba[passed, :3] = (0, 204, 0)
        rgba[failed, :3] = (255, 34, 34)
        rgba[..., 3] = np.where(valid, self.overlay_alpha, 0).astype(np.uint8)
        return rgba

    def _overlay_rgba(self, plane: str) -> np.ndarray | None:
        gamma2d = self._slice_for_plane(self.gamma, plane)
        if self.overlay_mode == "Gamma":
            valid = None if gamma2d is None else np.isfinite(gamma2d)
            return self._scalar_rgba(gamma2d, (0.0, 2.0), valid)
        if self.overlay_mode == "Pass/Fail":
            return self._pass_fail_rgba(gamma2d)
        if self.overlay_mode == "Ref Dose":
            ref2d = self._slice_for_plane(self.ref_dose, plane)
            valid = None if ref2d is None else ref2d >= self._dose_vmax * 0.1
            return self._scalar_rgba(ref2d, (0.0, self._dose_vmax), valid)
        if self.overlay_mode == "Eval Dose":
            eval2d = self._slice_for_plane(self.eval_dose, plane)
            valid = None if eval2d is None else eval2d >= self._dose_vmax * 0.1
            return self._scalar_rgba(eval2d, (0.0, self._dose_vmax), valid)
        if self.overlay_mode == "Dose Ratio":
            ref2d = self._slice_for_plane(self.ref_dose, plane)
            eval2d = self._slice_for_plane(self.eval_dose, plane)
            if ref2d is None or eval2d is None:
                return None
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(ref2d > 0, eval2d / ref2d, np.nan)
            valid = np.isfinite(ratio) & (ref2d >= self._dose_vmax * 0.1)
            return self._scalar_rgba(ratio, (0.5, 1.5), valid, palette="blue_red")
        return None

    def _update_plane_image(self, plane: str):
        QtCore = self.QtCore
        state = self.plane_states[plane]
        ct2d = self._slice_for_plane(self.ct, plane)
        width, height = self._plane_size(plane)
        state.ct_item.setImage(ct2d, autoLevels=False, levels=self.ct_levels)
        state.ct_item.setRect(QtCore.QRectF(0, 0, width, height))
        state.ct_item.setVisible(self.visible["CT"])

        rgba = self._overlay_rgba(plane)
        if rgba is None:
            state.gamma_item.clear()
        else:
            state.gamma_item.setImage(rgba, autoLevels=False)
            state.gamma_item.setRect(QtCore.QRectF(0, 0, width, height))
        self._update_structure_items(plane)
        state.title.setText(f"{plane.capitalize()} (idx {self._plane_index(plane)}) {self._slice_gpr_text(self._slice_for_plane(self.gamma, plane))}")
        state.view.setRange(QtCore.QRectF(0, 0, width, height), padding=0.02)

    def _update_all_images(self):
        for plane in ("axial", "sagittal", "coronal"):
            self._update_plane_image(plane)

    def _format_cursor_text(self) -> str:
        z, y, x = int(self.cur_z), int(self.cur_y), int(self.cur_x)
        hu = _strict_voxel_value(self.ct, self.ct, z, y, x)
        ref = _strict_voxel_value(self.ref_dose, self.ct, z, y, x)
        eval_value = _strict_voxel_value(self.eval_dose, self.ct, z, y, x)
        hu_text = f"{int(round(hu))}" if hu is not None else "N/A"
        ref_text = f"{ref:.3f} {self.ref_unit}" if ref is not None else "N/A"
        eval_text = f"{eval_value:.3f} {self.eval_unit}" if eval_value is not None else "N/A"
        return f"HU: {hu_text}\nRef: {ref_text}\nEval: {eval_text}"

    def _sync_crosshair_labels_sliders(self):
        text = self._format_cursor_text()
        for plane, state in self.plane_states.items():
            x, y = self._cursor_xy_for_plane(plane)
            state.hline.setPos(y)
            state.vline.setPos(x)
            state.label.setText(text)
            state.label.setPos(x, y)
            self._syncing = True
            try:
                state.slider.setValue(self._plane_index(plane))
                state.slider_label.setText(str(self._plane_index(plane)))
            finally:
                self._syncing = False

    def _on_slider_changed(self, plane: str, value: int):
        if self._syncing:
            return
        self._set_plane_index(plane, value)
        self._update_plane_image(plane)
        self._sync_crosshair_labels_sliders()

    def _on_plane_wheel(self, plane: str, step: int):
        old_idx = self._plane_index(plane)
        self._set_plane_index(plane, old_idx + step)
        if self._plane_index(plane) != old_idx:
            self._update_plane_image(plane)
        self._sync_crosshair_labels_sliders()

    def _on_plane_click(self, plane: str, view_x: float, view_y: float):
        old = {"axial": self.cur_z, "sagittal": self.cur_x, "coronal": self.cur_y}
        ix = int(round(view_x))
        iy = int(round(view_y))
        if plane == "axial":
            self.cur_x = int(np.clip(ix, 0, self.nx - 1))
            self.cur_y = int(np.clip(iy, 0, self.ny - 1))
        elif plane == "sagittal":
            self.cur_y = int(np.clip(ix, 0, self.ny - 1))
            self.cur_z = int(np.clip(iy, 0, self.nz - 1))
        else:
            self.cur_x = int(np.clip(ix, 0, self.nx - 1))
            self.cur_z = int(np.clip(iy, 0, self.nz - 1))

        if old["axial"] != self.cur_z:
            self._update_plane_image("axial")
        if old["sagittal"] != self.cur_x:
            self._update_plane_image("sagittal")
        if old["coronal"] != self.cur_y:
            self._update_plane_image("coronal")
        self._sync_crosshair_labels_sliders()

    def _on_alpha_changed(self, value: int):
        self.overlay_alpha = int(np.clip(round(value / 100 * 255), 0, 255))
        for plane in ("axial", "sagittal", "coronal"):
            rgba = self._overlay_rgba(plane)
            if rgba is not None:
                self.plane_states[plane].gamma_item.setImage(rgba, autoLevels=False)
            else:
                self.plane_states[plane].gamma_item.clear()

    def _on_visibility_changed(self, label: str, checked: bool):
        self.visible[label] = bool(checked)
        self._update_all_images()

    def _on_roi_visibility_changed(self, roi: str, checked: bool):
        self.roi_visible[roi] = bool(checked)
        self._update_all_images()

    def _on_mode_changed(self, button):
        self.overlay_mode = button.text()
        self.overlay_visible = self.gamma is not None or self.overlay_mode in {"Ref Dose", "Eval Dose", "Dose Ratio"}
        self._update_all_images()

    def _structure_segments(self, plane: str, idx: int, name: str) -> list[list[tuple[float, float]]]:
        ipp = self.dose_meta["ipp"]
        s_col, s_row = self.dose_meta["s_col"], self.dose_meta["s_row"]
        v_col = self.dose_meta["v_col"]
        v_row = self.dose_meta["v_row"]
        v_slice = self.dose_meta["v_slice"]
        segments = []
        if plane == "axial":
            from rtgamma.mask import _world_xy_to_grid_rc

            z_w = ipp[2] + self.dose_meta["z_coords_mm"][idx] * v_slice[2]
            for contour in self.roi_contours.get(name, []):
                if abs(contour["z"] - z_w) < self.sz * 0.51:
                    rc = _world_xy_to_grid_rc(contour["points"], self.dose_meta)
                    pts = rc[:, [1, 0]]
                    for i in range(len(pts)):
                        segments.append([tuple(pts[i]), tuple(pts[(i + 1) % len(pts)])])
        elif plane == "sagittal":
            x_w = ipp[0] + self.dose_meta["x_coords_mm"][idx] * v_col[0]
            for contour in self.roi_contours.get(name, []):
                pts = contour["points"]
                z_grid = (contour["z"] - ipp[2]) / (self.sz * v_slice[2])
                inters = []
                for k in range(len(pts)):
                    p1, p2 = pts[k], pts[(k + 1) % len(pts)]
                    if (p1[0] - x_w) * (p2[0] - x_w) <= 0 and p1[0] != p2[0]:
                        inters.append((p1[1] + (x_w - p1[0]) / (p2[0] - p1[0]) * (p2[1] - p1[1]) - ipp[1]) / (s_row * v_row[1]))
                if len(inters) >= 2:
                    inters.sort()
                    for i in range(0, (len(inters) // 2) * 2, 2):
                        segments.append([(inters[i], z_grid), (inters[i + 1], z_grid)])
        elif plane == "coronal":
            y_w = ipp[1] + self.dose_meta["y_coords_mm"][idx] * v_row[1]
            for contour in self.roi_contours.get(name, []):
                pts = contour["points"]
                z_grid = (contour["z"] - ipp[2]) / (self.sz * v_slice[2])
                inters = []
                for k in range(len(pts)):
                    p1, p2 = pts[k], pts[(k + 1) % len(pts)]
                    if (p1[1] - y_w) * (p2[1] - y_w) <= 0 and p1[1] != p2[1]:
                        inters.append((p1[0] + (y_w - p1[1]) / (p2[1] - p1[1]) * (p2[0] - p1[0]) - ipp[0]) / (s_col * v_col[0]))
                if len(inters) >= 2:
                    inters.sort()
                    for i in range(0, (len(inters) // 2) * 2, 2):
                        segments.append([(inters[i], z_grid), (inters[i + 1], z_grid)])
        return segments

    def _segments_to_plot_data(self, segments: list[list[tuple[float, float]]]) -> tuple[np.ndarray, np.ndarray]:
        if not segments:
            return np.array([]), np.array([])
        xs = []
        ys = []
        for segment in segments:
            xs.extend([segment[0][0], segment[1][0], np.nan])
            ys.extend([segment[0][1], segment[1][1], np.nan])
        return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)

    def _update_structure_items(self, plane: str):
        state = self.plane_states[plane]
        idx = self._plane_index(plane)
        show_structure = self.visible["Structure"] and bool(self.rtstruct_meta)
        for name, item in state.structure_items.items():
            if not show_structure or not self.roi_visible.get(name, True):
                item.setData([], [])
                continue
            x, y = self._segments_to_plot_data(self._structure_segments(plane, idx, name))
            item.setData(x, y)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="PyQtGraph fast 3D viewer PoC")
    parser.add_argument("--ct", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--eval")
    parser.add_argument("--gamma-npz")
    parser.add_argument("--rtstruct")
    parser.add_argument("--roi")
    parser.add_argument("--dd", type=float, default=3.0)
    parser.add_argument("--dta", type=float, default=2.0)
    parser.add_argument("--cutoff", type=float, default=10.0)
    parser.add_argument("--gamma-type", choices=["global", "local"], default="global")
    parser.add_argument("--norm", choices=["global_max", "max_ref", "none"], default="global_max")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = _parse_args(argv)
    QtCore, QtWidgets, pg = _import_qtgraph()
    if QtCore is None:
        return 1

    logger.info("Loading CT: %s", args.ct)
    ct_meta = load_ct(args.ct)
    logger.info("Loading reference dose: %s", args.ref)
    dose_meta = load_rtdose(args.ref)
    ct_on_dose = resample_ct_onto_dose(ct_meta, dose_meta)
    eval_on_ref, eval_unit = _resample_eval(args.eval, dose_meta)
    gamma = _compute_gamma_if_needed(args, dose_meta, eval_on_ref)
    rtstruct_meta = load_rtstruct(args.rtstruct) if args.rtstruct else None
    if args.roi:
        roi_names = [name.strip() for name in args.roi.split(",") if name.strip()]
    elif rtstruct_meta:
        roi_names = [roi["name"] for roi in rtstruct_meta["roi_list"]]
    else:
        roi_names = []

    per_structure = []
    gamma_shape_matches_ref = gamma is not None and gamma.shape == dose_meta["dose"].shape
    roi_masks = build_roi_masks(rtstruct_meta, dose_meta, roi_names=roi_names) if rtstruct_meta and gamma_shape_matches_ref else {}
    for name, mask in roi_masks.items():
        masked_gamma = gamma[mask]
        finite = np.isfinite(masked_gamma)
        if finite.any():
            pass_rate = float(np.sum(masked_gamma[finite] <= 1.0) / np.sum(finite) * 100.0)
        else:
            pass_rate = float("nan")
        per_structure.append({"roi_name": name, "pass_rate_percent": pass_rate})

    logger.info("Shape CT(on dose): %s", ct_on_dose.shape)
    logger.info("Shape Ref dose:   %s", dose_meta["dose"].shape)
    logger.info("Shape Eval dose:  %s", None if eval_on_ref is None else eval_on_ref.shape)
    logger.info("Shape Gamma:      %s", None if gamma is None else gamma.shape)
    if gamma is not None and gamma.shape != dose_meta["dose"].shape:
        logger.warning("Gamma shape mismatch. Overlay will be disabled.")
    if gamma is None:
        logger.warning("Gamma overlay is unavailable.")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    viewer = FastPlaneViewer(
        ct=ct_on_dose,
        ref_dose=dose_meta["dose"],
        eval_dose=eval_on_ref,
        gamma=gamma,
        dose_meta=dose_meta,
        rtstruct_meta=rtstruct_meta,
        roi_names=roi_names,
        per_structure_stats=per_structure,
        gpr_cond={"dd": args.dd, "dta": args.dta, "cutoff": args.cutoff},
        ref_label=os.path.basename(args.ref),
        eval_label=os.path.basename(args.eval) if args.eval else "",
        ref_unit=dose_meta.get("units", ""),
        eval_unit=eval_unit,
        QtCore=QtCore,
        QtWidgets=QtWidgets,
        pg=pg,
    )
    viewer.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
