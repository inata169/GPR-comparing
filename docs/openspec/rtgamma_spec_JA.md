# rtgamma 日本語仕様書（説明書） v0.1

本書は、DICOM RTDOSE 同士の比較ガンマ解析ツール rtgamma の日本語仕様書です。CLI/GUI の使い方、入出力、幾何取り扱い、アルゴリズム、検証方法をまとめます。Markdown/ログは UTF-8（BOMなし）を推奨します。

## 1. 概要
- 目的: RTDOSE×RTDOSE の 2D/3D ガンマ解析を、幾何整合（IPP/IOP/PixelSpacing/GFOV）を厳密に保ちながら、再現性高く実行する。
- 範囲: 2D/3D ガンマ、Global/Local、シフト最適化（粗→細）、GUI 起動、レポート生成（CSV/JSON/MD）。
- 非対象: ROI/RTSTRUCT マスクの本格対応（将来検討）、GPU/CuPy（検討中）。

## 2. システム要件
- Python 3.9 以上
- 依存関係: `pydicom`, `numpy`, `scipy`, `matplotlib`, `numba`
  - インストール: `pip install pydicom numpy scipy matplotlib numba`

## 3. インストールと準備
- リポジトリを取得し、作業ディレクトリで依存関係をインストール。
- サンプル DICOM は `dicom/` 配下（匿名化サンプル）。個人情報を含む DICOM はコミット禁止。

## 4. クイックスタート
- 3D（レポートのみ）
  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report phits-linac-validation/output/rtgamma/run3d`
- 2D axial（中央、画像保存）
  - `python -m rtgamma.main --mode 2d --plane axial --plane-index auto --ref <ref.dcm> --eval <eval.dcm> --save-gamma-map out/gamma.png --save-dose-diff out/diff.png --report out/axial`
- 臨床プリセットとスレッド
  - `--profile {clinical_abs,clinical_rel,clinical_2x2,clinical_3x3}`（既定はシフト OFF）
  - `--threads <N>`（0=auto）

## 5. 入出力仕様
- 入力: DICOM RTDOSE（主タグ: ImagePositionPatient, ImageOrientationPatient, PixelSpacing, GridFrameOffsetVector, DoseGridScaling）
- 出力:
  - 2D: ガンマ画像（PNG/TIFF）、線量差画像（%）
  - 3D: `gamma3d.npz`（gamma）、`dose_diff3d.npz`（%）
  - レポート: CSV/JSON/MD（ベースパス `--report <path>`）
  - JSON スキーマ: `docs/openspec/report.schema.json`

## 6. 幾何・座標系
- LPS 準拠。GFOV（GridFrameOffsetVector）昇順にソートし、z 軸とフレーム順序を整合。
- 2D 平面の世界座標グリッドは配列軸 (z,y,x) に整合（固定次元は単一軸）。
  - axial: (1, y, x) / sagittal: (z, y, 1) / coronal: (z, 1, x)
- FrameOfReferenceUID/方向一致度（`orientation_min_dot`）をレポート出力。

## 7. ガンマ解析
- パラメータ
  - `--dd` [%], `--dta` [mm], `--cutoff` [%]
  - `--gamma-type {global,local}`（既定: global）
  - `--norm {global_max,max_ref,none}`（既定: `global_max`、現状 `max_ref` と同等）
- 実装: Numba ベース 3D カーネル（pymedphys は既定で不使用）。
- 出力: gamma マップ（2D/3D）、統計（mean/median/max）、GPR（γ≤1 の割合）。
- Global/Local の違いと例: `docs/openspec/Global_Local_Illustrated_JA.md`

## 8. シフト最適化
- 粗→細の二段探索（fine 範囲・刻み調整、早期打ち切り）。
- 2D プリスキャンで XY 空間を狭め、3D 探索の初期領域を短縮可能。
- 既定は臨床プリセットで最適化 OFF。必要時のみ `--opt-shift on`。

## 9. 実行モード
- 2D: `--mode 2d --plane <axis> --plane-index <n|auto>`
  - 最適化 OFF では選択スライスのみ計算する高速経路（fast path）。
- 3D: `--mode 3d`（体積全体でガンマ計算）。

## 10. レポート出力（JSON 項目）
- 代表項目: `mode`, `plane`, `plane_index`, `dd_percent`, `dta_mm`, `cutoff_percent`, `gamma_type`, `norm`, `pass_rate_percent`, `best_shift_mm`, `best_shift_mag_mm`, `absolute_geometry_only`, `ref_for_uid`, `eval_for_uid`, `same_for_uid`, `orientation_min_dot`, `warnings`, `gamma_mean/median/max`。
- 厳格検証: `python scripts/validate_report.py --sanitize-nan <report.json>`

## 11. GUI の使い方（Windows）
- 起動: `run_gui.bat` または `scripts/run_gui.ps1`
- 操作:
  - Ref/Eval の RTDOSE を選択。出力フォルダを指定。
  - Action（Header/3D/2D）、臨床プリセット、平面（2D）、Threads、Local gamma トグル（既定 OFF）。
  - 進捗・ログ表示、サマリ自動オープン、ログ保存に対応。
- 詳細: `docs/openspec/GUI_RUN.md`

## 12. 検証と再現
- スキーマ検証: `scripts/validate_report.py --sanitize-nan <report.json>`
- 2D/3D スライス整合: `scripts/compare_slice_gpr.py <gamma3d.npz> --plane coronal --index 101 --report2d <coronal_101.json>`
- コロナル検証（例）: `docs/openspec/rtgamma_openspec.md` の 9.2 節を参照。

## 13. トラブルシューティング（抜粋）
- 出力パスの `FileNotFoundError`: 親ディレクトリが無い。ベースパスにフルパスを指定。
- TransferSyntaxUID が無い: 非 Part10 の可能性。既定で ImplicitVRLittleEndian を採用。
- PowerShell でコロン含みの文字列: `"x:{0}:{1}:1" -f a,b` のように `-f` 書式を使用。
- 低 GPR: 幾何不一致やスケール差の可能性。ヘッダ比較と 2D 可視化で確認。

## 14. よくある質問
- `docs/openspec/FAQ_JA.md` を参照。

## 15. 付録A: コマンド例
- 2D axial（clinical_rel, shift OFF, auto 中央）
  - `python -m rtgamma.main --profile clinical_rel --mode 2d --plane axial --plane-index auto --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm --save-gamma-map phits-linac-validation/output/rtgamma/spec_check/axial_gamma.png --save-dose-diff phits-linac-validation/output/rtgamma/spec_check/axial_diff.png --report phits-linac-validation/output/rtgamma/spec_check/axial --threads 0 --log-level INFO`
- 3D（clinical_rel, shift OFF）
  - `python -m rtgamma.main --profile clinical_rel --ref dicom/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm --eval dicom/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm --mode 3d --opt-shift off --save-gamma-map phits-linac-validation/output/rtgamma/spec_check3d/gamma3d.npz --save-dose-diff phits-linac-validation/output/rtgamma/spec_check3d/diff3d.npz --report phits-linac-validation/output/rtgamma/spec_check3d/run3d --threads 0 --log-level INFO`
- レポート検証
  - `python scripts/validate_report.py --sanitize-nan phits-linac-validation/output/rtgamma/spec_check/axial.json`
- スライス整合チェック
  - `python scripts/compare_slice_gpr.py phits-linac-validation/output/rtgamma/spec_check_coronal3d/gamma3d.npz --plane coronal --index 101 --report2d phits-linac-validation/output/rtgamma/spec_check_coronal/coronal_101/coronal_101.json`

## 16. バージョニングと変更管理
- 変更履歴: `CHANGELOG.md`
- 設計判断: `DECISIONS.md`
- 仕様（英日混在）: `docs/openspec/rtgamma_openspec.md`

## 17. 参照
- コード: `rtgamma/main.py`, `rtgamma/io_dicom.py`, `rtgamma/gamma.py`, `rtgamma/resample.py`, `rtgamma/optimize.py`, `rtgamma/report.py`
- GUI: `scripts/run_gui.ps1`, `run_gui.bat`, `config/gui_defaults.json`
- 運用: `AGENTS.md`, `TEST_PLAN.md`, `TROUBLESHOOTING.md`
