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
from rtgamma.io_dicom import load_ct, load_rtdose, world_to_index
from rtgamma.main import build_ref_world_coords
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


class FastPlaneViewer:
    def __init__(
        self,
        ct: np.ndarray,
        ref_dose: np.ndarray,
        eval_dose: np.ndarray | None,
        gamma: np.ndarray | None,
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
        self.gamma_alpha = 128
        self.gamma_visible = self.gamma is not None
        self.ct_levels = self._ct_levels()
        self._syncing = False

        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("rtgamma Fast 3D Viewer PoC")
        self.plane_states: dict[str, PlaneState] = {}
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
        self.gamma_check = QtWidgets.QCheckBox("Gamma")
        self.gamma_check.setChecked(self.gamma_visible)
        self.gamma_check.setEnabled(self.gamma is not None)
        self.gamma_check.toggled.connect(self._on_gamma_visible_changed)
        controls.addWidget(self.gamma_check)

        controls.addWidget(QtWidgets.QLabel("Gamma alpha"))
        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(50)
        self.alpha_slider.valueChanged.connect(self._on_alpha_changed)
        controls.addWidget(self.alpha_slider, stretch=1)

        self.status_label = QtWidgets.QLabel(self.gamma_warning)
        controls.addWidget(self.status_label, stretch=2)
        root.addLayout(controls)
        self.window.setCentralWidget(central)

        grid.addWidget(self._make_plane_widget("axial", "Axial"), 0, 0)
        grid.addWidget(self._make_plane_widget("sagittal", "Sagittal"), 0, 1)
        grid.addWidget(self._make_plane_widget("coronal", "Coronal"), 1, 0)

        note = QtWidgets.QLabel(
            "PoC: click=cursor, wheel=slice, sliders=slice. No save/settings/ROI in this viewer."
        )
        note.setStyleSheet("color: #CCCCCC; background: #222222; padding: 12px;")
        grid.addWidget(note, 1, 1)

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
        graph.ci.addItem(view, row=0, col=0)

        ct_item = pg.ImageItem()
        gamma_item = pg.ImageItem()
        view.addItem(ct_item)
        view.addItem(gamma_item)

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
        )
        return wrap

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

            def wheelEvent(self, ev, axis=None):
                delta = ev.delta() if hasattr(ev, "delta") else ev.angleDelta().y()
                self.parent._on_plane_wheel(self.plane_name, 1 if delta > 0 else -1)
                ev.accept()

        return BoundViewBox(self, plane)

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

    def _gamma_rgba(self, gamma2d: np.ndarray | None) -> np.ndarray | None:
        if gamma2d is None:
            return None
        valid = np.isfinite(gamma2d) & (gamma2d != 0)
        t = np.clip(gamma2d.astype(np.float32) / 2.0, 0.0, 1.0)
        rgba = np.zeros(gamma2d.shape + (4,), dtype=np.uint8)
        rgba[..., 0] = (255 * np.clip((t - 0.25) * 2.0, 0.0, 1.0)).astype(np.uint8)
        rgba[..., 1] = (255 * np.clip(1.0 - np.abs(t - 0.5) * 2.0, 0.0, 1.0)).astype(np.uint8)
        rgba[..., 2] = (255 * np.clip((0.5 - t) * 2.0, 0.0, 1.0)).astype(np.uint8)
        rgba[..., 3] = np.where(valid & self.gamma_visible, self.gamma_alpha, 0).astype(np.uint8)
        return rgba

    def _update_plane_image(self, plane: str):
        QtCore = self.QtCore
        state = self.plane_states[plane]
        ct2d = self._slice_for_plane(self.ct, plane)
        width, height = self._plane_size(plane)
        state.ct_item.setImage(ct2d, autoLevels=False, levels=self.ct_levels)
        state.ct_item.setRect(QtCore.QRectF(0, 0, width, height))

        gamma2d = self._slice_for_plane(self.gamma, plane)
        rgba = self._gamma_rgba(gamma2d)
        if rgba is None:
            state.gamma_item.clear()
        else:
            state.gamma_item.setImage(rgba, autoLevels=False)
            state.gamma_item.setRect(QtCore.QRectF(0, 0, width, height))
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
        self.gamma_alpha = int(np.clip(round(value / 100 * 255), 0, 255))
        for plane in ("axial", "sagittal", "coronal"):
            gamma2d = self._slice_for_plane(self.gamma, plane)
            rgba = self._gamma_rgba(gamma2d)
            if rgba is not None:
                self.plane_states[plane].gamma_item.setImage(rgba, autoLevels=False)

    def _on_gamma_visible_changed(self, checked: bool):
        self.gamma_visible = bool(checked)
        self._on_alpha_changed(self.alpha_slider.value())


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="PyQtGraph fast 3D viewer PoC")
    parser.add_argument("--ct", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--eval")
    parser.add_argument("--gamma-npz")
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
