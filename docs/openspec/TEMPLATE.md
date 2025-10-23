# {{PROJECT}} OpenSpec (v{{VERSION}})

## 1. Overview
- Purpose: 本仕様の目的と背景
- Scope: 対象/非対象（Non-Goals を含む）
- Stakeholders & Users: 想定ユーザー/運用者

## 2. Use Cases
- ユースケース/ユーザーストーリー（例: QA で CCC と MC の RTDOSE を比較し GPR を得る）

## 3. Inputs & Outputs
- Inputs:
  - DICOM: RTDOSE（座標系 LPS）、必要フィールド（IPP/IOP/PixelSpacing/GFOV/DoseGridScaling）
  - CLI 引数: dd/dta/cutoff/gamma-type/norm/opt-shift/shift-range 等（既存 CLI を参照）
- Outputs:
  - 2D: 画像（gamma/diff）
  - 3D: NPZ（gamma, dose_diff_pct）
  - Report: CSV/JSON/MD（`docs/openspec/report.schema.json` 参照）

## 4. Geometry & Coordinates
- LPS 準拠。`ImagePositionPatient`/`ImageOrientationPatient`/`PixelSpacing`/`GridFrameOffsetVector` を厳守。
- GFOV は単調増加となるようフレームと z 座標を並べ替える（昇順）。
- 2D 平面の世界座標は配列軸順（z,y,x）に合わせ、固定次元は単一軸で表現（axial/sagittal/coronal）。

## 5. Resampling
- 参照グリッド上へ評価線量をリサンプリング。
- `world_to_index()` により eval 側の (i,j,k) を求め、`map_coordinates` で補間（linear 既定）。

## 6. Gamma Analysis
- 定義: DD[%]/DTA[mm]/Cutoff[%]、`gamma-type`（global/local）、`norm`（global_max/max_ref/none）。
- 実装: Numba ベースの 3D カーネル。2D 最適化 OFF では slice 限定の高速経路。

## 7. Shift Optimization
- 粗密二段探索（coarse→fine）＋早期打ち切り（epsilon/patience）。
- 2D プリスキャンで XY 範囲を絞り込み（オプション）。

## 8. Performance & Accuracy
- パフォーマンス目標（例）: Test05 3D（最適化 OFF）完走、2D 高速経路の秒単位完了。
- 精度受け入れ基準（例）: Self-compare ≈100%；幾何一致時の再現性±0.5pp。

## 9. Logging & Reproducibility
- ログ: `rtgamma.log` と GUI ログ（run_log_*.txt）。
- レポートへ FoR/orientation/shift/warnings を記録（トリアージ容易化）。

## 10. Security & Privacy
- PHI を含む DICOM はコミット禁止。匿名化サンプルのみ利用。

## 11. Open Questions & Constraints
- 例：Coronal GPR 差分の要因、局所ガンマの CLI 露出方針、ROI マスクの扱い。

## 12. Versioning & Change Control
- バージョンは本ファイル先頭 `v{{VERSION}}` を更新。
- 重要な決定は `DECISIONS.md`、変更履歴は `CHANGELOG.md` に追記し相互参照。

