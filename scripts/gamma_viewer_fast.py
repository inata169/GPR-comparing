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

from rtgamma.gamma import compute_gamma, gamma_engine_version
from rtgamma.io_dicom import (
    load_ct,
    load_rtdose,
    load_rtstruct,
    validate_rtdose_pair_geometry,
    world_to_index,
)
from rtgamma.main import build_ref_world_coords
from rtgamma.mask import build_roi_masks
from rtgamma.resample import resample_ct_onto_dose, resample_eval_onto_ref
from rtgamma.viewer_cache import load_validated_gamma_cache

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


def _pass_fail_text(gamma_value: float | None) -> str:
    if gamma_value is None:
        return "N/A"
    return "Pass" if gamma_value <= 1.0 else "Fail"


def _gamma_value_text(
    gamma_value: float | None,
    gamma_loaded: bool,
    ref_value: float | None,
    cutoff_threshold: float | None,
) -> str:
    if gamma_value is not None:
        return f"{gamma_value:.3f}"
    if not gamma_loaded:
        return "N/A"
    if ref_value is not None and cutoff_threshold is not None and ref_value < cutoff_threshold:
        return "Excluded"
    return "N/A"


def _gamma_coverage_text(gamma: np.ndarray | None) -> str:
    if gamma is None:
        return "Gamma evaluated: N/A"
    valid = np.isfinite(gamma)
    valid_count = int(np.sum(valid))
    total_count = int(gamma.size)
    if total_count == 0:
        return "Gamma evaluated: 0/0 valid"
    pct = valid_count / total_count * 100.0
    return f"Gamma evaluated: {valid_count}/{total_count} ({pct:.3f}%)"


def _overall_gpr_text(gamma: np.ndarray | None) -> str:
    if gamma is None:
        return "Overall GPR: N/A"
    valid = np.isfinite(gamma)
    evaluated = int(np.sum(valid))
    if evaluated == 0:
        return "Overall GPR: N/A (0 evaluated)"
    passed = int(np.sum(gamma[valid] <= 1.0))
    return f"Overall GPR: {passed / evaluated * 100.0:.2f}% ({passed}/{evaluated})"


def _dose_diff_value(eval_value: float | None, ref_value: float | None) -> float | None:
    if eval_value is None or ref_value is None:
        return None
    return eval_value - ref_value


def _auto_dose_display_range(volume: np.ndarray | None) -> tuple[float, float]:
    if volume is None:
        return 0.0, 1.0
    positive = volume[np.isfinite(volume) & (volume > 0)]
    if positive.size == 0:
        return 0.0, 1.0
    hi = float(np.percentile(positive, 99.5))
    if not np.isfinite(hi) or hi <= 0.0:
        hi = float(np.nanmax(positive))
    if not np.isfinite(hi) or hi <= 0.0:
        hi = 1.0
    return 0.0, hi


def _validated_dose_display_range(
    min_value: float,
    max_value: float,
    previous: tuple[float, float],
) -> tuple[tuple[float, float], bool, str]:
    if not np.isfinite(min_value) or not np.isfinite(max_value):
        return previous, False, "min and max must be finite numbers"
    if max_value <= min_value:
        return previous, False, "max must be greater than min"
    return (float(min_value), float(max_value)), True, ""


def _coord_edges(coords: np.ndarray) -> tuple[float, float]:
    coords = np.asarray(coords, dtype=float)
    if coords.size == 0:
        return 0.0, 1.0
    if coords.size == 1:
        step = 1.0
    else:
        step = float(np.nanmedian(np.diff(coords)))
        if not np.isfinite(step) or step == 0.0:
            step = 1.0
    return float(coords[0] - step / 2.0), float(coords[-1] + step / 2.0)


def _nearest_index(coords: np.ndarray, value: float) -> int:
    coords = np.asarray(coords, dtype=float)
    if coords.size == 0:
        return 0
    idx = int(np.nanargmin(np.abs(coords - float(value))))
    return int(np.clip(idx, 0, coords.size - 1))


def _index_to_coord(coords: np.ndarray, index_value: float) -> float:
    coords = np.asarray(coords, dtype=float)
    if coords.size == 0:
        return float(index_value)
    return float(np.interp(float(index_value), np.arange(coords.size, dtype=float), coords))


def display_point_for_cursor(
    plane: str,
    cursor: tuple[int, int, int],
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_coords: np.ndarray,
) -> tuple[float, float]:
    z, y, x = cursor
    if plane == "axial":
        return float(x_coords[x]), float(y_coords[y])
    if plane == "sagittal":
        return float(y_coords[y]), float(z_coords[z_coords.size - 1 - z])
    if plane == "coronal":
        return float(x_coords[x]), float(z_coords[z_coords.size - 1 - z])
    raise ValueError(f"Unknown plane: {plane}")


def cursor_from_display_point(
    plane: str,
    display_x: float,
    display_y: float,
    cursor: tuple[int, int, int],
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_coords: np.ndarray,
) -> tuple[int, int, int]:
    z, y, x = cursor
    if plane == "axial":
        x = _nearest_index(x_coords, display_x)
        y = _nearest_index(y_coords, display_y)
    elif plane == "sagittal":
        y = _nearest_index(y_coords, display_x)
        z = z_coords.size - 1 - _nearest_index(z_coords, display_y)
    elif plane == "coronal":
        x = _nearest_index(x_coords, display_x)
        z = z_coords.size - 1 - _nearest_index(z_coords, display_y)
    else:
        raise ValueError(f"Unknown plane: {plane}")
    return int(z), int(y), int(x)


def plane_display_extent(
    plane: str,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_coords: np.ndarray,
) -> tuple[float, float, float, float]:
    if plane == "axial":
        x0, x1 = _coord_edges(x_coords)
        y0, y1 = _coord_edges(y_coords)
    elif plane == "sagittal":
        x0, x1 = _coord_edges(y_coords)
        y0, y1 = _coord_edges(z_coords)
    elif plane == "coronal":
        x0, x1 = _coord_edges(x_coords)
        y0, y1 = _coord_edges(z_coords)
    else:
        raise ValueError(f"Unknown plane: {plane}")
    return x0, x1, y0, y1


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


def _resample_eval(
    eval_path: str | None,
    dose_meta: dict,
) -> tuple[np.ndarray | None, str, dict | None]:
    if not eval_path:
        return None, "", None
    eval_meta = load_rtdose(eval_path)
    validate_rtdose_pair_geometry(dose_meta, eval_meta)
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
    return eval_on_ref, eval_meta.get("units", ""), eval_meta


def _compute_gamma_if_needed(
    args,
    dose_meta: dict,
    eval_on_ref: np.ndarray | None,
    eval_meta: dict | None = None,
) -> np.ndarray | None:
    if args.gamma_npz and getattr(args, "gamma_report", None):
        gamma = load_validated_gamma_cache(
            args.gamma_npz,
            args.gamma_report,
            expected_settings={
                "gamma_engine": args.engine,
                "gamma_engine_version": gamma_engine_version(args.engine),
                "dd_percent": args.dd,
                "dta_mm": args.dta,
                "cutoff_percent": args.cutoff,
                "gamma_type": args.gamma_type,
                "norm": args.norm,
                "interp_fraction": args.interp_fraction,
                "opt_shift": getattr(args, "opt_shift", "off") == "on",
                "shift_range": getattr(
                    args, "shift_range", "x:-3:3:1,y:-3:3:1,z:-3:3:1"
                ),
                "refine": getattr(args, "refine", "coarse2fine"),
                "fine_range_mm": getattr(args, "fine_range_mm", 10.0),
                "fine_step_mm": getattr(args, "fine_step_mm", 1.0),
                "early_stop_epsilon": getattr(args, "early_stop_epsilon", 0.05),
                "early_stop_patience": getattr(args, "early_stop_patience", 100),
                "prescan_2d": getattr(args, "prescan_2d", "on") == "on",
            },
            ref_source_sha256=dose_meta["source_sha256"],
            eval_source_sha256=eval_meta["source_sha256"] if eval_meta else "",
            logger=logger,
        )
    else:
        gamma = _load_gamma_npz(args.gamma_npz)
    if gamma is not None and gamma.shape != dose_meta["dose"].shape:
        logger.warning(
            "Ignoring Gamma cache with shape %s; reference shape is %s",
            gamma.shape,
            dose_meta["dose"].shape,
        )
        gamma = None
    if gamma is not None:
        return gamma
    if getattr(args, "opt_shift", "off") == "on":
        raise ValueError(
            "No compatible shift-optimized Gamma cache is available. "
            "Run 3D Gamma with Optimize Shift enabled before opening the Viewer."
        )
    if getattr(args, "skip_gamma_compute", False):
        logger.info(
            "No compatible Gamma cache. Skipping synchronous Gamma calculation "
            "so the Viewer can open immediately."
        )
        return None
    if eval_on_ref is not None:
        logger.info("No compatible Gamma cache. Computing Gamma map for display.")
        axes = (dose_meta["z_coords_mm"], dose_meta["y_coords_mm"], dose_meta["x_coords_mm"])
        gamma_map, _, _ = compute_gamma(
            axes_ref_mm=axes,
            dose_ref=dose_meta["dose"],
            axes_eval_mm=axes,
            dose_eval=eval_on_ref,
            dd_percent=args.dd,
            dta_mm=args.dta,
            cutoff_percent=args.cutoff,
            gamma_type=args.gamma_type,
            norm=args.norm,
            engine=args.engine,
            interp_fraction=args.interp_fraction,
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
    orientation_items: list[object]


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
            self.gamma_warning = (
                "Gamma / Pass-Fail: unavailable (run 3D Gamma to create "
                "gamma3d.npz); dose overlays remain available"
            )
        elif gamma.shape != ref_dose.shape:
            self.gamma_warning = f"Gamma overlay disabled: shape {gamma.shape} != ref {ref_dose.shape}"

        self.ref_unit = _format_dose_unit(ref_unit)
        self.eval_unit = _format_dose_unit(eval_unit)
        self.QtCore = QtCore
        self.QtWidgets = QtWidgets
        self.pg = pg

        self.nz, self.ny, self.nx = self.ct.shape
        self.x_coords_mm = np.asarray(dose_meta["x_coords_mm"], dtype=float)
        self.y_coords_mm = np.asarray(dose_meta["y_coords_mm"], dtype=float)
        self.z_coords_mm = np.asarray(dose_meta["z_coords_mm"], dtype=float)
        self.cur_z = self.nz // 2
        self.cur_y = self.ny // 2
        self.cur_x = self.nx // 2
        self.overlay_alpha = 128
        self.overlay_mode = (
            "Gamma"
            if self.gamma is not None
            else ("Dose Ratio" if self.eval_dose is not None else "Ref Dose")
        )
        self.overlay_visible = True
        self.visible = {"CT": True, "Structure": True, "Info": True}
        self.roi_visible = {name: True for name in self.roi_names}
        self.ct_levels = self._ct_levels()
        z_mm = dose_meta["z_coords_mm"]
        self.sz = abs(float(z_mm[1] - z_mm[0])) if len(z_mm) > 1 else 1.0
        self._dose_vmax = self._compute_dose_vmax()
        self._dose_display_auto_range = {
            "ref": _auto_dose_display_range(self.ref_dose),
            "eval": _auto_dose_display_range(self.eval_dose),
        }
        self._dose_display_manual_range: dict[str, tuple[float, float] | None] = {"ref": None, "eval": None}
        self._dose_display_auto_enabled = {"ref": True, "eval": True}
        self._dose_range_control_key = "ref"
        self._overlay_rgba_cache: dict[tuple, np.ndarray | None] = {}
        self._syncing_dose_range_controls = False
        self._gamma_cutoff_threshold = self._compute_gamma_cutoff_threshold()
        self._log_dose_volume_debug("Ref", "ref", self.ref_dose)
        self._log_dose_volume_debug("Eval", "eval", self.eval_dose)
        self.roi_contours = {}
        if self.rtstruct_meta:
            for roi in self.rtstruct_meta["roi_list"]:
                if roi["name"] in self.roi_names:
                    self.roi_contours[roi["name"]] = roi["contours"]
        self._syncing = False
        self.active_plane = "axial"
        self.user_zoomed = {"axial": False, "sagittal": False, "coronal": False}

        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("rtgamma Fast 3D Viewer PoC")
        self._key_event_filter = self._make_key_event_filter()
        self.window.installEventFilter(self._key_event_filter)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self._key_event_filter)
        self.plane_states: dict[str, PlaneState] = {}
        self._viewport_click_filters = []
        self._view_actions = {}
        self._overlay_actions = {}
        self._build_ui()
        self._update_all_images()
        self._sync_crosshair_labels_sliders()

    def show(self):
        self.window.resize(1400, 900)
        self.window.show()

    def _build_ui(self):
        QtCore, QtWidgets, pg = self.QtCore, self.QtWidgets, self.pg
        pg.setConfigOptions(imageAxisOrder="row-major")
        self._build_menus()
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
        self.alpha_value_label = QtWidgets.QLabel("50%")
        controls.addWidget(self.alpha_value_label)

        status_text = "Pass/Fail: gamma <= 1.0"
        if self.gamma_warning:
            status_text += f" | {self.gamma_warning}"
        self.status_label = QtWidgets.QLabel(status_text)
        controls.addWidget(self.status_label, stretch=2)
        root.addLayout(controls)

        grid.addWidget(self._make_plane_widget("axial", "Axial"), 0, 0)
        grid.addWidget(self._make_plane_widget("sagittal", "Sagittal"), 0, 1)
        grid.addWidget(self._make_plane_widget("coronal", "Coronal"), 1, 0)
        grid.addWidget(self._make_sidebar(), 1, 1)
        self.window.setCentralWidget(central)

    def _build_menus(self):
        QtWidgets = self.QtWidgets
        menu = self.window.menuBar()

        file_menu = menu.addMenu("&File")
        for label, value in [
            ("CT", "CT series loaded from command line"),
            ("Ref Dose", self.ref_label),
            ("Eval Dose", self.eval_label or "N/A"),
            ("Structure", "Loaded" if self.rtstruct_meta else "N/A"),
        ]:
            action = file_menu.addAction(label)
            action.triggered.connect(lambda checked=False, l=label, v=value: self._show_loaded_data(l, v))
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.window.close)

        view_menu = menu.addMenu("&View")
        self._view_actions["Info"] = view_menu.addAction("Show &Info")
        self._view_actions["Info"].setCheckable(True)
        self._view_actions["Info"].setChecked(True)
        self._view_actions["Info"].triggered.connect(lambda checked: self._on_visibility_changed("Info", checked))
        self._view_actions["CT"] = view_menu.addAction("Show &CT")
        self._view_actions["CT"].setCheckable(True)
        self._view_actions["CT"].setChecked(True)
        self._view_actions["CT"].triggered.connect(lambda checked: self.ct_check.setChecked(checked))
        self._view_actions["Structure"] = view_menu.addAction("Show &Structure")
        self._view_actions["Structure"].setCheckable(True)
        self._view_actions["Structure"].setChecked(bool(self.roi_names))
        self._view_actions["Structure"].triggered.connect(lambda checked: self.structure_check.setChecked(checked))
        overlay_menu = view_menu.addMenu("&Overlay")
        for mode in ["Gamma", "Pass/Fail", "Ref Dose", "Eval Dose", "Dose Diff", "Dose Ratio"]:
            action = overlay_menu.addAction(mode)
            action.setCheckable(True)
            action.setChecked(mode == self.overlay_mode)
            if mode in {"Gamma", "Pass/Fail"}:
                action.setEnabled(self.gamma is not None)
            elif mode in {"Eval Dose", "Dose Diff", "Dose Ratio"}:
                action.setEnabled(self.eval_dose is not None)
            action.triggered.connect(lambda checked=False, m=mode: self._set_overlay_mode(m))
            self._overlay_actions[mode] = action
        view_menu.addSeparator()
        view_menu.addAction("&Fit All Views", self._reset_all_views)

        help_menu = menu.addMenu("&Help")
        help_menu.addAction("&Controls", self._show_help)

    def _show_loaded_data(self, label: str, value: str):
        self.QtWidgets.QMessageBox.information(self.window, label, str(value))

    def _make_sidebar(self):
        QtWidgets = self.QtWidgets
        side = QtWidgets.QWidget()
        side.setStyleSheet(
            """
            QWidget {
                background: #222222; color: #DDDDDD;
                font-family: Consolas, monospace; font-size: 11px;
            }
            QCheckBox, QRadioButton { spacing: 5px; padding: 1px; }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 11px; height: 11px; border: 1px solid #AAAAAA; background: #111111;
            }
            QCheckBox::indicator:checked {
                background: #2ECC71; border: 1px solid #2ECC71;
            }
            QRadioButton::indicator { border-radius: 6px; }
            QRadioButton::indicator:checked {
                background: #2D7DFF; border: 1px solid #BFD6FF;
            }
            QGroupBox {
                border: 1px solid #555555; margin-top: 5px; padding-top: 7px;
                font-family: Consolas, monospace; font-size: 11px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QPushButton { min-height: 20px; padding: 2px 6px; }
            """
        )
        layout = QtWidgets.QVBoxLayout(side)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        note = QtWidgets.QLabel("Help: H/?   Info: I")
        note.setStyleSheet("color: #DDEEFF; font-family: Consolas, monospace; font-size: 11px;")
        layout.addWidget(note)

        data_box = QtWidgets.QGroupBox("Data")
        data_layout = QtWidgets.QGridLayout(data_box)
        data_layout.setContentsMargins(6, 10, 6, 6)
        data_layout.setHorizontalSpacing(8)
        data_layout.setVerticalSpacing(2)
        for row, (label, value) in enumerate(
            [
                ("CT", f"{self.ct.shape[0]} slices"),
                ("Ref", self.ref_label),
                ("Eval", self.eval_label or "N/A"),
                ("Struct", "yes" if self.rtstruct_meta else "no"),
            ]
        ):
            data_layout.addWidget(QtWidgets.QLabel(label), row, 0)
            text = QtWidgets.QLabel(value)
            text.setWordWrap(True)
            text.setStyleSheet("color: #AAAAAA;")
            data_layout.addWidget(text, row, 1)
        layout.addWidget(data_box)

        self.ct_check = QtWidgets.QCheckBox("CT")
        self.ct_check.setChecked(True)
        self.ct_check.toggled.connect(lambda checked: self._on_visibility_changed("CT", checked))
        self.info_check = QtWidgets.QCheckBox("Info")
        self.info_check.setChecked(True)
        self.info_check.toggled.connect(lambda checked: self._on_visibility_changed("Info", checked))
        self.structure_check = QtWidgets.QCheckBox("Structure")
        self.structure_check.setChecked(bool(self.roi_names))
        self.structure_check.setEnabled(bool(self.roi_names))
        self.structure_check.toggled.connect(lambda checked: self._on_visibility_changed("Structure", checked))

        display_box = QtWidgets.QGroupBox("Display")
        display_layout = QtWidgets.QGridLayout(display_box)
        display_layout.setContentsMargins(6, 10, 6, 6)
        display_layout.addWidget(self.ct_check, 0, 0)
        display_layout.addWidget(self.structure_check, 0, 1)
        display_layout.addWidget(self.info_check, 1, 0)
        layout.addWidget(display_box)

        roi_box = QtWidgets.QGroupBox("ROI visibility")
        roi_layout = QtWidgets.QVBoxLayout(roi_box)
        roi_layout.setContentsMargins(6, 10, 6, 6)
        roi_layout.setSpacing(2)
        self.roi_checks = {}
        for name in self.roi_names:
            check = QtWidgets.QCheckBox(f"Show ROI: {name}")
            check.setChecked(True)
            check.toggled.connect(lambda checked, roi=name: self._on_roi_visibility_changed(roi, checked))
            self.roi_checks[name] = check
            roi_layout.addWidget(check)
        if not self.roi_names:
            roi_layout.addWidget(QtWidgets.QLabel("No ROI loaded"))
        layout.addWidget(roi_box)

        mode_box = QtWidgets.QGroupBox("Overlay")
        mode_layout = QtWidgets.QGridLayout(mode_box)
        mode_layout.setContentsMargins(6, 10, 6, 6)
        mode_layout.setHorizontalSpacing(10)
        mode_layout.setVerticalSpacing(2)
        self.mode_group = QtWidgets.QButtonGroup(mode_box)
        for i, mode in enumerate(["Gamma", "Pass/Fail", "Ref Dose", "Eval Dose", "Dose Diff", "Dose Ratio"]):
            button = QtWidgets.QRadioButton(mode)
            button.setChecked(mode == self.overlay_mode)
            if mode in {"Gamma", "Pass/Fail"}:
                button.setEnabled(self.gamma is not None)
                if self.gamma is None:
                    button.setToolTip("Run 3D Gamma first to create gamma3d.npz and run3d.json.")
            elif mode in {"Eval Dose", "Dose Diff", "Dose Ratio"}:
                button.setEnabled(self.eval_dose is not None)
            self.mode_group.addButton(button, i)
            mode_layout.addWidget(button, i // 2, i % 2)
        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        layout.addWidget(mode_box)

        self.dose_range_box = QtWidgets.QGroupBox("Dose Range")
        dose_range_layout = QtWidgets.QGridLayout(self.dose_range_box)
        dose_range_layout.setContentsMargins(6, 10, 6, 6)
        dose_range_layout.setHorizontalSpacing(6)
        dose_range_layout.setVerticalSpacing(3)
        self.dose_auto_check = QtWidgets.QCheckBox("Auto dose range")
        self.dose_auto_check.toggled.connect(self._on_dose_auto_changed)
        class DoseRangeSpinBox(QtWidgets.QDoubleSpinBox):
            def focusInEvent(self, event):
                super().focusInEvent(event)
                self.lineEdit().selectAll()

            def mousePressEvent(self, event):
                was_focused = self.hasFocus()
                super().mousePressEvent(event)
                if not was_focused:
                    self.lineEdit().selectAll()

        self.dose_min_edit = DoseRangeSpinBox()
        self.dose_max_edit = DoseRangeSpinBox()
        for edit in (self.dose_min_edit, self.dose_max_edit):
            edit.setRange(0.0, 100.0)
            edit.setDecimals(4)
            edit.setSingleStep(0.1)
            edit.setKeyboardTracking(False)
            edit.setMinimumWidth(90)
        self.dose_min_edit.editingFinished.connect(self._on_dose_range_edited)
        self.dose_max_edit.editingFinished.connect(self._on_dose_range_edited)
        dose_range_layout.addWidget(self.dose_auto_check, 0, 0, 1, 2)
        dose_range_layout.addWidget(QtWidgets.QLabel("Dose display min [Gy]"), 1, 0)
        dose_range_layout.addWidget(self.dose_min_edit, 1, 1)
        dose_range_layout.addWidget(QtWidgets.QLabel("Dose display max [Gy]"), 2, 0)
        dose_range_layout.addWidget(self.dose_max_edit, 2, 1)
        layout.addWidget(self.dose_range_box)
        self._sync_dose_range_controls()

        zoom_box = QtWidgets.QGroupBox("Zoom")
        zoom_layout = QtWidgets.QHBoxLayout(zoom_box)
        zoom_layout.setContentsMargins(6, 10, 6, 6)
        btn_zoom_in = QtWidgets.QPushButton("Zoom +")
        btn_zoom_out = QtWidgets.QPushButton("Zoom -")
        btn_zoom_reset = QtWidgets.QPushButton("Fit")
        btn_zoom_in.clicked.connect(lambda: self._zoom_plane(self.active_plane, 0.8))
        btn_zoom_out.clicked.connect(lambda: self._zoom_plane(self.active_plane, 1.25))
        btn_zoom_reset.clicked.connect(self._reset_all_views)
        zoom_layout.addWidget(btn_zoom_in)
        zoom_layout.addWidget(btn_zoom_out)
        zoom_layout.addWidget(btn_zoom_reset)
        layout.addWidget(zoom_box)

        stats = QtWidgets.QLabel(self._stats_text())
        stats.setStyleSheet("font-family: Consolas, monospace; color: #00FF00; font-size: 11px;")
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
        graph.setFocusPolicy(self.QtCore.Qt.FocusPolicy.StrongFocus)
        graph.installEventFilter(self._key_event_filter)
        view = self._make_viewbox(plane)
        view.setAspectLocked(True)
        # Keep voxel/readout coordinates unchanged and match the Legacy viewer's
        # clinical display orientation through view transforms only.
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
        orientation_items = self._make_orientation_items(plane, view)

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
            orientation_items=orientation_items,
        )
        return wrap

    def _make_orientation_items(self, plane: str, view) -> list[object]:
        labels = self._orientation_labels(plane)
        items = []
        for text, pos, anchor in labels:
            item = self.pg.TextItem(text=text, color="#FFD966", anchor=anchor, fill=self.pg.mkBrush(0, 0, 0, 120))
            item.setPos(*pos)
            view.addItem(item)
            items.append(item)
        return items

    def _orientation_labels(self, plane: str) -> list[tuple[str, tuple[float, float], tuple[float, float]]]:
        x0, x1, y0, y1 = self._plane_extent(plane)
        xm = (x0 + x1) / 2.0
        ym = (y0 + y1) / 2.0
        if plane == "axial":
            return [
                ("R", (x0, ym), (0, 0.5)),
                ("L", (x1, ym), (1, 0.5)),
                ("A", (xm, y0), (0.5, 0)),
                ("P", (xm, y1), (0.5, 1)),
            ]
        if plane == "sagittal":
            return [
                ("A", (x0, ym), (0, 0.5)),
                ("P", (x1, ym), (1, 0.5)),
                ("S", (xm, y0), (0.5, 0)),
                ("I", (xm, y1), (0.5, 1)),
            ]
        return [
            ("R", (x0, ym), (0, 0.5)),
            ("L", (x1, ym), (1, 0.5)),
            ("S", (xm, y0), (0.5, 0)),
            ("I", (xm, y1), (0.5, 1)),
        ]

    def _make_key_event_filter(self):
        QtCore = self.QtCore

        class KeyEventFilter(QtCore.QObject):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent

            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.Type.KeyPress:
                    return self.parent._on_key_press(event)
                return False

        return KeyEventFilter(self)

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

            def mouseDragEvent(self, ev, axis=None):
                if ev.button() == self.parent.QtCore.Qt.MouseButton.MiddleButton:
                    current = self.mapSceneToView(ev.scenePos())
                    previous = self.mapSceneToView(ev.lastScenePos())
                    self.translateBy(x=previous.x() - current.x(), y=previous.y() - current.y())
                    self.parent.active_plane = self.plane_name
                    self.parent.user_zoomed[self.plane_name] = True
                    ev.accept()
                    return
                super().mouseDragEvent(ev, axis=axis)

            def wheelEvent(self, ev, axis=None):
                delta = ev.delta() if hasattr(ev, "delta") else ev.angleDelta().y()
                modifiers = self.parent.QtWidgets.QApplication.keyboardModifiers()
                if modifiers & self.parent.QtCore.Qt.KeyboardModifier.ControlModifier:
                    self.parent._zoom_plane(self.plane_name, 0.8 if delta > 0 else 1.25)
                else:
                    step = self.parent._wheel_step(self.plane_name, delta)
                    if modifiers & self.parent.QtCore.Qt.KeyboardModifier.ShiftModifier:
                        step *= 5
                    self.parent._on_plane_wheel(self.plane_name, step)
                ev.accept()

        return BoundViewBox(self, plane)

    def _on_key_press(self, event) -> bool:
        key = event.key()
        QtCore = self.QtCore
        if key == QtCore.Qt.Key.Key_Left:
            self._move_cursor_in_active_plane(-1, 0)
            return True
        if key == QtCore.Qt.Key.Key_Right:
            self._move_cursor_in_active_plane(1, 0)
            return True
        if key == QtCore.Qt.Key.Key_Up:
            self._move_cursor_in_active_plane(0, -1)
            return True
        if key == QtCore.Qt.Key.Key_Down:
            self._move_cursor_in_active_plane(0, 1)
            return True
        if key in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
            self._zoom_plane(self.active_plane, 0.8)
            return True
        if key in (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Underscore):
            self._zoom_plane(self.active_plane, 1.25)
            return True
        if key in (QtCore.Qt.Key.Key_0, QtCore.Qt.Key.Key_Home):
            self._reset_all_views()
            return True
        if key == QtCore.Qt.Key.Key_F:
            self._reset_all_views()
            return True
        if key in (QtCore.Qt.Key.Key_H, QtCore.Qt.Key.Key_Question):
            self._show_help()
            return True
        if key == QtCore.Qt.Key.Key_O:
            self.overlay_visible = not self.overlay_visible
            self._update_all_images()
            return True
        if key == QtCore.Qt.Key.Key_I:
            self.info_check.setChecked(not self.info_check.isChecked())
            return True
        if key == QtCore.Qt.Key.Key_C:
            self.ct_check.setChecked(not self.ct_check.isChecked())
            return True
        if key == QtCore.Qt.Key.Key_S:
            if self.structure_check.isEnabled():
                self.structure_check.setChecked(not self.structure_check.isChecked())
            return True

        mode_keys = {
            QtCore.Qt.Key.Key_G: "Gamma",
            QtCore.Qt.Key.Key_P: "Pass/Fail",
            QtCore.Qt.Key.Key_R: "Ref Dose",
            QtCore.Qt.Key.Key_E: "Eval Dose",
            QtCore.Qt.Key.Key_X: "Dose Diff",
            QtCore.Qt.Key.Key_D: "Dose Ratio",
        }
        if key in mode_keys:
            self._set_overlay_mode(mode_keys[key])
            return True
        return False

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

    def _display_slice_for_plane(self, volume: np.ndarray | None, plane: str) -> np.ndarray | None:
        slice2d = self._slice_for_plane(volume, plane)
        if slice2d is None:
            return None
        if plane in {"sagittal", "coronal"}:
            return np.flipud(slice2d)
        return slice2d

    def _display_z_coord(self, z_index: float) -> float:
        display_index = (self.nz - 1) - float(z_index)
        return _index_to_coord(self.z_coords_mm, display_index)

    def _plane_size(self, plane: str) -> tuple[int, int]:
        if plane == "axial":
            return self.nx, self.ny
        if plane == "sagittal":
            return self.ny, self.nz
        return self.nx, self.nz

    def _plane_extent(self, plane: str) -> tuple[float, float, float, float]:
        return plane_display_extent(plane, self.x_coords_mm, self.y_coords_mm, self.z_coords_mm)

    def _plane_rect(self, plane: str):
        x0, x1, y0, y1 = self._plane_extent(plane)
        return self.QtCore.QRectF(x0, y0, x1 - x0, y1 - y0)

    def _cursor_xy_for_plane(self, plane: str) -> tuple[int, int]:
        if plane == "axial":
            return int(self.cur_x), int(self.cur_y)
        if plane == "sagittal":
            return int(self.cur_y), int(self.cur_z)
        return int(self.cur_x), int(self.cur_z)

    def _cursor_display_xy_for_plane(self, plane: str) -> tuple[float, float]:
        return display_point_for_cursor(
            plane,
            (int(self.cur_z), int(self.cur_y), int(self.cur_x)),
            self.x_coords_mm,
            self.y_coords_mm,
            self.z_coords_mm,
        )

    def _set_cursor_from_display_xy(self, plane: str, display_x: float, display_y: float):
        self.cur_z, self.cur_y, self.cur_x = cursor_from_display_point(
            plane,
            display_x,
            display_y,
            (int(self.cur_z), int(self.cur_y), int(self.cur_x)),
            self.x_coords_mm,
            self.y_coords_mm,
            self.z_coords_mm,
        )

    def _move_cursor_in_active_plane(self, dx: int, dy: int):
        old = {"z": self.cur_z, "y": self.cur_y, "x": self.cur_x}
        if self.active_plane == "axial":
            self.cur_x = int(np.clip(self.cur_x + dx, 0, self.nx - 1))
            self.cur_y = int(np.clip(self.cur_y + dy, 0, self.ny - 1))
        elif self.active_plane == "sagittal":
            self.cur_y = int(np.clip(self.cur_y + dx, 0, self.ny - 1))
            self.cur_z = int(np.clip(self.cur_z - dy, 0, self.nz - 1))
        else:
            self.cur_x = int(np.clip(self.cur_x + dx, 0, self.nx - 1))
            self.cur_z = int(np.clip(self.cur_z - dy, 0, self.nz - 1))
        self._update_planes_for_cursor_change(old)

    def _update_planes_for_cursor_change(self, old: dict[str, int]):
        if old["z"] != self.cur_z:
            self._update_plane_image("axial")
        if old["x"] != self.cur_x:
            self._update_plane_image("sagittal")
        if old["y"] != self.cur_y:
            self._update_plane_image("coronal")
        self._sync_crosshair_labels_sliders()

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

    def _dose_key_for_mode(self, mode: str | None = None) -> str | None:
        mode = self.overlay_mode if mode is None else mode
        if mode == "Ref Dose":
            return "ref"
        if mode == "Eval Dose":
            return "eval"
        return None

    def _dose_key_for_controls(self) -> str:
        return self._dose_key_for_mode() or self._dose_range_control_key

    def _active_dose_display_range(self, dose_key: str) -> tuple[float, float]:
        if self._dose_display_auto_enabled.get(dose_key, True):
            return self._dose_display_auto_range[dose_key]
        manual = self._dose_display_manual_range.get(dose_key)
        if manual is not None:
            return manual
        return self._dose_display_auto_range[dose_key]

    def _set_manual_dose_display_range(self, dose_key: str, min_value: float, max_value: float) -> bool:
        previous = self._active_dose_display_range(dose_key)
        new_range, ok, reason = _validated_dose_display_range(min_value, max_value, previous)
        if not ok:
            logger.warning("Invalid dose display range: %s.", reason)
            return False
        self._dose_display_manual_range[dose_key] = new_range
        self._dose_display_auto_enabled[dose_key] = False
        self._invalidate_dose_overlay_cache(dose_key)
        self._log_dose_volume_debug(self._dose_label(dose_key), dose_key, self._dose_volume(dose_key))
        return True

    def _dose_label(self, dose_key: str) -> str:
        return "Ref" if dose_key == "ref" else "Eval"

    def _dose_volume(self, dose_key: str) -> np.ndarray | None:
        return self.ref_dose if dose_key == "ref" else self.eval_dose

    def _format_dose_range_value(self, value: float) -> str:
        return f"{float(value):.4g}"

    def _sync_dose_range_controls(self):
        if not hasattr(self, "dose_auto_check"):
            return
        dose_key = self._dose_key_for_controls()
        self._syncing_dose_range_controls = True
        try:
            self.dose_range_box.setTitle(f"Dose Range ({self._dose_label(dose_key)})")
            self.dose_auto_check.setEnabled(True)
            self.dose_min_edit.setEnabled(not self._dose_display_auto_enabled.get(dose_key, True))
            self.dose_max_edit.setEnabled(not self._dose_display_auto_enabled.get(dose_key, True))
            auto_enabled = self._dose_display_auto_enabled[dose_key]
            self.dose_auto_check.setChecked(auto_enabled)
            lo, hi = self._active_dose_display_range(dose_key)
            self.dose_min_edit.setValue(float(np.clip(lo, 0.0, 100.0)))
            self.dose_max_edit.setValue(float(np.clip(hi, 0.0, 100.0)))
        finally:
            self._syncing_dose_range_controls = False

    def _parse_dose_range_fields(self) -> tuple[float, float] | None:
        return float(self.dose_min_edit.value()), float(self.dose_max_edit.value())

    def _on_dose_auto_changed(self, checked: bool):
        if self._syncing_dose_range_controls:
            return
        dose_key = self._dose_key_for_controls()
        self._dose_display_auto_enabled[dose_key] = bool(checked)
        if checked:
            self._invalidate_dose_overlay_cache(dose_key)
            self._log_dose_volume_debug(self._dose_label(dose_key), dose_key, self._dose_volume(dose_key))
            self._refresh_current_dose_overlay(dose_key)
        else:
            values = self._parse_dose_range_fields()
            if values is not None and self._set_manual_dose_display_range(dose_key, values[0], values[1]):
                self._refresh_current_dose_overlay(dose_key)
            else:
                self._dose_display_auto_enabled[dose_key] = True
        self._sync_dose_range_controls()

    def _on_dose_range_edited(self):
        if self._syncing_dose_range_controls:
            return
        dose_key = self._dose_key_for_controls()
        if self._dose_display_auto_enabled.get(dose_key, True):
            self._sync_dose_range_controls()
            return
        values = self._parse_dose_range_fields()
        if values is not None and self._set_manual_dose_display_range(dose_key, values[0], values[1]):
            self._refresh_current_dose_overlay(dose_key)
        self._sync_dose_range_controls()

    def _invalidate_dose_overlay_cache(self, dose_key: str | None = None):
        if dose_key is None:
            self._overlay_rgba_cache.clear()
            return
        modes = {"ref": "Ref Dose", "eval": "Eval Dose"}
        mode = modes[dose_key]
        for key in list(self._overlay_rgba_cache):
            if key[0] == mode:
                self._overlay_rgba_cache.pop(key, None)

    def _refresh_current_dose_overlay(self, dose_key: str):
        current_key = self._dose_key_for_mode()
        if current_key == dose_key:
            self._update_all_images()

    def _log_dose_volume_debug(self, label: str, dose_key: str, volume: np.ndarray | None):
        if not logger.isEnabledFor(logging.DEBUG):
            return
        active_lo, active_hi = self._active_dose_display_range(dose_key)
        auto_lo, auto_hi = self._dose_display_auto_range[dose_key]
        if volume is None:
            logger.debug(
                "%s dose stats: volume=N/A auto=(%.6g, %.6g) active=(%.6g, %.6g)",
                label,
                auto_lo,
                auto_hi,
                active_lo,
                active_hi,
            )
            return
        finite_mask = np.isfinite(volume)
        finite = volume[finite_mask]
        positive = volume[finite_mask & (volume > 0)]
        if finite.size:
            raw_min = float(np.nanmin(finite))
            raw_max = float(np.nanmax(finite))
            percentiles = [float(np.percentile(finite, p)) for p in (95, 99, 99.5, 99.9)]
            finite_indices = np.argwhere(finite_mask)
            max_index = tuple(int(i) for i in finite_indices[int(np.argmax(finite))])
        else:
            raw_min = raw_max = float("nan")
            percentiles = [float("nan")] * 4
            max_index = None
        logger.debug(
            "%s dose stats: finite=%d positive=%d raw_min=%.6g raw_max=%.6g "
            "p95=%.6g p99=%.6g p99.5=%.6g p99.9=%.6g auto=(%.6g, %.6g) "
            "active=(%.6g, %.6g) max_index=%s",
            label,
            int(finite.size),
            int(positive.size),
            raw_min,
            raw_max,
            percentiles[0],
            percentiles[1],
            percentiles[2],
            percentiles[3],
            auto_lo,
            auto_hi,
            active_lo,
            active_hi,
            max_index,
        )

    def _log_rgba_debug(self, label: str, plane: str, rgba: np.ndarray | None):
        if rgba is None or not logger.isEnabledFor(logging.DEBUG):
            return
        rgb = rgba[..., :3]
        alpha = rgba[..., 3]
        flat_rgba = rgba.reshape(-1, 4)
        unique_count = int(np.unique(flat_rgba, axis=0).shape[0]) if flat_rgba.shape[0] <= 200_000 else -1
        logger.debug(
            "%s %s RGBA: rgb_min=%s rgb_max=%s alpha_min=%d alpha_max=%d "
            "alpha_nonzero=%d unique_colors=%s",
            label,
            plane,
            [int(v) for v in rgb.reshape(-1, 3).min(axis=0)],
            [int(v) for v in rgb.reshape(-1, 3).max(axis=0)],
            int(alpha.min()),
            int(alpha.max()),
            int(np.count_nonzero(alpha)),
            unique_count if unique_count >= 0 else "skipped",
        )

    def _compute_gamma_cutoff_threshold(self) -> float | None:
        if not self.gpr_cond:
            return None
        cutoff = self.gpr_cond.get("cutoff")
        if cutoff is None:
            return None
        norm = self.gpr_cond.get("norm", "global_max")
        if norm in {"global_max", "max_ref"}:
            finite_ref = self.ref_dose[np.isfinite(self.ref_dose)]
            norm_factor = float(np.nanmax(finite_ref)) if finite_ref.size else 1.0
        else:
            norm_factor = 1.0
        return norm_factor * float(cutoff) / 100.0

    def _stats_text(self) -> str:
        text = ""
        if self.gpr_cond:
            text += f"Criteria: {self.gpr_cond['dta']:.1f}mm / {self.gpr_cond['dd']:.1f}%\n"
            text += f"Cutoff  : {self.gpr_cond['cutoff']:.1f}%\n"
        text += f"{_overall_gpr_text(self.gamma)}\n"
        text += f"{_gamma_coverage_text(self.gamma)}\n"
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
        gamma2d = self._display_slice_for_plane(self.gamma, plane)
        if self.overlay_mode == "Gamma":
            valid = None if gamma2d is None else np.isfinite(gamma2d)
            return self._scalar_rgba(gamma2d, (0.0, 2.0), valid)
        if self.overlay_mode == "Pass/Fail":
            return self._pass_fail_rgba(gamma2d)
        if self.overlay_mode == "Ref Dose":
            if not self.overlay_visible:
                return None
            dose_key = "ref"
            dose_range = self._active_dose_display_range(dose_key)
            cache_key = (self.overlay_mode, plane, self._plane_index(plane), self.overlay_alpha, dose_range)
            if cache_key in self._overlay_rgba_cache:
                return self._overlay_rgba_cache[cache_key]
            ref2d = self._display_slice_for_plane(self.ref_dose, plane)
            valid = None if ref2d is None else np.isfinite(ref2d)
            rgba = self._scalar_rgba(ref2d, dose_range, valid)
            self._overlay_rgba_cache[cache_key] = rgba
            self._log_rgba_debug("Ref Dose", plane, rgba)
            return rgba
        if self.overlay_mode == "Eval Dose":
            if not self.overlay_visible:
                return None
            dose_key = "eval"
            dose_range = self._active_dose_display_range(dose_key)
            cache_key = (self.overlay_mode, plane, self._plane_index(plane), self.overlay_alpha, dose_range)
            if cache_key in self._overlay_rgba_cache:
                return self._overlay_rgba_cache[cache_key]
            eval2d = self._display_slice_for_plane(self.eval_dose, plane)
            valid = None if eval2d is None else np.isfinite(eval2d)
            rgba = self._scalar_rgba(eval2d, dose_range, valid)
            self._overlay_rgba_cache[cache_key] = rgba
            self._log_rgba_debug("Eval Dose", plane, rgba)
            return rgba
        if self.overlay_mode == "Dose Diff":
            ref2d = self._display_slice_for_plane(self.ref_dose, plane)
            eval2d = self._display_slice_for_plane(self.eval_dose, plane)
            if ref2d is None or eval2d is None:
                return None
            diff = eval2d - ref2d
            max_abs = max(float(np.nanmax(np.abs(diff[np.isfinite(diff)]))) if np.any(np.isfinite(diff)) else 1.0, 1.0)
            valid = np.isfinite(diff)
            return self._scalar_rgba(diff, (-max_abs, max_abs), valid, palette="blue_red")
        if self.overlay_mode == "Dose Ratio":
            ref2d = self._display_slice_for_plane(self.ref_dose, plane)
            eval2d = self._display_slice_for_plane(self.eval_dose, plane)
            if ref2d is None or eval2d is None:
                return None
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(ref2d > 0, eval2d / ref2d, np.nan)
            valid = np.isfinite(ratio) & (ref2d >= self._dose_vmax * 0.1)
            return self._scalar_rgba(ratio, (0.5, 1.5), valid, palette="blue_red")
        return None

    def _update_plane_image(self, plane: str):
        state = self.plane_states[plane]
        ct2d = self._display_slice_for_plane(self.ct, plane)
        state.ct_item.setImage(ct2d, autoLevels=False, levels=self.ct_levels)
        state.ct_item.setRect(self._plane_rect(plane))
        state.ct_item.setVisible(self.visible["CT"])

        rgba = self._overlay_rgba(plane)
        if rgba is None:
            state.gamma_item.clear()
        else:
            state.gamma_item.setImage(rgba, autoLevels=False)
            state.gamma_item.setRect(self._plane_rect(plane))
        self._update_structure_items(plane)
        state.title.setText(f"{plane.capitalize()} (idx {self._plane_index(plane)}) {self._slice_gpr_text(self._display_slice_for_plane(self.gamma, plane))}")
        if not self.user_zoomed.get(plane, False):
            self._reset_zoom(plane)

    def _update_all_images(self):
        for plane in ("axial", "sagittal", "coronal"):
            self._update_plane_image(plane)

    def _format_cursor_text(self) -> str:
        z, y, x = int(self.cur_z), int(self.cur_y), int(self.cur_x)
        hu = _strict_voxel_value(self.ct, self.ct, z, y, x)
        ref = _strict_voxel_value(self.ref_dose, self.ct, z, y, x)
        eval_value = _strict_voxel_value(self.eval_dose, self.ct, z, y, x)
        gamma_value = _strict_voxel_value(self.gamma, self.ct, z, y, x)
        diff_value = _dose_diff_value(eval_value, ref)
        hu_text = f"{int(round(hu))}" if hu is not None else "N/A"
        ref_text = f"{ref:.3f} {self.ref_unit}" if ref is not None else "N/A"
        eval_text = f"{eval_value:.3f} {self.eval_unit}" if eval_value is not None else "N/A"
        diff_text = f"{diff_value:.3f} {self.eval_unit}" if diff_value is not None else "N/A"
        gamma_text = _gamma_value_text(gamma_value, self.gamma is not None, ref, self._gamma_cutoff_threshold)
        coord_text = self._format_physical_coordinate(z, y, x)
        return (
            f"Idx: ({z}, {y}, {x})\n"
            f"Coord: {coord_text}\n"
            f"HU: {hu_text}\n"
            f"Ref: {ref_text}\n"
            f"Eval: {eval_text}\n"
            f"Diff: {diff_text}\n"
            f"Gamma: {gamma_text}\n"
            f"Pass/Fail: {_pass_fail_text(gamma_value)}"
        )

    def _format_physical_coordinate(self, z: int, y: int, x: int) -> str:
        try:
            x_mm = float(self.dose_meta["x_coords_mm"][x])
            y_mm = float(self.dose_meta["y_coords_mm"][y])
            z_mm = float(self.dose_meta["z_coords_mm"][z])
            ipp = np.asarray(self.dose_meta["ipp"], dtype=float)
            v_col = np.asarray(self.dose_meta["v_col"], dtype=float)
            v_row = np.asarray(self.dose_meta["v_row"], dtype=float)
            v_slice = np.asarray(self.dose_meta["v_slice"], dtype=float)
            point = ipp + x_mm * v_col + y_mm * v_row + z_mm * v_slice
            if not np.all(np.isfinite(point)):
                return "N/A"
            return f"({point[0]:.1f}, {point[1]:.1f}, {point[2]:.1f}) mm"
        except Exception:
            return "N/A"

    def _sync_crosshair_labels_sliders(self):
        text = self._format_cursor_text()
        for plane, state in self.plane_states.items():
            x, y = self._cursor_display_xy_for_plane(plane)
            state.hline.setPos(y)
            state.vline.setPos(x)
            state.label.setText(text)
            state.label.setPos(x, y)
            state.label.setVisible(self.visible["Info"])
            self._syncing = True
            try:
                state.slider.setValue(self._plane_index(plane))
                state.slider_label.setText(str(self._plane_index(plane)))
            finally:
                self._syncing = False

    def _on_slider_changed(self, plane: str, value: int):
        if self._syncing:
            return
        self.active_plane = plane
        self._set_plane_index(plane, value)
        self._update_plane_image(plane)
        self._sync_crosshair_labels_sliders()

    def _on_plane_wheel(self, plane: str, step: int):
        self.active_plane = plane
        old_idx = self._plane_index(plane)
        self._set_plane_index(plane, old_idx + step)
        if self._plane_index(plane) != old_idx:
            self._update_plane_image(plane)
        self._sync_crosshair_labels_sliders()

    def _on_plane_click(self, plane: str, view_x: float, view_y: float):
        self.active_plane = plane
        old = {"z": self.cur_z, "y": self.cur_y, "x": self.cur_x}
        self._set_cursor_from_display_xy(plane, view_x, view_y)
        self._update_planes_for_cursor_change(old)

    def _on_alpha_changed(self, value: int):
        self.overlay_alpha = int(np.clip(round(value / 100 * 255), 0, 255))
        self.alpha_value_label.setText(f"{int(value)}%")
        self._invalidate_dose_overlay_cache()
        for plane in ("axial", "sagittal", "coronal"):
            rgba = self._overlay_rgba(plane)
            if rgba is not None:
                self.plane_states[plane].gamma_item.setImage(rgba, autoLevels=False)
                self.plane_states[plane].gamma_item.setRect(self._plane_rect(plane))
            else:
                self.plane_states[plane].gamma_item.clear()

    def _on_visibility_changed(self, label: str, checked: bool):
        self.visible[label] = bool(checked)
        if label == "Info":
            for state in self.plane_states.values():
                state.label.setVisible(bool(checked))
            if hasattr(self, "info_check") and self.info_check.isChecked() != bool(checked):
                self.info_check.setChecked(bool(checked))
            if "Info" in self._view_actions and self._view_actions["Info"].isChecked() != bool(checked):
                self._view_actions["Info"].setChecked(bool(checked))
            return
        if label == "CT" and "CT" in self._view_actions and self._view_actions["CT"].isChecked() != bool(checked):
            self._view_actions["CT"].setChecked(bool(checked))
        if label == "Structure" and "Structure" in self._view_actions and self._view_actions["Structure"].isChecked() != bool(checked):
            self._view_actions["Structure"].setChecked(bool(checked))
        self._update_all_images()

    def _on_roi_visibility_changed(self, roi: str, checked: bool):
        self.roi_visible[roi] = bool(checked)
        self._update_all_images()

    def _on_mode_changed(self, button):
        self._set_overlay_mode(button.text())

    def _set_overlay_mode(self, mode: str):
        self.overlay_mode = mode
        dose_key = self._dose_key_for_mode(mode)
        if dose_key is not None:
            self._dose_range_control_key = dose_key
        for button in self.mode_group.buttons():
            if button.text() == mode:
                button.setChecked(True)
                break
        for name, action in self._overlay_actions.items():
            action.setChecked(name == mode)
        self.overlay_visible = self.gamma is not None or self.overlay_mode in {"Ref Dose", "Eval Dose", "Dose Diff", "Dose Ratio"}
        self._sync_dose_range_controls()
        self._update_all_images()

    def _reset_zoom(self, plane: str):
        self.user_zoomed[plane] = False
        self.plane_states[plane].view.setRange(self._plane_rect(plane), padding=0.02)

    def _reset_all_views(self):
        for plane in ("axial", "sagittal", "coronal"):
            self._reset_zoom(plane)

    def _zoom_plane(self, plane: str, scale_factor: float):
        state = self.plane_states[plane]
        view_range = state.view.viewRange()
        (xmin, xmax), (ymin, ymax) = view_range
        cx, cy = self._cursor_display_xy_for_plane(plane)
        x0_extent, x1_extent, y0_extent, y1_extent = self._plane_extent(plane)
        width = x1_extent - x0_extent
        height = y1_extent - y0_extent
        cur_w = max(float(xmax - xmin), 1.0)
        cur_h = max(float(ymax - ymin), 1.0)
        new_w = float(np.clip(cur_w * scale_factor, 8.0, width * 1.5))
        new_h = float(np.clip(cur_h * scale_factor, 8.0, height * 1.5))
        x0 = float(np.clip(cx - new_w / 2.0, x0_extent - width * 0.25, x1_extent + width * 0.25 - new_w))
        y0 = float(np.clip(cy - new_h / 2.0, y0_extent - height * 0.25, y1_extent + height * 0.25 - new_h))
        state.view.setRange(xRange=(x0, x0 + new_w), yRange=(y0, y0 + new_h), padding=0)
        self.user_zoomed[plane] = True

    def _show_help(self):
        self.QtWidgets.QMessageBox.information(
            self.window,
            "Fast Viewer Controls",
            "\n".join(
                [
                    "Mouse:",
                    "  Left click: move crosshair",
                    "  Wheel: scroll slice",
                    "  Shift + wheel: fast slice scroll",
                    "  Ctrl + wheel: zoom",
                    "  Middle drag: pan",
                    "",
                    "Keyboard:",
                    "  Arrow keys: move cursor in active plane",
                    "  + / -: zoom active plane",
                    "  0 or F: fit/reset all views",
                    "  I: toggle current point info",
                    "  O: toggle overlay",
                    "  C: toggle CT",
                    "  S: toggle structures",
                    "  G/P/R/E/X/D: Gamma, Pass/Fail, Ref, Eval, Diff, Ratio",
                    "  H or ?: show this help",
                    "",
                    "Current point values are read from source voxel arrays.",
                    "Coordinates are derived from existing dose-grid DICOM metadata.",
                ]
            ),
        )

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
                        p0 = pts[i]
                        p1 = pts[(i + 1) % len(pts)]
                        segments.append([
                            (_index_to_coord(self.x_coords_mm, p0[0]), _index_to_coord(self.y_coords_mm, p0[1])),
                            (_index_to_coord(self.x_coords_mm, p1[0]), _index_to_coord(self.y_coords_mm, p1[1])),
                        ])
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
                    z_mm = self._display_z_coord(z_grid)
                    for i in range(0, (len(inters) // 2) * 2, 2):
                        segments.append([
                            (_index_to_coord(self.y_coords_mm, inters[i]), z_mm),
                            (_index_to_coord(self.y_coords_mm, inters[i + 1]), z_mm),
                        ])
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
                    z_mm = self._display_z_coord(z_grid)
                    for i in range(0, (len(inters) // 2) * 2, 2):
                        segments.append([
                            (_index_to_coord(self.x_coords_mm, inters[i]), z_mm),
                            (_index_to_coord(self.x_coords_mm, inters[i + 1]), z_mm),
                        ])
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
    parser.add_argument("--gamma-report")
    parser.add_argument("--rtstruct")
    parser.add_argument("--roi")
    parser.add_argument("--dd", type=float, default=3.0)
    parser.add_argument("--dta", type=float, default=2.0)
    parser.add_argument("--cutoff", type=float, default=10.0)
    parser.add_argument("--gamma-type", choices=["global", "local"], default="global")
    parser.add_argument("--norm", choices=["global_max", "max_ref", "none"], default="global_max")
    parser.add_argument("--engine", choices=["pymedphys", "numba"], default="pymedphys")
    parser.add_argument("--interp-fraction", type=int, default=1)
    parser.add_argument(
        "--skip-gamma-compute",
        action="store_true",
        help="Open the Viewer without synchronously computing a missing Gamma cache.",
    )
    parser.add_argument("--opt-shift", choices=["on", "off"], default="off")
    parser.add_argument(
        "--shift-range",
        default="x:-3:3:1,y:-3:3:1,z:-3:3:1",
    )
    parser.add_argument("--refine", choices=["none", "coarse2fine"], default="coarse2fine")
    parser.add_argument("--fine-range-mm", type=float, default=10.0)
    parser.add_argument("--fine-step-mm", type=float, default=1.0)
    parser.add_argument("--early-stop-epsilon", type=float, default=0.05)
    parser.add_argument("--early-stop-patience", type=int, default=100)
    parser.add_argument("--prescan-2d", choices=["on", "off"], default="on")
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
    try:
        eval_on_ref, eval_unit, eval_meta = _resample_eval(args.eval, dose_meta)
        gamma = _compute_gamma_if_needed(args, dose_meta, eval_on_ref, eval_meta)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1
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
        gpr_cond={"dd": args.dd, "dta": args.dta, "cutoff": args.cutoff, "norm": args.norm},
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
