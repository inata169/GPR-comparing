# rtgamma — DICOM RTDOSE ガンマ解析 (2D/3D)

![CI](https://github.com/inata169/GPR-comparing/actions/workflows/ci.yml/badge.svg)

DICOM RTDOSE ペアに対する高速で再現性の高いガンマ解析ツールです。堅牢なジオメトリ処理、CLI/GUI サポート、軽量なドキュメントと仕様を備えています。

## 主な機能
- **高精度な空間整合**: DICOMタグ (IPP/IOP/PixelSpacing/GFOV) に厳密に基づく座標投影。ROIマスクも線量グリッドに正確にマッピングします。
- **2D/3Dガンマ解析**: 高速な3Dカーネル (Numba) および特定スライスのみを計算する軽量な2D経路。
- **シフト最適化**: 計算領域を粗密2段階で自動走査し、最適な空間シフト（位置ズレ）を探索。
- **ROI 限定解析**: RTSTRUCT ファイルと ROI 名を指定することで、特定構造（PTV, GTV など）内のガンマパス率（GPR）や統計値を算出可能。
- **Global / Local ガンマ**: 基準線量最大値（Global）または各ボクセル値（Local）に基づくガンマ計算の切り替え。
- **使いやすい GUI**: PowerShell / WinForms ベースの GUI サポート。

## インストール
- 要件: Python 3.9 以上
- 依存ライブラリ:
  ```bash
  pip install pydicom numpy scipy matplotlib numba
  ```

## クイックスタート (CLI)
- **3D 解析 (レポートのみ出力)**
  ```bash
  python -m rtgamma.main --ref dicom/Reference.dcm --eval dicom/Evaluate.dcm --mode 3d --report output/run3d
  ```
- **ROI 限定の 3D 解析**
  ```bash
  python -m rtgamma.main --ref dicom/Ref.dcm --eval dicom/Eval.dcm --rtstruct dicom/Struct.dcm --roi GTV --mode 3d --report output/run3d_gtv
  ```

## 臨床プリセットとスレッド数
- **プリセット**: `--profile {clinical_abs, clinical_rel, clinical_2x2, clinical_3x3}` (デフォルトではシフト最適化が無効化されます)
- **スレッド数**: `--threads <N>` で Numba 並列スレッド数を指定 (0=自動)

## Global / Local ガンマ
- `--gamma-type {global,local}` で選択可能 (デフォルト: global)
- 詳細な仕様と挙動については、`docs/openspec/Global_Local_Illustrated_JA.md` を参照してください。

## 出力形式
- **レポート**: CSV / JSON / Markdown (`--report <basepath>`) 。ROIごとの統計情報 (`per_structure`) を含みます。
- **2D 画像**: PNG形式でのガンママップと線量差分 (`--save-gamma-map`, `--save-dose-diff`)
- **3D 配列**: NPZ形式での生データ出力（オプション）

## GUI (グラフィカル・ユーザー・インターフェース)
- 起動: `run_gui.bat` をダブルクリック（または `scripts/run_gui.ps1` を実行）
- Ref / Eval の RTDOSE ファイル、出力先フォルダを選び、「Run」をクリックするだけ。
- **RTSTRUCT の読み込みと ROI 入力**にも対応しており、GUIから直接 ROI 限定解析を実行できます。
- Local Gamma の切り替えや、プログレスバーによる進捗確認に対応。

## テストと検証
- 座標系丸め誤差（Round-trip）テストや、合成データを用いた単体テストを完備しています。
  ```bash
  pytest -q
  ```

## 最近のアップデート
- **2026-03**: RTSTRUCT読込機能および ROI (ポリゴンマスク) 限定のガンマ解析機能を完全統合。GUIからのROI指定に対応。
- **2026-03**: DICOM 世界座標 (LPS) と画像インデックス間の変換ロジックを刷新し、斜めスライス等に対する座標変換往復テスト (Round-trip tests) を実装しました。
- **2025-10**: Local gamma オプション (`--gamma-type local`) の追加。OpenSpec ドキュメントの導入。

## **免責事項 / Disclaimer**

## **⚠️ 重要：使用上の注意 (Important Notice)**

### **1\. 本ソフトウェアの位置づけ (Software Status)**

本ソフトウェアは、作者個人の研究成果として公開されているものであり、**医療機器としての承認（薬機法等）を受けたものではありません。**

標準的な治療計画装置（TPS）や検証用ファントム、測定機器を**置き換えるものではありません。**

This software is published as a personal research outcome and **is not a certified medical device** under any regulation. It does not replace, and is not intended to replace, any commercial Treatment Planning System (TPS), phantom, or measurement device.

### **2\. 使用の制限と責任 (Limitation of Use and Liability)**

本ソフトウェアは、その設計上、**研究および教育目的**での利用を意図しています。

本ソフトウェアを、**患者の診断、治療計画の立案、あるいは治療の品質保証（QA）など、臨床判断に直接関わるプロセスに使用することはできません。**

医学物理士などの専門家が、本ソフトウェアを臨床業務の「**参考用**」として（例：セカンドチェックの補助、研究的解析など）使用することもあるかもしれません。その場合であっても、使用者は以下の点に同意する必要があります：

1. **使用者の全責任:** ソフトウェアを使用する前に、自身の施設環境で十分な検証（コミッショニング）を行い、その正確性、特性、限界をすべて把握すること。  
2. **結果の保証の否認:** 本ソフトウェアが出力する計算結果の妥当性、正確性について、作者は一切保証しません。  
3. **最終責任の所在:** 本ソフトウェアを使用したこと、またはその結果を参照したことにより生じる**すべての臨床判断と、それに伴う一切の結果について、作者は一切の責任を負わず、使用者が単独で全責任を負うものとします。**

### **3\. 無保証 (No Warranty)**

本ソフトウェアは、MITライセンスに基づき「**現状有姿 (AS IS)**」で提供されます。作者は、本ソフトウェアの正確性、完全性、特定目的への適合性、非侵害について、明示的か黙示的かを問わず、一切の保証を行いません。

### **4\. 免責 (Limitation of Liability)**

作者または著作権者は、本ソフトウェアの使用、誤用、または使用不能から生じる、いかなる直接的、間接的、付随的、特別、懲罰的、結果的な損害（データの損失、逸失利益、業務の中断、あるいは患者への危害を含むがこれに限られない）についても、一切の責任を負いません。
