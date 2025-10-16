# 更新（2025-10）

- ヘッダ比較ツール拡張：`scripts/compare_rtdose_headers.py` に `--plan-a` / `--plan-b` を追加（RTPLAN由来の Isocenter/SAD/SSD をMDに追記）。
- 自動フォールバック強化：粗→密の2段探索、早期打ち切り、2D中央スライス事前スキャンを標準化。
  - 追加CLI: `--fine-range-mm` / `--fine-step-mm` / `--early-stop-epsilon` / `--early-stop-patience` / `--prescan-2d`。

例: ヘッダ比較（RTPLANあり）
```
python scripts/compare_rtdose_headers.py \
  --a <ref_rtdose.dcm> --b <eval_rtdose.dcm> \
  --plan-a <ref_rtplan.dcm> --plan-b <eval_rtplan.dcm> \
  --out phits-linac-validation/output/rtgamma/dose_compare.md
```

例: 3D（2段探索＋早期打ち切り・2D事前スキャン）
```
python -m rtgamma.main \
  --ref <ref.dcm> --eval <eval.dcm> --mode 3d \
  --shift-range "x:-10:10:2,y:-10:10:2,z:-10:10:2" \
  --fine-range-mm 5 --fine-step-mm 1 \
  --early-stop-epsilon 0.05 --early-stop-patience 200 \
  --report phits-linac-validation/output/rtgamma/run3d
```

例: 2D中央スライス（最適化OFF）
```
python -m rtgamma.main \
  --ref <ref.dcm> --eval <eval.dcm> \
  --mode 2d --plane axial --plane-index auto --opt-shift off \
  --save-gamma-map phits-linac-validation/output/rtgamma/axial_gamma.png \
  --save-dose-diff phits-linac-validation/output/rtgamma/axial_diff.png \
  --report phits-linac-validation/output/rtgamma/axial
```

# RTDOSE 繧ｬ繝ｳ繝櫁ｧ｣譫・CLI・・D/3D繝ｻ荳芽ｻｸ繧ｷ繝輔ヨ譛驕ｩ蛹厄ｼ・
謾ｾ蟆・ｷ壽ｲｻ逋２A蜷代￠縺ｫ縲・縺､縺ｮ DICOM RTDOSE 繧呈ｯ碑ｼ・＠縺ｦ 2D/3D 繧ｬ繝ｳ繝槭う繝ｳ繝・ャ繧ｯ繧ｹ繧定ｨ育ｮ励☆繧九ヤ繝ｼ繝ｫ縺ｧ縺吶ら焚繧ｰ繝ｪ繝・ラ繝ｻ逡ｰ蠎ｧ讓咏ｳｻ縺ｮ謨ｴ蜷医∽ｸ芽ｻｸ繧ｷ繝輔ヨ譛驕ｩ蛹悶∝庄隕門喧縲√Ξ繝昴・繝亥・蜉帙↓蟇ｾ蠢懊＠縺ｾ縺吶・
- 譌｢螳壽擅莉ｶ: `DD=3.0%`, `DTA=2.0 mm`, `Cutoff=10%`
- 繧ｬ繝ｳ繝樒ｨｮ蛻･: `global`・・--gamma-type`縺ｧ蛻・崛蜿ｯ・・- 豁｣隕丞喧: `global_max`・・--norm`縺ｧ `max_ref` / `none` 驕ｸ謚槫庄・・
蜷梧｢ｱ繧ｵ繝ｳ繝励Ν・郁ぜ逞・ｾ具ｼ・- `dicom/PHITS_Iris_10_rtdose.dcm`
- `dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm`

蛯呵・ `phits-linac-validation/` 縺ｫ縺ｯPHITS蜃ｺ蜉帙→螳滓ｸｬCSV縺ｮ1D繝励Ο繝輔ぃ繧､繝ｫ豈碑ｼ・ヤ繝ｼ繝ｫ縺悟挨騾泌性縺ｾ繧後∪縺呻ｼ域悽README縺ｯRTDOSE蜷悟｣ｫ縺ｮ繝懊Μ繝･繝ｼ繝豈碑ｼ・ヤ繝ｼ繝ｫ縺ｮ隱ｬ譏弱〒縺呻ｼ峨・
## 繧､繝ｳ繧ｹ繝医・繝ｫ

- Python 3.9+ 繧呈耳螂ｨ
- 萓晏ｭ倬未菫ゅ・繧､繝ｳ繧ｹ繝医・繝ｫ
  - `pip install pydicom numpy scipy matplotlib numba`

## 菴ｿ縺・婿・亥渕譛ｬ・・
- 3D 繧ｬ繝ｳ繝橸ｼ九す繝輔ヨ譛驕ｩ蛹厄ｼ九Ξ繝昴・繝亥・蜉・  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report phits-linac-validation/output/rtgamma/lung3d_report --save-gamma-map phits-linac-validation/output/rtgamma/gamma3d.npz --save-dose-diff phits-linac-validation/output/rtgamma/dose_diff3d.npz`

- 2D Axial 繧ｹ繝ｩ繧､繧ｹ・医せ繝ｩ繧､繧ｹ逡ｪ蜿ｷ 50・会ｼ狗判蜒丈ｿ晏ｭ・  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 2d --plane axial --plane-index 50 --save-gamma-map phits-linac-validation/output/rtgamma/gamma_axial.png --save-dose-diff phits-linac-validation/output/rtgamma/diff_axial.png --report phits-linac-validation/output/rtgamma/lung2d_axial`

蜃ｺ蜉帛・繝・ぅ繝ｬ繧ｯ繝医Μ縺ｯ閾ｪ蜍穂ｽ懈・縺輔ｌ縺ｾ縺呻ｼ医ヵ繧｡繧､繝ｫ蜷阪・縺ｿ縺ｮ蝣ｴ蜷医・繧ｫ繝ｬ繝ｳ繝医↓蜃ｺ蜉幢ｼ峨・
## 荳ｻ縺ｪ蠑墓焚・域栢邊具ｼ・
- 蜈･蜉・  - `--ref <path>` 蝓ｺ貅・RTDOSE・・ICOM・・  - `--eval <path>` 豈碑ｼ・RTDOSE・・ICOM・・
- 隗｣譫舌Δ繝ｼ繝・  - `--mode {3d,2d}` 譌｢螳・ `3d`
  - `--plane {axial,sagittal,coronal}`・・D譎ゑｼ・  - `--plane-index <int>`・・D譎ゅ√せ繝ｩ繧､繧ｹ逡ｪ蜿ｷ・・
- 隧穂ｾ｡譚｡莉ｶ
  - `--dd <float>` 譌｢螳・ `3.0`
  - `--dta <float>` 譌｢螳・ `2.0`
  - `--cutoff <float>` 譌｢螳・ `10.0`
  - `--gamma-type {global,local}` 譌｢螳・ `global`
  - `--norm {global_max,max_ref,none}` 譌｢螳・ `global_max`

- 繧ｷ繝輔ヨ譛驕ｩ蛹厄ｼ・N/OFF, 遽・峇・・  - `--opt-shift {on,off}` 譌｢螳・ `on`
  - `--shift-range "x:-3:3:1,y:-3:3:1,z:-3:3:1"`
    - 荳闊ｬ縺ｫIMRT/VMAT縺ｧ縺ｯﾂｱ3mm, 1mm蛻ｻ縺ｿ遞句ｺｦ縺檎岼螳・    - 3D-CRT縺ｪ縺ｩ縺ｧ蠎・ａ縺ｫ謗｢邏｢縺吶ｋ蝣ｴ蜷・ 萓・`x:-5:5:1,y:-5:5:1,z:-5:5:1`

- 陬憺俣
  - `--interp {linear,bspline,nearest}` 譌｢螳・ `linear`

- 蜃ｺ蜉・  - `--save-gamma-map <path>` 2D: PNG/TIFF, 3D: NPZ
  - `--save-dose-diff <path>` 2D: PNG/TIFF, 3D: NPZ・・ef蝓ｺ貅悶〒%陦ｨ險假ｼ・  - `--report <path>` 諡｡蠑ｵ蟄舌↑縺励〒謖・ｮ夲ｼ・SV/JSON/MD 繧定・蜍慕函謌撰ｼ・
## 蜃ｺ蜉帙ヵ繧｡繧､繝ｫ萓・
- `phits-linac-validation/output/rtgamma/gamma3d.npz` 3D 繧ｬ繝ｳ繝樣・蛻・- `phits-linac-validation/output/rtgamma/dose_diff3d.npz` 3D 蟾ｮ蛻・ｼ・・・- `phits-linac-validation/output/rtgamma/gamma_axial.png` 2D 繧ｬ繝ｳ繝樒判蜒・- `phits-linac-validation/output/rtgamma/diff_axial.png` 2D 蟾ｮ蛻・判蜒・- `phits-linac-validation/output/rtgamma/lung3d_report.csv|json|md` 隕∫ｴ・ｼ医ヱ繧ｹ邇・∵怙驕ｩ繧ｷ繝輔ヨ縲∫ｵｱ險茨ｼ・- `phits-linac-validation/output/rtgamma/lung3d_report_search_log.json` 繧ｷ繝輔ヨ謗｢邏｢繝ｭ繧ｰ

## 螳溯｣・Γ繝｢

- RTDOSE 縺ｮ蠎ｧ讓吶・ `ImagePositionPatient` / `ImageOrientationPatient` / `PixelSpacing` / `GridFrameOffsetVector` 繧堤畑縺・※ LPS 縺ｸ蠕ｩ蜈・- 隧穂ｾ｡蛛ｴ縺ｯ蜿ら・繧ｰ繝ｪ繝・ラ荳翫∈騾｣邯夂ｩｺ髢楢｣憺俣・・scipy.ndimage.map_coordinates`・・- 繧ｬ繝ｳ繝槭・ `numba` 螳溯｣・ｼ・D・峨〒鬮倬溷喧縲…utoff譛ｪ貅縺ｯ髯､螟・- 繧ｷ繝輔ヨ謗｢邏｢縺ｯ coarse竊断ine 縺ｮ2谿ｵ髫弱げ繝ｪ繝・ラ繧ｵ繝ｼ繝・
## 譛霑代・菫ｮ豁｣・磯㍾隕・ｼ・
- GFOV 縺ｨ繝輔Ξ繝ｼ繝驟榊・縺ｮ蜷梧悄・啻GridFrameOffsetVector` 縺ｫ蜷医ｏ縺帙※Z繧ｹ繝ｩ繧､繧ｹ鬆・ｺ上ｒ譏・・↓蜀埼・鄂ｮ・・dose = dose[order, ...]`・峨・蠎ｧ讓吶→繝・・繧ｿ縺ｮ荳堺ｸ閾ｴ繧定ｧ｣豸医・- 蜴溽せ蟾ｮ陬懈ｭ｣縺ｮ蜴ｳ蟇・喧・唔PP蟾ｮ繧貞盾辣ｧ縺ｮ譁ｹ蜷台ｽ吝ｼｦ・・ow/col/slice・峨∈蟆・ｽｱ縺励※蜷・ｻｸ蟾ｮ・・x,dy,dz・峨ｒ邂怜・縲・- 譛驕ｩ繧ｷ繝輔ヨ驕ｩ逕ｨ縺ｮ譁ｹ蜷台ｿｮ豁｣・壼盾辣ｧ霆ｸ謌仙・縺ｮ繧ｷ繝輔ヨ繧・LPS 繝吶け繝医Ν縺ｸ螟画鋤縺励※縺九ｉ繝ｪ繧ｵ繝ｳ繝励Μ繝ｳ繧ｰ縺ｫ驕ｩ逕ｨ縲・- 蜃ｺ蜉帛・繝・ぅ繝ｬ繧ｯ繝医Μ縺ｮ螳牙・蛹厄ｼ夂ｩｺ繝・ぅ繝ｬ繧ｯ繝医Μ蜷阪〒 `os.makedirs('')` 縺ｫ縺ｪ繧峨↑縺・ｈ縺・ぎ繝ｼ繝峨・
## 譌｢遏･縺ｮ蛻ｶ髯・/ 莉雁ｾ後・諡｡蠑ｵ

- ROI/繝槭せ繧ｯ・・TSTRUCT騾｣謳ｺ・峨・譛ｪ螳溯｣・ｼ郁ｦ∵悍縺後≠繧後・蟇ｾ蠢懶ｼ・- 螻謇謗｢邏｢・・elder-Mead 遲会ｼ峨・霑ｽ蜉讀懆ｨ・- GPU・・uPy・牙ｯｾ蠢懊・莉雁ｾ梧､懆ｨ・ 
---

繧ｵ繝悶・繝ｭ繧ｸ繧ｧ繧ｯ繝茨ｼ・D繝励Ο繝輔ぃ繧､繝ｫ豈碑ｼ・ｼ峨・ `phits-linac-validation/README.md` 繧貞盾辣ｧ縺励※縺上□縺輔＞縲・
## 繧ｯ繧､繝・け繧ｹ繧ｿ繝ｼ繝茨ｼ域耳螂ｨ・・
- 萓晏ｭ倥・蟆主・・亥・迴ｾ諤ｧ縺ｮ縺溘ａ縺ｫ貅匁侠迚医ｒ菴ｿ逕ｨ・・  - `pip install -r REQUIREMENTS.txt`
- 閾ｪ蟾ｱ豈碑ｼ・ｼ・anity check・・  - `python -m rtgamma.main --ref dicom/RTDOSE_2.16.840.1.114337.1.2604.1760077605.1.dcm --eval dicom/RTDOSE_2.16.840.1.114337.1.2604.1760077605.1.dcm --mode 3d --report phits-linac-validation/output/rtgamma/self_check`
- 繝壹い豈碑ｼ・・萓具ｼ・D, 譌｢螳・3%/2mm/10%・・  - `python -m rtgamma.main --ref dicom/RTDOSE_2.16.840.1.114337.1.2604.1760077605.3.dcm --eval dicom/RTDOSE_2.16.840.1.114337.1.2604.1760079109.3.dcm --mode 3d --report phits-linac-validation/output/rtgamma/pair3_3d`

## 髢｢騾｣繝峨く繝･繝｡繝ｳ繝・
- `AGENTS.md`・郁ｲ｢迪ｮ繧ｬ繧､繝会ｼ・- `TROUBLESHOOTING.md`・医ヨ繝ｩ繝悶Ν繧ｷ繝･繝ｼ繝茨ｼ・- `TEST_PLAN.md`・域焔蜍募屓蟶ｰ縺ｮ謇矩・ｼ・- `CHANGELOG.md`・亥､画峩螻･豁ｴ・・- `DECISIONS.md`・井ｸｻ隕∵橿陦灘愛譁ｭ縺ｮ隕∫ｴ・ｼ・
## 譛ｬ譌･縺ｮ謌先棡・・025-10-15・・
- 繝ｬ繝昴・繝域僑蠑ｵ縺ｨ隴ｦ蜻雁・蜉幢ｼ育ｴ泌ｹｾ菴輔・遒ｺ隱阪ｒ蠑ｷ蛹厄ｼ・  - `FrameOfReferenceUID` 繧偵Ξ繝昴・繝医↓蜃ｺ蜉幢ｼ・ref_for_uid`,`eval_for_uid`,`same_for_uid`・峨・  - 譛驕ｩ繧ｷ繝輔ヨ縺ｮ螟ｧ縺阪＆繧貞・蜉幢ｼ・best_shift_mag_mm`・峨＠縲∵園螳壹＠縺阪＞蛟､・域里螳・0 mm・芽ｶ・℃縺ｧ `warnings` 縺ｫ譏守､ｺ縲・  - 譁ｹ蜷台ｽ吝ｼｦ縺ｮ荳閾ｴ蠎ｦ繧呈焚蛟､蛹厄ｼ・orientation_min_dot`・峨＠縲√★繧後′螟ｧ縺阪＞蝣ｴ蜷医・隴ｦ蜻翫・  - 邏泌ｹｾ菴包ｼ・--opt-shift off` 縺九▽ `--norm none`・峨〒縺ｮ螳溯｡後ｒ `absolute_geometry_only` 縺ｨ縺励※繝ｬ繝昴・繝医↓譏守､ｺ縲・
- 螳溯｡後せ繧ｯ繝ｪ繝励ヨ縺ｮ霑ｽ蜉繝ｻ謾ｹ蝟・ｼ・owerShell・・  - `scripts/run_autofallback.ps1`: 邏泌ｹｾ菴補・縺励″縺・､譛ｪ貅/隴ｦ蜻翫≠繧翫〒蠎・爾邏｢・按ｱ150/ﾂｱ50/ﾂｱ50, 5mm・峨↓閾ｪ蜍輔ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ縲・D蜀崎ｩ穂ｾ｡繧ょｮ滓命縲・  - 螟画焚螻暮幕縺ｧ縺ｮ繧ｳ繝ｭ繝ｳ豺ｷ蝨ｨ縺ｫ蟇ｾ縺吶ｋPowerShell縺ｮ荳榊・蜷医ｒ蝗樣∩・・-f` 縺ｧ譁・ｭ怜・蜷域・・峨・  - `scripts/run_test02_2d.ps1` / `run_test02_abs_vs_bestshift.ps1` / `run_test02_wide_bestshift.ps1` 繧呈紛蛯吶・
- 繝倥ャ繝豈碑ｼ・Θ繝ｼ繝・ぅ繝ｪ繝・ぅ
  - `scripts/compare_rtdose_headers.py`: 2縺､縺ｮRTDOSE縺ｮ DICOM 蟷ｾ菴輔・繧ｹ繧ｱ繝ｼ繝ｫ縺ｮ蟾ｮ蛻・ｒMarkdown縺ｧ荳隕ｧ蛹厄ｼ・oR, IPP/IOP, PixelSpacing, GFOV遽・峇繝ｻ荳ｭ螟ｮ蛟､繧ｹ繝・ャ繝・ DoseUnits/Scaling, 繝ｯ繝ｼ繝ｫ繝牙ｺｧ讓咏ｯ・峇, 蜴溽せ蟾ｮ(dx,dy,dz) 縺ｪ縺ｩ・峨・
- 螳滓ｸｬ逧・ｭｦ縺ｳ
  - Test04・・MV vs 10MV・峨〒縺ｯ邏泌ｹｾ菴輔・縺ｿ縺ｧ 3D GPR 竕・60% 縺ｨ螯･蠖薙ゅお繝阪Ν繧ｮ繝ｼ蟾ｮ縺ｮ蠖｢迥ｶ驕輔＞縺瑚ｦ∝屏縲・  - Test01/03・・SD=100 cm・峨〒縺ｮ螟ｧ繧ｷ繝輔ヨ繝ｻ菴雑PR縺ｯ縲∬ｨｭ螳夲ｼ・SD/SCD/繧｢繧､繧ｽ荳ｭ蠢・ｼ峨・鬟溘＞驕輔＞縺梧怏蜉帛屏蟄舌・  - Test02/04・・CD=100 cm・峨〒縺ｯ蟷ｾ菴輔′濶ｯ螂ｽ縺ｧ縲；PR縺梧隼蝟・・
螳溯｡御ｾ具ｼ・陦鯉ｼ・- 閾ｪ蜍輔ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ・井ｾ・ Test03・・  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_autofallback.ps1 -Name Test03_auto -Ref "dicom\Test03\RTDOSE_2.16.840.1.114337.1.2604.1760077605.4.dcm" -Eval "dicom\Test03\RTDOSE_2.16.840.1.114337.1.2604.1760077605.5.dcm"`

## 豕ｨ諢丈ｺ矩・
- 蛟倶ｺｺ諠・ｱ・・HI・峨ｒ蜷ｫ繧DICOM縺ｯ繝ｪ繝昴ず繝医Μ縺ｫ繧ｳ繝溘ャ繝医＠縺ｪ縺・〒縺上□縺輔＞・亥酔譴ｱ繧ｵ繝ｳ繝励Ν縺ｯ蛹ｿ蜷榊喧逕ｨ騾費ｼ峨・- 逕滓・迚ｩ繝ｻ螟ｧ螳ｹ驥上ヵ繧｡繧､繝ｫ縺ｯ讌ｵ蜉帙さ繝溘ャ繝医○縺壹～phits-linac-validation/output/rtgamma/` 驟堺ｸ九↓菫晏ｭ倥＠縺ｦ縺上□縺輔＞・・it ignore 謗ｨ螂ｨ・峨・
## 2025蟷ｴ10譛・4譌･縺ｮ隱ｿ譟ｻ繧ｵ繝槭Μ

`rtgamma`繝・・繝ｫ縺後∫黄逅・噪縺ｫ縺ｻ縺ｼ蜷御ｸ縺ｧ縺ゅｋ縺ｹ縺・縺､縺ｮRTDOSE繝輔ぃ繧､繝ｫ・・CC蟇ｾMC・峨↓蟇ｾ縺励※菴弱＞繧ｬ繝ｳ繝槭ヱ繧ｹ邇・ｒ遉ｺ縺吝撫鬘後・隱ｿ譟ｻ繧定｡後▲縺溘・
### 蛻､譏弱＠縺溽せ

1.  **蟷ｾ菴募ｭｦ逧・↑蝠城｡・**
    -   2縺､縺ｮ繝輔ぃ繧､繝ｫ縺ｮ`ImagePositionPatient`・亥ｺｧ讓吝次轤ｹ・峨・X霆ｸ縺形+114mm`逡ｰ縺ｪ縺｣縺ｦ縺・ｋ縲・    -   繝・・繝ｫ縺ｮ閾ｪ蜍募次轤ｹ陬懈ｭ｣繝ｭ繧ｸ繝・け縺御ｸ埼←蛻・〒縺ゅｋ蜿ｯ閭ｽ諤ｧ縺碁ｫ倥￥縲√％繧後ｒ謇薙■豸医☆縺溘ａ縺ｫ謇句虚縺ｧ`dx 竕・-114mm`縺ｮ繧ｷ繝輔ヨ繧帝←逕ｨ縺吶ｋ縺薙→縺ｧ縲∵ｭ｣縺励＞蟷ｾ菴募ｭｦ逧・ｽ咲ｽｮ縺ｫ霑代▼縺上％縺ｨ縺悟愛譏弱＠縺溘・
2.  **邱夐㍼逧・↑蝠城｡・**
    -   2縺､縺ｮ繝輔ぃ繧､繝ｫ縺ｮ`DoseGridScaling`・育ｷ夐㍼螟画鋤菫よ焚・峨′逡ｰ縺ｪ縺｣縺ｦ縺・ｋ縲・    -   繝・・繝ｫ縺ｮ蜀・Κ縺ｫ縺ゅ▲縺溘∵怙螟ｧ蛟､繧貞ｼｷ蛻ｶ逧・↓荳閾ｴ縺輔○繧区ｭ｣隕丞喧蜃ｦ逅・ｒ辟｡蜉ｹ蛹悶＠縺溘・    -   縺昴・荳翫〒邨ｶ蟇ｾ邱夐㍼豈碑ｼ・ｒ陦後▲縺溽ｵ先棡縲∽ｾ晉┯縺ｨ縺励※繧ｬ繝ｳ繝櫁ｩ穂ｾ｡縺御ｸ榊粋譬ｼ・医ヱ繧ｹ邇・< 3%・峨→縺ｪ縺｣縺溘ゅ％繧後・縲・縺､縺ｮ繧｢繝ｫ繧ｴ繝ｪ繧ｺ繝縺ｮ險育ｮ礼ｵ先棡縺ｫ縲．ICOM隕乗ｼ縺ｫ貅匁侠縺励◆豈碑ｼ・〒縺ｯ辟｡隕悶〒縺阪↑縺・檎悄縺ｮ蟾ｮ縲阪′蟄伜惠縺吶ｋ縺薙→繧堤､ｺ蜚・＠縺ｦ縺・ｋ縲・
### 菫ｮ豁｣縺励◆繝・・繝ｫ蜀・・繝舌げ

-   `optimize.py`: 繧ｷ繝輔ヨ謗｢邏｢遽・峇縺ｮ隧穂ｾ｡繝ｭ繧ｸ繝・け繧剃ｿｮ豁｣縺励∵焔蜍輔〒縺ｮ繧ｷ繝輔ヨ驥丞崋螳壹ｒ蜿ｯ閭ｽ縺ｫ縺励◆縲・-   `main.py`: 邨ｶ蟇ｾ邱夐㍼豈碑ｼ・ｒ螯ｨ縺偵※縺・◆蠑ｷ蛻ｶ豁｣隕丞喧蜃ｦ逅・ｒ辟｡蜉ｹ蛹悶＠縺溘・
