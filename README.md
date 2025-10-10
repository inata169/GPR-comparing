# RTDOSE ガンマ解析 CLI（2D/3D・三軸シフト最適化対応）

放射線治療QA向けに、2つの DICOM RTDOSE を比較して 2D/3D ガンマインデックスを計算するツールです。異グリッド・異座標系の整合、三軸シフト最適化、可視化、レポート出力に対応します。

- 既定基準: `DD=3.0%`, `DTA=2.0 mm`, `Cutoff=10%`
- ガンマ種別: `global`（変更可）
- 正規化: `global_max`（`--norm max_ref` に切替可）

本リポジトリには、比較用のサンプル RTDOSE（肺症例）が含まれます。
- `PHITS_Iris_10_rtdose.dcm`
- `RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm`

なお、`phits-linac-validation/` には PHITS 出力と実測CSVの1Dプロファイル比較ツールが別途含まれています（本READMEは RTDOSE 同士のボリューム比較ツールの説明です）。

## インストール

- Python 3.9+ を推奨
- 依存関係のインストール
  - `pip install pydicom numpy scipy matplotlib pymedphys`

## 使い方（基本）

- 3D ガンマ＋シフト最適化＋要約出力
  - `python -m rtgamma.main --ref PHITS_Iris_10_rtdose.dcm --eval RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report output/rtgamma/lung3d_report --save-gamma-map output/rtgamma/gamma3d.npz --save-dose-diff output/rtgamma/dose_diff3d.npz`
- 2D（axial スライス 例: 50）＋画像保存
  - `python -m rtgamma.main --ref PHITS_Iris_10_rtdose.dcm --eval RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 2d --plane axial --plane-index 50 --save-gamma-map output/rtgamma/gamma_axial.png --save-dose-diff output/rtgamma/diff_axial.png --report output/rtgamma/lung2d_axial`

出力先フォルダは事前に作成してください（例：`output/rtgamma`）。

## 主な引数（抜粋）

- 入力
  - `--ref <path>`: 基準 RTDOSE（DICOM）
  - `--eval <path>`: 比較 RTDOSE（DICOM）
- 解析モード
  - `--mode {3d,2d}`（既定: `3d`）
  - `--plane {axial,sagittal,coronal}`（2D時）
  - `--plane-index <int>`（2D時のスライス番号）
- 評価条件
  - `--dd <float>`（%） 既定: `3.0`
  - `--dta <float>`（mm） 既定: `2.0`
  - `--cutoff <float>`（%） 既定: `10.0`
  - `--gamma-type {global,local}` 既定: `global`
  - `--norm {global_max,max_ref,none}` 既定: `global_max`
- シフト最適化（ON/OFF, 範囲）
  - `--opt-shift {on,off}` 既定: `on`
  - `--shift-range "x:-3:3:1,y:-3:3:1,z:-3:3:1"`
    - IMRT/VMAT では既定（±3mm, 1mm刻み）が一般的
    - 3D-CRT で広めに探索: 例 `x:-5:5:1,y:-5:5:1,z:-5:5:1`
- グリッド/補間
  - `--interp {linear,bspline,nearest}` 既定: `linear`
- 出力
  - `--save-gamma-map <path>`（2D: PNG/TIFF, 3D: NPZ）
  - `--save-dose-diff <path>`（2D: PNG/TIFF, 3D: NPZ）
  - `--report <path>`（拡張子なしで指定。CSV/JSON/MD を併産）

## 出力ファイル（例）

- `output/rtgamma/gamma3d.npz`（3D ガンマ配列）
- `output/rtgamma/dose_diff3d.npz`（%差分 3D 配列）
- `output/rtgamma/gamma_axial.png`（2D ガンマ画像）
- `output/rtgamma/diff_axial.png`（2D 差分画像）
- `output/rtgamma/lung3d_report.csv|json|md`（要約：パス率、最適シフト、ガンマ統計など）
- `output/rtgamma/lung3d_report_search_log.json`（全シフトのパス率ログ）

## 実装メモ

- RTDOSE の座標は `ImagePositionPatient`/`ImageOrientationPatient`/`PixelSpacing`/`GridFrameOffsetVector` から LPS 座標化
- 比較は基準 RTDOSE グリッド上に評価側を補間して実施
- ガンマ計算は `pymedphys.gamma` を呼び出し

## 既知の制約 / 今後の拡張

- ROI/マスク（RTSTRUCT）は未実装（次回対応予定）
- 局所探索（Nelder-Mead 等）の実装は今後の拡張
- GPU 対応（cupy）は将来的な検討項目

---

- サブプロジェクト（1Dプロファイル比較ツール）は `phits-linac-validation/README.md` を参照してください。

