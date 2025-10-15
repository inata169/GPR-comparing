# TODO (Next Actions)

Date: 2025-10-15

High priority
- [ ] Header diffs: run scripts/compare_rtdose_headers.py for Test01–04 and review outputs
  - [ ] Test01 → phits-linac-validation/output/rtgamma/Test01_dose_compare.md
  - [ ] Test02 → phits-linac-validation/output/rtgamma/Test02_dose_compare.md
  - [ ] Test03 → phits-linac-validation/output/rtgamma/Test03_dose_compare.md
  - [ ] Test04 → phits-linac-validation/output/rtgamma/Test04_dose_compare.md
  - [ ] Summarize findings (SSD vs SCD/SAD; origin deltas; FoR; orientation) into headers_summary.md

- [ ] RTPLAN support in header compare
  - [ ] Extend scripts/compare_rtdose_headers.py with --plan-a/--plan-b
  - [ ] Extract: IsocenterPosition, SAD (and SSD estimate if derivable), BeamName if available
  - [ ] Report deltas: plan_isocenter_delta_mm, SAD/SSD differences

- [ ] Auto-fallback improvements
  - [ ] Standardize two-stage search: coarse (e.g., x:-150:150:10,y:-30:30:10,z:-30:30:10, --refine none) → fine (±10 mm, 1 mm)
  - [ ] Early stop if improvement < epsilon across N steps
  - [ ] Include warnings/same_for_uid/orientation_min_dot in scripts/run_autofallback.ps1 summary output

Medium priority
- [ ] Update command.txt with new presets after enhancements
- [ ] Documentation
  - [ ] README: note on SSD vs SCD(SAD) impacts on GPR; link to header-compare flow
  - [ ] TEST_PLAN: recommended flow (Header compare → Absolute geometry → Coarse → Fine; optional ROI)

Optional / stretch
- [ ] ROI/RTSTRUCT masking for ROI-limited GPR
- [ ] Local gamma option wired to CLI and report
- [ ] 2D pre-scan to narrow 3D search space automatically

How to resume
1) Generate header diffs (see command.txt lines 15–18) and review Notes sections.
2) If geometry is sound, run absolute geometry (opt-shift=off, norm=none). If low GPR, use coarse→fine search.
3) If large shifts re-occur, confirm plan isocenter/SAD/SSD via RTPLAN comparison.

