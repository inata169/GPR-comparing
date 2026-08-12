# Windows TPS PC オフライン導入ガイド

## 対象と前提

この手順は、インターネット未接続の Windows TPS PC に、USBストレージ経由で GPR-comparing を導入するためのものです。患者データはバンドルやスモークテストに含めません。

- 対象OS: 64-bit Windows 10/11
- Python: 既存の互換CPython 3.12 64-bit、または同梱CPython 3.12.10 64-bit
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
7. GUIが更新する `app/config/gui_config.ini` を除き、同梱ファイルのSHA-256が一致する

生成したZIPをUSBストレージへコピーします。`dicom/`、`output/`、`.venv/`、`.git/`などGit管理外のデータは収集されません。

## 2. オフラインTPS PCへ導入する

1. USB上のZIPを、TPS PCのローカルで書込み可能な短いパス（例: `C:\GPR-comparing-offline`）へコピーします。
2. ZIPをWindows標準機能などで展開します。USB上から直接実行せず、ローカルディスクへ展開してください。
3. 展開された `GPR-comparing-offline-win64-py312` 内の `INSTALL_OFFLINE.bat` をダブルクリックします。
4. `[SUCCESS] GPR-comparing was installed and verified.` が表示されることを確認します。

インストーラは次を行います。

- SHA-256によるバンドル完全性確認
- 外部のPython 3.12 x64が既に存在する場合、公式Pythonインストーラを起動せず安全停止
- 既存の互換CPython 3.12 x64がある場合は、それを変更せず `app/.venv` の作成元としてのみ使用
- 互換Pythonがない場合は、バンドル内 `runtime/python312` へPython 3.12.10をユーザー領域インストール
- `app/.venv` 専用仮想環境の作成
- `PIP_NO_INDEX=1`、`PIP_CONFIG_FILE=NUL`、`--no-index --find-links wheelhouse`を指定したwheel導入
- Python 3.12 x64と主要importの確認
- 非患者合成DICOMによるスモークテスト

既にPCへ互換CPython 3.12 x64が導入されている場合、その実行ファイルは専用仮想環境 `app/.venv` の作成元としてのみ使用します。既存Python本体、グローバルsite-packages、PATH、レジストリは変更しません。依存パッケージは専用仮想環境へ同梱wheelhouseからのみ導入します。実行可能な互換Pythonがなく、Python 3.12の登録情報だけが残っている場合は、既存環境との衝突を避けるため安全停止します。

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
- 大規模3D Gammaでは、GUIの既定 `Numba (fast full-volume GPR)` と `Sub-voxel Interp = 4` を使用してください。`PyMedPhys (reference / slow 3D)` は参照計算用で、数十分以上かかる場合があります。`Threads = 0` はNumbaの自動スレッド選択です。
- GUIの3D GammaはViewer用の`gamma3d.npz`、`diff3d.npz`、`run3d.json`を出力フォルダへ常に保存します。同じ出力フォルダを選んだまま3D Viewerを開くとGamma/Pass-Failを検証済みキャッシュから読み込みます。
- 同一線量に対する99.99%以上のPass Rate

結果はバンドル直下の `smoke_output/YYYYMMDD_HHMMSS/` に保存されます。成功時は `SMOKE_TEST_RESULT.json` に `"status": "PASS"` が記録されます。

## 検証状況（2026-08-10）

- Ruff: 合格
- pytest: `45 passed, 7 skipped`
- GitHub Actions: Windows/Ubuntu、Python 3.10/3.11/3.12の全6ジョブ成功
- 23個の固定wheelを `--no-index` で導入し、主要importに成功
- 245個の不変ファイルについてSHA-256検証に成功
- `config/gui_config.ini` を変更した後も、同ファイルを除く完全性検証に成功
- 非患者合成DICOMによるHeader Compare、2D/3D Gamma、帳票・画像生成に成功
- 既存Python 3.12.10があるWindows 11 Home PCで、既存Pythonを変更せず専用venvの作成元として選択できることを確認
- 最終Codexレビュー: 重大な問題なし

Python 3.12未導入のクリーンWindows PCが現在ないため、初回完全導入の受入試験は保留中です。詳細な開発記録と配布ZIPのSHA-256は [Progress Log — 2026-08-10](PROGRESS_2026-08-10.md) を参照してください。

## トラブルシューティングと制約

- `SHA-256 mismatch`: USBコピーまたは展開時に破損しています。ZIPを再コピーしてください。
- Pythonインストール失敗: TPS PCのアプリケーション制御ポリシーを管理者へ確認してください。
- `[SAFETY STOP]`: Python 3.12の登録情報はありますが、実行可能な互換CPython 3.12 x64が見つかりません。壊れた登録や不完全なアンインストールを確認してください。同梱Pythonインストーラは既存環境を保護するため起動されません。
- `python_install.log`: Python本体の無人導入に失敗した場合、バンドル直下のこのログで終了理由を確認してください。既に同じPython 3.12系列がユーザーインストールされているPCでは、公式インストーラが保守モードとして動作する場合があります。
- wheel導入時にネットワークへ接続しようとする表示がある: このバッチでは通信を無効化しています。必ず同梱 `INSTALL_OFFLINE.bat` を使用してください。
- Qt/GUIが起動しない: 画面ドライバ、リモートデスクトップ制限、セキュリティ製品のログを確認してください。
- バンドル容量: PySide6/Qtと数値計算wheelを含むため、数百MB規模になることがあります。
- Visual C++ランタイム: Pythonおよび一部wheelがOSのMicrosoft Visual C++ランタイムに依存する場合があります。対象TPS PCの標準構成で不足する場合は、施設承認済みのランタイムを別途導入してください。

本スモークテストは導入健全性の確認であり、臨床受入試験や施設固有のコミッショニングを代替しません。臨床使用前に、施設承認済みの非患者QAデータと期待値で別途検証してください。

## ライセンスと配布前監査

GPR-comparing のアプリケーションコードと文書は MIT License です。ZIP 直下の
`LICENSE` で全文を確認できます。Python、Qt / PySide6、wheelhouse 内の Python
パッケージはそれぞれ固有の第三者ライセンスに従います。

ライセンスおよび配布に関する連絡先は、同梱の `offline/NOTICE.txt` を参照してください。

配布前にはビルド処理が次を自動確認します。

1. CPython 3.12.10 x64 公式インストーラーの Python Software Foundation による
   Authenticode 署名と、Python 公式 SPDX 文書に記載された SHA-256
2. すべての wheel の `.dist-info/METADATA` にある名前、正確なバージョン、
   ライセンス情報、依存関係、配布元 URL
3. すべての wheel に空でないライセンス・著作権・NOTICE 等の資料があること
4. PySide6 メタパッケージと PySide6_Addons がなく、実際に使用する
   PySide6_Essentials、shiboken6、pyqtgraph のみに縮小されていること
5. 未使用の GPL 専用 Qt モジュールが wheelhouse に残っていないこと
6. 患者 DICOM、ローカルの `config/gui_config.ini`、計算結果、PHITS 関連実行
   ファイル、秘密情報が ZIP にないこと

1件でもライセンス情報を確認できない場合、ZIP 作成は対象 wheel を表示して失敗
します。パッケージ名からライセンスを推測したり、不明な項目を黙って無視したり
しません。wheel は ZIP アーカイブとして読み取り、収集処理ではコードを実行しません。

ZIP 直下の確認場所は次のとおりです。

- `LICENSE`: GPR-comparing の MIT License
- `NOTICE.txt`: Python、Qt / PySide6、除外対象、用途制限に関する配布通知
- `THIRD_PARTY_MANIFEST.json`: 全 wheel の名称、バージョン、ライセンス、配布元、
  SHA-256、ライセンス資料への対応
- `THIRD_PARTY_LICENSES/`: wheel 内から収集した原文、PSF License、Python 公式
  SPDX、Qt / PySide6 の LGPLv3・GPLv3・GPLv2・Qt GPL Exception

Fast Viewer は Qt for Python / PySide6 Community Edition の QtCore、QtGui、
QtWidgets を使用します。個々の Qt / PySide6 ライブラリバイナリは改変しません。
上流 PySide6_Essentials wheel のアーカイブから未使用の GPL 専用モジュールのみを
除き、`RECORD` を再生成します。元 wheel と同梱 wheel の SHA-256、除外した全パス、
バイナリ非改変の記録は `THIRD_PARTY_MANIFEST.json` に残ります。この配布物は、
LGPL 対象ライブラリの差し替えや、変更したライブラリをデバッグするためのリバース
エンジニアリングを禁止する追加条件を設けません。

PHITS、RT-PHITS、phits2dicom、Sumtally は同梱しません。利用者自身が権利者の
指定する正規の方法で取得してください。患者 DICOM、施設・ベンダーの非公開
データ、認証情報、ローカル設定、計算結果も同梱しません。本ソフトウェアは教育・
研究用であり、臨床判断や患者固有 QA に使用しないでください。
