# README 霑ｽ蜉諠・ｱ・・025-10・・
縺薙・繝ｪ繝ｪ繝ｼ繧ｹ縺ｧ霑ｽ蜉繝ｻ蠑ｷ蛹悶＆繧後◆讖溯・縺ｨ縲√◎縺ｮ菴ｿ縺・婿縺ｮ謚懃ｲ九〒縺吶・
## 霑ｽ蜉讖溯・

- 繝倥ャ繝豈碑ｼ・ヤ繝ｼ繝ｫ諡｡蠑ｵ・啻scripts/compare_rtdose_headers.py` 縺ｫ `--plan-a` / `--plan-b` 繧定ｿｽ蜉・・TPLAN縺ｮ Isocenter/SAD/SSD 繧樽D縺ｫ霑ｽ險假ｼ峨・- 閾ｪ蜍輔ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ蠑ｷ蛹厄ｼ育ｲ冷・蟇・・2谿ｵ謗｢邏｢縲∵掠譛滓遠縺｡蛻・ｊ縲・D荳ｭ螟ｮ繧ｹ繝ｩ繧､繧ｹ莠句燕繧ｹ繧ｭ繝｣繝ｳ・峨・  - 譁ｰ隕修LI: `--fine-range-mm` / `--fine-step-mm` / `--early-stop-epsilon` / `--early-stop-patience` / `--prescan-2d`縲・
## 繝倥ャ繝豈碑ｼ・ｼ・TPLAN縺ゅｊ・・```
python scripts/compare_rtdose_headers.py \
  --a <ref_rtdose.dcm> --b <eval_rtdose.dcm> \
  --plan-a <ref_rtplan.dcm> --plan-b <eval_rtplan.dcm> \
  --out phits-linac-validation/output/rtgamma/dose_compare.md
```

## 3D隗｣譫撰ｼ・谿ｵ謗｢邏｢・区掠譛滓遠縺｡蛻・ｊ繝ｻ2D莠句燕繧ｹ繧ｭ繝｣繝ｳ・・```
python -m rtgamma.main \
  --ref <ref.dcm> --eval <eval.dcm> --mode 3d \
  --shift-range "x:-10:10:2,y:-10:10:2,z:-10:10:2" \
  --fine-range-mm 5 --fine-step-mm 1 \
  --early-stop-epsilon 0.05 --early-stop-patience 200 \
  --report phits-linac-validation/output/rtgamma/run3d
```

## 2D蜿ｯ隕門喧・井ｸｭ螟ｮ繧ｹ繝ｩ繧､繧ｹ縲∵怙驕ｩ蛹飽FF・・```
python -m rtgamma.main \
  --ref <ref.dcm> --eval <eval.dcm> \
  --mode 2d --plane axial --plane-index auto --opt-shift off \
  --save-gamma-map phits-linac-validation/output/rtgamma/axial_gamma.png \
  --save-dose-diff phits-linac-validation/output/rtgamma/axial_diff.png \
  --report phits-linac-validation/output/rtgamma/axial
```

## 縺ｾ縺ｨ繧∝・蜉幢ｼ医し繝槭ΜMD/PDF・・```
python scripts/make_summary.py --case Test05 --out-dir phits-linac-validation/output/rtgamma
```

陬懆ｶｳ・夊ｩｳ邏ｰ縺ｪ菫ｮ豁｣螻･豁ｴ縺ｯ `CHANGELOG.md` 繧貞盾辣ｧ縺励※縺上□縺輔＞縲・
## 髢狗匱逕ｨ繝・せ繝茨ｼ・ytest・・
- 萓晏ｭ倩ｿｽ蜉・医Ο繝ｼ繧ｫ繝ｫ・・```
pip install -r requirements-dev.txt
```
- 螳溯｡・```
pytest -q
```
- 蜷ｫ縺ｾ繧後ｋ繝・せ繝・  - `tests/test_headers_script.py`: 繝倥ャ繝豈碑ｼ・せ繧ｯ繝ｪ繝励ヨ縺ｮ螳溯｡梧､懆ｨｼ
  - `tests/test_cli_2d_axial.py`: 2D axial 荳ｭ螟ｮ繧ｹ繝ｩ繧､繧ｹ・域怙驕ｩ蛹飽FF・峨・CLI螳溯｡・  - `tests/test_io_monotonic.py`: DICOM GFOV 縺ｮ蜊倩ｪｿ諤ｧ讀懆ｨｼ
  - `tests/test_gamma_3d_quick.py`: Test05繧堤畑縺・◆蟆城伜沺3D繧ｬ繝ｳ繝橸ｼ育洒譎る俣逕ｨ繧ｯ繝ｭ繝・・・・

## 臨床プリセット（profiles）

典型的な条件を `--profile` で一括指定できます（いずれもシフト最適化OFF）。

- 絶対線量: `--profile clinical_abs`（DD=3, DTA=2, Cutoff=10, norm=none）
- 相対線量: `--profile clinical_rel`（DD=3, DTA=2, Cutoff=10, norm=global_max）
- 2%/2mm: `--profile clinical_2x2`
- 3%/3mm: `--profile clinical_3x3`

例）相対線量・2D中央スライス（axial）
```
python -m rtgamma.main --profile clinical_rel \
  --ref dicom/Test05/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm \
  --eval dicom/Test05/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm \
  --mode 2d --plane axial --plane-index auto \
  --save-gamma-map phits-linac-validation/output/rtgamma/Test05_axial_gamma.png \
  --save-dose-diff phits-linac-validation/output/rtgamma/Test05_axial_diff.png \
  --report phits-linac-validation/output/rtgamma/Test05_axial
```

並列スレッド数は `--threads` で指定できます（Numbaスレッド）。
