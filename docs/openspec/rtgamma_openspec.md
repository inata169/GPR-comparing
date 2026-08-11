# rtgamma OpenSpec (v0.9.1 - 2026-06-07版)

> **履歴仕様:** この文書は v0.9.1 までの設計・観測記録を保存しています。現在の公開正本は `README.md`、PyMedPhys標準化の現行提案は `docs/openspec/changes/pymedphys-standard-engine/` です。本文中の臨床用途を連想させる表現、3DVHの合否、症例別パラメータ調整、および商用化表現は、現在の検証済み主張または受入基準ではありません。

## 1. Overview
- Purpose: DICOM RTDOSE の幾何整合とガンマ解析（2D/3D）を、研究・教育用途で再現可能に実行するための履歴仕様。
- Scope: RTDOSE×RTDOSE比較、3D/2Dガンマ解析、シフト最適化、RTSTRUCT/ROIマスクによる部位別集計、**DVH（線量体積ヒストグラム）計算・比較**、3Dインタラクティブビューア、CSVによるバッチ一括処理、PDF帳票自動生成、解析結果のSQLite DB永続化、JSONプリセット管理、EXE実行環境の自動構成・統合。
- Future: GPU/CuPy 実装、ローカル探索、WebベースGUI、クリーンvenvによるEXE軽量化（200〜250MB目標）、PDF主軸レポート。
- PoC: Matplotlib/TkAgg 版3D Viewerの描画限界検証として、PyQtGraph + PySide6 のFast 3D Viewer PoCを追加する。既存3D Viewerの置換ではない。
- Status (2026-06-07): v0.9.1でGUI解析プロセスの引数渡しを修正した。PowerShellの自動変数 `$args` との衝突を避け、Source/Python modeでは `.venv\Scripts\python.exe` を優先する。READMEにはGUI実行完了画像とFast 3D Viewer画像を掲載済み。v0.9.0以降、GUIの3D Viewer起動経路はFast Viewer固定。
- Stakeholders: 医療物理・QA担当、研究開発者、データ提供者。

## 2. Use Cases
- 2つの線量（CCC vs MC など）を 3%/2mm/10% で比較し、GPR と差の可視化を得る。
- 幾何差（FoR/IPP/IOP/GFOV/スケール）をヘッダ比較で事前確認。
- GUI でファイル（またはフォルダ）選択・DTA/DD/Cutoff 直接入力・2D/3D 実行・サマリ自動オープンまでをワンクリックで行う。

## 3. Inputs & Outputs
- Inputs
  - DICOM: RTDOSE（LPS）。必須タグ: ImagePositionPatient, ImageOrientationPatient, PixelSpacing, GridFrameOffsetVector, DoseGridScaling。
  - CLI 主パラメータ（既定）
    - dd=3.0, dta=2.0, cutoff=10.0, gamma-type={global|local}, norm={global_max|max_ref|none}
    - mode={3d|2d}, plane={axial|sagittal|coronal}, plane-index={int|auto}
    - opt-shift={on|off}, shift-range="x:-3:3:1,y:-3:3:1,z:-3:3:1"
    - refine=coarse2fine, fine-range-mm=10, fine-step-mm=1, early-stop-*
    - prescan-2d={on|off}, interp={linear|bspline|nearest}, interp-fraction=<N>, threads=<N>
    - rtstruct=<path_to_RTSTRUCT>, roi="<roi1>,<roi2>" (オプション: ROIごとの解析)
- Outputs
  - 2D: gamma 画像（PNG/TIFF）、dose diff 画像（%）。
  - 3D: gamma（NPZ）、dose_diff_pct（NPZ）。
  - レポート: CSV/JSON/MD/PDF（スキーマ叩き台は `docs/openspec/report.schema.json`）。
    - JSONとMDには `per_structure` が含まれ、指定ROI単位での voxel_count, evaluated_count, pass_rate, mean, median, max が出力される。さらに、Ref/Eval それぞれの DVH 統計値（D95, D50等）とヒストグラムデータも保持。
    - PDFには再現性確保のため実行時パッケージバージョンとコマンド引数が印字される。
    - **DVH比較**: 各ROIごとにRef/Evalを重ね合わせたDVHグラフと指標比較テーブルが出力される。グラフ画像は `chart/` サブフォルダに保存される。
  - バッチサマリ: CSV（`batch_summary.csv` 等）、JSON、MD形式での全体集計レポート。
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

### 6.1 Normalization (norm)
ガンマ解析における `% Dose Difference (DD)` や `Cutoff (TH)` の基準（100%）を何に設定するかを定義します。
- `global_max` / `max_ref`:
  - **定義**: Reference（基準）線量データの全体における**最大線量値**を 100% として正規化します（両者は内部的に全く同じ動作エイリアスです）。
  - **用途**: 放射線治療のQAで最も一般的な設定（Global DTA/DD）。例えば最大線量が 83 Gy で 3% 許容の場合、全体一律で `83 * 0.03 = 2.49 Gy` の誤差が許容されます。
- `none`:
  - **定義**: 正規化を行わず、DICOMのピクセル値（Gyなど）そのものに対して直接 % 計算を行います。つまり `1.0 Gy` を 100% として扱います。
  - **用途**: 入力されるDICOMファイルがあらかじめ 0.0〜1.0 の相対線量としてスケーリングされているような特殊なケースでのみ使用します。絶対線量に対して使用すると極端に厳しい評価（ノイズレベルの許容差）となり、GPRが不当に低下します。

### 6.2 Gamma Type (gamma-type)
線量差の許容幅を計算する際の、空間的な基準の持ち方を定義します。
- `global` (デフォルト):
  - 全てのボクセルにおいて、前述の Normalization (例: `global_max`) で決まった**一定の線量幅**（例: 2.49 Gy）を基準として評価します。低線量域でも高線量域でも定規の目盛りは同じです。
- `local`:
  - 各ボクセル自身の**その場所の線量値**を 100% とみなし、場所ごとに異なる許容幅を使用します。例えば 50 Gy の場所の許容幅は 1.5 Gy、10 Gy の場所は 0.3 Gy となり、線量が低い領域ほど要求される精度が非常に厳しくなります。強度変調の急峻な線量勾配をシビアに検証する特殊なケースで用いられます。

## 6.3 DVH Analysis (v0.7.4 で追加)
RTSTRUCT が提供されている場合、各 ROI に対して累積 DVH を構築します。
- **計算手法**: 推奨される interp_fraction に基づき、RTDOSE グリッド上でマスクされたボクセルの線量ヒストグラムから算出。
- **抽出指標**: D98, D95, D50, D2, Mean, Max, Min。
- **比較**: Reference と Evaluation（シフト補正後）の DVH を同一チャート上にプロット。凡例にはそれぞれの DICOM ファイル名を表示。
- **可視化**: 出力先ディレクトリの `chart/` フォルダに PNG 形式で保存。

## 7. Shift Optimization
- coarse→fine の二段探索。fine は `±(fine-range-mm)` を `fine-step-mm` で走査する標準的2段階探索。
- 探索順序: 中心（原点、またはベストシフト位置）から外側へ向かうように距離順 (Magnitude) でソートして実行。
- 早期停止: パス率の改善幅が `epsilon` 未満の状態が `patience` 回続いた場合、無駄な探索を打ち切る (Early stop)。
- 2D プリスキャン: 中央スライスで XY 範囲を狭めて 3D 探索の初期領域を短縮。

## 8. Performance & Accuracy
- 性能
  - 2D（opt-shift=off）: スライス限定の高速経路。
  - 3D: Numba JIT + `--threads` で並列。初回は JIT によりウォームアップが必要。
  - **高速化方針（2026-03-12 完了）**: ノン補間・補間両モードにおいて「距離順探索（中心から外側へ螺旋状に探索）」と「Early Exit（ガンマ1以下で即時終了）」を実装。ノン補間モードで約2.6倍、補間モードで約1.1倍の高速化を達成。GPR並列計算のメモリバス負荷を低減。
  - **描画性能**: Structure が多い場合の `plt.plot()` ループは遅いため `LineCollection` で一括描画し高速化。さらに `viewer_settings.json` による座標や可視性の永続化をサポート。
  - **Fast 3D Viewer**: `scripts/gamma_viewer_fast.py` はPyQtGraph + PySide6による高速3断面Viewerであり、v0.9.0以降のGUI 3D Viewer起動経路で固定使用する。既存 `scripts/gamma_viewer.py` はLegacy Viewerとして残す。
  - **GUI解析プロセス起動**: v0.9.1以降、`ProcessStartInfo` へ渡す引数は文字列 `Arguments` として明示設定する。PowerShell自動変数 `$args` と衝突しない変数名を使用し、ログに実際の `FileName` と `Arguments` を出力する。
    - 範囲は3断面、CT grayscale、6 overlay mode（Gamma / Pass-Fail / Ref Dose / Eval Dose / Dose Diff / Dose Ratio）、共有voxel cursor、現在点readout、Ref/Evalファイル名、RTSTRUCT輪郭、ROI別GPR表示。
    - 内部カーソルは voxel index `(z, y, x)` とし、Axial / Sagittal / Coronal の3断面で共有する。HU / Ref Dose / Eval Dose / Dose Diff / Gamma / Pass-Fail のreadoutは補間後の表示値ではなくsource voxel arraysから取得する。
    - `gamma=0.0` は有効な有限値とする。Pass/Failは有限gammaのみで判定し、missing / nonfinite / shape mismatchは `N/A` とする。Dose Diffは `Eval Dose - Ref Dose` とする。
    - RTSTRUCT overlayは既存の voxel index / patient coordinate変換経路を変更しない。Fast描画の物理mm mappingは表示専用layerとし、source voxel readoutとは分離する。
    - Sagittal / Coronal は元arrayを変形せず、物理mm座標extentとViewBox aspect lockで1:1表示する。方向表示はHFS前提の固定orientation labelとし、PatientPosition自動補正は対象外。
    - 操作は、クリックで共有cursor移動、ホイールでslice移動、`Shift + wheel`で高速slice移動、`Ctrl + wheel`でzoom、middle dragでpan、各断面sliderでslice移動とする。キーボードはカーソルキーでactive plane上のcursor移動、`+`/`-`で拡大縮小、`0`/`F`でreset/fit、`I`でInfo、`O`でoverlay、`C`でCT、`S`でStructure、`G/P/R/E/X/D`でoverlay mode切替とする。`H` / `?` はHelp表示。
    - OverlayはCTとは別ImageItemとし、NaN/inf/未計算領域を透明扱い、alpha sliderは選択中のoverlayに作用する。
    - `--gamma-npz` は既存Viewerと同じ `gamma` キーを基本とし、キー欠損やshape不一致ではViewer全体を落とさずGamma overlayのみ無効化する。
    - HU / Ref / Eval は個別に欠損・shape不一致・範囲外・非finiteを確認し、取得できない値だけ `N/A` と表示する。Dose単位は表示上 `Gy` とする。
    - 非範囲: 画像保存、スクリーンショット保存。
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

## 9.3 外部商用システム (Sun Nuclear 3DVH) との過去の探索的比較

**実施日**: 2026-03-05 / **パラメータ**: 3.0% / 2.0mm / 10% Cutoff / Global Max / interp_fraction=10

| Case | rtgamma GPR | 3DVH GPR | Δ (pp) |
|---|---|---|---|
| Prostate CCC vs MC | 85.82% | 84.7% | +1.12 |
| BreastBolus CCC vs MC | 99.59% | 97.6% | +1.99 |

- 詳細レポート: `output/3dvh_crossval/crossval_summary.md`
- この表は履歴上の観測値であり、臨床的クロスバリデーション、受入合格、同等性、精度保証、またはvendor endorsementを示しません。公開リポジトリには入力DICOM、3DVHの完全な出力・version・手順、実行時メタデータが揃っておらず、現状では再現可能な検証結果として扱えません。
- `scripts/run_interp_experiment.py` は過去に症例ごとに3DVHとの差を小さくする `interp_fraction` を探索しました。この方法は今後の固定条件比較では禁止し、下表の値は標準設定または受入根拠として使用しません。

  | Case | 最適 interp_fraction | rtgamma GPR | 3DVH GPR | Δ (pp) |
  |---|---|---|---|---|
  | Prostate | **3** | 85.26% | 84.7% | +0.56 |
  | BreastBolus | **2** | 97.73% | 97.6% | +0.13 |


## 10. Security & Privacy
- PHI を含む DICOM はリポジトリへコミット禁止。匿名化サンプルのみ使用。
- 大容量バイナリ・生成物はコミットせず、出力フォルダに保存。

## 11. Open Questions & Constraints
- Coronal GPR の回帰現象（~82% vs ~93%）の要因切り分け（正規化・平面整合・スライス選択）。
- ROI/RTSTRUCT マスクの仕様（v1.0で実装済: 輪郭ポリゴンからの3Dマスク生成と `per_structure` 集計）。
- 将来的な GPU バックエンド（CuPy）の互換要件。

## 12. Versioning & Change Control
- 本仕様の版: v0.1（初稿）。変更時は本ヘッダと `CHANGELOG.md` を更新し、設計判断は `DECISIONS.md` に ADR として追記。
- 実装-仕様の差分は `docs/openspec/report.schema.json` と `rtgamma/main.py` の出力フィールドで相互検証。

## 13. References (Code/Docs)
- CLI/入出力・実行: rtgamma/main.py
- DICOM I/O・幾何: rtgamma/io_dicom.py
- レポート出力: rtgamma/report.py, scripts/pdf_report.py
- GUI: scripts/run_gui.ps1, run_gui_python.bat, config/gui_defaults.json (ダークテーマ、直接数値入力、ログ領域拡大、PDF出力設定、マウスオーバーツールチップ)
  - 設定読み込みは `scripts/gui_config_common.ps1` で共通化する。`viewer_type` は互換目的で残すが、3D Viewer起動時は常にFastを使用する。
  - 3D Viewer起動はFast固定。`Analysis/viewer_type=legacy` が保存済みでもFastを起動する。
  - Fast起動失敗時は、例外要約、依存関係、ログパスを表示してGUIへ戻す。Legacy fallbackは提示しない。
  - EXE運用: PyInstaller ビルドスクリプト `scripts/build_exe.ps1` と `.spec` ファイルによるビルド。Legacy ZIPは軽量配布、Fast ZIPは `gamma_viewer_fast` とPySide6/Qt/pyqtgraphを同梱する大容量配布として分離する。
  - Fast ZIPはPyInstaller onedirで作成し、Qt/PySide6バイナリは改変しない。`NOTICE.txt`、`THIRD_PARTY_LICENSES/`、`bundled_manifest.txt` を同梱し、`qwindows.dll` がQt platform plugin pathにあること、GPL-only Qt modules/pluginsが意図せず同梱されていないこと、PySide6/Qt componentsがLegacy ZIPに入っていないことをmanifestで確認する。
- 運用: AGENTS.md, TEST_PLAN.md, TROUBLESHOOTING.md, CHANGELOG.md, DECISIONS.md
- 3Dビューア: scripts/gamma_viewer.py (Axial/Sagittal/Coronal同期2x2マルチプレーン, 3Dカーソル, Slice GPR表示, 設定永続化, 5モード: Gamma/Pass-Fail/Ref Dose/Eval Dose/Dose Ratio, CT+Structure重畳, カラーバー, ファイル名表示, 物理アスペクト比対応, Axial医療慣習表示)
- Fast 3D Viewer: scripts/gamma_viewer_fast.py (PyQtGraph + PySide6, 3断面CT/overlay表示, 共有voxel cursor, HU/Ref/Eval/Diff/Gamma/Pass-Fail readout, Ref/Evalファイル名表示, RTSTRUCT輪郭, ROI別GPR, 6 overlay mode, Info toggle, menu bar, physical-mm display mapping, HFS orientation labels, GUI 3D Viewer起動経路でFast固定)
- 設定・DB: config/presets.json, rtgamma.db (SQLite)

## 14. Historical feature roadmap（旧機能ロードマップ）
以下は過去の開発計画の要約であり、臨床QAソフトウェア、商用品質、または検証完了を意味しません。詳細は履歴資料 `docs/feature_roadmap.md` にあります。
- **Tier 1: コア品質と信頼性 (Completed)**: バッチ処理一括化（`batch.py`）、PDFQA帳票自動生成（`pdf_report.py`）、RTPLANヘッダ統合、CIテストカバレッジ強化（E2E JSONSchema検証・合成データ回帰テスト）
- **Tier 2: ユーザー体験の飛躍 (Completed)**: Web GUI設計、マルチプレーン連動ビューア（**Axial/Sagittal/Coronal同期・Slice GPR表示・設定永続化完了**）、SQLトレンド保存・プリセット管理、GUI ワンクリックPDF対応（完了）、GUI設定解説ツールチップ実装（完了）
- **Tier 3: 高度解析機能**: ガンマヒストグラム、過去の3DVH探索比較、症例別interp_fraction感度実験、Numbaカーネル高速化、探索的DVH指標などの履歴。3DVH比較と症例別調整は現行の検証完了事項ではありません。
- **Tier 4: 運用エコシステム**: `.exe` バイナリビルド同梱と GUI 統合連携（完了）、最小構成ZIPパッケージ生成・配布対応（完了）、**EXE容量の本格削減**（クリーンvenv + exclude + UPX で200〜250MB目標）、**出力形式PDF主軸化**（MD→PDF移行）、完全日英多言語対応、コンプライアンス準拠
