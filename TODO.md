# TODO (Next Actions)

Date: 2025-10-15

High priority
- [x] Header diffs: run scripts/compare_rtdose_headers.py for Test01–04 and review outputs
  - [x] Test01 → phits-linac-validation/output/rtgamma/Test01_dose_compare.md
  - [x] Test02 → phits-linac-validation/output/rtgamma/Test02_dose_compare.md
  - [x] Test03 → phits-linac-validation/output/rtgamma/Test03_dose_compare.md
  - [x] Test04 → phits-linac-validation/output/rtgamma/Test04_dose_compare.md
  - [x] Summarize findings (SSD vs SCD/SAD; origin deltas; FoR; orientation) into headers_summary.md

- [x] RTPLAN support in header compare
  - [x] Extend scripts/compare_rtdose_headers.py with --plan-a/--plan-b
  - [x] Extract: IsocenterPosition, SAD (and SSD estimate if derivable), BeamName if available
  - [x] Report deltas: plan_isocenter_delta_mm, SAD/SSD differences

- [ ] Auto-fallback improvements
  - [ ] Standardize two-stage search: coarse (e.g., x:-150:150:10,y:-30:30:10,z:-30:30:10, --refine none) → fine (±10 mm, 1 mm)
  - [ ] Early stop if improvement < epsilon across N steps
  - [ ] Include warnings/same_for_uid/orientation_min_dot in scripts/run_autofallback.ps1 summary output

Medium priority
- [ ] Update command.txt with new presets after enhancements
- [x] Documentation
  - [x] README: note on SSD vs SCD(SAD) impacts on GPR; link to header-compare flow
  - [x] TEST_PLAN: recommended flow (Header compare → Absolute geometry → Coarse → Fine; optional ROI)

Optional / stretch
- [x] ROI/RTSTRUCT masking for ROI-limited GPR (Implemented generation & JSON/MD output)
- [x] DICOM/Grid Coordinate Alignment (Fixed ROI projection and coordinate system inconsistencies)
- [x] Local gamma option wired to CLI and report
- [x] 空間不整合の修正: 画像配列とLPS座標系のマッピングを修正し、ROIマスクが線量グリッドと正しく重なるようにしました。
- [x] RTSTRUCT 読み込みのロバスト性向上: ディレクトリ指定時に配下の RTSTRUCT を自動検索する機能、および拡張子に依らないモダリティ判定ロジックの実装。
- [x] GUI RTSTRUCT/ROI support (Added Browse/Input fields to run_gui.ps1)
- [x] Coordinate round-trip unit tests (Added test_coord_roundtrip.py)
- [ ] 2D pre-scan to narrow 3D search space automatically

## 商用化レベル機能ロードマップ (全19項目)
「研究スクリプト」から「商用レベル品質」への引き上げのため、以下の実装が中・長期の優先課題となります。（詳細は `docs/feature_roadmap.md` を参照）
- **Tier 1 (コア品質)**: **[ ] バッチ処理一括実行**, **[ ] PDF レポート自動生成**, [x] RTPLAN ヘッダ統合, [ ] テスト カバレッジ & CI 強化
- **Tier 2 (ユーザー体験)**: [ ] Web GUI化 (クロスプラットフォーム), [ ] マルチプレーン/DVH 同時表示, [ ] トレンド解析DB保存, [ ] YAML設定プリセット管理
- **Tier 3 (高度解析)**: [ ] ガンマヒストグラム・空間分析, [ ] 多基準同時評価並行実行, [ ] トレランス基準のアラート, [ ] 不確かさのブートストラップ推定, [ ] MHD/NRRD対応
- **Tier 4 (運用・配布)**: [ ] `pip` / `.exe` パッケージ・インストーラ配布, [ ] 完全日英多言語化 (i18n), [ ] プラグイン機構, [ ] 監査・コンプライアンス対応

## 次のステップ (2026-03-03)
- [x] clinical preset 廃止と DTA/DD/Cutoff 直接入力への移行 (dd_percent 指定ミスバグの恒久対策)。
- [x] GUI デザインのダークテーマ刷新。
- [x] GUI 文字化け修正 (Unicode em-dash/▶ 除外)。
- [x] ログ領域の拡大 (280px) とウィンドウ縦幅 (950px) の調整。
- [x] **3D ガンマビューアの実装**
  - [x] CT画像シリーズ読み込み (`load_ct`)
  - [x] CT→DOSEグリッドへのリサンプリング (`resample_ct_onto_dose`)
  - [x] インタラクティブな3Dビューア (`scripts/gamma_viewer.py`)
  - [x] CT/Gamma/Structureの個別ON/OFFスイッチ、1パネル集約、マルチ断面表示
  - [x] UI視認性向上: チェックボックス（Matplotlib対応）とGPR条件（DTA等）の常時表示。
  - [x] MC vs 標準線量の評価テストバッチ(`run_viewer_test.bat`)の更新。
  - [x] 初期リサンプリングの遅延評価化による解析速度向上。

- [x] 自己比較時の最適化バイパスおよび同等パス率時の最小シフト選択ロジック（`optimize.py`更新）。
- [x] シフト最適化における不用意な評価点数保護ルール（80%ルール）の撤回（異なる照射野サイズでの正当なアライメント棄却防止）。
- [x] RTSTRUCT 読み込み時のロバスト性向上（ディレクトリ指定対応、ファイル名に依らないモダリティ判定）。

## 次のステップ (2026-03-04)
- [x] **3D ガンマビューアの大幅強化** (`scripts/gamma_viewer.py`)
  - [x] Ref / Eval 線量分布の表示モード追加（jet カラーマップ、カラーバー付き）
  - [x] 表示モード切替 RadioButtons: Gamma / Pass/Fail / Ref Dose / Eval Dose / Dose Ratio の5モード
  - [x] Pass/Fail モード: gamma <= 1.0 を緑(OK)、> 1.0 を赤(NG) で表示。スライス毎の GPR をオーバーレイ表示
  - [x] Dose Ratio モード: Eval/Ref の線量比を bwr カラーマップ (0.8-1.2) で表示
  - [x] Ref/Eval の DICOM ファイル名をビューア左上に常時表示
  - [x] チェックボックス描画の修正（壊れた try/else 構文→if hasattr に修正、draw_idle() で再描画保証）
  - [x] カラーバーの追加（モード切替時にラベル・スケール自動更新）
  - [x] `--gamma-npz` と `--eval` の併用対応（NPZ使用時でも Eval Dose 表示が可能に）

- [x] **Sub-voxel interpolation (Trilinear) の実装**
  - [x] Numba JIT での 3D ガンマ検索時に指定された `interp_fraction` (デフォルト 10) 分だけボクセルを細分化して検索するアルゴリズムを導入。
  - [x] Test06の実測データにおいて SunNuclear 3DVH (84.7%) との GPR の差異を 1.1pp (85.82%) にまで大幅に短縮することに成功。
  - [x] GUI に `Sub-voxel Interp` の数値を指定するオプションを追加し、デフォルトを10へ変更。
- [x] **Test01〜Test04 のヘッダ情報の比較とサマリ化**
  - [x] `compare_rtdose_headers.py` を用いて、各テストペアの IPP / SSD / SAD / 解像度 / DoseUnit を解析。
  - [x] 結果を `phits-linac-validation/output/rtgamma/headers_summary.md` に出力し、原因を考察。
- [ ] **3D ガンマビューアを用いた Test06 解析**
  - [ ] Dose Ratio 機能などを利用し、MC と CCC 間の空間的な線量差の特徴を特定・記録する。

## 未解決・今後の課題 (2026-03-03 追加)
- [x] **シフト探索と最終計算の不整合調査**: 
  - (原因1) 初期座標の相違を吸収するアフィン変換の射影(`origin_offset_vec`)において、符合（ベクトル方向）が逆になっていたバグを特定し修正しました。
  - (原因2) 最適化探索後に行う「最終ガンマ評価」において、これまでは空間を内挿(Interpolation)によるリサンプリングでRefグリッドへ固定してから評価していましたが、これによって2D/3D空間上での用量分布のピークがぼやけ(blur)、解像度以下の真の距離を評価できずパス率が急減する現象が生じることを突き止めました。
  - (対策) 最終評価時のGamma値算出において、リサンプリングで「ボクセルを動かした」用量分布の形を評価するのではなく、原画像の用量分布データそのものを維持し、逆に「評価点用軸（`axes_eval_mm_final`）」を最適シフト分だけ物理的にずらす方式へ改修しました。これにより、純粋な位置ズレとして高解像度のサブグリッド評価が復活し、自己比較の100%パスなどを完全に保証できるようになりました。

How to resume
1) Generate header diffs (see command.txt lines 15–18) and review Notes sections.
2) If geometry is sound, run absolute geometry (opt-shift=off, norm=none). If low GPR, use coarse→fine search.
3) If large shifts re-occur, confirm plan isocenter/SAD/SSD via RTPLAN comparison.


---

Follow-up 2025-10-16 (Coronal GPR regression + GUI)

Context
- Test05 2D fast path (opt-shift=off, clinical_rel) shows sagittal ≈ 93.38% (index 126), coronal ≈ 82.10% (index 101).
- Previously, coronal was remembered at ≈ 93%.
- Recent fixes: 2D plane world-coords for sagittal/coronal corrected to align array axes; GUI now opens run3d.md for 3D.

Hypotheses
- H1: Prior runs benefited from unintended eval-dose normalization to ref-max (now removed); stricter comparison can lower GPR.
- H2: Previous coronal plane had axis mix-up that incidentally improved GPR; corrected geometry yields lower but accurate GPR.
- H3: Auto central slice picked a different index; ±1 slice can shift GPR notably in high-gradient regions.

Actions (High priority)
- [ ] Coronal index sweep at same settings (clinical_rel, opt-shift=off, interp=linear, cutoff=10%):
      - plane-index 100/101/102; compare pass rates and images.
      - Example:
        - python -m rtgamma.main --profile clinical_rel --ref <ref> --eval <eval> --mode 2d --plane coronal --plane-index 100 \
          --save-gamma-map phits-linac-validation/output/rtgamma/Test05_guiTest/coronal_100_gamma.png \
          --save-dose-diff phits-linac-validation/output/rtgamma/Test05_guiTest/coronal_100_diff.png \
          --report phits-linac-validation/output/rtgamma/Test05_guiTest/coronal_100 --opt-shift off
        - (repeat for 101/102)
- [ ] Norm sensitivity check:
      - Compare --norm global_max (clinical_rel) vs --norm none (absolute) on the same coronal index.
- [ ] 2D fast path vs 3D slice consistency:
      - Run 3D with NPZ save (temporary): ensure 2D coronal slice GPR matches 3D gamma slice at same index.
      - If mismatch > 0.5 pp, investigate axes/spacing in compute_gamma inputs.

Actions (GUI, optional)
- [ ] Add plane-index numeric input to GUI for 2D runs (default auto).
- [ ] Add optional 3D NPZ save toggle and path; keep auto-open preference to run3d.md when Action=3D.

References
- Logs: phits-linac-validation/output/rtgamma/Test05_guiTest/run_log_20251016_171244.txt (coronal 82.10%, index 101)
- Logs: phits-linac-validation/output/rtgamma/Test05_guiTest/run_log_20251016_171131.txt (sagittal 93.38%, index 126)

Done (today)
- [x] Fix 2D coronal/sagittal slice shape mismatch (consistent (z,y,x) singleton axes per plane).
- [x] GUI: prefer run3d.md (3D), <plane>.md (2D), header_compare.md (Header) when auto-opening.
