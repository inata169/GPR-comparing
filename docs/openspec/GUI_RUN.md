# GUI 実行ガイド（rtgamma GUI）

## 目的
- GUI から Ref/Eval の RTDOSE を選択し、臨床プリセットで 2D/3D を実行。
- 実行ログ（`run_log_*.txt`）の保存とサマリ自動オープンを確認。

## 起動
- Source/Python mode: `run_gui_python.bat`
- PowerShellから直接起動する場合: `scripts/run_gui.ps1`
- 配布ZIP: 同梱のGUIランチャーを使用します。

## Fast 3D Viewer
- 目的: PyQtGraph + PySide6 による高速な臨床QA向け3断面ビューアとして、GUIの3D Viewer起動経路で使用します。
- 起動: GUIの `Action: 3D Viewer`、または `run_viewer_fast_test.bat`
- 依存関係: `pip install -r requirements-fast-viewer.txt`
- 範囲: Axial / Sagittal / Coronal の3断面、CT表示、6 overlay mode（Gamma / Pass-Fail / Ref Dose / Eval Dose / Dose Diff / Dose Ratio）、共有voxel cursor、現在点readout、Ref/Evalファイル名表示、RTSTRUCT輪郭表示、ROI別GPR表示。
- 非範囲: Fileメニューからの新規DICOM読み込み、画像保存、スクリーンショット保存。
- 操作:
  - マウスクリック: クリック断面上のvoxelへ共有cursorを移動。
  - マウスホイール: 操作中断面のslice indexを移動。`Shift + wheel` で高速slice移動。
  - `Ctrl + wheel`: zoom。
  - middle drag: pan。
  - slice slider: Axial / Sagittal / Coronal を個別に移動。
  - Zoomボタン: `Zoom +` で拡大、`Zoom -` で縮小、`Fit` で全断面fit。
  - キーボード: カーソルキーでactive plane上のcursor移動、`+`/`-`で拡大縮小、`0`/`F`でreset/fit。
  - キーボード: `I`で現在点Info、`O`でoverlay表示、`C`でCT、`S`でStructureを切り替え。
  - キーボード: `G/P/R/E/X/D`でGamma / Pass-Fail / Ref Dose / Eval Dose / Dose Diff / Dose Ratioへ切替。
  - `H` / `?` でControlsを表示。
  - いずれの操作でも3断面のcrosshairと現在点readoutを同期更新。
  - Overlay alpha sliderは現在選択中のoverlay表示に作用。
  - CT / Structure / Info / ROI checkboxで表示を切り替え。
  - Overlay radio buttonでGamma / Pass-Fail / Ref Dose / Eval Dose / Dose Diff / Dose Ratioを切り替え。
- 安全動作:
  - `--gamma-npz` は既存Viewerと同じく `gamma` キーを基本とします。キー欠損やshape不一致ではViewer全体を落とさずGamma overlayのみ無効化します。
  - HU / Ref / Eval / Dose Diff / Gamma / Pass-Fail は個別にshape・範囲・finite確認を行い、取得できない値だけ `N/A` と表示します。
  - `gamma=0.0` は有効な有限値として扱います。
  - Pass/Failは有限gammaのみ対象です。`gamma <= 1.0` はPass、`gamma > 1.0` はFail、missing / nonfinite / shape mismatchは `N/A` です。
  - Ref Dose / Eval Dose overlayは有限な線量voxelを表示対象にし、Ref/Evalそれぞれ独立したDose display rangeでcolormapを正規化します。
  - Dose display rangeの既定はpositive voxelの99.5 percentileをmaxにしたauto rangeです。`Auto dose range`をOFFにすると、`Dose display min [Gy]` / `Dose display max [Gy]` に手入力した非永続rangeを使用します。入力欄は0〜100 Gyのnumeric fieldです。Ref/Eval以外のoverlay表示中も、最後に選択したdose mode（初期Ref）のrangeを操作できます。
  - invalid range（非数、inf、max <= min）は前回の有効rangeを保持し、viewerは落としません。Dose Ratioは低Ref線量域を除外します。
  - Dose Diffは `Eval Dose - Ref Dose` です。
  - Cursor readoutは補間後の表示値ではなく、元voxel値を使用します。
  - 内部cursor stateは `(z, y, x)` のarray indexを正とし、表示用の物理mm mappingとsource voxel readoutを分離します。
  - RTSTRUCT overlayは既存のvoxel index / patient coordinate変換経路を変更しません。
  - Sagittal / Coronal は元arrayを変更せず、表示用スライスだけをz方向に反転します。CT、Gamma、Pass/Fail、Ref/Eval Dose、Dose Diff/Ratio、RTSTRUCT輪郭、クリック位置、crosshair、上下カーソルキー移動は同じ表示座標系で同期します。
  - `Overall GPR` は有限gammaのみを分母にした pass/evaluated として表示します。全voxelに対する評価対象割合は `Gamma evaluated` として別表示します。
  - cutoffで除外されたvoxelの現在点Gammaは `Excluded` と表示し、Gamma未読込やshape不一致の `N/A` と区別します。
  - 今回の方向表示はHFS前提の固定orientation labelです。Axial / Coronalは表示左側を `R`、右側を `L` とします。prone / feet first / PatientPosition自動補正は対象外です。

## 手順
- ファイル選択
  - `Ref RTDOSE (.dcm)` と `Eval RTDOSE (.dcm)` を選択。
  - `Output Folder` に保存先ディレクトリ（例: `phits-linac-validation/output/rtgamma/Test05_gui`）を指定。
- アクション選択
  - Action: `3D (clinical preset)` または `2D (clinical preset)`（2D は Plane/Index 指定あり）。
  - 3D ViewerはFast Viewer固定で起動します。保存済み `viewer_type=legacy` は互換目的で残っていても起動選択には使いません。
  - Source/Python modeでは `.venv\Scripts\python.exe` を優先して `scripts/gamma_viewer_fast.py` を起動します。未セットアップの場合は `setup_fast_viewer_venv.bat` を実行してください。
  - GUIからFast Viewerを起動する場合、DD / DTA / cutoff / norm はpreset適用後の実効値を渡します。保存済み `gamma3d.npz` を開く場合も、cutoff除外readoutは解析条件と一致します。
  - Fast起動に失敗した場合は、例外要約・依存関係・ログパスを表示します。Legacy fallbackは提示しません。
  - Clinical Preset: 既定は `clinical_rel`（3%/2mm/10%、norm=global_max、opt-shift=off）。
  - Optimize shift: 既定は OFF（必要時のみ ON）。
  - Threads: CPU コア数を目安（0=auto）。
- 快適オプション
  - `Open summary on finish`: ON でサマリ自動オープン。
  - `Save log to file`: ON で `run_log_YYYYMMDD_HHMMSS.txt` を出力フォルダへ保存。
  - `Local gamma`: OFF=Global（既定）/ ON=Local（厳格）。
- 実行
  - `Run` をクリック。進捗バーとログに実行状況が表示されます。
  - v0.9.1以降は、ログに実際の `Launching FileName` と `Launching Arguments` が表示され、GUI表示コマンドと子プロセス引数のズレを確認できます。

## 自動オープンの優先順位
- 3D: `run3d.md`
- 2D: `<plane>.md`（例: `axial.md`）
- Header Compare: `header_compare.md`
- 上記が無ければ、フォルダ内の最新 `*.md` を開きます。

## 期待される出力
- Logs: `.../run_log_*.txt`（UTF-8 推奨）
- Reports: `.../run3d.{csv,json,md}` または `<plane>.{csv,json,md}`
- 2D Images: `<plane>_gamma.png`, `<plane>_diff.png`
- 3D NPZ: `gamma3d.npz`, `dose_diff3d.npz`（指定時）

## 配布モード
- Source/Python: `run_gui_python.bat` で起動。3D ViewerはFast固定。
- Fast ZIP: `run_gui_fast_exe.bat` で起動。`gamma_viewer_fast`、PySide6/Qt/pyqtgraphを同梱し、Fast固定。
- Legacy ZIP / Legacy Viewer: 実装と配布スクリプトは互換資産として残すが、v0.9.0以降のGUI 3D Viewer運用では主対象外。
- Fast ZIPには `NOTICE.txt`、`THIRD_PARTY_LICENSES/`、`bundled_manifest.txt` を同梱します。`qwindows.dll` はQt platform pluginとして解決可能な `platforms/qwindows.dll` 相当のパスに配置されていることをmanifestで確認します。

## 文字コード（Windows）
- Markdown/ログは UTF-8（BOMなし）推奨。文字化け回避のためエディタ設定を確認してください。

## スクリーンショット（任意）
- `docs/openspec/images/` に小さめの画像で保存してください。
  - `Gui-screenshot.png`（README掲載用のGUI実行完了例）
  - `gui_main.png`（UI メインウィンドウ）
  - `gui_after_run3d.png`（3D 実行後）
  - `gui_after_run2d_axial.png`（2D axial 実行後、axial.md 表示）
  - 画像は大きすぎないよう、圧縮・縮小して追加してください。

## 参照
- GUI スクリプト: `scripts/run_gui.ps1`
- Source/Pythonランチャ: `run_gui_python.bat`
- 設定: `config/gui_defaults.json`
