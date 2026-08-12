# Changelog

## [0.9.4] - 2026-08-12

### Fixed
- 3D Gamma runs started from the GUI now always save the validated `gamma3d.npz`/`run3d.json` Viewer cache. The Viewer clearly disables unavailable Gamma/Pass-Fail choices and automatically shows Dose Ratio when evaluation dose is loaded but no compatible Gamma cache exists.
- Large full-volume 3D runs started from the GUI now default to the parallel Numba GPR engine with interpolation fraction 4. PyMedPhys remains available as the reference engine, with an explicit slow-run warning and 30-second liveness messages. The GUI thread limit is now actually applied to Numba; `0` means automatic selection.
- Windowsオフラインインストーラーが既存のCPython 3.12 x64を検出した場合、そのPython本体やグローバルパッケージを変更せず、アプリ専用venvの作成元として利用できるようにした。
- RTDOSEのスナップショット読込後にヘッダー比較が`Dataset.filename`の`BytesIO`値をパスとして扱い、スモークテストが失敗する問題を修正。
- PHITS由来RTDOSEなどでFrameOfReferenceUIDが異なっても、線量単位と方向余弦が互換なら明示的なDICOM患者座標で解析を継続し、不一致をレポート警告として記録するよう修正。
- 3D Viewerの標準出力・例外・終了コードをGUIへ戻し、起動直後の異常終了を成功表示せずログとダイアログで通知するよう修正。
- GUIから3D Viewerを開く際、有効なGamma cacheがなければ大規模Gammaをウィンドウ表示前に同期計算せず、CT・Ref/Eval線量Viewerを先に表示するよう修正。Gamma overlayは「Save 3D NPZ」を有効にした3D解析後に検証済みcacheから表示可能。
- Qt公式ライセンス取得元を一時的に503となるcode.qt.ioからQt公式GitHubミラーへ切り替え、固定SHA-256検証を維持したままオフラインバンドルを安定して再生成できるようにした。

## [0.9.3] - 2026-08-11

### Added
- PyMedPhys 0.41.0をCLI・batch・GUIの標準gamma engineとして選択し、Numbaを明示的なlegacy/experimental選択として保持。
- report schema version 2のprovenanceを追加し、application/Git、engine、Python/OS、UTC実行時間、入力SHA-256、gamma/shift/geometry設定をJSON・CSV・Markdown・PDF・SQLiteへ記録。
- GUIのEngine選択、`Gamma/engine`永続化、旧INIの移行警告、PyInstallerでのPyMedPhys収集設定を追加。
- Python 3.12.10 x64本体、固定wheel、リポジトリ本体を収集するWindowsオフラインバンドルビルダーを追加。
- 専用仮想環境へ通信なしで導入する `INSTALL_OFFLINE.bat`、GUI起動用バッチ、SHA-256検証、非患者合成DICOMスモークテストを追加。
- オンラインPCでのバンドル作成、USB搬送、オフライン導入、検証方法を説明する日本語ガイドを追加。

### Fixed
- shift optimizationの全候補へ最終計算と同じ`interp_fraction`を渡すよう修正。
- JSON reportの非有限値を`null`へ変換し、非標準`NaN`を出力しないstrict JSONへ変更。
- 既存の外部Python 3.12を検出した場合、同梱Pythonインストーラ起動前に安全停止するよう修正。
- オフラインpipが参照するwheelhouseパスの区切り不足を修正。
- GUIが更新する `config/gui_config.ini` を不変ファイルのチェックサム対象から除外し、再検証時の誤検出を防止。
- PyMedPhys 0.41.0の厳密なバージョン確認、DICOM geometry/endianness検証、入力スナップショットSHA-256、計算契約を含むViewer cache検証をfail-closed化。

### Validation
- Python 3.12.10でRuff合格、pytest `134 passed, 7 skipped`。Windows/Ubuntu、Python 3.10/3.11/3.12のCI matrixも合格。
- source/EXE GUI PowerShell構文、report schema/example、実RTDOSE由来ケースでの省略時PyMedPhys実行を確認。
- PR #26の最終Codex reviewで重大な問題なし、未解決review threadなしを確認。
- Python 3.12未導入のクリーンWindows PCでの初回完全導入試験は保留中。

## [0.9.1] - 2026-06-07
### Fixed
- GUI解析プロセスが無引数Pythonとして起動し、Python REPLの `>>>` 待ちで終了しない問題を修正。
- PowerShellの自動変数 `$args` との衝突を避け、`ProcessStartInfo.Arguments` に実引数を確実に渡すようにした。
- Source/Python modeでは `.venv\Scripts\python.exe` を優先して解析CLIを起動するようにした。

### Changed
- GUIログに実際の `Launching FileName` と `Launching Arguments` を表示し、起動状態を追跡しやすくした。
- READMEのGUIスクリーンショットを、3D Gamma解析完了後の画面に更新。
 
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
