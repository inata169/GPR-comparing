# TODO (Next Actions)

Date: 2026-03-13

High priority
- [x] **ポータブル実行環境 (EXE版GUI) の構築と安定化 (完了)**
- [x] **DVH（線量体積ヒストグラム）計算・比較機能の実装 (完了)**
- [x] **ビルドの安定性復旧と実行時エラーの解消 (完了)**
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
