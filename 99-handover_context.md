# GUI・EXE軽量化・機能拡張: Handover Context (2026-03-09 v0.7.1 開発中)

## 1. 現在の進捗状況 (Current Progress)

### EXE容量の極限軽量化 (進行中: 難航)
- **現状**: CLI版 (`rtgamma_cli.exe`) のインポートエラー (`scipy.special`) に対し、`.spec` ファイルでの明示的なサブモジュール指定を試行中。`--help` の起動は確認。
- **欠落事項**: `gamma_viewer.exe` が未ビルド。また、リサンプリングやPDF生成など、実際の重い処理が軽量化版で完遂するかは未検証。

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
