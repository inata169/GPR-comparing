# FAQ（よくある質問）

## Global と Local はどちらを使えばよいですか？
- 臨床 QA の第一選択は Global（寛容で再現性が高い）。
- Local は低線量域に厳しく、IMRT/VMAT などの高精度評価や研究用途で有効。

## `--norm` と `--gamma-type` の関係は？
- `--gamma-type {global,local}` は ΔD[%] の分母（基準線量）の定義を切り替えます。
  - global: 参照線量の最大値で正規化。
  - local: 画素ごとの参照線量で正規化（点ごとに分母が変化）。
- `--norm {global_max,max_ref,none}` はレポート基準の正規化と Cutoff 判定の基準です。
  - 現行実装では `global_max` と `max_ref` は同等（参照の最大値）。
  - Cutoff（%）の判定もこのグローバル基準に基づきます。

## 2D fast path と 3D の同一スライスで GPR が一致しません
- まず `scripts/compare_slice_gpr.py` で 3D の該当スライスと 2D レポートを突合してください。

## 3D Gamma が `Lower dose cutoff set ...` の後で長時間進みません
- PyMedPhysは大規模3D格子で数十分以上かかることがあり、計算中の割合進捗を出しません。GUIでは `Numba (fast full-volume GPR)`、`Sub-voxel Interp = 4`、`Threads = 0`（自動）を推奨します。
- Numbaはサンプル点の合否判定後に早期終了するためGPR用途向けです。通過点を含む最小gamma値、gamma平均、gammaヒストグラムをPyMedPhysと数値同等とは扱わないでください。

## 3D ViewerでGammaまたはPass/Failが表示されません
- 選択中のOutput Folderに`gamma3d.npz`と`run3d.json`が必要です。先に同じReference/Evaluation RTDOSE、条件、Output Folderで3D Gammaを完了してください。GUIからの3D GammaではViewer cacheを常に保存します。
- Viewerログに`Ignoring stale Gamma cache`がある場合は、RTDOSEまたはGamma条件が計算時と異なります。現在の条件で3D Gammaを再実行してください。
- Dose RatioはGamma cacheを必要としません。評価RTDOSEが読み込まれていれば、Gamma cacheがない場合の初期Overlayとして表示されます。
- バージョンが古い場合、2D 正規化の整合修正前だと差が出ます。最新に更新してください。
- `--plane-index` の±1で GPR が変動することがあります（高勾配領域）。
- 幾何（IPP/IOP/PixelSpacing/GFOV）に差がないか `scripts/compare_rtdose_headers.py` で確認。

## FrameOfReferenceUID（FoR）が異なります
- 幾何原点や向きの不一致が疑われます。`scripts/compare_rtdose_headers.py` でヘッダ差分を確認し、
  必要ならシフト最適化（`--opt-shift on`）で探索してください。FoR 不一致のまま高い GPR を狙うと再現性が低下します。
- 線量単位と方向余弦が互換であれば、解析は明示的なDICOM患者座標を使って継続し、FoR不一致をログ・JSON・PDFの警告と`same_for_uid=false`に記録します。線量単位または方向余弦が異なる場合は安全のため停止します。

## Pass Rate が低いときの対処
- データ起因（異なる装置/線質/スケール）なら Global でも低下します。まず 2D 可視化で空間パターンを確認。
- 設定緩和：`--dd 3 --dta 3 --cutoff 10` など。ROI で評価領域を絞るのも有効（将来の ROI 機能）。
- シフト最適化：粗→細の二段探索を推奨（coarse → fine）。

## PowerShell で `:` を含む shift-range が失敗します
- 変数展開入りのコロン区切りは `-f` 書式を使って回避してください。
  - 例: `"x:{0}:{1}:1" -f $a, $b`

## JSON に `NaN` が含まれてスキーマ検証に失敗します
- `python scripts/validate_report.py --sanitize-nan <report.json>` を使用（`NaN` を `null` に整形）。
- スキーマ（`docs/openspec/report.schema.json`）は `null` / "NaN" も許容します。

## GUI のサマリ自動オープンの優先度は？
- 3D: `run3d.md`、2D: `<plane>.md`、Header: `header_compare.md`。無ければ最新の `*.md`。

## `plane-index auto` と手動指定の使い分け
- `auto` は中央スライス相当を選択。コロナル/サジタルは症例により有意差が出るため、±1〜2 で比較を推奨。

## 文字コードの推奨は？
- Markdown/ログとも UTF-8（BOMなし）を推奨（Windows の文字化け回避）。
