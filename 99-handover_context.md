# 99-handover_context.md

## 1. 現在の進捗 (Current Progress)
- **目的**: Structure (RTSTRUCT) 別の Gamma Pass Rate 評価機能の実装と結合テスト。3Dインタラクティブビューアの開発。
- **完了した作業**:
  1. `rtgamma/io_dicom.py`: RTSTRUCTファイルを読み込み、ROIごとの輪郭データ (LPS座標) を抽出する `load_rtstruct()` の実装。
  2. `rtgamma/mask.py`: `matplotlib.path.Path` を用いて、ROI輪郭から3Dバイナリマスクを生成するモジュールの作成。
  3. `rtgamma/main.py`: `--rtstruct` と `--roi` のCLI引数を追加し、ROIごとの評価(`per_structure`)を出力へ連携。
  4. `rtgamma/report.py`: MarkdownおよびJSON出力におけるテーブル・スキーマの拡張。
  5. **結合テストと確認**: `dicom/2024101700` の実データを使用し、CLIで1478枚のスライス輪郭(patient ROI)に対する3Dマスク構築を実行 (成功、処理時間は約40秒〜60秒)。自己対向 (Self-compare: RefとEvalが同一ファイル) のテストでもGamma=100.0%を算出可能であることを確認しました。
  6. **ドキュメントとスキーマ**: `docs/openspec/rtgamma_openspec.md` にCLI引数と出力仕様を追記。`report.schema.json` へ `per_structure` プロパティを追加し `scripts/validate_report.py` にてテストがパスすることを検証しました。
  7. **Local Gamma サポートの完全統合**: シフト最適化 (`--opt-shift on`) においても `--gamma-type local` が正しく適用されるように `rtgamma/optimize.py` および `rtgamma/main.py` を修正しました。自己対向テストにて最適化ループ内で local gamma が使用されていることを確認しました。
  8. **空間不整合の修正**: 画像配列とLPS座標系のマッピングを修正し、ROIマスクが線量グリッドと正しく重なるようにしました。
  9. **単位テストの拡充**: `test_coord_roundtrip.py` を追加し、DICOM世界座標（LPS）と画像配列インデックス間の往復変換の一貫性を実データを含めて保証しました。
  10. **GUIの強化**: `scripts/run_gui.ps1` に RTSTRUCT のファイルパスと ROI名（複数指定可）の入力欄を追加。
  11. **GUIの機能修正とデザイン刷新 (2026-03-03)**:
      - 臨床プリセット（Profile）選択方式を廃止し、**DTA [mm], DD [%], Cutoff [%]** を直接数値指定する方式に移行。これにより、プリセット選択時に適切な dd_percent が引き継がれないバグを解消しました。
      - デザインをダークテーマに刷新し、ステータス（Idle/Running/Done/Error/Canceled）に応じてテキスト色やボタンスタイルを最適化。
      - ログ表示領域を 280px、ウィンドウ全体の縦幅を 950px に拡大し、解析ログの視認性を向上。
      - 日本語環境での文字化け防止のため、Unicode 文字（em-dash, ▶ 等）をすべて ASCII 文字（-, >> 等）に置換。
  12. **RTSTRUCT 読み込みのロバスト性向上 (2026-03-03)**:
      - 引数にディレクトリが渡された場合、配下にある RTSTRUCT ファイル（Modality == 'RTSTRUCT'）を自動探索する機能を追加。
      - ファイル名や拡張子（.dcm, .0等）に依存せず、メタデータを検証して読み込むように強化。
  13. **3D ガンマビューアの実装 (2026-03-03)**:
      - CT画像読み込み (`load_ct`) と DOSEグリッドへのリサンプリング (`resample_ct_onto_dose`) を実装。
      - matplotlib ベースの高速・軽量なインタラクティブビューア (`scripts/gamma_viewer.py`) を作成。
      - CT、ガンマ分布、Structure輪郭の重畳表示、および要素ごとの表示ON/OFFスイッチ機能を搭載。
  14. **バグ修正と信頼性向上 (2026-03-03)**:
      - `load_ct` における `TransferSyntaxUID` 欠損対応を追加。
      - `grid_search_best_shift` にて、パス率が同一の場合は最小シフトを優先するロジックを導入。
      - 自己比較（RefとEvalが同一ファイル）時に無駄な探索をスキップするロジックを追加し、パス率が不整合を起こすバグを防止。
      - 異なる照射野サイズの比較時における正当なアライメント棄却リスク（80%ルール）を撤回し、純粋なパス率ベースの評価へ修正。
  15. **3Dビューアの表示改善 (2026-03-03)**:
      - 古いMatplotlibと最新版の双方に対応するため、チェックマークの描画ロジックを修正しAttributeErrorを解消。
      - ダークテーマ上でチェックボックス（の枠線）が見えなくなる問題を `set_frame_props` 等を駆使して解消。
      - 画面右下に評価条件（DTA/DD/Cutoff）を表示し、スクリーンショット等で条件が確認できるように改善。
      - CCC(標準)線量とMC線量を比較するための `run_viewer_test.bat` を改修。
  - **パフォーマンス最適化 (2026-03-03)**:
      - 初期リサンプリング(`eval_on_ref`)を遅延評価(Lazy Evaluation)に変更。線量差表示（`--save-dose-diff`）やスライス抽出が行われない場合、不要な計算がスキップされるようになりました。
  16. **3D ガンマビューアの大幅強化 (2026-03-04)**:
      - **Ref / Eval 線量分布の表示**: RefのDOSE配列およびEvalのリサンプリング済みDOSE配列をビューアに引き渡し、`jet` カラーマップ + カラーバーで CT 上にオーバーレイ表示可能に。
      - **5モード切替 RadioButtons**: `Gamma` / `Pass/Fail` / `Ref Dose` / `Eval Dose` / `Dose Ratio` を瞬時に切り替えるUIを追加。
      - **Pass/Fail モード**: ガンマ値 <= 1.0 を緑(OK)、> 1.0 を赤(NG) で二値表示。スライス毎の GPR と OK/NG ボクセル数を画面左下にオーバーレイ。
      - **Dose Ratio モード**: Eval/Ref の線量比を `bwr` カラーマップ (0.8-1.2) で表示。Cutoff 未満のボクセルは自動マスク。
      - **ファイル名表示**: ビューア左上に Ref / Eval の DICOM ファイル名 (basename) を常時表示。
      - **チェックボックス描画の修正**: 壊れていた `try/else` ブロックを `if hasattr` に書き換え、`draw_idle()` で再描画を保証。
      - **`--gamma-npz` + `--eval` 併用対応**: NPZ使用時でも `--eval` を指定すれば Eval Dose / Dose Ratio 表示が利用可能。
  17. **RTPLAN 統合ヘッダ比較の追加 (2026-03-04)**:
      - `scripts/compare_rtdose_headers.py` に `--plan-a`, `--plan-b` 引数を追加。
      - Isocenterの差分（`plan_isocenter_delta_mag_mm`）とSSD/SADの情報が表示されるように拡張しました。
  18. **ジオメトリヘッダの徹底比較 (2026-03-04)**:
      - Test01〜Test04 のテスト用データペアに対してヘッダ比較を行い検証結果を `headers_summary.md` に出力しました。
      - SSD や Dose Unit の違いなどの要因よる大きなジオメトリズレ（>50mm）が Test01 および Test02 で検出され、対処フローをドキュメント化しました。
  19. **Sub-voxel Interpolation によるガンマ解析精度の向上 (2026-03-04)**:
      - 3DVH とのガンマパス率の乖離 (約20pp) を解消するため、`gamma.py` のカーネルに trilinear サブボクセル内挿を導入しました。
      - `--interp-fraction` 引数で指定された刻み幅で DTA 球内を密に探索し、gamma <= 1.0 に達した時点で即時 Early Exit する最適化を実装。
      - Test06 データにおいて `--interp-fraction 10` 指定時、Overall GPR が 85.82% に達し、3DVH (84.7%) との差を 1.1pp に短縮しました (計算時間の増加は数秒)。
## 2. 実装上の留意事項 (Implementation Notes)
- **座標系**: `io_dicom.py` のメタデータ名を `v_col`, `v_row`, `v_slice`, `s_col`, `s_row` に変更し、DICOM規格（PixelSpacing[0]=垂直/row, [1]=水平/col）と配列インデックス `(j, i)` の対応を厳密に定義しました。
- **最終評価時のガンママップ解像度低下の解決**: `optimize.py` のシフト探索時におけるパス率と、最終評価時のパス率が一致しない（大幅に低下する）バグが生じていました。調査の結果、(1) 前処理時のIPP起点のオフセット吸収における符合（ベクトル）の逆転設定エラー、および (2) 最終の `resample_eval_onto_ref` によって内挿(Interpolation)されることによる解像度以下の座標ピークの消失が原因であることを突き止めました。
  対策として、差分マップ生成用にリサンプリングされたボクセルを `compute_gamma` にそのまま渡すことをやめ、最適化時のように「評価用配列そのまま」に対して「評価軸(`axes_eval_mm`)」を物理レベルでずらす手法へ改めました。これによりサブボクセル・サブグリッドでの高精度なガンマ算出が常に保証されるようになりました。
- `mask.py` の `contour_to_mask_3d` 関数は、輪郭スライス数が膨大な場合 (例えば1400層以上) の包含判定 (`contains_points`) において、Pythonの処理速度の影響で約1分近くかかる場合がありますが、正しく完了しメモリも安全な水準に保たれています。
- `per_structure` が出力される場合、一部のROI内で計算対象ボクセル数がゼロ(全てCutoff未満など)の場合は、`pass_rate`、`gamma_mean`、`gamma_median`、`gamma_max` が数値ではなく `NaN` (JSON仕様上は文字列 `"NaN"` や `null`) で出力されます。最新のJSONスキーマはこれらを許容する設定になっています。

## 3. 保留中のタスク・今後の展望 (Pending Tasks / Future)
- (オプション) `mask.py` におけるROIのポリゴン構築が遅い場合の最適化 (例: NumbaベースのPoint-in-Polygonへの置き換えやbboxによる限定的な検査)。
- (オプション) ROI に特化したシフト最適化（ROI 内のガンマパス率を最大にする専用の最適化探索）。

## 4. 直近で実行すべきコマンド (Next Commands)
次回の作業では、強化された 3D ビューアを活用して、Test06 (MC vs CCC) などの線量分布比較（Ref Dose / Eval Dose / Dose Ratio 表示）を実施する予定です。
`run_gui.bat` (または `scripts/run_gui.ps1`) でビューアを利用したり、Dose Ratio モードで系統的な線量差の強い領域（例：ビルドアップ領域や不均質部）の局所的な違いを特定します。

※ また、大きなガンマパス率が予想されるケースに対しては `Action` を `Header Compare` に設定して、ジオメトリ差異の事前確認を行うことが `TEST_PLAN.md` で推奨されています。

## 5. 商用品質に向けたロードマップ (全19項目)
これまでの開発経緯を踏まえた商用レベル機能ロードマップを隠しフォルダから復旧し `docs/feature_roadmap.md` に保存しました。次回の主要な優先順位は以下の通りです：
1. **バッチ処理** (CSV/フォルダ構造での複数ペアの一括実行と結果集約)
2. **PDFレポート自動生成** (施設名、日付、グラフを含むQA承認用の帳票フォーマット)
3. **RTPLANヘッダ統合** (実装完了)
4. **テスト・CI強化** (結合テスト・テスト自動実行環境の構築)
5. **設定プリセット管理** (TG-218等の規格に準拠したDTA/DD設定のプロトコル化)
