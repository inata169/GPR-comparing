# GUI改修・EXE化対応・ドキュメント拡充: Handover Context (2026-03-06 v0.6.0 リリース完了)

## 1. 現在の進捗状況 (Current Progress)

### Prostate: interp_fraction 感度実験 (完了)
- `scripts/run_interp_experiment.py --max-frac 20` にて Prostate の GPR を fraction 1〜20 で計測。
- **結論**: `interp_fraction = 3` が 3DVH ターゲット (84.7%) に最も近い。
  - fraction=3 → GPR=**85.26%** (Δ=+0.56pp) ← 最小 Δ
- `config/3dvh_reference.json` の Prostate エントリの `interp_fraction` を `3` に更新済み。
- 結果 CSV: `output/interp_experiment/Prostate/interp_experiment_results.csv`

### BreastBolus: interp_fraction 感度実験 (完了)
- `scripts/run_interp_experiment.py --case BreastBolus --max-frac 20` にて BreastBolus の GPR を fraction 1〜20 で計測。
- **結論**: `interp_fraction = 2` が 3DVH ターゲット (97.6%) に最も近い。
  - fraction=2 → GPR=**97.73%** (Δ=+0.13pp) ← 最小 Δ
- `config/3dvh_reference.json` の BreastBolus エントリの `interp_fraction` を `2` に更新済み。
- 結果 CSV: `output/interp_experiment/BreastBolus/interp_experiment_results.csv`

### リポジトリ状態 (Repository Status)
- すべての interp_fraction 実験は両ケース完了。
- `ruff` による Lint エラーも修正済みで、GitHub Actions (CI) は **Success (Green)** の状態。
- **v0.6.0** を正式に最新リリースとして公開済み（GUI PDF対応、ツールチップ拡充、PyInstaller対応）。
- ドキュメント・設定・テストもすべて最新化して push 済み。

### GUI改修、 EXE化、バグ修正 (完了)
- `config/gui_config.ini` を導入し、設定保存機能をモダン化（JSONからINIへ）。
- フォルダ/ファイル選択ダイアログを `OpenFileDialog` ベースに変更し、パスの直接入力・コピペに対応。
- **PyInstaller 対応 (`scripts/build_exe.ps1`)**: `rtgamma_cli.exe` と `gamma_viewer.exe` をスタンドアロンビルドできるように対応 (Tier 4タスク消化)。 相対パス・依存パッケージ(`scipy`)の問題などを専用エントリポイント化で解決済。
- **GUI の自動 EXE 切り替えロジック**: `run_gui.ps1` は `dist/` ディレクトリが存在する場合、Python ではなく自動的にビルドされた EXE を使って起動するように改修。Python 無しの環境での運用パスを確立。
- GUIの各種難解パラメータ (`Local/Global` `Normalization` `Sub-voxel Interp` 等) に詳細な ToolTip を追加し、ユーザビリティを向上。

### ドキュメント拡充 (Documentation)
- `docs/openspec/rtgamma_openspec.md` および `TODO.md` にて、EXE化に関する仕様追加と、商用化ロードマップの進捗（Tier 4の一部達成）を更新。
- Gamma Type や Normalization (`none`) の極端な厳しさ（絶対基準でのノイズ評価化）に関する定義を明文化。

## 2. 保留中のタスク (Pending Tasks)
次のセッションからは **Tier 2/3 未実装機能** に着手可能。

候補 (Tier 2/3):
- **Web GUI 化** (クロスプラットフォーム対応)
- **マルチプレーン/DVH 同時表示**
- **不確かさのブートストラップ推定**
- **MHD/NRRD フォーマット対応**
- **多基準同時評価の並行実行**

## 3. 次のステップでの確認事項 (Next Steps)
- 次回セッション開始時に、今回の「EXE 切り替え統合」がユーザのPC実環境下で問題なく通るかを（実際にGUI画面からボタンを押して）テストして頂くことをお勧めします。
- `dist` ディレクトリ内の `.exe` ビルドはコミット対象外 (`.gitignore`) のため、別PCへの持ち出しテストを行う場合は `dist` フォルダと `run_gui.bat` 類を含むZIPを手動で作成し検証してください。
