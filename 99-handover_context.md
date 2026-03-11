# CI修正・マルチプレーン化着手前: Handover Context (2026-03-11 夜 v0.7.1 開発中)

## 1. 現在の進捗状況 (Current Progress)

### 本日完了 (2026-03-11)
- **CI エラーの修正 (完了)**:
  - `rtgamma/io_dicom.py` で `import pydicom` の前に余分な空行があり Ruff `I001` エラー。
  - `ruff check --fix` で修正し、commit `ee70eb7` として push 済み。CI 全 6 ジョブ PASS 確認。
- **TROUBLESHOOTING.md への知見追記 (完了)**:
  - 「CI Ruff I001 エラー」と「Windows git push 認証失敗」の原因・対策を日本語で追記。commit `5a7f3b6`。

### 次のステップ (翌日以降)
- **マルチプレーン・連動ビューアの実装** (Tier 2 最優先):
  - `scripts/gamma_viewer.py` を拡張。
  - 2×2 グリッドレイアウト（Axial / Sagittal / Coronal + コントロール）。
  - マウスクリックで全 3 断面のスライスが同期するクロスヘア機能。
  - 3 軸インデックス `(iz, iy, ix)` で全断面の表示位置を一元管理。

## 2. 実装上の注意・ハマりどころ (Caveats & Gotchas)

- **Ruff I001 予防**: サードパーティ import 群（numpy, pydicom 等）は空行で区切らずまとめること。commit 前に `ruff check --fix` を実行する習慣を徹底。
- **インポート隠蔽の禁止**: `io_dicom.py` のように `try-except` で依存ライブラリのインポートエラーを黙らせると PyInstaller 環境でのデバッグが困難になる。
- **Windows git push**: PAT 再発行後は資格情報マネージャーの古いエントリを削除する。git コマンド出力は Python スクリプト経由で UTF-8 ログに書き出す。
- **PyInstaller のキャッシュ**: ビルドが不安定な場合は `pyinstaller --clean` や `Remove-Item build, dist` を実施。

## 3. 次の課題 (Upcoming Tasks)

1. **マルチプレーン・連動ビューアの実装** (最優先):
   - Axial / Sagittal / Coronal を 2×2 グリッドで同時表示。
   - クロスヘア連動（クリックで全断面が同期）。
2. **EXE 容量の最適化（再考）**:
   - 安定性確保済みのため、`cv2`・`torch` 等の除外を再検討（現状 ~500MB）。
3. **Web ベース GUI 試作** (Tier 2):
   - Streamlit または Flask ベースの軽量 Web UI。
