# interp_fraction 最適化: Handover Context

## 1. 現在の進捗状況 (Current Progress)

### Prostate: interp_fraction 感度実験 (完了)
- `scripts/run_interp_experiment.py --max-frac 20` にて Prostate の GPR を fraction 1〜20 で計測。
- **結論**: `interp_fraction = 3` が 3DVH ターゲット (84.7%) に最も近い。
  - fraction=3 → GPR=**85.26%** (Δ=+0.56pp) ← 最小 Δ
  - fraction=2 → GPR=82.89% (Δ=-1.81pp)
  - fraction=10 → GPR=85.82% (Δ=+1.12pp)
- `config/3dvh_reference.json` の Prostate エントリの `interp_fraction` を `3` に更新済み。
- 結果 CSV: `output/interp_experiment/Prostate/interp_experiment_results.csv`

### BreastBolus: interp_fraction 感度実験 (未実施)
- BreastBolus の実験はまだ実行の機会なし。
- 次回セッションで実施予定。

## 2. 保留中のタスク (Pending Tasks)

- **BreastBolus の interp_fraction 実験**:
  ```powershell
  $env:PYTHONUTF8=1; python scripts/run_interp_experiment.py --case BreastBolus --max-frac 20
  ```
  - 完了したら `config/3dvh_reference.json` の BreastBolus エントリも更新する。

- **Git Push**: 実験結果と設定変更をリモートへ push する（確認後）。

## 3. 直近で実行すべきコマンド (Commands to Run Next)

```powershell
# BreastBolus の interp_fraction 感度実験
$env:PYTHONUTF8=1; python scripts/run_interp_experiment.py --case BreastBolus --max-frac 20

# 全テスト確認
$env:PYTHONUTF8=1; pytest tests/ -v

# まとめてコミット + プッシュ
$env:LC_ALL='C'; git add -A
$env:LC_ALL='C'; git commit -F _msg.txt
$env:LC_ALL='C'; git push
```

以上です。次のチャットでこのファイル (`99-handover_context.md`) を読み込ませて開始してください。
