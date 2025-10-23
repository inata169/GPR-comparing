# Global / Local ガンマの図式解説（日本語）

## 何が違う？（定義の違い）
- Global: ΔD[%] = (|Eval−Ref| / Ref 全体の最大値) × 100
- Local:  ΔD[%] = (|Eval−Ref| / その点の Ref) × 100
- 直観:
  - 同じ絶対差でも、局所線量が小さいほど Local は大きな ΔD[%] になります（低線量域に厳しい）。
  - Global は全体最大値を基準にするため、低線量域で相対的に寛容です。

## 図示（イメージ）
- 例：参照線量の断面が「高線量プラトー＋低線量テール」を持つとします。
  - 高線量プラトー: Local と Global の差は小さめ。
  - 低線量テール: 同じ絶対誤差でも Local の ΔD[%] が大きくなりやすい ⇒ Fail 増。

## カットオフ（Cutoff）の扱い
- 低線量ノイズに対して Local は敏感です。臨床相当では `--cutoff 10`（10%）を推奨。
- 本実装では Cutoff 判定はグローバル基準（参照の最大値）に基づきます。

## 実行例（このリポジトリのサンプル）
- データ: AGLPhantom（CCC vs MC）、臨床相当 `clinical_rel`（3%/2mm/10%）、shift OFF、axial 中央スライス、threads=auto。
- Global（既定）:
  - `python -m rtgamma.main --profile clinical_rel \
    --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm \
    --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm \
    --mode 2d --plane axial --plane-index auto --opt-shift off \
    --save-gamma-map phits-linac-validation/output/rtgamma/GvL/axial_gamma_global.png \
    --save-dose-diff phits-linac-validation/output/rtgamma/GvL/axial_diff_global.png \
    --report phits-linac-validation/output/rtgamma/GvL/axial_global`
  - 観測目安: GPR ≈ 96.87%
- Local（より厳格）:
  - `python -m rtgamma.main --profile clinical_rel \
    --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm \
    --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm \
    --mode 2d --plane axial --plane-index auto --opt-shift off \
    --gamma-type local \
    --save-gamma-map phits-linac-validation/output/rtgamma/GvL/axial_gamma_local.png \
    --save-dose-diff phits-linac-validation/output/rtgamma/GvL/axial_diff_local.png \
    --report phits-linac-validation/output/rtgamma/GvL/axial_local`
  - 観測目安: GPR ≈ 82.26%（Global より低下）

## Tips（運用上の注意）
- Local を使う際は十分な Cutoff を設定（例: 10%）。
- ROI（将来機能）、スムージング等で評価領域やノイズの影響を調整可能。
- レポート（JSON/MD）を保存して Global/Local の差分をアーカイブしておくと再現が容易です。

