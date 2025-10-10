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
- Matplotlib display issues on servers
  - Use non-interactive save only (default) or set `MPLBACKEND=Agg`.
- Line endings / CRLF warnings in Git
  - Prefer text files with LF; avoid committing generated binaries/outputs.

## Performance Tips
- Use `--opt-shift on` with coarse-to-fine (default) for balanced runtime.
- Keep search ranges tight for clinical QA (e.g., `x:-3:3:1,y:-3:3:1,z:-3:3:1`).
- Numba JIT: first call may be slower; subsequent runs are faster.

## Validation Checklist
- Self-compare of a single RTDOSE yields ~100% pass.
- Pair logs show IPP/IOP/PixelSpacing/GFOV echoed; verify expected geometry.
- Outputs saved under `phits-linac-validation/output/rtgamma/` with CSV/JSON/MD and images for 2D.
