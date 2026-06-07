# rtgamma — DICOM RTDOSE ガンマ解析 (2D/3D)

![CI](https://github.com/inata169/GPR-comparing/actions/workflows/ci.yml/badge.svg)

DICOM RTDOSE ペアに対する高速で再現性の高いガンマ解析ツールです。堅牢なジオメトリ処理、CLI/GUI サポート、軽量なドキュメントと仕様を備えています。

## 主な機能
- **高精度な空間整合**: DICOMタグ (IPP/IOP/PixelSpacing/GFOV) に厳密に基づく座標投影。ROIマスクも線量グリッドに正確にマッピングします。
- **2D/3Dガンマ解析**: 高速な3Dカーネル (Numba) および特定スライスのみを計算する軽量な2D経路。
- **Sub-voxel Interpolation**: 金標準 (SunNuclear 3DVH等) に匹敵する精度を実現する、trilinear内挿ベースの Expanding shell サブボクセル探索アルゴリズム (`--interp-fraction` 対応)。
- **3D ガンマビューア**: CT、線量分布、ガンママップ、Structure輪郭線を重ねて1つのインターフェースで確認できるインタラクティブビューア。Pass/Fail表示やDose Ratio表示にも対応。
- **Fast 3D Viewer**: PyQtGraph + PySide6 による高速ビューア。GUIの3D Viewer起動経路はFast固定です。
- **RTPLAN 統合ヘッダ比較**: RTDOSE に加え、RTPLAN から Isocenter 座標や SAD/SSD を読み取り、プラン間のズレを客観的に出力可能。
- **シフト最適化**: 計算領域を粗密2段階で自動走査し、最適な空間シフト（位置ズレ）を探索。
- **ROI 限定解析**: RTSTRUCT ファイルと ROI 名を指定することで、特定構造（PTV, GTV など）内のガンマパス率（GPR）や統計値を算出可能。
- **Global / Local ガンマ**: 基準線量最大値（Global）または各ボクセル値（Local）に基づくガンマ計算の切り替え。
- **使いやすい GUI**: PowerShell / WinForms ベースの GUI サポート（ダークテーマ、直接数値入力対応）。

## インストール
- 要件: Python 3.9 以上
- 依存ライブラリ:
  ```bash
  pip install pydicom numpy scipy matplotlib numba
  ```
- Fast 3D Viewer をSource/Python環境で使う場合:
  ```bash
  pip install -r requirements-fast-viewer.txt
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
- **起動**: `run_gui_python.bat` をダブルクリック（または PowerShell から `scripts/run_gui.ps1` を実行）
- 3D Viewer は `Fast` 固定で起動します。保存済み設定に `viewer_type=legacy` が残っていてもFast Viewerを起動します。
- Fast Viewer起動に失敗した場合は、依存関係やログパスを含む診断メッセージを表示します。Legacy fallbackは提示しません。

### 基本的な使い方
1. **必須項目の選択**
   - **Ref RTDOSE / Eval RTDOSE**: 比較したい基準線量と評価線量のDICOMファイルを選択します。
   - **Output Folder**: 結果（レポート、CSV、画像等）の保存先フォルダを指定します。
2. **ROI 限定解析 (オプション)**
   - **RTSTRUCT**: 輪郭情報が含まれる DICOM ファイルを選択します。
   - **ROI Name**: 評価対象の ROI 名を入力します（例: `PTV` や `GTV,Rectum` のようにカンマ区切りで複数指定が可能。空欄の場合は含まれる全ROIが抽出されます）。
3. **解析設定の選択**
   - **Action**: 全体の3D解析、特定の2D断面解析、3Dガンマビューアの起動、またはヘッダ情報の比較から実行モードを選択します。
   - **Viewer**: 3D ViewerはFast Viewer固定で起動します。
   - **Clinical Preset (旧)**: 現在は DTA (mm), DD (%), Cutoff (%) の各評価基準を直接テキストボックスに入力する方式です。
4. **オプション設定**
   - **Optimize shift**: チェックを入れると、位置ズレを補正して最も合格率が高くなる「シフト量」を自動探索します。
   - **Local gamma**: 各ボクセルの線量値を基準とする Local ガンマで計算します（オフの場合は Global ガンマ）。
   - **Sub-voxel Interp**: 高精度な trilinear サブボクセル内挿を行うための分割数（デフォルトおよび推奨: 10）。解像度計算をスキップする場合は1に設定します。
5. **解析の実行**
   - 「Run」ボタンをクリックすると計算が始まり、プログレスバーとリアルタイムログで進捗が確認できます。
   - 計算完了後、自動的に Markdown 形式のサマリレポートが開きます。
   - 💡 よく使う設定は「Save Settings」ボタンで保存し、次回起動時に復元できます。

### GUI 実行例

![rtgamma GUI after successful 3D gamma analysis](docs/openspec/images/Gui-screenshot.png)

上の例では、合成RTDOSE/RTSTRUCTデータで3D Gammaを実行し、PDF/NPZ/SQLite DBの保存まで完了しています。

### 3D Viewer

- **Fast Viewer**: PyQtGraph + PySide6版。描画が高速で、CT、Structure、Gamma / Pass-Fail / Ref Dose / Eval Dose / Dose Diff / Dose Ratio overlay、ROI別GPR、現在点のHU/Ref/Eval/Diff/Gamma/Pass-Fail readoutに対応します。
- Legacy Viewer実装と配布スクリプトは互換性維持のため残っていますが、GUIの3D Viewer起動経路では使用しません。
- 3断面は共通のcursor stateを共有します。Sagittal / Coronalも物理mmスケールで表示し、HFS前提の orientation label (`L/R`, `A/P`, `S/I`) を各断面に表示します。
- 右下パネルでは、読み込みデータ、CT/Structure/Info表示、ROI visibility、overlay mode、zoom操作をコンパクトに確認・変更できます。`File` / `View` / `Help` メニューから読み込み情報、表示切替、操作Helpも確認できます。
- Fast Viewerの基本操作:
  - クリック: 共有cursorをクリック位置のvoxelへ移動
  - ホイール / slice slider: 各断面のslice移動、`Shift + ホイール`: 高速slice移動
  - `Ctrl + ホイール` / `+` / `-`: 拡大 / 縮小
  - 中ボタンドラッグ: Pan
  - `0` / `F`: 全断面の表示範囲reset / fit
  - `H` / `?`: 操作Help表示
  - `I`: 現在点情報の表示/非表示
  - カーソルキー: active plane上でcursorを移動
  - `O`: overlay表示切替、`C`: CT表示切替、`S`: Structure表示切替
  - `G/P/R/E/X/D`: Gamma / Pass-Fail / Ref Dose / Eval Dose / Dose Diff / Dose Ratioへ切替
- Fast Viewerの表示方向補正は表示変換で行い、voxel readoutやRTSTRUCT座標変換は変更しません。現在点の値は表示補間ではなくsource voxel arraysから取得します。

## 配布パッケージ
- **Source/Python**: `run_gui_python.bat` で起動。3D ViewerはFast固定です。
- **Fast ZIP**: `run_gui_fast_exe.bat` で起動する大容量EXE配布。`gamma_viewer_fast`、PySide6/Qt、pyqtgraphを同梱します。
- **Legacy ZIP / Legacy Viewer**: 既存資産として残っていますが、今後のGUI 3D Viewer運用では主対象外です。
- Fast ZIPはPyInstaller `onedir` で作成し、Qt/PySide6バイナリは改変しません。`NOTICE.txt`、`THIRD_PARTY_LICENSES/`、`bundled_manifest.txt` を同梱します。
- アプリケーションソースコードはMITライセンスですが、同梱第三者コンポーネントは各ライセンスに従います。PySide6/QtはMITではありません。

## 🛠 外部ツールとの連携
本ツールの GUI は起動時に `config/gui_config.ini` を読み込みます。外部スクリプト（`dicom-phits_inp` など）からこの INI ファイルを事前に書き換えることで、特定の DICOM ファイルや解析結果を選択した状態でシームレスにビュアーを起動することが可能です。

**主な設定項目 (`[Paths]` セクション):**
- `ref_dose`: 参照線量のパス
- `eval_dose`: 評価線量のパス
- `ct_dir`: CT 画像ディレクトリのパス
- `output_dir`: 解析結果（`gamma_map.npz` 等）が含まれるディレクトリのパス

### 💡 ガンマパス率が低い場合の推奨ワークフロー
パス率が著しく低い場合、座標系やセットアップの違いが原因であるケースがあります。
1. **Header Compare**: `Action` を `Header Compare` にし、RTDOSE (可能なら RTPLAN も) のヘッダを比較します。Isocenter のズレや、**SSD (Source-to-Surface Distance) vs SAD (Source-to-Axis Distance) の定義の違い**により、初期座標(IPP)が数十mm〜100mm規模でズレて出力されているケース（例: `-114mm` のズレ等）を発見できます。
2. **Absolute**: `Optimize shift` OFF でそのまま実行し、座標差を把握します。
3. **Optimize Shift**: ズレが判明している場合は `Optimize shift` を ON にして補正計算を行います。
*(詳細は [TEST_PLAN.md](TEST_PLAN.md) の Recommended Workflow を参照してください)*

## テストと検証
- 座標系丸め誤差（Round-trip）テストや、合成データを用いた単体テストを完備しています。
  ```bash
  pytest -q
  ```

## 最近のアップデート
- **2026-03**: Sub-voxel Interpolation の独自実装を追加し、SunNuclear 3DVH と遜色ない解析精度（±1pp圏内）を達成。
- **2026-03**: 3D ガンマビューアの大幅強化（Ref/Eval/Ratio線量重畳、カラーバー、UI刷新など）。
- **2026-03**: RTPLAN DICOM の統合ヘッダ比較をサポート。
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
