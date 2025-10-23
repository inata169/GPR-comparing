# OpenSpec (プロジェクト仕様)

このフォルダは本プロジェクトの仕様（OpenSpec）を管理する場所です。まずテンプレートから着手し、必要な章を埋めてください。エンコーディングは UTF-8（BOMなし）を推奨します。

## はじめ方
- `TEMPLATE.md` をベースに、新規仕様ファイル（例: `rtgamma_openspec.md`）を作成します。
- 仕様は最低限、次をカバーしてください。
  - 目的・範囲・非対象
  - ユースケース / ユーザーストーリー
  - 入出力（DICOM/CLI 引数/レポート構造）
  - 幾何・座標系（IPP/IOP/PixelSpacing/GFOV の取り扱い）
  - アルゴリズム（リサンプリング / ガンマ / 最適化）
  - パフォーマンス・精度の受け入れ基準
  - ログ / 再現性 / セキュリティ
  - 既知の制約・未決事項

## レポート JSON スキーマ
- `report.schema.json` に、CLI が出力するサマリ JSON のスキーマ雛形があります。
- 実装と付き合わせて、必要に応じて更新してください（`CHANGELOG.md` / `DECISIONS.md` と相互参照）。
- メモ: Python の `json.dump` は非標準トークン `NaN` を出力する場合があります。厳格 JSON が必要な場合は `NaN` を `null` または文字列 `"NaN"` に整形してから検証してください（本スキーマは `null` / `"NaN"` も許容）。

## 運用のヒント
- 仕様ドキュメントはレビュー/PR で小さく頻繁に更新します。
- 変更は `CHANGELOG.md` とリンクし、重要な決定は `DECISIONS.md` と相互参照します。
- GUI の実行とログ保存手順は `docs/openspec/GUI_RUN.md` を参照してください。

## 主要ドキュメント（日本語）
- 仕様書（本書の要約＋詳細）: `docs/openspec/rtgamma_spec_JA.md`
- ガンマ種別の図式解説: `docs/openspec/Global_Local_Illustrated_JA.md`
- FAQ: `docs/openspec/FAQ_JA.md`
