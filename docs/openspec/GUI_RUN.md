# GUI Execution Guide (rtgamma GUI)

## Goal
- GUI から Ref/Eval RTDOSE を選択し、臨床プリセットで 2D/3D を実行。
- 実行ログ（run_log_*.txt）保存とサマリ自動オープンの確認。

## Launch
- Double-click: `run_gui.bat`
- Or: `scripts/run_gui.ps1`

## Steps
- Select files
  - `Ref RTDOSE (.dcm)` と `Eval RTDOSE (.dcm)` を選択。
  - `Output Folder` に保存先ディレクトリ（例: `phits-linac-validation/output/rtgamma/Test05_gui`）。
- Choose action
  - Action: `3D (clinical preset)` または `2D (clinical preset)`（2D は Plane/Index 指定）。
  - Clinical Preset: `clinical_rel`（既定：3%/2mm/10%、norm=global_max、opt-shift=off）。
  - Optimize shift: 既定 OFF（必要時のみ ON）。
  - Threads: CPU コア数を目安に設定（0=auto）。
- Comfort options
  - `Open summary on finish`: ON（サマリ自動オープン）。
  - `Save log to file`: ON（run_log_YYYYMMDD_HHMMSS.txt を出力フォルダへ保存）。
  - `Local gamma`: OFF=Global（既定）、ON=Local ガンマ（厳格）。
- Run
  - `Run` をクリック。進捗バーとログに実行状況が表示されます。

## Auto-open Preference
- 3D: `run3d.md`
- 2D: `<plane>.md`（例: `axial.md`）
- Header Compare: `header_compare.md`
- 上記が無ければ、フォルダ内の最新の `*.md` を開きます。

## Expected Outputs
- Logs: `.../run_log_*.txt`（UTF-8 推奨）
- Reports: `.../run3d.{csv,json,md}` または `<plane>.{csv,json,md}`
- 2D Images: `<plane>_gamma.png`, `<plane>_diff.png`
- 3D NPZ: `gamma3d.npz`, `dose_diff3d.npz`（指定時）

## Encoding Note (Windows)
- Markdown/ログは UTF-8（BOMなし）推奨。文字化け回避にエディタ設定を確認してください。

## Screenshots (Optional)
- 次のファイル名で `docs/openspec/images/` に保存してください（任意・小サイズ推奨）。
  - `gui_main.png`（GUI メインウィンドウ）
  - `gui_after_run3d.png`（3D 実行後、run3d.md が開かれた状態）
  - `gui_after_run2d_axial.png`（2D axial 実行後、axial.md が開かれた状態）
- リポジトリには大きな画像を含めない方針です。圧縮・縮小してから追加してください。

## References
- GUI script: `scripts/run_gui.ps1`
- Batch launcher: `run_gui.bat`
- Config: `config/gui_defaults.json`
