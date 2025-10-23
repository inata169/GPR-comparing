# 放射線治療における GPR 解析の Global と Local の違い

本ノートは、本リポジトリの rtgamma 実装（2D/3D ガンマ）における Global/Local の意味と使い分けを、再現可能な実行例つきで整理します。（UTF-8 / BOM なし）

## ガンマ解析の基本（用語）
- DD[%]: 許容線量差（例: 3%）
- DTA[mm]: 許容距離差（例: 2 mm）
- Cutoff[%]: 低線量除外のしきい値（例: 10%）
- GPR: Gamma Passing Rate（γ ≤ 1.0 の体積/画素の割合[%]）

本実装では、次の 2 つの設定が関与します。
- `--gamma-type {global,local}`: ΔD（線量差）の正規化の仕方を選択
  - global: 参照線量の「グローバル基準」（最大値）で ΔD[%] を計算
  - local: 各ボクセルの「局所の参照線量」で ΔD[%] を計算（点ごとに母数が変わる）
- `--norm {global_max,max_ref,none}`: 参照線量を百分率へ換算する際の正規化
  - 現行実装では `global_max` と `max_ref` は同等（参照の最大値を使用）
  - Cutoff の判定もこのグローバル基準に基づきます（Local 選択時も同じ）

注意
- Local は局所線量 0 近傍で ΔD[%] が定義できなくなるため、本実装では極小値ガードを入れ、Cutoff も十分に設定することを推奨します（例: 10%）。

## Global（グローバル）
- 定義: ΔD[%] = (ΔD / 参照線量の最大値) × 100
- 特徴: 低線量領域で相対的に寛容。全体の再現性評価に向く
- 主な用途: 定期 QA、日常臨床 QA（例: 3%/2mm/10%、passing rate ≥ 95% など）

## Local（ローカル）
- 定義: ΔD[%] = (ΔD / その点の参照線量) × 100
- 特徴: 低線量領域で厳しくなる。高勾配・高精度領域の局所一致性の確認に向く
- 主な用途: 研究評価、IMRT/VMAT、SRS/SBRT などの高精度治療

## 比較（要点）
- 基準線量: Global=参照最大、Local=各点の参照線量
- 厳しさ: Local > Global（一般に Local の方が GPR は低く出やすい）
- 低線量域: Global は寛容、Local はノイズ影響で Fail が増えやすい
- 推奨: 臨床 QA の第一選択は Global、Local は補助的な厳格評価に活用

## 実行例（このリポジトリの DICOM サンプル）
サンプル: AGLPhantom（CCC vs MC）、臨床相当（clinical_rel）、シフト最適化 OFF、axial 中央スライス、threads=auto。

- Global（既定）
  - `python -m rtgamma.main --profile clinical_rel \
    --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm \
    --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm \
    --mode 2d --plane axial --plane-index auto --opt-shift off \
    --save-gamma-map phits-linac-validation/output/rtgamma/GvL/axial_gamma_global.png \
    --save-dose-diff phits-linac-validation/output/rtgamma/GvL/axial_diff_global.png \
    --report phits-linac-validation/output/rtgamma/GvL/axial_global`
  - 観測 GPR の目安: 約 96.87%

- Local（厳格）
  - `python -m rtgamma.main --profile clinical_rel \
    --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm \
    --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm \
    --mode 2d --plane axial --plane-index auto --opt-shift off \
    --gamma-type local \
    --save-gamma-map phits-linac-validation/output/rtgamma/GvL/axial_gamma_local.png \
    --save-dose-diff phits-linac-validation/output/rtgamma/GvL/axial_diff_local.png \
    --report phits-linac-validation/output/rtgamma/GvL/axial_local`
  - 観測 GPR の目安: 約 82.26%（Global より厳しくなる）

備考
- 実際の数値はデータに依存します。上記は本リポジトリ同梱のサンプルでの一例です
- 3D でも `--gamma-type local` は有効です（出力レポートの `gamma_type` で判別可能）

## 運用のヒント
- Local を使う場合は Cutoff を十分に設定（例: 10%）し、低線量ノイズの影響を抑制
- 必要に応じて ROI マスク（将来機能）やスムージングの活用も検討
- レポート JSON/MD を保存し、Global/Local の比較結果をアーカイブしておくと再現が容易

## 実装メモ（rtgamma）
- `--gamma-type` は ΔD[%] の分母（global: 参照最大、local: 参照局所）を切替
- `--norm` は百分率変換と Cutoff 判定の基準（現状 `global_max`/`max_ref` は同等）
- Cutoff は Global 基準で判定（Local 選択時でも変わらない）
- コード参照: `rtgamma/gamma.py`（Numba 3D カーネル）、`rtgamma/main.py`（CLI）

