# GUI 実行ガイド（rtgamma GUI）

## 目的
- GUI から Ref/Eval の RTDOSE を選択し、臨床プリセットで 2D/3D を実行。
- 実行ログ（`run_log_*.txt`）の保存とサマリ自動オープンを確認。

## 起動
- ダブルクリック: `run_gui.bat`
- または: `scripts/run_gui.ps1`

## Fast 3D Viewer
- 目的: Matplotlib/TkAgg 版3D Viewerの描画限界を超えられるか、PyQtGraph + PySide6 で検証します。
- 起動: `run_viewer_fast_test.bat`
- 依存関係: `pip install -r requirements-fast-viewer.txt`
- 範囲: Axial / Sagittal / Coronal の3断面、CT表示、5 overlay mode（Gamma / Pass-Fail / Ref Dose / Eval Dose / Dose Ratio）、共有voxel cursor、`HU / Ref / Eval` ラベル表示、Ref/Evalファイル名表示、RTSTRUCT輪郭表示、ROI別GPR表示。
- 非範囲: 画像保存、スクリーンショット保存。
- 操作:
  - マウスクリック: クリック断面上のvoxelへ共有cursorを移動。
  - マウスホイール: 操作中断面のslice indexを移動。
  - slice slider: Axial / Sagittal / Coronal を個別に移動。
  - Zoomボタン: `+` で拡大、`-` で縮小、`0` で現在断面の表示範囲をreset。
  - キーボード: カーソルキーでactive planeのslice移動、`+`/`-`で拡大縮小、`0`/`Home`でreset。
  - キーボード: `O`でoverlay表示切替、`C`でCT表示切替、`S`でStructure表示切替、`G/P/R/E/D`でGamma / Pass-Fail / Ref Dose / Eval Dose / Dose Ratioへ切替。
  - いずれの操作でも3断面のcrosshairと `HU / Ref / Eval` ラベルを同期更新。
  - Overlay alpha sliderは現在選択中のoverlay表示に作用。
  - CT / Structure / ROI checkboxで表示を切り替え。
  - Overlay radio buttonでGamma / Pass-Fail / Ref Dose / Eval Dose / Dose Ratioを切り替え。
- 安全動作:
  - `--gamma-npz` は既存Viewerと同じく `gamma` キーを基本とします。キー欠損やshape不一致ではViewer全体を落とさずGamma overlayのみ無効化します。
  - HU / Ref / Eval は個別にshape・範囲・finite確認を行い、取得できない値だけ `N/A` と表示します。
  - Cursor readoutは補間後の表示値ではなく、元voxel値を使用します。
  - RTSTRUCT overlayはLegacy Viewerと同じvoxel index / patient coordinate変換経路を使用し、Fast側の描画都合によるtransposeやaxis inversionは比較確認対象とします。
  - Fast Viewerの表示方向補正はPyQtGraph ViewBoxの表示変換で行い、voxel/readout/RTSTRUCT座標変換は変更しません。Axial左右、Sagittal/Coronal上下はLegacy/Fast比較の目視確認対象です。

## 手順
- ファイル選択
  - `Ref RTDOSE (.dcm)` と `Eval RTDOSE (.dcm)` を選択。
  - `Output Folder` に保存先ディレクトリ（例: `phits-linac-validation/output/rtgamma/Test05_gui`）を指定。
- アクション選択
  - Action: `3D (clinical preset)` または `2D (clinical preset)`（2D は Plane/Index 指定あり）。
  - 3D Viewer起動時は Viewer: `Legacy` / `Fast` を選択可能。
  - Source/Python modeとFast ZIPでは、保存済み設定がなければ既定は `Fast` です。
  - Legacy ZIPはPySide6/Qtを同梱しない軽量配布のため、保存済み設定がなければ既定は `Legacy` です。
  - `Fast` はSource/Python modeでは `.venv\Scripts\python.exe` を優先して `scripts/gamma_viewer_fast.py` を起動します。未セットアップの場合は `setup_fast_viewer_venv.bat` を実行してください。
  - Fast起動に失敗した場合は、失敗したviewer type、例外要約、ログパスを表示し、確認後にLegacyで開けます。黙ってLegacyへfallbackしません。
  - Clinical Preset: 既定は `clinical_rel`（3%/2mm/10%、norm=global_max、opt-shift=off）。
  - Optimize shift: 既定は OFF（必要時のみ ON）。
  - Threads: CPU コア数を目安（0=auto）。
- 快適オプション
  - `Open summary on finish`: ON でサマリ自動オープン。
  - `Save log to file`: ON で `run_log_YYYYMMDD_HHMMSS.txt` を出力フォルダへ保存。
  - `Local gamma`: OFF=Global（既定）/ ON=Local（厳格）。
- 実行
  - `Run` をクリック。進捗バーとログに実行状況が表示されます。

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
- Source/Python: Fast依存があればFast既定、Legacy選択可。
- Legacy ZIP: `run_gui_exe.bat` で起動。PySide6/Qtなし、Legacy既定。
- Fast ZIP: `run_gui_fast_exe.bat` で起動。`gamma_viewer_fast`、PySide6/Qt/pyqtgraphを同梱し、Fast既定。
- Fast ZIPには `NOTICE.txt`、`THIRD_PARTY_LICENSES/`、`bundled_manifest.txt` を同梱します。`qwindows.dll` はQt platform pluginとして解決可能な `platforms/qwindows.dll` 相当のパスに配置されていることをmanifestで確認します。

## 文字コード（Windows）
- Markdown/ログは UTF-8（BOMなし）推奨。文字化け回避のためエディタ設定を確認してください。

## スクリーンショット（任意）
- `docs/openspec/images/` に小さめの画像で保存してください。
  - `gui_main.png`（UI メインウィンドウ）
  - `gui_after_run3d.png`（3D 実行後、run3d.md 表示）
  - `gui_after_run2d_axial.png`（2D axial 実行後、axial.md 表示）
  - 画像は大きすぎないよう、圧縮・縮小して追加してください。

## 参照
- GUI スクリプト: `scripts/run_gui.ps1`
- バッチランチャ: `run_gui.bat`
- 設定: `config/gui_defaults.json`
