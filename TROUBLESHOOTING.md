# Troubleshooting

## Common Issues
- FileNotFoundError on report paths
  - Cause: parent directory missing.
  - Fix: tool now auto-creates directories when dirname is non-empty. Pass full paths like `phits-linac-validation/output/rtgamma/run3d`.
- Missing TransferSyntaxUID in DICOM
  - Cause: non-Part 10 files or incomplete meta.
  - Fix: loader defaults to ImplicitVRLittleEndian when absent.
- Very low pass rates for different systems
  - Cause: true geometric/scale differences across sources (grid size, scaling, origin).
  - Action: confirm with 2D visuals and logs; try `--dd 3 --dta 3` or ROI-limited evaluation.
- Multi-line commands on PowerShell fail
  - Use single-line `python -m ...` or separate lines; avoid here-docs.
- PowerShell string with colon and variables fails (InvalidVariableReference)
  - Use composite formatting: `"x:{0}:{0}:1" -f $dx` instead of `"x:$dx:$dx:1"`.
- Matplotlib display issues on servers
  - Use non-interactive save only (default) or set `MPLBACKEND=Agg`.
- Line endings / CRLF warnings in Git
  - Prefer text files with LF; avoid committing generated binaries/outputs.

## Performance Tips
- Use `--opt-shift on` with coarse-to-fine (default) for balanced runtime.
- Keep search ranges tight for clinical QA (e.g., `x:-3:3:1,y:-3:3:1,z:-3:3:1`).
- Numba JIT: first call may be slower; subsequent runs are faster.
- Wide search is expensive: prefer two-stage search
  - Coarse: e.g., `x:-150:150:10,y:-30:30:10,z:-30:30:10, --refine none`
  - Refine around the best: e.g., `x:75:85:1,y:-55:-45:1,z:-25:-15:1, --refine coarse2fine`

## Validation Checklist
- Self-compare of a single RTDOSE yields ~100% pass.
- Pair logs show IPP/IOP/PixelSpacing/GFOV echoed; verify expected geometry.
- Outputs saved under `phits-linac-validation/output/rtgamma/` with CSV/JSON/MD and images for 2D.
- Check report fields for geometry sanity:
  - `same_for_uid==true`, `orientation_min_dot≈1.0`, small `best_shift_mag_mm` in absolute runs.
