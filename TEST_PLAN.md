# Test Plan (Manual Regression)

## Scope
Covers core gamma workflows: DICOM I/O, resampling, shift optimization, gamma computation, and reporting.

## Fast Viewer Default / Distribution Checks
- Source/Python mode: no `config/gui_config.ini` selects `Fast`; saved `viewer_type=legacy` selects Legacy; saved `viewer_type=fast` selects Fast.
- Missing/invalid `viewer_type`: use the mode fallback for the current launch, show a warning/log, and do not rewrite INI until Save Settings is clicked.
- Legacy ZIP: no saved config selects Legacy, PySide6/Qt components are absent, and Fast selection gives a clear dependency/distribution error with a Legacy launch path.
- Fast ZIP: no saved config selects Fast, starts without Python installed, includes `NOTICE.txt`, `THIRD_PARTY_LICENSES/`, and a relative-path `bundled_manifest.txt`.
- Fast ZIP manifest: confirm `qwindows.dll` is under a Qt `platforms/` plugin path, GPL-only Qt modules/plugins are not unintentionally included, and PySide6/Qt components are not present in Legacy ZIP.

## Legacy / Fast Viewer Consistency Checks
- PROSTATE data: open Legacy and Fast with the same inputs and output folder.
- Axial / Sagittal / Coronal open the same CT slice index.
- Same cursor voxel reports matching HU / Ref Dose / Eval Dose / Gamma after display rounding.
- Cursor readout uses original voxel values, not interpolated display values.
- Gamma overlay threshold/mask behavior is equivalent, and `gamma=0` regions are not incorrectly hidden.
- RTSTRUCT overlay appears at the same anatomical location as Legacy.
- Old or mismatched `gamma3d.npz` with RTSTRUCT does not crash the viewer.

## Fast Viewer Performance Smoke
- Open the representative PROSTATE dataset in Fast Viewer.
- Scroll at least 50 slices in each plane.
- Confirm no obvious UI freeze and no continuously increasing memory usage during repeated scrolling.

## Test Matrix
1) Self-compare (sanity)
- Command: `python -m rtgamma.main --ref dicom/RTDOSE_...7605.1.dcm --eval dicom/RTDOSE_...7605.1.dcm --mode 3d --report phits-linac-validation/output/rtgamma/self_check`
- Expected: pass rate ~100%, best shift (0,0,0).

2) Cross-pair 3D (default 3%/2mm/10%)
- Command: `python -m rtgamma.main --ref dicom/RTDOSE_...7605.1.dcm --eval dicom/RTDOSE_...9109.1.dcm --mode 3d --report phits-linac-validation/output/rtgamma/pair_3d`
- Expected (reference run): pass ~0.43% ±0.2%; small negative dx best shift.

3) Cross-pair 3D (3%/3mm/10%)
- Command: `python -m rtgamma.main --dd 3 --dta 3 --cutoff 10 --ref <ref> --eval <eval> --mode 3d --report .../pair_3d_3by3`
- Expected (reference run): pass ~1.1% ±0.3%.

4) 2D visuals (axial/sagittal/coronal)
- Commands: use `--mode 2d --plane <axis> --plane-index <n> --save-gamma-map ... --save-dose-diff ...`
- Expected: images generated, gamma high in mismatch regions; diff shows spatial pattern.

5) PHITS vs RTD.deposit sample
- Command: `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report .../phits_vs_rtd`
- Expected (reference run): pass ~0.16%.

## Acceptance Criteria
- Commands complete without exceptions.
- Reports written (CSV/JSON/MD) with plausible stats and search logs.
- Self-compare meets 100%; cross-pairs within expected bands.

## Recommended Workflow (トラブルシューティング用)
ガンマパス率が予想以上に低い場合は、以下の順序で要因分析と最適化を行うことを推奨します：

1. **Header compare (ヘッダ比較)**
   - `scripts/compare_rtdose_headers.py` または GUIの "Header Compare" を使用し、Ref と Eval の DICOM メタデータを比較します。
   - IPP(原点)、SSD/SAD (RTPLAN)、Dose Grid Scaling の違いをここで事前に特定します。
2. **Absolute geometry (絶対座標系による評価)**
   - 最適化オフ (`--opt-shift off`) かつ 正規化なし (`--norm none`) または `global_max` で素のガンマパス率を確認します。
   - ヘッダ比較で特定した物理的なズレがそのまま反映されている状態です。
3. **Coarse search (粗い探索)**
   - `--opt-shift on` とし、広範囲 (`--shift-range`) を粗いステップ (`2mm`など) で探索し、パス率が改善するおおよその絶対位置のズレ（例: -114mm）を特定します。
4. **Fine search (密な探索)**
   - Coarse で見つけた位置周辺を `--fine-range-mm 10`, `--fine-step-mm 1` などの詳細レベルで最適化し、最大パス率を得ます。
5. **ROI 限定解析 (オプション)**
   - 全体評価の後に特定の臓器（GTVなど）のみのパス率にボトルネックがないか `--rtstruct` と `--roi` を用いて検証します。

## Geometry Sanity (Header Compare)
- Run: `python scripts/compare_rtdose_headers.py --a <ref.dcm> --b <eval.dcm> --plan-a <ref_plan.dcm> --plan-b <eval_plan.dcm> --out phits-linac-validation/output/rtgamma/<pair>_dose_compare.md`
- Verify:
  - `FrameOfReferenceUID` matches.
  - `origin_delta_projected_mm (dx,dy,dz)` is small unless a known setup shift exists.
  - `plan_isocenter_delta_mag_mm` is ~0.
  - Pixel spacing and GFOV look reasonable (monotonic; median step ~ slice spacing).
