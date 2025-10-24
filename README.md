# rtgamma — DICOM RTDOSE Gamma Analysis (2D/3D)

![CI](https://github.com/inata169/GPR-comparing/actions/workflows/ci.yml/badge.svg)

Fast and reproducible gamma analysis for DICOM RTDOSE pairs with robust geometry handling, CLI/GUI, and lightweight docs/specs.

This README is normalized to UTF-8 (no BOM). For prior details, see CHANGELOG and docs under docs/openspec/.

## Features
- 2D/3D gamma with shift optimization (coarse→fine, early stop) and 2D fast path
- DICOM geometry fidelity (IPP/IOP/PixelSpacing/GFOV; GFOV-order alignment)
- Global and Local gamma selection
- CLI and Windows GUI (PowerShell/WinForms)
- Reports (CSV/JSON/MD), optional NPZ saves, and schema validation
- OpenSpec docs with examples and helper scripts

## Install
- Python 3.9+
- Dependencies:
  - `pip install pydicom numpy scipy matplotlib numba`

## Quick Start (CLI)
- 3D analysis (report only)
  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report phits-linac-validation/output/rtgamma/run3d`
- 2D axial (central slice, save images)
  - `python -m rtgamma.main --mode 2d --plane axial --plane-index auto --ref <ref.dcm> --eval <eval.dcm> --save-gamma-map out/gamma.png --save-dose-diff out/diff.png --report out/axial`

## Clinical Presets and Threads
- Presets: `--profile {clinical_abs,clinical_rel,clinical_2x2,clinical_3x3}` (shift OFF)
- Threads: `--threads <N>` to control Numba parallelism (0=auto)

## Global vs Local Gamma
- Select with `--gamma-type {global,local}` (default: global)
- GUI toggle: Local gamma (default OFF)
- Guide and examples: see `GPR_Global_vs_Local.md`

## Geometry and Coordinates
- Obeys DICOM IPP/IOP/PixelSpacing/GFOV; frames sorted by ascending GFOV
- 2D plane grids align to array order (z,y,x) with a singleton axis for the fixed dimension

## Outputs
- 2D images: PNG/TIFF (`--save-gamma-map`, `--save-dose-diff`)
- 3D arrays: NPZ (`--save-gamma-map`, `--save-dose-diff`)
- Reports: CSV/JSON/MD (`--report <basepath>`) with geometry sanity fields

## GUI
- Launch: double-click `run_gui.bat` (or run `scripts/run_gui.ps1`)
- Pick Ref/Eval RTDOSE, select output folder, choose Action (Header/3D/2D), preset, plane, threads
- Comfort: live log, status, elapsed, auto-open summary, save log; Local gamma toggle
- Details: `docs/openspec/GUI_RUN.md`
 
### Screenshots (small, optional)
- docs/openspec/images/gui_main.png
- docs/openspec/images/gui_after_run3d.png
- docs/openspec/images/gui_after_run2d_axial.png
- Helper: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\capture_gui_screens.ps1 -OutDir docs/openspec/images -DelayMs 1500

- Available example:
  - docs/openspec/images/Gui-screenshot.png
  
  ![Gui-screenshot.png 704x551](docs/openspec/images/Gui-screenshot.png)

## OpenSpec and Validation
- Docs/specs: `docs/openspec/` (README, TEMPLATE, `report.schema.json`, examples, `rtgamma_openspec.md`)
- Validate a report JSON:
  - `python scripts/validate_report.py --sanitize-nan phits-linac-validation/output/rtgamma/spec_check/axial.json`
- Compare a 3D gamma slice vs a 2D report:
  - `python scripts/compare_slice_gpr.py <gamma3d.npz> --plane coronal --index 101 --report2d <coronal_101.json>`

### Japanese Docs
- Full Japanese spec: `docs/openspec/rtgamma_spec_JA.md`
- Illustrated Global/Local guide: `docs/openspec/Global_Local_Illustrated_JA.md`
- FAQ (JA): `docs/openspec/FAQ_JA.md`

## Testing
- Lightweight tests: `pytest -q`
- Includes gamma local vs global checks and I/O/header utilities

## Notes
- Prefer UTF-8 (no BOM) for Markdown on Windows
- Do not commit PHI; use anonymized test DICOM only
- Write outputs under `phits-linac-validation/output/rtgamma/`

## Recent Updates (2025-10-23)
- Local gamma support (`--gamma-type local`); GUI toggle added
- OpenSpec initialized; report schema and validators included
- Slice consistency helper script added
- Reproducible 2D/3D commands and validation steps documented

## **免責事項 / Disclaimer**

## **⚠️ 重要：使用上の注意 (Important Notice)**

### **1\. 本ソフトウェアの位置づけ (Software Status)**

本ソフトウェアは、作者個人の研究成果として公開されているものであり、**医療機器としての承認（薬機法等）を受けたものではありません。**

標準的な治療計画装置（TPS）や検証用ファントム、測定機器を**置き換えるものではありません。**

This software is published as a personal research outcome and **is not a certified medical device** under any regulation. It does not replace, and is not intended to replace, any commercial Treatment Planning System (TPS), phantom, or measurement device.

### **2\. 使用の制限と責任 (Limitation of Use and Liability)**

本ソフトウェアは、その設計上、**研究および教育目的**での利用を意図しています。

本ソフトウェアを、**患者の診断、治療計画の立案、あるいは治療の品質保証（QA）など、臨床判断に直接関わるプロセスに使用することはできません。**

医学物理士などの専門家が、本ソフトウェアを臨床業務の「**参考用**」として（例：セカンドチェックの補助、研究的解析など）使用することもあるかもしれません。その場合であっても、使用者は以下の点に同意する必要があります：

1. **使用者の全責任:** ソフトウェアを使用する前に、自身の施設環境で十分な検証（コミッショニング）を行い、その正確性、特性、限界をすべて把握すること。  
2. **結果の保証の否認:** 本ソフトウェアが出力する計算結果の妥当性、正確性について、作者は一切保証しません。  
3. **最終責任の所在:** 本ソフトウェアを使用したこと、またはその結果を参照したことにより生じる**すべての臨床判断と、それに伴う一切の結果について、作者は一切の責任を負わず、使用者が単独で全責任を負うものとします。**

### **3\. 無保証 (No Warranty)**

本ソフトウェアは、MITライセンスに基づき「**現状有姿 (AS IS)**」で提供されます。作者は、本ソフトウェアの正確性、完全性、特定目的への適合性、非侵害について、明示的か黙示的かを問わず、一切の保証を行いません。

### **4\. 免責 (Limitation of Liability)**

作者または著作権者は、本ソフトウェアの使用、誤用、または使用不能から生じる、いかなる直接的、間接的、付随的、特別、懲罰的、結果的な損害（データの損失、逸失利益、業務の中断、あるいは患者への危害を含むがこれに限られない）についても、一切の責任を負いません。
