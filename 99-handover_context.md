# ビルド安定化・マルチプレーン化準備: Handover Context (2026-03-11 v0.7.1 開発中)

## 1. 現在の進捗状況 (Current Progress)

### ビルドの安定性復旧 (完了)
- **現状**: v0.7.0 (commit deece88) をベースにビルド構成を整理し、`rtgamma_cli.exe` と `gamma_viewer.exe` の双方が正しく動作する状態に戻しました。
- **解決済み**: `rtgamma/io_dicom.py` の `try-except` が原因で `pydicom` のインポートエラーが隠蔽されていた問題を解消しました。これにより、EXE環境でも正常に DICOM 読み込みが可能です。
- **検証済み**: CLI による 3D 解析 + PDF レポート生成の完遂、および Viewer の起動を確認。

### マルチプレーンビューア (次ステップ)
- **計画**: `scripts/gamma_viewer.py` を拡張し、3断面（Axial/Sagittal/Coronal）の同時表示およびクロスヘア（中心点連動）機能を実装予定。

## 2. 実装上の注意・ハマりどころ (Caveats & Gotchas)

- **インポート隠蔽の禁止**: `io_dicom.py` のように、ライブラリのインポート成否を `try-except` で黙らせると PyInstaller 環境でのデバッグが極端に困難になります。依存関係は明示的にエラーを出す設計を維持してください。
- **PyInstaller のキャッシュ**: ビルドが不安定な場合は `pyinstaller --clean` や `Remove-Item build, dist` をためらわずに行ってください。

## 3. 次の課題 (Upcoming Tasks)

1.  **マルチプレーン・連動ビューアの実装**:
    - Axial / Sagittal / Coronal を 2x2（または 1x3 + info）で同時表示するモードの実装。
    - マウスクリックした座標が全断面で同期するクロスヘア機能。
2.  **EXE 容量の最適化（再考）**:
    - 安定性が確保されたため、再度安全な範囲で `cv2` や `torch` などの不要パッケージの除外を検討（現在は約 512MB）。
