import argparse
import json
import numpy as np
from pathlib import Path


def compute_pass_rate(g2d: np.ndarray) -> float:
    finite = np.isfinite(g2d)
    if not finite.any():
        return float("nan")
    return float(np.sum((g2d <= 1.0) & finite) / np.sum(finite) * 100.0)


def main(argv=None):
    p = argparse.ArgumentParser(description="Compare 3D gamma slice GPR to 2D report")
    p.add_argument("npz", help="Path to 3D gamma NPZ (keys: gamma)")
    p.add_argument("--plane", choices=["axial", "sagittal", "coronal"], required=True)
    p.add_argument("--index", type=int, required=True, help="Slice index along the chosen plane")
    p.add_argument("--report2d", required=True, help="Path to 2D JSON report for comparison")
    p.add_argument("--tolerance_pp", type=float, default=0.5, help="Allowed difference in percentage points")
    args = p.parse_args(argv)

    gamma3d = np.load(args.npz)["gamma"]  # shape: (z,y,x)
    plane = args.plane
    sl = int(args.index)
    if plane == "axial":
        g_slice = gamma3d[sl, :, :]
    elif plane == "sagittal":
        g_slice = gamma3d[:, :, sl]
    else:  # coronal
        g_slice = gamma3d[:, sl, :]

    gpr_3d_slice = compute_pass_rate(g_slice)

    with open(args.report2d, "r", encoding="utf-8") as f:
        r2 = json.load(f)
    gpr_2d = float(r2.get("pass_rate_percent"))

    diff_pp = abs(gpr_3d_slice - gpr_2d)
    print(json.dumps({
        "plane": plane,
        "index": sl,
        "gpr_3d_slice": gpr_3d_slice,
        "gpr_2d": gpr_2d,
        "diff_pp": diff_pp,
        "within_tolerance": bool(diff_pp <= args.tolerance_pp)
    }, ensure_ascii=False))

    if diff_pp > args.tolerance_pp:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

