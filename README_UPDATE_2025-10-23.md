#+ Updates (2025-10-23)

- Local gamma support:
  - CLI: add `--gamma-type local`.
  - GUI: new checkbox "Local gamma" (default OFF = Global).
  - See `GPR_Global_vs_Local.md` for guidance and examples.
- OpenSpec docs initialized under `docs/openspec/`:
  - README, TEMPLATE, `report.schema.json`, examples, `GUI_RUN.md`.
  - Validate report JSON via `scripts/validate_report.py`.
- Slice consistency helper: `scripts/compare_slice_gpr.py` compares a 3D gamma slice vs a 2D report.
- Sample 2D/3D commands and schema validation steps are documented in `docs/openspec/rtgamma_openspec.md`.

Note: The main `README.md` contains legacy encoding artifacts. If you want, I can normalize it to UTF-8 (no BOM) and fold these updates directly into `README.md` in a follow-up.
