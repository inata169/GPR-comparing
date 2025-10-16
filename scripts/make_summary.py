#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def build_summary(case: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / case
    # Reports JSON paths
    j3d = out_dir / f"{case}_3d.json"
    jax = out_dir / f"{case}_axial.json"
    jsg = out_dir / f"{case}_sagittal.json"
    jco = out_dir / f"{case}_coronal.json"
    with open(j3d, 'r', encoding='utf-8') as f:
        r3d = json.load(f)
    with open(jax, 'r', encoding='utf-8') as f:
        rax = json.load(f)
    with open(jsg, 'r', encoding='utf-8') as f:
        rsg = json.load(f)
    with open(jco, 'r', encoding='utf-8') as f:
        rco = json.load(f)

    # Markdown summary
    md_lines = []
    md_lines.append(f"# {case} Summary (3D + 2D views)")
    md_lines.append("")
    md_lines.append("| View | Pass Rate (%) | Image | Diff |")
    md_lines.append("|---|---:|---|---|")
    md_lines.append(f"| 3D | {r3d['pass_rate_percent']} | - | - |")
    img = {
        'axial': (f"{case}_axial_gamma.png", f"{case}_axial_diff.png"),
        'sagittal': (f"{case}_sagittal_gamma.png", f"{case}_sagittal_diff.png"),
        'coronal': (f"{case}_coronal_gamma.png", f"{case}_coronal_diff.png"),
    }
    for view, rep in [('axial', rax), ('sagittal', rsg), ('coronal', rco)]:
        pr = rep['pass_rate_percent']
        g, d = img[view]
        md_lines.append(f"| {view} | {pr} | {g} | {d} |")
    md_path = out_dir / f"{case}_summary.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

    # Simple PDF with matplotlib
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.image as mpimg

    pdf_path = out_dir / f"{case}_summary.pdf"
    with PdfPages(pdf_path) as pdf:
        # Page 1: Gamma maps
        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        for ax, view in zip(axes, ['axial', 'sagittal', 'coronal']):
            img_path = out_dir / img[view][0]
            ax.imshow(mpimg.imread(img_path))
            ax.set_title(f"{view} gamma")
            ax.axis('off')
        fig.suptitle(f"{case} Gamma Maps | 3D GPR: {r3d['pass_rate_percent']:.3f}%")
        plt.tight_layout(rect=[0, 0, 1, 0.92])
        pdf.savefig(fig); plt.close(fig)
        # Page 2: Dose difference maps
        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        for ax, view in zip(axes, ['axial', 'sagittal', 'coronal']):
            img_path = out_dir / img[view][1]
            ax.imshow(mpimg.imread(img_path))
            ax.set_title(f"{view} diff (%)")
            ax.axis('off')
        fig.suptitle(f"{case} Dose Difference (%)")
        plt.tight_layout(rect=[0, 0, 1, 0.92])
        pdf.savefig(fig); plt.close(fig)
    return md_path, pdf_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', default='Test05', help='Case prefix (e.g., Test05)')
    ap.add_argument('--out-dir', default='phits-linac-validation/output/rtgamma')
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    md, pdf = build_summary(args.case, out_dir)
    print(f"Wrote {md}")
    print(f"Wrote {pdf}")


if __name__ == '__main__':
    main()

