# rtgamma OpenSpec (v0.1)

## 1. Overview
- Purpose: DICOM RTDOSE の幾何整合とガンマ解析（2D/3D）を、臨床QAで再現性高く実行するための仕様。
- Scope: RTDOSE×RTDOSE 比較、3D/2D ガンマ、シフト最適化、ヘッダ比較（RTPLAN補助含む）、レポート・可視化・GUI 起動。
- Non-Goals: RTSTRUCT/ROI マスクの本格対応、GPU/CuPy 実装、Nelder–Mead 等のローカル探索（将来案）。
- Stakeholders: 医療物理・QA担当、研究開発者、データ提供者。

## 2. Use Cases
- 2つの線量（CCC vs MC など）を 3%/2mm/10% で比較し、GPR と差の可視化を得る。
- 幾何差（FoR/IPP/IOP/GFOV/スケール）をヘッダ比較で事前確認し、必要に応じてシフト最適化を適用。
- GUI でファイル選択・臨床プリセット・2D/3D 実行・サマリ自動オープンまでをワンクリックで行う。

## 3. Inputs & Outputs
- Inputs
  - DICOM: RTDOSE（LPS）。必須タグ: ImagePositionPatient, ImageOrientationPatient, PixelSpacing, GridFrameOffsetVector, DoseGridScaling。
  - CLI 主パラメータ（既定）
    - dd=3.0, dta=2.0, cutoff=10.0, gamma-type={global|local}, norm={global_max|max_ref|none}
    - mode={3d|2d}, plane={axial|sagittal|coronal}, plane-index={int|auto}
    - opt-shift={on|off}, shift-range="x:-3:3:1,y:-3:3:1,z:-3:3:1"
    - refine=coarse2fine, fine-range-mm=10, fine-step-mm=1, early-stop-*
    - prescan-2d={on|off}, interp={linear|bspline|nearest}, threads=<N>
- Outputs
  - 2D: gamma 画像（PNG/TIFF）、dose diff 画像（%）。
  - 3D: gamma（NPZ）、dose_diff_pct（NPZ）。
  - レポート: CSV/JSON/MD（スキーマ叩き台は docs/openspec/report.schema.json）。
  - GUI: 実行ログ run_log_*.txt、サマリ自動オープン（run3d.md / <plane>.md / header_compare.md）。

## 4. Geometry & Coordinates
- LPS に準拠。IPP/IOP/PixelSpacing/GFOV を厳守し、GFOV に合わせて dose フレームを昇順へ並べ替える（z 軸定義の一貫性）。
- 2D 平面の世界座標グリッドは配列軸順 (z,y,x) と整合。固定次元は単一軸にし、形状を以下に統一：
  - axial: (1, y, x)、sagittal: (z, y, 1)、coronal: (z, 1, x)。
- FoR/Orientation チェックを行い、`orientation_min_dot` が 0.99 未満で警告。

## 5. Resampling
- 参照グリッドの世界座標 (Xw,Yw,Zw) を構築し、評価線量を `world_to_index` で eval 側 (i,j,k) へ投影。
- `scipy.ndimage.map_coordinates` 相当で補間（linear 既定）。
- 2D 最適化OFFでは選択スライスのみに対してリサンプリング（高速経路）。

## 6. Gamma Analysis
- パラメータ: DD[%], DTA[mm], Cutoff[%], gamma-type（global/local）, norm（global_max|max_ref|none）。
- 実装: Numba ベース 3D カーネル。pymedphys はオフ。
- 出力: gamma_map、統計（mean/median/max）、GPR（<=1 の割合）。

## 7. Shift Optimization
- coarse→fine の二段探索。fine は `±(fine-range-mm)` を `fine-step-mm` で走査。
- 早期停止: 改善幅 < epsilon が `patience` 回続けば打ち切り。
- 2D プリスキャン: 中央スライスで XY 範囲を狭めて 3D 探索の初期領域を短縮。
- PowerShell のコロン混在引数は複合書式 `"x:{0}:{1}:1" -f a,b` を推奨。

## 8. Performance & Accuracy
- 性能
  - 2D（opt-shift=off）: スライス限定の高速経路。
  - 3D: Numba JIT + `--threads` で並列。初回は JIT によりウォームアップが必要。
- 精度受け入れ
  - Self-compare ≈ 100%。
  - 2D（fast path）と 3D 同一スライスの GPR 差は ≲ 0.5pp を目安。
  - 幾何不一致（SSD/SCD/SAD/スケール差）では低 GPR もデータ由来として許容。

## 9. Logging & Reproducibility
- ログ: `rtgamma.log`（INFO/DEBUG 選択可）、GUI の run_log_*.txt を保存可能。
- レポート: FoR、orientation_min_dot、best_shift、warnings、absolute_geometry_only を出力。
- 出力先: 既定では `phits-linac-validation/output/rtgamma/` を推奨（成果物の隔離）。

## 9.1 Validation Steps (CLI Examples)
- 2D axial（中央・最適化OFF・臨床プリセット相当）
  - `python -m rtgamma.main --profile clinical_rel --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm --mode 2d --plane axial --plane-index auto --opt-shift off --save-gamma-map phits-linac-validation/output/rtgamma/spec_check/axial_gamma.png --save-dose-diff phits-linac-validation/output/rtgamma/spec_check/axial_diff.png --report phits-linac-validation/output/rtgamma/spec_check/axial --threads 0 --log-level INFO`
  - 期待: GPR ≈ 96.9%、`spec_check/axial.{csv,json,md}` が生成。
- 3D（最適化OFF・臨床プリセット相当）
  - `python -m rtgamma.main --profile clinical_rel --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm --mode 3d --opt-shift off --save-gamma-map phits-linac-validation/output/rtgamma/spec_check3d/gamma3d.npz --save-dose-diff phits-linac-validation/output/rtgamma/spec_check3d/diff3d.npz --report phits-linac-validation/output/rtgamma/spec_check3d/run3d --threads 0 --log-level INFO`
  - 期待: GPR ≈ 92.8%、`spec_check3d/run3d.{csv,json,md}` が生成。
- JSON スキーマ検証
  - `python scripts/validate_report.py --sanitize-nan phits-linac-validation/output/rtgamma/spec_check/axial.json`
  - `python scripts/validate_report.py --sanitize-nan phits-linac-validation/output/rtgamma/spec_check3d/run3d.json`

## 9.2 Coronal GPR Investigation (Repro)
- 設定: `--profile clinical_rel --opt-shift off --interp linear --cutoff 10`
- インデックス掃引（例: 100/101/102）
  - `python -m rtgamma.main --profile clinical_rel --ref <ref> --eval <eval> --mode 2d --plane coronal --plane-index 100 --save-gamma-map phits-linac-validation/output/rtgamma/guiTest/coronal_100_gamma.png --save-dose-diff phits-linac-validation/output/rtgamma/guiTest/coronal_100_diff.png --report phits-linac-validation/output/rtgamma/guiTest/coronal_100 --opt-shift off`
  - 同様に 101/102 で実行し、GPR と可視化を比較。
- 正規化感度
  - 同一スライスで `--norm global_max` vs `--norm none` を比較。
- 2D fast path と 3D スライスの一致
  - 3D 実行で NPZ を保存し、同スライスの GPR が 2D と ≲0.5pp 差で一致することを確認。

### Observed Results (Sample)
- Dataset: AGLPhantom (CCC vs MC), clinical_rel, opt-shift=off, interp=linear, cutoff=10
- Coronal indices and GPR (this repo, 2025-10-23):
  - index 100 → 81.1236%
  - index 101 → 82.1029%
  - index 102 → 80.5369%
  - 出力先: `phits-linac-validation/output/rtgamma/spec_check_coronal/`

#### Observed Results (2025-10-23, post-fix)
- 本リポジトリ同梱データ（CCC vs pMCFF）、clinical_rel（global, 3%/2mm/10%, shift OFF）にて、コロナル index 100/101/102 はすべて 100.0% を観測。
- 要約: `phits-linac-validation/output/rtgamma/spec_check_coronal/summary.md`
- 備考: 正規化と平面ジオメトリ修正後、2D fast path は 3D と整合する挙動となり、本データセットでは完全一致となった。

### 2D fast path vs 3D slice consistency
- Axial 中央スライス（index 124）
  - 2D fast path GPR: 96.8729%
  - 3D gamma の axial 同スライス: 96.8729%（一致）
- Coronal（indices 100/101/102）
  - 修正前（参考）: 2D fast path が ~81% 前後、3D スライスが 100% で不一致
  - 修正後: 2D fast path も 100% に一致（2D での正規化を「全体の最大値」に統一）
  - 方針: 2D fast path の Global/MaxRef 正規化は全体の最大値を使用（3D と揃える）
  - 補助スクリプト: `scripts/compare_slice_gpr.py`（3D NPZ の特定スライスと 2D レポートの GPR を比較）

## 10. Security & Privacy
- PHI を含む DICOM はリポジトリへコミット禁止。匿名化サンプルのみ使用。
- 大容量バイナリ・生成物はコミットせず、出力フォルダに保存。

## 11. Open Questions & Constraints
- Coronal GPR の回帰現象（~82% vs ~93%）の要因切り分け（正規化・平面整合・スライス選択）。
- Local gamma オプションの CLI/GUI 露出方針とレポート整合。
- ROI/RTSTRUCT マスクの仕様（範囲、重み、閾値）。
- 将来的な GPU バックエンド（CuPy）の互換要件。

## 12. Versioning & Change Control
- 本仕様の版: v0.1（初稿）。変更時は本ヘッダと `CHANGELOG.md` を更新し、設計判断は `DECISIONS.md` に ADR として追記。
- 実装-仕様の差分は `docs/openspec/report.schema.json` と `rtgamma/main.py` の出力フィールドで相互検証。

## 13. References (Code/Docs)
- CLI/入出力・実行: rtgamma/main.py
- DICOM I/O・幾何: rtgamma/io_dicom.py
- レポート出力: rtgamma/report.py
- GUI: scripts/run_gui.ps1, run_gui.bat, config/gui_defaults.json
- 運用: AGENTS.md, TEST_PLAN.md, TROUBLESHOOTING.md, CHANGELOG.md, DECISIONS.md
