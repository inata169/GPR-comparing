# TODO (Next Actions)

Date: 2026-06-05 (Fast Viewer final operational check)

High priority
- [x] **Fast Viewer既定化・選択式運用・Fast EXE別配布の実装**
  - [x] Source/Python mode は保存設定なしでFast既定にする
  - [x] Legacy ZIP は保存設定なしでLegacy既定にする
  - [x] Fast ZIP用 `run_gui_fast_exe.bat` と `gamma_viewer_fast.spec` を追加する
  - [x] `scripts/gui_config_common.ps1` で設定読み込み・merge・viewer_type解決を共通化する
  - [x] Fast起動失敗時に明示エラーとLegacy起動導線を出す
  - [x] Fast ZIPに `NOTICE.txt` / `THIRD_PARTY_LICENSES/` / `bundled_manifest.txt` を生成するパッケージ処理を追加する
- [x] **Fast ZIPの実ビルド・配布検証**
  - [x] `scripts/build_exe.ps1 -FastViewer` で `dist/gamma_viewer_fast` を生成する
  - [x] `scripts/package_release.ps1 -DistributionMode Fast` でFast ZIPを生成する
  - [x] `bundled_manifest.txt` で `platforms/qwindows.dll` 配置とGPL-only Qt module非同梱を確認する
  - [ ] Python未インストールWindows環境でFast EXE起動を確認する
- [x] **Fast Viewer表示方向・操作性修正**
  - [x] PyQtGraph表示でAxi/Cor/Sag画像が小さく見え、クリック位置と画像がずれる問題を補正する
  - [x] Sagittal / Coronal の上下反転を補正する
  - [x] Axial の左右反転を補正する
  - [x] Axi/Cor/Sag の拡大縮小ボタン、`+`/`-`/`0` キー、カーソルキーslice操作、overlay/CT/Structure/overlay modeショートカットを追加する
- [x] **README改訂と作業終了処理**
  - [x] READMEにFast Viewer既定化、Legacy/Fast ZIP、Fast Viewer操作、第三者ライセンス注意を反映する
  - [x] `99-daily-summary.md` / `99-handover_context.md` / OpenSpec関連文書の終了時更新を行う
- [ ] **Fast Viewerの実運用前最終確認**
  - [ ] PR #11 / #12 の修正後に、PROSTATEデータでFast Viewerを再起動する
  - [ ] Gamma overlayで `gamma=0` 領域が消えないことを確認する
  - [ ] 古い/別gridの `gamma3d.npz` でもRTSTRUCT付き起動で落ちないことを確認する
  - [ ] 修正後Fast ZIPでAxi左右、Sag/Cor上下、クリック位置、ズーム、キーボード操作を別PCで再確認する
- [ ] **GUI経由の運用確認**
  - [ ] `run_gui_python.bat` でGUIを起動する
  - [ ] Viewerを `Fast` にして3D Viewerを起動する
  - [ ] Legacy / Fast の切替が期待通り動くことを確認する
- [x] **Fast Viewer運用方針の最終判断**
  - [x] Source/Python と Fast ZIP はFast既定にする
  - [x] Legacy/Fast選択式のまま運用する
  - [x] EXE化はPySide6/Qt込みのFast ZIPを通常Legacy ZIPと分けて配布する
- [x] **3D Viewer軽量キャッシュ高速化PRの完了**（PR #6 merged）
- [x] **3D Viewerクロスポイント値表示の完了**（PR #7 merged）
- [x] **PyQtGraph版 Fast 3D Viewer PoC の追加**（PR #8 merged）
  - [x] `scripts/gamma_viewer_fast.py` を追加
  - [x] `.venv` セットアップ用 `setup_fast_viewer_venv.bat` を追加
  - [x] `run_viewer_fast_test.bat` を追加
  - [x] OpenSpecへPoC範囲・非範囲・操作仕様を反映
- [x] **Fast 3D Viewer PoC: 断面方向と旧Viewer比較の検証**（Issue #9）
  - [x] 旧ViewerとFast Viewerで同一中心sliceを比較
  - [x] axial / sagittal / coronal の上下左右反転・断面入れ替わりを確認
  - [x] click / wheel / slider のcrosshair同期と `HU / Ref / Eval` ラベル同期を確認
  - [x] 臨床で普段扱うビューア相当の速度感で、Axi/Cor/Sag のスクロールも問題なしと目視確認
- [x] **Fast Viewer旧Viewer相当サイドバー機能の追加**
  - [x] Ref/Evalファイル名、CT/Structure/ROI checkbox、Criteria/Cutoff、ROI GPRを表示
  - [x] `Gamma`, `Pass/Fail`, `Ref Dose`, `Eval Dose`, `Dose Ratio` のoverlay切替を追加
  - [x] `--rtstruct` / `--roi` に対応し、PROSTATE用 `run_viewer_fast_test.bat` からRTSTRUCTを渡す
- [x] **Fast Viewer統合方針の決定とGUI選択式統合**
  - [x] 旧Viewerを残し、GUIから `Legacy` / `Fast` を選択できる方式に決定
  - [x] `config/gui_config.ini` 保存時に `Analysis/viewer_type = legacy|fast` を保持
  - [x] Fast選択時は `.venv\Scripts\python.exe` 優先で `scripts/gamma_viewer_fast.py` を起動
- [x] **ポータブル実行環境 (EXE版GUI) の構築と安定化 (完了)**
- [x] **DVH（線量体積ヒストグラム）計算・比較機能の実装 (完了)**
- [x] **ビルドの安定性復旧と実行時エラーの解消 (完了)**
- [x] **CI（Ruff Lint/GitHub Actions）の安定化完了 (v0.8.7)**
- [x] リモートリポジトリ（GPR-comparing / dicom-phits_inp）の同期完了
- [x] `rtgamma_cli.exe` での `scipy.special` / `pydicom` 等のインポートエラーを解消
- [x] `gamma_viewer.exe` のビルド成功とヘルプ表示の動作確認
- [x] `rtgamma_cli.exe` での実データ解析・PDF生成完遂の確認
- [x] **マルチプレーンビューア (Axial/Sagittal/Coronal同時表示) の実装 (完了)**
  - [x] LineCollection による描画高速化とクロスセクション表示の実装
  - [x] 2x2 グリッドレイアウトへの更新
  - [x] 3Dカーソル同期・各面独立スクロールの実装
  - [x] 各面への Slice GPR オーバーレイ表示
  - [x] 設定の永続化 (JSON保存・復元)
  - [x] 臨床向けUI視認性強化（チェックボックスのコントラスト改善、文字色調整、**ファイル名・解析条件の常時表示**）
- [x] **各断面への独立スクロールバー (Slider) とスライス番号/mm位置入力 (TextBox) の実装**
- [x] **サジタル・コロナル画面の上下方向 (Sup-Inf) 正位化とクロスカーソル同期の修正**
- [x] **2D断面解析時の RTSTRUCT マスク適用バグ (IndexError) の修正**

Tier 1: コア品質と信頼性 (Completed)
- [x] バッチ処理一元化 (`rtgamma/batch.py`)
- [x] PDF レポート自動生成 (`rtgamma/pdf_report.py`)
- [x] RTPLAN ヘッダ比較統合
- [x] CI テストカバレッジ強化 (E2E, JSONSchema, Regression)

Tier 2: ユーザー体験の飛躍
- [x] GUI ワンクリック PDF 出力
- [x] GUI 設定解説ツールチップ (Hover ToolTips)
- [x] **マルチプレーン画面連動ビューアの実装**（完了）
- [x] Webベース GUI 試作 (現在一部計画中)
- [x] **DVH（線量体積ヒストグラム）計算・比較機能の実装** (完了)

Tier 3: 高度解析機能
- [x] ガンマヒストグラム・累積パス率統計
- [x] 3DVH クロスバリデーション (Prostate/BreastBolus)
- [x] interp_fraction 感度実験と最適値確定
- [x] **GPR計算カーネルの高速化**（ノン補間・補間両モードでの距離順探索・早期終了の実装により2.6倍〜高速化完了）
- [ ] 不確かさのブートストラップ推定

Tier 4: 運用エコシステム
- [x] PyInstaller による EXE パッケージ化
- [x] 最小構成 ZIP 配布パッケージ作成
- [ ] **EXE容量の本格削減（クリーンvenv + exclude + UPX で200〜250MB目標）**
  - [ ] 専用ビルド環境（venv）の構築スクリプト作成
  - [ ] 不要モジュールの exclude 設定精査
  - [ ] UPX 圧縮の導入検討
- [x] **出力形式 PDF 主軸化**（エンドユーザー向けレポートを MD→PDF へ移行） (完了)
- [ ] 英語・日本語の完全バイリンガル化
- [ ] ユーザーマニュアル・チュートリアル作成
