# Changelog
 
## [0.8.0] - 2026-03-13
### 追加 (Added)
- **DVH（線量体積ヒストグラム）計算・比較機能**: 
  - 累積DVHおよび線量指標（D95, D50, Dmean等）の自動算出を実装。
  - PDFレポートへのDVH比較グラフと統計テーブルの追加。
  - チャート凡例に比較元のDICOMファイル名を表示。
- **解析レポートの強化**: 
  - 生成されたグラフ画像を `chart/` サブフォルダに自動的に整理して保存する機能。
  - PDFレポートに実行時のパッケージバージョンとコマンド引数を印字し、解析の再現性を向上。
- **GPR計算エンジンの劇的高速化**: 
  - 探索アルゴリズムの刷新（距離順探索）と Early Exit 最適化により、計算時間を大幅に短縮。
- **3Dマルチプレーンビューアの安定化**: 
  - スクロールバー、数値入力同期、およびサジタル・コロナル面の上下方向（Sup-Inf）の正位化。
- **ポータブル実行環境（EXE版GUI）の構築**:
  - Python未インストール環境向けにEXEを強制使用するポータブルランチャー (`run_gui_exe.bat`) および専用スクリプトを作成。
  - PowerShellスクリプトのエンコーディング（UTF-8 with BOM）を最適化し、日本語環境での起動エラーを解消。
  - 別のPCにコピーするだけで即座に使用可能な配布パッケージ形式での提供に対応。

### 修正 (Fixed)
- **PDF生成バグの修正**: `pdf_report.py` における `numpy` インポート漏れを修正。
- **2D断面解析の安定化**: RTSTRUCT マスク適用時の `IndexError` を解消。

## [0.6.0] - 2026-03-06
### 追加 (Added)
- **GUI ツールチップ**: GUI 上の各パラメータ（Local Gamma, Norm, DTA, DD 等）にホバー時の詳細な解説ツールチップを追加しました。
- **EXE パッケージ化対応**: `scripts/build_exe.ps1` を追加し、PyInstaller を用いて `rtgamma` バックエンドと3Dビューアを独立した実行ファイル（`.exe`）としてパッケージ化できるようにしました。GUI はビルド済みの `.exe` を自動検出して使用します。
- **GUI PDF 生成ボタン**: GUI からワンクリックで PDF レポートを生成・保存するオプションを追加しました。

### 変更 (Changed)
- 3D Viewer: パラメータ設定の表示やマルチパスレンダリングの動作を改善し、安定性を向上しました。
- **Local Gamma ドキュメント強化**: Local Gamma 選択時に GPR が低下する挙動について、正規化の数学的根拠に基づく解説をチュートリアルおよび仕様書へ追記しました。

## [0.4.0] - 2026-03-04
### 追加 (Added)
- **サブボクセル内挿 (Sub-voxel Interpolation)**: 3Dガンマ探索において、ボクセル解像度が DTA 基準より大きい場合に生じる極端なパス率低下を修正するため、トリリニア・サブボクセル内挿表示 (`--interp-fraction`) を導入しました。これにより 3DVH との GPR 差分が ~1.1pp まで改善されました。
- **商用化ロードマップ**: 計19項目の機能強化ロードマップをドキュメント (`docs/feature_roadmap.md`, `TODO.md`, `99-handover_context.md`) に復元・統合しました。
- **ヘッダ比較分析**: テストデータセットにおける IPP / DoseUnit / SSD の差異を比較分析したレポートを生成しました。

### 変更 (Changed)
- GUI: `Sub-voxel Interp` パラメータをUIに露出し、臨床の推奨デフォルト値を 10 に設定しました。
- ドキュメント: GPR低下時の特定と推奨ワークフロー (Header Compare -> Absolute -> Coarse -> Fine) を追加して `README.md` と `TEST_PLAN.md` を更新しました。

## [0.3.0] - 2026-03-04
### Added
- 3D Gamma Viewer (`scripts/gamma_viewer.py`): Interactive visualization with ROI overlays and toggleable structure visibility, Dose Ratio, and Pass/Fail modes.
- RTSTRUCT support: Ability to calculate and display per-structure GPR (Gamma Pass Rate) in both CLI and GUI.
- RTPLAN support: `compare_rtdose_headers.py` now accepts `--plan-a`/`--plan-b` to compare Isocenter, SAD, and SSD settings.
- Evaluation condition display: The viewer now shows current DD/DTA/Cutoff settings.

### Changed
- GUI Redesign: Dark theme implementation with improved layout and direct input fields for analysis parameters.
- Performance Optimization: Implemented lazy evaluation for resampling, significantly reducing startup time and improving UI responsiveness.

### Fixed
- Coordinate Alignment: Resolved inconsistencies in LPS coordinate projection when comparing DICOM volumes with different origins.
- UI Toggling: Fixed a visual bug in the 3D viewer where checkboxes sometimes failed to update their checkmarks visually despite data toggling correctly.

## [0.1.0] - 2025-10-23
### Added
- Local gamma support (`--gamma-type local`) with GUI toggle.
- OpenSpec documentation under `docs/openspec/` (README, TEMPLATE, report.schema.json, examples, GUI guide).
- Validators: `scripts/validate_report.py` (JSON schema), `scripts/compare_slice_gpr.py` (3D slice vs 2D).
- Synthetic, DICOM-free tests: `tests/test_cli_help.py`, `tests/test_gamma_synthetic.py`.
- Japanese README: `README_JA.md` and GUI screenshot reference.
- CI: GitHub Actions for Windows and Ubuntu with Python 3.10–3.12.

### Changed
- README normalized to UTF-8 (no BOM) and updated with latest guidance and CI badge.
- GUI script (`scripts/run_gui.ps1`): Local gamma checkbox; minor docs links.

### Fixed
- 2D fast path normalization aligned with 3D (use full-volume reference max for global/max_ref), fixing coronal slice GPR consistency.
- CI stability: DICOM-dependent tests now skip when sample data is absent.

### Notes
- Coronal GPR investigation notes updated in OpenSpec with post-fix behavior.

## [2025-10-15]
### Added
- Report fields: `ref_for_uid`, `eval_for_uid`, `same_for_uid`, `best_shift_mag_mm`, `absolute_geometry_only`, `orientation_min_dot`, `warnings`.
- Console warnings for FoR mismatch and large shifts; CLI `--warn-large-shift-mm`.
- PowerShell: `scripts/run_autofallback.ps1` (auto-fallback from absolute geometry to wide best-shift), `run_test02_abs_vs_bestshift.ps1`, `run_test02_wide_bestshift.ps1`.
- Utility: `scripts/compare_rtdose_headers.py` (Markdown diff of RTDOSE geometry/scale).

### Fixed
- PowerShell string interpolation with colons in shift spec (use `-f` formatting) to avoid parser errors.

### Notes
- Test04 (6MV vs 10MV) absolute geometry yields ~60% GPR (expected due to energy profile differences).
- Test01/03 (SSD=100 cm) vs Test02/04 (SCD=100 cm) suggest setup discrepancy as a primary cause of low GPR in earlier runs.

## [2025-10-10]
### Added
- Documentation overhaul: README streamlined; AGENTS.md (contributor guide).
- Troubleshooting, Test Plan, Decisions (ADR) docs.

### Changed
- DICOM Z-slice order handling: synchronize `GridFrameOffsetVector` (GFOV) with dose frames by reordering in ascending GFOV.
- Origin offset correction: project IPP delta onto reference row/col/slice directions for robust alignment across orientations.
- Shift application: convert axis shifts (dx,dy,dz along ref axes) to an LPS vector before resampling.
- Output directory handling: guard against empty dirname when creating folders.

### Fixed
- Occasional `FileNotFoundError` when output directory didn’t exist.
- Missing `TransferSyntaxUID` handled by defaulting to ImplicitVRLittleEndian when absent.
- Minor scoping/name issues in optimization flow.

### Notes
- Self-compare pass rate is 100% (expected). Cross-system pairs with different grid sizes/scales naturally yield low pass rates; this is data-driven, not a software defect.
