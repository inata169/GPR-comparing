# OpenSpec (Project Specification)

このフォルダは本プロジェクトの仕様（OpenSpec）を管理する場所です。まずはテンプレートから着手し、必要な章を埋めてください（UTF-8/BOMなし推奨）。

## はじめ方
- `TEMPLATE.md` をベースに、新規仕様ファイル（例: `rtgamma_openspec.md`）を作成します。
- 仕様は以下を最低限カバーしてください。
  - 目的・範囲・非対象
  - ユースケース/ユーザーストーリー
  - 入出力（DICOM/CLI引数/レポート構造）
  - 幾何・座標系（IPP/IOP/PixelSpacing/GFOV の扱い）
  - アルゴリズム（リサンプリング/ガンマ/最適化）
  - パフォーマンス・精度の受け入れ基準
  - ログ/再現性/セキュリティ
  - 既知の制約・未決事項

## レポート JSON のスキーマ
- `report.schema.json` に、CLI が出力するサマリ JSON の叩き台スキーマを置いています。
- 実装差分に合わせて項目や型を更新してください（CHANGELOG/DECISIONS を参照）。
- メモ: Python の `json.dump` は非標準の `NaN` をトークンとして出力する場合があります。厳格 JSON 準拠が必要な場合は、`NaN` を `null` または 文字列 `"NaN"` に整形してから検証してください（本スキーマは `null`/`"NaN"` も許容）。

## 運用のヒント
- 仕様はドキュメントとしてレビュー/PRで更新します（小さく・頻繁に）。
- 変更は `CHANGELOG.md` とリンクし、重要な決定は `DECISIONS.md` と相互参照してください。
- GUI 実行とログ保存の手順は `docs/openspec/GUI_RUN.md` を参照してください。
