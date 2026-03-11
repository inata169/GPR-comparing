# TODO (Next Actions)

Date: 2026-03-11

High priority
- [x] **ビルドの安定性復旧と実行時エラーの解消 (完了)**
- [x] `rtgamma_cli.exe` での `scipy.special` / `pydicom` 等のインポートエラーを解消
- [x] `gamma_viewer.exe` のビルド成功とヘルプ表示の動作確認
- [x] `rtgamma_cli.exe` での実データ解析・PDF生成完遂の確認
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
