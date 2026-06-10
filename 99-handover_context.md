# 記憶の引き継ぎ書: Handover Context (2026-06-10 Fast Viewer表示整合性修正後)

## 1. 現在の進捗状況 (Current Progress)

### 本セッション (23) で完了したこと
- **Fast 3D Viewer 表示整合性修正**:
    - Sagittal / CoronalのCT画像がSI方向でorientation labelと逆に見える問題を修正した。
    - 表示用スライスをz方向に反転し、CT、Gamma、Pass/Fail、Ref/Eval Dose、Dose Diff/Ratio、RTSTRUCT輪郭、クリック位置、crosshairを同じ表示座標系へ統一した。
    - Sagittal / Coronalの上下カーソルキー移動を表示方向に合わせ、上キーでS方向、下キーでI方向へ移動するようにした。
- **GPR表示修正**:
    - `Overall GPR` は有限gammaのみを分母にした pass/evaluated として表示し、`run3d.pdf` の `pass_rate_percent` と一致する。
    - 全voxelに対する評価対象割合は `Gamma evaluated` として別表示に分離した。
    - cutoff除外voxelは現在点readoutで `Excluded` と表示し、Gamma未読込の `N/A` と区別する。
- **検証**:
    - `python -m pytest tests/test_fast_viewer_helpers.py -q`: `9 passed`
    - `temp/gamma3d.npz` で `Overall GPR: 99.06% (121016/122163)` と `Gamma evaluated: 122163/3372033 (3.623%)` を確認。
    - EXEビルドは実施していない。Source/Python modeの `scripts/gamma_viewer_fast.py` が対象。

### 現在の正本
- main: `origin/main` からブランチを切ってPR化予定。
- 未コミット変更: `config/gui_config.ini` はGUI操作由来のユーザー状態なので触らない。

### 本セッション (22) で完了したこと
- **GUI解析プロセス起動修正**:
    - GUIから3D/2D/Header解析を起動すると、表示ログ上は `python.exe -u -m rtgamma.main ...` だが実際には無引数Python REPLが起動し、`>>>` 待ちでタスクが終わらない問題を修正した。
    - 原因はPowerShellの自動変数 `$args` と `Set-ProcessArguments` の仮引数名衝突。
    - `scripts/run_gui.ps1` / `scripts/run_gui_exe.ps1` で仮引数を `$procArgs` に変更し、`ProcessStartInfo.Arguments` へ明示設定するようにした。
    - Source/Python modeでは `.venv\Scripts\python.exe` を優先して `rtgamma.main` を起動する。
    - GUIログへ `Launching FileName` / `Launching Arguments` を出すようにした。
- **検証**:
    - `ProcessStartInfo` 経由の `rtgamma.main --help` がCLIとしてExit 0で終了することを確認。
    - 合成DICOM-RTデータで3D Gamma / 2D axial / Header compareを確認。
    - `pytest -q`: `29 passed, 7 skipped, 6 warnings`。
- **Docs / Release / PR**:
    - READMEにGUI実行完了画像とFast 3D Viewer画像を追加。
    - `CHANGELOG.md` / `README_JA.md` / `TODO.md` / `docs/openspec/GUI_RUN.md` / `docs/openspec/rtgamma_openspec.md` をv0.9.1内容へ更新。
    - `v0.9.1` tagをpushし、ユーザーがGitHub Releaseを手動公開。
    - PR #16 `docs: add Fast 3D Viewer screenshot` を作成し、squash merge済み。

### 現在の正本
- main: `9baa8b9` (`docs: add Fast 3D Viewer screenshot`)
- tag/release: `v0.9.1`
- GitHub Release: `https://github.com/inata169/GPR-comparing/releases/tag/v0.9.1`
- PR #16: `https://github.com/inata169/GPR-comparing/pull/16` merged
- 未コミット変更: `config/gui_config.ini` のみ。GUI操作由来のユーザー状態なので触らない。

### 次回の注意点
- Fast ZIP / Python未インストールWindows環境での配布確認は未完了。
- EXE容量削減は別Issueとして扱う。
- 実データでFast Viewerのorientation label、physical coordinate表示、ROI contour表示を追加確認する。

### 本セッション (21) で完了したこと
- **Fast Viewer一本化**:
    - GUIの3D Viewer起動経路はFast Viewer固定になった。
    - 保存済み `viewer_type=legacy` が残っていてもFast Viewerを起動する。
    - Legacy Viewer実装と既存packaging scriptsは削除していない。
    - Fast Viewer起動失敗時はLegacy fallbackを提示せず、依存関係・失敗理由・ログパスを表示してGUIへ戻れる。
    - Output Folder空欄時の `gamma3d.npz` 探索をskipし、空白を含むWindows pathは `ProcessStartInfo` の引数要素として扱う。
- **Fast Viewer Phase 1 UI改善**:
    - Info表示はcheckboxと `I` キーでON/OFF可能。
    - 右下パネルをData / Display / ROI visibility / Overlay / Zoomに整理。
    - `File` / `View` / `Help` メニューを追加。Fileは読み込み情報確認のみで、新規DICOM読み込みは未実装。
    - `Ctrl + wheel` zoom、middle-drag pan、`F` fit、`H` / `?` help、`0` resetを整理。
    - Sagittal / Coronalは物理mmスケール1:1表示。HFS前提のorientation labelを各planeに表示。
    - ユーザー手動確認後、Axial / CoronalのRL表示向きを反転修正してOK確認済み。
- **現在点readout / overlay改善**:
    - 表示項目は voxel index、physical coordinate、HU、Ref Dose、Eval Dose、Dose Diff、Gamma、Pass/Fail。
    - readoutはsource voxel arraysから `(z, y, x)` で取得し、display-interpolated image値は使わない。
    - `gamma=0.0` は有限な有効値として扱う。
    - Pass/Failは有限gammaのみ対象。missing / nonfinite / shape mismatchは `N/A`。
    - `Dose Diff = Eval Dose - Ref Dose` overlayを追加。
- **合成DICOM-RT検証データ**:
    - `scripts/create_synthetic_dicom_rt_dataset.py` を追加。
    - synthetic CT series、Ref RTDOSE、Eval RTDOSE、optional RTSTRUCTを `test_data_local/` に生成する。
    - patient情報は完全ダミー。生成物はgitignore対象でコミットしない。
- **Docs / Release / Branch cleanup**:
    - READMEにFast Viewerスクリーンショットと現行操作説明を反映。
    - TEST_PLAN / OpenSpec / handover / daily summaryをFast固定方針へ更新。
    - PR #15を作成・マージし、CIのRuff import orderingを追加修正。
    - Release `v0.9.0` を公開済み。
    - 不要なremote branchを削除し、remote branchは `main` のみ。

### 現在の正本
- main: `2bd0688` (`fix(ci): satisfy ruff for synthetic data script`)
- tag/release: `v0.9.0`
- GitHub Release: `https://github.com/inata169/GPR-comparing/releases/tag/v0.9.0`
- 今日のFast Viewer実装が正。昨日までのPoC/選択式/個別fix branchは不要として整理済み。

### 次回の注意点
- Fast ZIPの別PC確認、Python未インストールWindows確認、EXE容量削減は別イシュー扱い。
- DICOM座標変換、gamma calculation、dose resampling、RTSTRUCT loadingは今回触っていない。
- Fast Viewerの表示座標改善とsource voxel readoutは分離している。内部cursor stateは `(z, y, x)` のarray indexを正とする。

### 本セッション (20) で完了したこと
- **Fast Viewer既定化・選択式運用**:
    - `scripts/gui_config_common.ps1` を追加し、`Read-GuiDefaults` / `Read-GuiConfig` / `Merge-GuiConfig` / `Resolve-ViewerType` を共通化。
    - Source/Python modeは保存設定なしでFast既定、Legacy ZIPは保存設定なしでLegacy既定、Fast ZIPはFast既定。
    - 保存済み `viewer_type=legacy|fast` は尊重。欠損・不正値では現在起動のみmode別fallbackし、警告/ログを出す。INIはSave Settings時のみ正規化値を保存。
    - Fast起動失敗時は、失敗したviewer type、例外要約、ログパスを表示し、確認後にLegacyで開ける導線を追加。
- **Fast EXE / Fast ZIP配布準備**:
    - `gamma_viewer_fast.spec` を追加。PyInstaller onedirでFast Viewerをビルドする方針。
    - `run_gui_fast_exe.bat` を追加し、`scripts/run_gui_exe.ps1 -DistributionMode FastZip` を起動。
    - `scripts/build_exe.ps1 -FastViewer` でFast Viewer EXEを追加ビルド可能にした。
    - `scripts/package_release.ps1 -DistributionMode Legacy|Fast` に分離。Fast ZIPでは `NOTICE.txt`、`THIRD_PARTY_LICENSES/`、`bundled_manifest.txt` を生成。
    - Fast ZIP manifestで `platforms/qwindows.dll` 配置、GPL-only Qt module/plugin混入、Legacy ZIPへのPySide6/Qt混入を確認する処理を追加。
- **Fast ZIP実ビルド・manifest確認**:
    - `run_gui_python.bat` はユーザー手動確認でOK。
    - `scripts/build_exe.ps1 -FastViewer` で `dist/gamma_viewer_fast` を生成済み。
    - 初回Fast buildはsandbox権限で `build/gamma_viewer_fast` 作成に失敗したため、権限付きで再実行して成功。
    - PyInstaller過剰収集で `QtGraphs` / `QtQuick3D` / `QtVirtualKeyboard` 系が検出されたため、`gamma_viewer_fast.spec` を絞り込み、Fast ZIP stagingから不要Qt pluginを除去する処理を追加。
    - Windows PowerShell 5.1対応として `bundled_manifest.txt` の相対パス生成を `System.Uri.MakeRelativeUri` に変更。
    - `scripts/build_exe.ps1` は `Invoke-Checked` で外部コマンド失敗を検出するよう修正。
    - `release_staging/rtgamma_v0.7.0_fast_windows_x64.zip` 生成済み（約677.1MB）。
    - `release_staging/rtgamma_v0.7.0_windows_x64.zip` 生成済み（約423.4MB）。
    - Fast ZIP内に `NOTICE.txt`、`THIRD_PARTY_LICENSES/`、`bundled_manifest.txt` が存在。
    - Fast ZIP内の `qwindows.dll` は `dist/gamma_viewer_fast/_internal/PySide6/plugins/platforms/qwindows.dll` に配置。
    - manifest review対象のGPL-only候補（`QtGraphs`, `QtHttpServer`, `QtLocation`, `QtNetworkAuth`, `QtQuick3D`, `QtVirtualKeyboard`）は0件。
    - Legacy ZIPへのPySide6/Qt/qwindows混入は0件。
- **ドキュメント更新**:
    - README / OpenSpec / TEST_PLAN にSource/Python・Legacy ZIP・Fast ZIPの既定Viewer差を記録。
    - PySide6/QtはMITではないこと、pyqtgraphはMITであること、Fast ZIPでは第三者ライセンス通知とmanifest確認が必要であることを記録。
    - Legacy/Fast比較では、readoutを元voxel値から取得し、RTSTRUCT overlayはLegacyと同じ座標変換経路を使う方針を記録。
- **Fast Viewer表示方向・操作性修正**:
    - 別PCのFast ZIP確認で、Axi/Cor/Sag画像が小さく見え、クリック位置と画像が合わない事象を確認。
    - `scripts/gamma_viewer_fast.py` にZoomボタン、`+`/`-`/`0` キー、カーソルキーslice操作、overlay/CT/Structure/overlay modeショートカットを追加。
    - Sagittal / Coronal の上下反転と Axial の左右反転を、voxel/readout/RTSTRUCT座標変換は変更せず、PyQtGraph ViewBoxの表示変換のみで補正。
    - 修正後の検証は `py_compile`、`ruff`、代表pytestまで完了。別PCのFast ZIP再確認は未完了。
    - `dist/gamma_viewer_fast/gamma_viewer_fast.exe` と `release_staging/rtgamma_v0.7.0_fast_windows_x64.zip` は修正後に再生成済み。ZIP内の `NOTICE.txt`、`THIRD_PARTY_LICENSES/`、`bundled_manifest.txt`、`qwindows.dll` 配置、GPL-only候補0件を確認済み。
- **README改訂と作業終了処理**:
    - `README.md` にFast Viewer既定化、Legacy/Fast選択式運用、Source/Python・Legacy ZIP・Fast ZIPの違いを追記。
    - Fast Viewer操作（クリック、ホイール、slider、Zoom、キーボードショートカット）と表示方向補正の方針をREADMEへ反映。
    - Fast ZIPのPyInstaller onedir配布、第三者ライセンス通知、PySide6/QtはMITではないことをREADMEへ明記。
    - 作業終了ルールに従い、TODO、日次サマリ、引き継ぎ、OpenSpec関連記録を更新してコミットする。

### 本セッション (19) で完了したこと
- **3D Viewer軽量高速化PRの完了**:
    - PR #6 `feat(viewer): 3Dビューアに軽量キャッシュを追加` をmainへマージ。
    - `--cache-radius`、overlay cache、structure cacheを追加。表示仕様・座標仕様・CT Window/Levelは変更しない方針を維持。
- **クロスポイント値表示の完了**:
    - PR #7 `feat(viewer): クロスポイントにHUと線量を表示` をmainへマージ。
    - 各断面のcrosshair交点に `HU / Ref / Eval` を表示。strict shape matching、個別 `N/A`、Dose単位 `Gy` 表示に対応。
- **PyQtGraph版 Fast 3D Viewer PoC の追加**:
    - PR #8 `feat(viewer): PyQtGraph版Fast 3D Viewer PoCを追加` をmainへsquash merge。
    - 追加ファイル: `scripts/gamma_viewer_fast.py`, `requirements-fast-viewer.txt`, `run_viewer_fast_test.bat`, `setup_fast_viewer_venv.bat`。
    - `.venv` 環境でFast Viewerを起動できるよう整備。
    - 既存 `scripts/gamma_viewer.py`, `run_viewer_test.bat`, `run_gui_exe.bat` は変更なし。
- **CI対応**:
    - PR #8 初回CI失敗は `ruff` のimport orderingが原因。
    - `scripts/gamma_viewer_fast.py` のimport順を修正し、6 checks成功を確認。
- **次Issue作成**:
    - Issue #9: `Fast 3D Viewer PoC: 断面方向と旧Viewer比較の検証` を作成。
- **Issue #9 断面方向・同期検証の完了**:
    - `run_viewer_test.bat` と `run_viewer_fast_test.bat` を同一PROSTATEデータで比較。
    - Fast Viewer側で axial のY方向を旧Viewer (`origin='upper'`) に合わせ、Gamma overlay の NaN/inf 色変換warningも抑制。
    - 目視確認で「臨床で普段扱うビューア相当の速度感」「Axi/Cor/Sag のスクロールも問題なし」と判断。
    - 既存 `scripts/gamma_viewer.py`, `run_viewer_test.bat`, `run_gui_exe.bat` は変更なし。
- **Fast Viewer旧Viewer相当サイドバー機能の追加**:
    - Fast ViewerにRef/Evalファイル名、CT/Structure/ROI checkbox、Criteria/Cutoff、ROI GPR[%]表示を追加。
    - overlay modeを `Gamma`, `Pass/Fail`, `Ref Dose`, `Eval Dose`, `Dose Ratio` へ拡張。
    - `--rtstruct` / `--roi` に対応し、`run_viewer_fast_test.bat` でPROSTATE RTSTRUCTを渡すよう更新。
    - 旧Viewerと既存GUIランチャーは変更なし。次は既存GUIへどう統合するかを判断する段階。
- **Fast Viewer UI修正**:
    - 画像クリックがImageItem/ROI描画に遮られてcrosshairへ反映されない問題に対し、PyQtGraph scene clickでもcursor更新するよう補強。
    - 右サイドバーを廃止し、Ref/Evalファイル名・Structure/ROI・Overlay・ROI GPR表示を右下パネルへ移動。
    - Overlay radio button / checkbox のindicatorを大きく色付きにして、選択状態を視覚的に分かりやすく修正。
    - 追加修正: CT/overlayのImageItem自体にもclick handlerを持たせ、画像上のクリックを直接crosshair更新へ流すよう補強。右下パネルのStructure/ROI/Overlayの文字サイズ・フォントをROI GPRと同じmonospace小サイズへ統一。
    - クリック不反応の原因調査: PyQtGraphのGraphicsScene内でImageItem/overlay/ROI itemが前面にある場合、ViewBox/scene click handlerだけでは実画面クリックを安定して拾えない。`GraphicsLayoutWidget.viewport()` にeventFilterを追加し、QtのMouseButtonPressを最前段で捕捉してcursor更新へ流すよう修正。
    - Sagittal/Coronal画面のwheel方向を反転。トラックボールUp/Down時のcrosshair移動が臨床操作の体感と一致するよう調整。
- **Fast Viewerの既存GUI選択式統合**:
    - `scripts/run_gui.ps1` と `scripts/run_gui_exe.ps1` に `Viewer: Legacy / Fast` コンボを追加。
    - 既定は Legacy。Fast選択時は `.venv\Scripts\python.exe` を優先し、無ければ `python` で `scripts/gamma_viewer_fast.py` を起動。
    - INI保存時に `Analysis/viewer_type = legacy|fast` を保存し、次回起動時に復元。
    - EXE版GUIでもFast選択は可能だが、Fast Viewer単体EXEは未作成のためPython/venvが必要。
    - `run_gui_python.bat` を追加し、Python/source mode GUIを明示的に起動可能にした。
    - `scripts/run_gui.ps1` をUTF-8 with BOMへ変換し、Windows PowerShellの `-File` 実行で日本語ツールチップが文字化けして構文エラーになる問題を修正。

### 本セッション (18) で完了したこと
- **リポジトリ同期とCI安定化 (v0.8.7)**:
    - **GitHub同期**: GPR-comparing および dicom-phits_inp の両リポジトリを最新化し、v0.8.7 タグを反映。
    - **CI復旧**: `config/gui_config.ini` の不正な `action` 値を `3D Viewer` へ戻し、`ruff --fix` による Lint エラーを一掃。CI パスを確認。
- **外部連携ガイドの追加**:
    - `AGENTS.md` 等に外部ツールからのシームレスな起動（INI連携）に関するプロトコルを追記。

### 本セッション (17) で完了したこと
- **ポータブル実行環境（EXE版GUI）の構築と安定化**:
    - **新ランチャー**: Python環境に依存せず、常に `dist/` 内のEXEを優先して使用する `run_gui_exe.bat` および `scripts/run_gui_exe.ps1` を実装。
    - **エンコーディング修正**: PowerShell 実行時の「メソッド呼び出し内に ')' が存在しません」等の解析エラーを、ファイルを UTF-8 with BOM で保存し直すことで解消。日本語ツールチップを維持したまま安定動作を実現。
    - **Viewer連携修正**: EXE版から 3D Viewer を起動する際、正しく `gamma_viewer.exe` を絶対パスで叩くように修正。
- **配布用ポータブルパッケージ (v0.8.0) の作成**:
    - `temp/v080` フォルダに必要な EXE、スクリプト、設定ファイルを統合。他PCへのコピー＆ランが可能な状態に整理。

### 本セッション (16) で完了したこと
- **DVH（線量体積ヒストグラム）計算・比較機能の実装**:
    - 各ROIごとのDVH計算（D95, D50等）。
    - PDFレポートへのDVH比較グラフと統計テーブルの追加。
- **EXEビルドの更新と動作確認**:
    - `build_exe.ps1` を更新し、DVHとPDFレポート機能を含んだ最新のEXEを生成・検証済み。

### 本セッション (15) で完了したこと
- **Git リポジトリの健全化と履歴クリーンアップ**:
    - **履歴整理**: 過去のコミットに混入していた巨大なビルド成果物 (`dist/`, `build/`) を `git reset` により履歴から完全に除去。Pushサイズを数百MBから数MBへ正常化。
    - **.gitignore 強化**: `temp/`, `release_staging/` および解析中の一時ファイルを追記し、再発を防止。
- **CI パイプラインの復旧 (Ruff 準拠)**:
    - **Lint 修正**: インポート順序の自動修正 (`ruff --fix`) および `bare except` の解消。
    - **テスト修正**: CLI の引数変更 (`--pdf` 廃止 -> デフォルト化) に伴う E2E テストの失敗を修正。
- **マルチプレーンビューアの実装完了**:
    - スクロールバー・数値入力同期・向きの正位化。
- **DVH（線量体積ヒストグラム）計算・比較機能の実装**:
    - 各ROIごとのDVH計算（D95, D50等）。
    - PDFレポートへのDVH比較グラフと統計テーブルの追加。
- **EXEビルドの更新と動作確認**:
    - `build_exe.ps1` を更新し、DVHとPDFレポート機能を含んだ最新のEXEを生成・検証済み。

### 本セッション (14) で完了したこと
- **マルチプレーンビューアの操作性・正確性の向上**:
    - **UI**: 各断面に**スクロールバー (Slider)** および**物理位置（mm）・インデックス入力 (TextBox)** を追加。表示の視認性も改善。
    - **表示**: サジタル・コロナル面の上下（Sup-Inf）の向きを正位化（頭部が上側）。クロスカーソルの同期ロジックもこれに合わせて修正。
    - **高速化**: 描画の差分更新、アキシャル輪郭データのキャッシュ。構造物が多い場合の描画遅延を大幅に削減。
- **2D Gamma 解析のクラッシュ修正**:
    - **バグ**: RTSTRUCT マスク適用時に発生していた `IndexError` を解消（断面に合わせたマスクのスライス処理を導入）。
- **GUI ランチャーの最適化**:
    - ビルド済みの古い EXE よりも、開発中の最新 Python ソースコードを優先実行するよう `run_gui.ps1` を調整。

### 本セッション (13) で完了したこと
- **GPR計算エンジンの極限高速化**:
    - **アルゴリズム**: 探索順序を「中心からの距離順」にソートし、`Early Exit` (gamma <= 1.0) を最短手数で発生させるリファクタリングを実施。
- **解析レポートの PDF 主軸化**:
    - **機能**: `main.py` のデフォルト出力を PDF 形式に変更。PDF に詳細なガンマ統計（Mean, Median, Max, P95, P99）を追加。

### 安定動作確認済みコマンド
```powershell
# ベンチマークによる性能確認
$env:PYTHONUTF8=1; python temp/benchmark_gamma.py
```

## 2. 保留中のタスク (Pending Tasks)

| 優先度 | タスク | Tier | 備考 |
|---|---|---|---|
| 1 | **Python未インストールWindows環境でのFast ZIP確認** | 2 | `run_gui_fast_exe.bat` からFast Viewerが起動し、Qt platform plugin errorがないことを確認。 |
| 2 | **Fast Viewerの実運用前最終確認** | 2 | PROSTATEデータで再起動し、`gamma=0` overlayと古い/別grid `gamma3d.npz` + RTSTRUCT起動を確認。 |
| 3 | **GUI経由の運用確認** | 2 | `run_gui_python.bat` からViewer既定Fast、Legacy / Fast切替、Fast失敗時のLegacy導線を確認。 |
| 4 | **クリーンWindows確認** | 2 | Python未インストール環境でFast ZIPの `run_gui_fast_exe.bat` からFast Viewerが起動することを確認。 |
| 5 | **修正後Fast ZIPの再確認** | 2 | 別PCでAxi左右、Sag/Cor上下、クリック位置、Zoom、キーボード操作、PROSTATE比較を確認。 |
| 6 | **EXE容量の削減** | 4 | クリーンな venv 構築スクリプトと PyInstaller exclude 設定の精査。 |
| 7 | **不確かさの推定** | 3 | 公称値だけなく、ブートストラップ法などによる解析精度の提示。 |
| 8 | **Webベース GUI 試作** | 2 | ブラウザベースのインターフェース検討。 |

## 3. 次のセッションで実行すべきこと
1. **Python未インストールWindows環境でのFast ZIP確認**:
    - `release_staging/rtgamma_v0.7.0_fast_windows_x64.zip` を展開する。
    - `run_gui_fast_exe.bat` からFast Viewerが起動し、Qt platform plugin errorが出ないことを確認する。
2. **Fast Viewerの最終確認**:
    - PR #11 / #12 の修正後に、PROSTATEデータでFast Viewerを再起動する。
    - Gamma overlayで `gamma=0` 領域が消えないことを確認する。
    - 古い/別gridの `gamma3d.npz` でもRTSTRUCT付き起動で落ちないことを確認する。
3. **GUI経由の運用確認**:
    - `run_gui_python.bat` でGUIを起動する。
    - Viewerを `Fast` にして3D Viewerを起動する。
    - Legacy / Fast の切替が期待通り動くか確認する。
4. **検証コマンド**:
    - `python -m ruff check rtgamma/ tests/ scripts/`
    - `python -m pytest tests/test_gamma_3d_quick.py tests/test_coord_roundtrip.py tests/test_io_monotonic.py`
    - `git diff -- scripts/gamma_viewer.py run_viewer_test.bat run_gui_exe.bat`

## 4. 補足情報
- Fast Viewer PoCは「めちゃくちゃ速い」「普段臨床で扱っているものと同様」「文句なし」と目視評価済み。Axi/Cor/Sag のスクロールも問題なし。旧Viewer相当のサイドバー表示と5 overlay modeもFast Viewer側へ追加済み。
- `.venv` は `.gitignore` に追加済み。Fast Viewerの依存関係は `setup_fast_viewer_venv.bat` で導入可能。
- Fast Viewer既定化の方針は、Source/PythonとFast ZIPはFast既定、Legacy ZIPはLegacy既定。Legacy/Fast選択式は維持。
- Fast ZIPはPySide6/Qt/pyqtgraph同梱の大容量配布。アプリ本体はMITだが、同梱第三者コンポーネントは各ライセンスに従う。
- READMEは2026-06-05終了時点のFast Viewer運用方針と配布方針へ更新済み。
- `C:\Users\...\ .config\git\ignore` の Permission denied 警告はリポジトリ差分ではない。
