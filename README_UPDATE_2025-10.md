# README 追加情報（2025-10）

このリリースで追加・強化された機能と、その使い方の抜粋です。

## 追加機能

- ヘッダ比較ツール拡張：`scripts/compare_rtdose_headers.py` に `--plan-a` / `--plan-b` を追加（RTPLANの Isocenter/SAD/SSD をMDに追記）。
- 自動フォールバック強化（粗→密の2段探索、早期打ち切り、2D中央スライス事前スキャン）。
  - 新規CLI: `--fine-range-mm` / `--fine-step-mm` / `--early-stop-epsilon` / `--early-stop-patience` / `--prescan-2d`。

## ヘッダ比較（RTPLANあり）
```
python scripts/compare_rtdose_headers.py \
  --a <ref_rtdose.dcm> --b <eval_rtdose.dcm> \
  --plan-a <ref_rtplan.dcm> --plan-b <eval_rtplan.dcm> \
  --out phits-linac-validation/output/rtgamma/dose_compare.md
```

## 3D解析（2段探索＋早期打ち切り・2D事前スキャン）
```
python -m rtgamma.main \
  --ref <ref.dcm> --eval <eval.dcm> --mode 3d \
  --shift-range "x:-10:10:2,y:-10:10:2,z:-10:10:2" \
  --fine-range-mm 5 --fine-step-mm 1 \
  --early-stop-epsilon 0.05 --early-stop-patience 200 \
  --report phits-linac-validation/output/rtgamma/run3d
```

## 2D可視化（中央スライス、最適化OFF）
```
python -m rtgamma.main \
  --ref <ref.dcm> --eval <eval.dcm> \
  --mode 2d --plane axial --plane-index auto --opt-shift off \
  --save-gamma-map phits-linac-validation/output/rtgamma/axial_gamma.png \
  --save-dose-diff phits-linac-validation/output/rtgamma/axial_diff.png \
  --report phits-linac-validation/output/rtgamma/axial
```

## まとめ出力（サマリMD/PDF）
```
python scripts/make_summary.py --case Test05 --out-dir phits-linac-validation/output/rtgamma
```

補足：詳細な修正履歴は `CHANGELOG.md` を参照してください。

