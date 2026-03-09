# TODO (Next Actions)

Date: 2026-03-09

High priority
- [x] **軽量化EXEのビルド成功とエラー修正**
  - [x] `scipy.special` の `ModuleNotFoundError` を解決
  - [ ] `rtgamma_cli.exe` での PDF生成テスト（PIL/matplotlibの動作確認）
  - [ ] `gamma_viewer.exe` での 3D表示・モード切替テスト（Tkinter/scipy.specialの動作確認）
- [ ] **マルチプレーンビューア (Axial/Sagittal/Coronal同時表示) の実装**
  - [ ] 2x2 グリッドレイアウトへの更新
  - [ ] クロスヘア連動インタラクションの追加

Tier 1: コア品質と信頼性 (Completed)
- [x] バッチ処理一元化 (`rtgamma/batch.py`)
- [x] PDF レポート自動生成 (`rtgamma/pdf_report.py`)
- [x] RTPLAN ヘッダ比較統合
- [x] CI テストカバレッジ強化 (E2E, JSONSchema, Regression)

Tier 2: ユーザー体験の飛躍
- [x] GUI ワンクリック PDF 出力
- [x] GUI 設定解説ツールチップ (Hover ToolTips)
- [ ] **マルチプレーン画面連動ビューアの実装**
- [ ] Webベース GUI 試作

Tier 3: 高度解析機能
- [x] ガンマヒストグラム・累積パス率統計
- [x] 3DVH クロスバリデーション (Prostate/BreastBolus)
- [x] interp_fraction 感度実験と最適値確定
- [ ] 不確かさのブートストラップ推定

Tier 4: 運用エコシステム
- [x] PyInstaller による EXE パッケージ化
- [x] 最小構成 ZIP 配布パッケージ作成
- [ ] **EXE 容量のさらなる軽量化 (v0.7.1 1.2GB → 514MB 現状)**
- [ ] 英語・日本語の完全バイリンガル化
- [ ] ユーザーマニュアル・チュートリアル作成
