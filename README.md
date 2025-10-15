# RTDOSE ガンマ解析 CLI（2D/3D・三軸シフト最適化）

放射線治療QA向けに、2つの DICOM RTDOSE を比較して 2D/3D ガンマインデックスを計算するツールです。異グリッド・異座標系の整合、三軸シフト最適化、可視化、レポート出力に対応します。

- 既定条件: `DD=3.0%`, `DTA=2.0 mm`, `Cutoff=10%`
- ガンマ種別: `global`（`--gamma-type`で切替可）
- 正規化: `global_max`（`--norm`で `max_ref` / `none` 選択可）

同梱サンプル（肺症例）
- `dicom/PHITS_Iris_10_rtdose.dcm`
- `dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm`

備考: `phits-linac-validation/` にはPHITS出力と実測CSVの1Dプロファイル比較ツールが別途含まれます（本READMEはRTDOSE同士のボリューム比較ツールの説明です）。

## インストール

- Python 3.9+ を推奨
- 依存関係のインストール
  - `pip install pydicom numpy scipy matplotlib numba`

## 使い方（基本）

- 3D ガンマ＋シフト最適化＋レポート出力
  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report phits-linac-validation/output/rtgamma/lung3d_report --save-gamma-map phits-linac-validation/output/rtgamma/gamma3d.npz --save-dose-diff phits-linac-validation/output/rtgamma/dose_diff3d.npz`

- 2D Axial スライス（スライス番号 50）＋画像保存
  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 2d --plane axial --plane-index 50 --save-gamma-map phits-linac-validation/output/rtgamma/gamma_axial.png --save-dose-diff phits-linac-validation/output/rtgamma/diff_axial.png --report phits-linac-validation/output/rtgamma/lung2d_axial`

出力先ディレクトリは自動作成されます（ファイル名のみの場合はカレントに出力）。

## 主な引数（抜粋）

- 入力
  - `--ref <path>` 基準 RTDOSE（DICOM）
  - `--eval <path>` 比較 RTDOSE（DICOM）

- 解析モード
  - `--mode {3d,2d}` 既定: `3d`
  - `--plane {axial,sagittal,coronal}`（2D時）
  - `--plane-index <int>`（2D時、スライス番号）

- 評価条件
  - `--dd <float>` 既定: `3.0`
  - `--dta <float>` 既定: `2.0`
  - `--cutoff <float>` 既定: `10.0`
  - `--gamma-type {global,local}` 既定: `global`
  - `--norm {global_max,max_ref,none}` 既定: `global_max`

- シフト最適化（ON/OFF, 範囲）
  - `--opt-shift {on,off}` 既定: `on`
  - `--shift-range "x:-3:3:1,y:-3:3:1,z:-3:3:1"`
    - 一般にIMRT/VMATでは±3mm, 1mm刻み程度が目安
    - 3D-CRTなどで広めに探索する場合: 例 `x:-5:5:1,y:-5:5:1,z:-5:5:1`

- 補間
  - `--interp {linear,bspline,nearest}` 既定: `linear`

- 出力
  - `--save-gamma-map <path>` 2D: PNG/TIFF, 3D: NPZ
  - `--save-dose-diff <path>` 2D: PNG/TIFF, 3D: NPZ（ref基準で%表記）
  - `--report <path>` 拡張子なしで指定（CSV/JSON/MD を自動生成）

## 出力ファイル例

- `phits-linac-validation/output/rtgamma/gamma3d.npz` 3D ガンマ配列
- `phits-linac-validation/output/rtgamma/dose_diff3d.npz` 3D 差分（%）
- `phits-linac-validation/output/rtgamma/gamma_axial.png` 2D ガンマ画像
- `phits-linac-validation/output/rtgamma/diff_axial.png` 2D 差分画像
- `phits-linac-validation/output/rtgamma/lung3d_report.csv|json|md` 要約（パス率、最適シフト、統計）
- `phits-linac-validation/output/rtgamma/lung3d_report_search_log.json` シフト探索ログ

## 実装メモ

- RTDOSE の座標は `ImagePositionPatient` / `ImageOrientationPatient` / `PixelSpacing` / `GridFrameOffsetVector` を用いて LPS へ復元
- 評価側は参照グリッド上へ連続空間補間（`scipy.ndimage.map_coordinates`）
- ガンマは `numba` 実装（3D）で高速化、cutoff未満は除外
- シフト探索は coarse→fine の2段階グリッドサーチ

## 最近の修正（重要）

- GFOV とフレーム配列の同期：`GridFrameOffsetVector` に合わせてZスライス順序を昇順に再配置（`dose = dose[order, ...]`）。Z座標とデータの不一致を解消。
- 原点差補正の厳密化：IPP差を参照の方向余弦（row/col/slice）へ射影して各軸差（dx,dy,dz）を算出。
- 最適シフト適用の方向修正：参照軸成分のシフトを LPS ベクトルへ変換してからリサンプリングに適用。
- 出力先ディレクトリの安全化：空ディレクトリ名で `os.makedirs('')` にならないようガード。

## 既知の制限 / 今後の拡張

- ROI/マスク（RTSTRUCT連携）は未実装（要望があれば対応）
- 局所探索（Nelder-Mead 等）の追加検討
- GPU（CuPy）対応は今後検討
 
---

サブプロジェクト（1Dプロファイル比較）は `phits-linac-validation/README.md` を参照してください。

## クイックスタート（推奨）

- 依存の導入（再現性のために準拠版を使用）
  - `pip install -r REQUIREMENTS.txt`
- 自己比較（sanity check）
  - `python -m rtgamma.main --ref dicom/RTDOSE_2.16.840.1.114337.1.2604.1760077605.1.dcm --eval dicom/RTDOSE_2.16.840.1.114337.1.2604.1760077605.1.dcm --mode 3d --report phits-linac-validation/output/rtgamma/self_check`
- ペア比較の例（3D, 既定 3%/2mm/10%）
  - `python -m rtgamma.main --ref dicom/RTDOSE_2.16.840.1.114337.1.2604.1760077605.3.dcm --eval dicom/RTDOSE_2.16.840.1.114337.1.2604.1760079109.3.dcm --mode 3d --report phits-linac-validation/output/rtgamma/pair3_3d`

## 関連ドキュメント

- `AGENTS.md`（貢献ガイド）
- `TROUBLESHOOTING.md`（トラブルシュート）
- `TEST_PLAN.md`（手動回帰の手順）
- `CHANGELOG.md`（変更履歴）
- `DECISIONS.md`（主要技術判断の要約）

## 本日の成果（2025-10-15）

- レポート拡張と警告出力（純幾何の確認を強化）
  - `FrameOfReferenceUID` をレポートに出力（`ref_for_uid`,`eval_for_uid`,`same_for_uid`）。
  - 最適シフトの大きさを出力（`best_shift_mag_mm`）し、所定しきい値（既定20 mm）超過で `warnings` に明示。
  - 方向余弦の一致度を数値化（`orientation_min_dot`）し、ずれが大きい場合は警告。
  - 純幾何（`--opt-shift off` かつ `--norm none`）での実行を `absolute_geometry_only` としてレポートに明示。

- 実行スクリプトの追加・改善（PowerShell）
  - `scripts/run_autofallback.ps1`: 純幾何→しきい値未満/警告ありで広探索（±150/±50/±50, 5mm）に自動フォールバック。2D再評価も実施。
  - 変数展開でのコロン混在に対するPowerShellの不具合を回避（`-f` で文字列合成）。
  - `scripts/run_test02_2d.ps1` / `run_test02_abs_vs_bestshift.ps1` / `run_test02_wide_bestshift.ps1` を整備。

- ヘッダ比較ユーティリティ
  - `scripts/compare_rtdose_headers.py`: 2つのRTDOSEの DICOM 幾何・スケールの差分をMarkdownで一覧化（FoR, IPP/IOP, PixelSpacing, GFOV範囲・中央値ステップ, DoseUnits/Scaling, ワールド座標範囲, 原点差(dx,dy,dz) など）。

- 実測的学び
  - Test04（6MV vs 10MV）では純幾何のみで 3D GPR ≈ 60% と妥当。エネルギー差の形状違いが要因。
  - Test01/03（SSD=100 cm）での大シフト・低GPRは、設定（SSD/SCD/アイソ中心）の食い違いが有力因子。
  - Test02/04（SCD=100 cm）では幾何が良好で、GPRが改善。

実行例（1行）
- 自動フォールバック（例: Test03）
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_autofallback.ps1 -Name Test03_auto -Ref "dicom\Test03\RTDOSE_2.16.840.1.114337.1.2604.1760077605.4.dcm" -Eval "dicom\Test03\RTDOSE_2.16.840.1.114337.1.2604.1760077605.5.dcm"`

## 注意事項

- 個人情報（PHI）を含むDICOMはリポジトリにコミットしないでください（同梱サンプルは匿名化用途）。
- 生成物・大容量ファイルは極力コミットせず、`phits-linac-validation/output/rtgamma/` 配下に保存してください（git ignore 推奨）。

## 2025年10月14日の調査サマリ

`rtgamma`ツールが、物理的にほぼ同一であるべき2つのRTDOSEファイル（CCC対MC）に対して低いガンマパス率を示す問題の調査を行った。

### 判明した点

1.  **幾何学的な問題:**
    -   2つのファイルの`ImagePositionPatient`（座標原点）のX軸が`+114mm`異なっている。
    -   ツールの自動原点補正ロジックが不適切である可能性が高く、これを打ち消すために手動で`dx ≈ -114mm`のシフトを適用することで、正しい幾何学的位置に近づくことが判明した。

2.  **線量的な問題:**
    -   2つのファイルの`DoseGridScaling`（線量変換係数）が異なっている。
    -   ツールの内部にあった、最大値を強制的に一致させる正規化処理を無効化した。
    -   その上で絶対線量比較を行った結果、依然としてガンマ評価が不合格（パス率 < 3%）となった。これは、2つのアルゴリズムの計算結果に、DICOM規格に準拠した比較では無視できない「真の差」が存在することを示唆している。

### 修正したツール内のバグ

-   `optimize.py`: シフト探索範囲の評価ロジックを修正し、手動でのシフト量固定を可能にした。
-   `main.py`: 絶対線量比較を妨げていた強制正規化処理を無効化した。
