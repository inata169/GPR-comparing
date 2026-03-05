# interp_fraction 感度実験: Handover Context

## 1. 現在の進捗状況 (Current Progress)

### 完了済みタスク (本日)
- **3DVH クロスバリデーション パイプライン (完了)**
  - `scripts/run_3dvh_crossval.py` 実行完了。Prostate (Δ=+1.12pp, PASS) / BreastBolus (Δ=+1.99pp, PASS) の両ケースで 3DVH との差が ≤2pp 以内を達成。
  - 結果ファイル: `output/3dvh_crossval/crossval_summary.md`, `histogram_comparison.png`
  - 変更はコミット済み。 (`git push` は実験結果確認後に実施)。

- **ガンマヒストグラム Unit Test (完了)**
  - `tests/test_gamma_histogram.py` を作成し、全テスト（26/27 PASS, 1件は別要因で修正済み）を確認。

- **回帰テストの修正 (完了)**
  - `tests/test_regression.py` の `test_regression_synthetic_gpr` を DTA=1.5mm / interp-fraction=1 に修正し、数値安定性を担保。

### 現在実行中
- **`interp_fraction` 感度実験 (実行中/完了待ち)**
  - コマンド: `$env:PYTHONUTF8=1; python scripts/run_interp_experiment.py --max-frac 20`
  - fraction 1〜20 を変えて Prostate と BreastBolus の GPR を計測し、3DVH 目標値 (Prostate: 84.7%, BreastBolus: 97.6%) に最も近い fraction を特定する実験。

## 2. 保留中のタスク (Pending Tasks)

- **実験結果の確認**
  - `output/interp_experiment/Prostate/interp_experiment_results.csv`
  - `output/interp_experiment/BreastBolus/interp_experiment_results.csv`
  - `output/interp_experiment/*/interp_experiment_plot.png`
  - 各 fraction の GPR および 3DVH との Δ(pp) を確認し、最適値を決定する。

- **最適 `interp_fraction` の反映 (実験結果確認後)**
  - `config/3dvh_reference.json` の各ケースに `optimal_interp_fraction` フィールドを追記する。
  - GUI の `--interp-fraction` デフォルト値を更新することを検討。

- **Git Push**
  - 実験結果の確認を経て、まとめてコミット + プッシュする。

## 3. 直近で実行すべきコマンド (Commands to Run Next)

```powershell
# 1. 実験スクリプトの実行（未完了の場合）
$env:PYTHONUTF8=1; python scripts/run_interp_experiment.py --max-frac 20

# 2. 結果を確認する
# output/interp_experiment/Prostate/interp_experiment_plot.png
# output/interp_experiment/BreastBolus/interp_experiment_plot.png

# 3. 全テストが通ることを確認する
$env:PYTHONUTF8=1; pytest tests/ -v

# 4. まとめてコミット + プッシュ
$env:LC_ALL='C'; git add -A
$env:LC_ALL='C'; git commit -F _msg.txt
$env:LC_ALL='C'; git push
```

以上です。次のチャットでこのファイル (`99-handover_context.md`) を読み込ませて開始してください。
