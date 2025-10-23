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
