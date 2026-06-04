# GUI 実行ガイド（rtgamma GUI）

## 目的
- GUI から Ref/Eval の RTDOSE を選択し、臨床プリセットで 2D/3D を実行。
- 実行ログ（`run_log_*.txt`）の保存とサマリ自動オープンを確認。

## 起動
- ダブルクリック: `run_gui.bat`
- または: `scripts/run_gui.ps1`

## Fast 3D Viewer PoC（任意）
- 目的: Matplotlib/TkAgg 版3D Viewerの描画限界を超えられるか、PyQtGraph + PySide6 で検証します。
- 起動: `run_viewer_fast_test.bat`
- 依存関係: `pip install -r requirements-fast-viewer.txt`
- 範囲: Axial / Sagittal / Coronal の3断面、CT表示、Gamma overlay、共有voxel cursor、`HU / Ref / Eval` ラベル表示。
- 非範囲: 画像保存、スクリーンショット保存、設定保存、ROI/RTSTRUCT、EXE同梱、既存GUI統合。
- 操作:
  - マウスクリック: クリック断面上のvoxelへ共有cursorを移動。
  - マウスホイール: 操作中断面のslice indexを移動。
  - slice slider: Axial / Sagittal / Coronal を個別に移動。
  - いずれの操作でも3断面のcrosshairと `HU / Ref / Eval` ラベルを同期更新。
  - Gamma alpha sliderはGamma overlayのみに作用。
- 安全動作:
  - `--gamma-npz` は既存Viewerと同じく `gamma` キーを基本とします。キー欠損やshape不一致ではViewer全体を落とさずGamma overlayのみ無効化します。
  - HU / Ref / Eval は個別にshape・範囲・finite確認を行い、取得できない値だけ `N/A` と表示します。

## 手順
- ファイル選択
  - `Ref RTDOSE (.dcm)` と `Eval RTDOSE (.dcm)` を選択。
  - `Output Folder` に保存先ディレクトリ（例: `phits-linac-validation/output/rtgamma/Test05_gui`）を指定。
- アクション選択
  - Action: `3D (clinical preset)` または `2D (clinical preset)`（2D は Plane/Index 指定あり）。
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
