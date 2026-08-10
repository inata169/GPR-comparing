# Windows TPS PC オフライン導入ガイド

## 対象と前提

この手順は、インターネット未接続の Windows TPS PC に、USBストレージ経由で GPR-comparing を導入するためのものです。患者データはバンドルやスモークテストに含めません。

- 対象OS: 64-bit Windows 10/11
- 固定Python: CPython 3.12.10 64-bit（Python 3.12系列）
- 導入先: 展開したバンドル内の `app/.venv` 専用仮想環境
- 通信: オフラインPC上のインストール・起動・スモークテストは外部通信不要
- 権限: 通常ユーザーでの導入を基本とし、管理者権限は不要

Python 3.12.10を採用する理由は、プロジェクトCIがPython 3.12を対象としており、Windows用の公式フルインストーラを同梱できるためです。通常のソース実行はPython 3.9+と記載されていますが、このオフラインバンドルはPython 3.12 x64だけをサポートします。

## 依存関係

実行時の直接依存は次のファイルを正とします。

- `REQUIREMENTS.txt`: pydicom、NumPy、SciPy、Numba、Matplotlib、ReportLab
- `requirements-fast-viewer.txt`: pyqtgraph、PySide6
- `offline/requirements-offline.txt`: 上記2ファイルをまとめるオフライン配布用入口
- `offline/constraints-py312-win64.txt`: Windows x64/Python 3.12で実検証した直接・推移依存の固定バージョン

オンライン収集時に `pip download --only-binary=:all:` で直接・推移依存を解決し、Windows x64/Python 3.12で実際にローカルwheelだけから仮想環境へインストールできることと、主要importを確認します。

## 1. オンラインPCでUSB用一式を作る

### 前提

- このリポジトリのクリーンなGit作業ツリー
- 64-bit Windows
- 64-bit Python 3.12（バンドル作成時のwheel解決・検証用）
- Git、PowerShell 5.1以降
- python.orgとPython Package Indexへ接続可能

PowerShellでリポジトリルートへ移動し、次を実行します。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\offline\build_offline_bundle.ps1
```

Python 3.12の実行ファイル名を明示する場合:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\offline\build_offline_bundle.ps1 -PythonExe C:\Python312\python.exe
```

生成物:

```text
dist/offline/
├─ GPR-comparing-offline-win64-py312/
│  ├─ app/                         リポジトリのGit管理ファイル
│  ├─ python/                      署名確認済み公式Pythonインストーラ
│  ├─ wheelhouse/                  依存wheel一式
│  ├─ INSTALL_OFFLINE.bat
│  ├─ LAUNCH_GPR_COMPARING.bat
│  ├─ RUN_SMOKE_TEST.bat
│  ├─ VERIFY_BUNDLE.ps1
│  ├─ BUNDLE_INFO.txt
│  └─ SHA256SUMS.txt
└─ GPR-comparing-offline-win64-py312.zip
```

作成処理は次を自動確認します。

1. ビルド用PythonがWindows x64のPython 3.12である
2. Git作業ツリーがクリーンで、バンドルが特定コミットと一致する
3. CPythonインストーラのAuthenticode署名元がPython Software Foundationである
4. 必要なwheelがすべてバイナリ形式で収集できる
5. 一時仮想環境へ `--no-index` でインストールできる
6. 主要ライブラリをimportできる
7. 全同梱ファイルのSHA-256が一致する

生成したZIPをUSBストレージへコピーします。`dicom/`、`output/`、`.venv/`、`.git/`などGit管理外のデータは収集されません。

## 2. オフラインTPS PCへ導入する

1. USB上のZIPを、TPS PCのローカルで書込み可能な短いパス（例: `C:\GPR-comparing-offline`）へコピーします。
2. ZIPをWindows標準機能などで展開します。USB上から直接実行せず、ローカルディスクへ展開してください。
3. 展開された `GPR-comparing-offline-win64-py312` 内の `INSTALL_OFFLINE.bat` をダブルクリックします。
4. `[SUCCESS] GPR-comparing was installed and verified.` が表示されることを確認します。

インストーラは次を行います。

- SHA-256によるバンドル完全性確認
- バンドル内 `runtime/python312` へのPython 3.12.10ユーザー領域インストール
- `app/.venv` 専用仮想環境の作成
- `PIP_NO_INDEX=1`、`PIP_CONFIG_FILE=NUL`、`--no-index --find-links wheelhouse`を指定したwheel導入
- Python 3.12 x64と主要importの確認
- 非患者合成DICOMによるスモークテスト

既にPCへ導入されているPythonやグローバルsite-packagesは使いません。

## 3. 起動する

`LAUNCH_GPR_COMPARING.bat` をダブルクリックします。起動バッチは `app/.venv/Scripts/python.exe` の存在を確認し、専用環境だけを使用します。

初回のGUI起動後、次を手動確認してください。

1. メインGUIが表示される
2. `Header Compare`、`2D Gamma`、`3D Gamma`の操作項目が表示される
3. `3D Viewer`を選択したときFast Viewerウィンドウが表示される
4. TPS PCのアプリケーション制御・ウイルス対策でPythonまたはQtが遮断されていない

GUI表示とGPU/画面ドライバの相性は無人スモークテストでは完全には検証できないため、この手動確認が必要です。

## 4. 再検証する

`RUN_SMOKE_TEST.bat` をダブルクリックします。患者情報を含まない合成データを毎回新規生成し、次を確認します。

- Python 3.12 x64および全実行時依存のimport
- Fast ViewerのPySide6/pyqtgraph依存読込
- 合成CT、RTDOSE、RTSTRUCTの生成と読込
- RTDOSEヘッダ比較
- 2D Gamma解析とJSON、Markdown、PDF、Gamma画像、線量差画像の生成
- 3D Gamma解析
- 同一線量に対する99.99%以上のPass Rate

結果はバンドル直下の `smoke_output/YYYYMMDD_HHMMSS/` に保存されます。成功時は `SMOKE_TEST_RESULT.json` に `"status": "PASS"` が記録されます。

## トラブルシューティングと制約

- `SHA-256 mismatch`: USBコピーまたは展開時に破損しています。ZIPを再コピーしてください。
- Pythonインストール失敗: TPS PCのアプリケーション制御ポリシーを管理者へ確認してください。
- `python_install.log`: Python本体の無人導入に失敗した場合、バンドル直下のこのログで終了理由を確認してください。既に同じPython 3.12系列がユーザーインストールされているPCでは、公式インストーラが保守モードとして動作する場合があります。
- wheel導入時にネットワークへ接続しようとする表示がある: このバッチでは通信を無効化しています。必ず同梱 `INSTALL_OFFLINE.bat` を使用してください。
- Qt/GUIが起動しない: 画面ドライバ、リモートデスクトップ制限、セキュリティ製品のログを確認してください。
- バンドル容量: PySide6/Qtと数値計算wheelを含むため、数百MB規模になることがあります。
- Visual C++ランタイム: Pythonおよび一部wheelがOSのMicrosoft Visual C++ランタイムに依存する場合があります。対象TPS PCの標準構成で不足する場合は、施設承認済みのランタイムを別途導入してください。

本スモークテストは導入健全性の確認であり、臨床受入試験や施設固有のコミッショニングを代替しません。臨床使用前に、施設承認済みの非患者QAデータと期待値で別途検証してください。
