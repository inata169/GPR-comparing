# GUI・EXE軽量化・機能拡張: Handover Context (2026-03-09 v0.7.1 開発中)

## 1. 現在の進捗状況 (Current Progress)

### EXE容量の極限軽量化 (進行中)
- **達成事項**: `scipy.special` エラーを解決し、`rtgamma_cli` の単体サイズを **514.46 MB** まで削減。
- **手法**: `.spec` ファイルで必要な SciPy サブモジュールのみを明示的に収集。`build_exe.ps1` に `--noconfirm` を導入。
- **現状**: `rtgamma_cli.exe --help` の正常動作を確認済み。さらなる除外（OpenCV等）の余地あり。

### 依存関係の解析
- `_analyze_deps.py`: インポートされるサブモジュールをトレースするためのスクリプト。
- `dist` フォルダの構成を見直し、配布用 ZIP パッケージ (`scripts/package_release.ps1`) への繋ぎ込み準備を完了。

## 2. 実装上の注意・ハマりどころ (Caveats & Gotchas)

- **Matplotlib の依存性**: `matplotlib.path.Path` など一部の機能呼び出しでも `PIL` や `scipy.special` が必要になる場合がある。
- **Tkinter の要否**: CLI 側 (`rtgamma_cli`) では `tkinter` は不要（除外可能）だが、Viewer 側 (`gamma_viewer`) は GUI ツールキットとして必須。

## 3. 次の課題 (Upcoming Tasks)

1.  **軽量化された EXE の網羅的動作テスト**:
    - `rtgamma_cli.exe --help` だけではなく、実際に DICOM を読み込んで PDF レポートが生成されるまでの完遂テスト。
    - `gamma_viewer.exe` で 3D 表示が崩れないかの確認。
2.  **マルチプレーン・連動ビューアの設計**:
    - 現在の 3D ビューアを拡張し、Axial / Sagittal / Coronal を 2x2 等で同時表示するモードの実装。
3.  **多言語対応の深化**:
    - GUI ラベルの I18N (日英切替) への道筋。
