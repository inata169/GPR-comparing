"""PDF generation module for rtgamma."""

import json
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
    HAS_JAPANESE_FONT = True
except Exception:
    HAS_JAPANESE_FONT = False


def _get_config():
    """Load PDF report configuration."""
    def_conf = {
        "facility_name": "Generic Hospital",
        "department": "Radiation Oncology",
        "machine_name": "LINAC",
        "physicist_name": "Default Physicist",
        "logo_path": "",
        "language": "en"
    }
    # try to find config/report_template.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base_dir, 'config', 'report_template.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                user_conf = json.load(f)
                def_conf.update(user_conf)
        except Exception:
            pass
    return def_conf


def save_summary_pdf(path: str, summary: dict):
    """Generate a QA PDF report."""
    config = _get_config()

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    font_name = 'HeiseiKakuGo-W5' if HAS_JAPANESE_FONT else 'Helvetica'

    # Title style
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=18,
        spaceAfter=14,
        alignment=1 # Center
    )

    # Base text style
    text_style = ParagraphStyle(
        'BaseText',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        spaceAfter=6,
    )

    # Bold text style
    if HAS_JAPANESE_FONT:
        bold_font = 'HeiseiKakuGo-W5'
    else:
        bold_font = 'Helvetica-Bold'

    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=10,
        spaceAfter=6,
    )

    Story = []

    # Header / Title
    fac_name = config.get('facility_name', 'Generic Hospital')
    Story.append(Paragraph(fac_name, text_style))
    Story.append(Paragraph("Gamma Analysis QA Report", title_style))
    Story.append(Spacer(1, 0.2*inch))

    # Patient Info & Run Info Table
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Extract data from summary
    ref_name = summary.get('ref', '')
    eval_name = summary.get('eval', '')
    patient_id = summary.get('patient_id', os.path.splitext(ref_name)[0])

    gpr = summary.get('pass_rate_percent', 'N/A')
    if isinstance(gpr, float):
        gpr_str = f"{gpr:.2f} %"
    else:
        gpr_str = str(gpr)

    dta = summary.get('dta_mm', 'N/A')
    dd = summary.get('dd_percent', 'N/A')
    cutoff = summary.get('cutoff_percent', 'N/A')
    criteria_str = f"{dd}%, {dta}mm, TH: {cutoff}%"

    info_data = [
        ["Patient ID:", patient_id, "Date:", date_str],
        ["Reference:", ref_name, "Machine:", config.get('machine_name', '')],
        ["Evaluation:", eval_name, "Physicist:", config.get('physicist_name', '')],
        ["Criteria:", criteria_str, "Overall GPR:", gpr_str],
    ]

    info_table = Table(info_data, colWidths=[1.5*inch, 3*inch, 1.2*inch, 1.5*inch])
    info_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 10),
        ('FONT', (0,0), (0,-1), bold_font, 10),
        ('FONT', (2,0), (2,-1), bold_font, 10),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    Story.append(info_table)
    Story.append(Spacer(1, 0.4*inch))

    # Result Status Block
    status = "PASS"
    status_color = colors.green
    if isinstance(gpr, float):
        if gpr < 90.0:
            status = "FAIL"
            status_color = colors.red
        elif gpr < 95.0:
            status = "WARNING"
            status_color = colors.orange

    status_style = ParagraphStyle(
        'StatusText',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=16,
        textColor=status_color,
        alignment=1
    )
    Story.append(Paragraph(f"STATUS: {status} (GPR = {gpr_str})", status_style))
    Story.append(Spacer(1, 0.4*inch))

    # Per structure sub-table
    per_struct = summary.get('per_structure', [])
    if per_struct:
        Story.append(Paragraph("ROI Gamma Analysis", bold_style))
        Story.append(Spacer(1, 0.1*inch))

        table_headers = ["ROI Name", "GPR (%)", "Voxels", "Mean", "Median", "Max"]
        table_data = [table_headers]
        for s in per_struct:
            r_pr = s.get('pass_rate_percent', 'N/A')
            if isinstance(r_pr, float):
                r_pr = f"{r_pr:.2f}"
            rmn = s.get('gamma_mean', 'N/A')
            if isinstance(rmn, float): rmn = f"{rmn:.3f}"
            rmd = s.get('gamma_median', 'N/A')
            if isinstance(rmd, float): rmd = f"{rmd:.3f}"
            rmx = s.get('gamma_max', 'N/A')
            if isinstance(rmx, float): rmx = f"{rmx:.3f}"

            table_data.append([
                s.get('roi_name', ''),
                r_pr,
                str(s.get('voxel_count', '')),
                rmn,
                rmd,
                rmx
            ])

        roi_table = Table(table_data, hAlign='LEFT')
        roi_table.setStyle(TableStyle([
            ('FONT', (0,0), (-1,0), bold_font, 10),
            ('FONT', (0,1), (-1,-1), font_name, 9),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        Story.append(roi_table)
        Story.append(Spacer(1, 0.4*inch))

    # Gamma Map image
    img_path = summary.get('save_gamma_map_path')
    if img_path and os.path.exists(img_path) and img_path.lower().endswith('.png'):
        Story.append(Paragraph("Gamma Distribution (Central Slice)", bold_style))
        Story.append(Spacer(1, 0.1*inch))
        # Keep aspect ratio, bounding box max 6x4 inches
        img = Image(img_path, width=6*inch, height=4*inch, kind='proportional')
        img.hAlign = 'CENTER'
        Story.append(img)
        Story.append(Spacer(1, 0.4*inch))

    # Shift parameters & Warnings
    Story.append(Paragraph("Optimization & Warnings", bold_style))
    shift_mm = summary.get('best_shift_mm', (0,0,0))
    if isinstance(shift_mm, (tuple, list)):
        try:
            shift_str = f"({shift_mm[0]:.2f}, {shift_mm[1]:.2f}, {shift_mm[2]:.2f}) mm"
        except Exception:
            shift_str = str(shift_mm)
    else:
        shift_str = str(shift_mm)

    mode = summary.get('mode', '')
    plane_idx = summary.get('plane_index', '')
    mode_str = mode
    if mode == '2d' and plane_idx is not None:
        mode_str += f" (plane_index={plane_idx})"

    op_data = [
        ["Mode:", mode_str],
        ["Best Shift (x, y, z):", shift_str],
        ["Absolute Geometry:", str(summary.get('absolute_geometry_only', 'N/A'))],
        ["Warnings:", summary.get('warnings', 'None') or 'None'],
    ]
    op_table = Table(op_data, colWidths=[2*inch, 5*inch], hAlign='LEFT')
    op_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 9),
        ('FONT', (0,0), (0,-1), bold_font, 9),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    Story.append(op_table)
    Story.append(Spacer(1, 0.3*inch))

    # Environment & Reproducibility
    Story.append(Paragraph("Reproducibility Information", bold_style))
    import importlib.metadata
    import platform
    import sys
    
    env_info = [["Python", sys.version.split()[0], "Platform", platform.platform()]]
    pkgs = ["pydicom", "numpy", "scipy", "numba", "matplotlib", "reportlab"]
    pkg_row1 = []
    pkg_row2 = []
    for i, pkg in enumerate(pkgs):
        try:
            ver = importlib.metadata.version(pkg)
        except Exception:
            ver = "N/A"
        if i < 3:
            pkg_row1.extend([pkg, ver])
        else:
            pkg_row2.extend([pkg, ver])
            
    env_info.append(pkg_row1)
    env_info.append(pkg_row2)

    env_table = Table(env_info, colWidths=[1*inch, 1.3*inch, 1*inch, 1.3*inch, 1*inch, 1.3*inch], hAlign='LEFT')
    env_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 8),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.darkgrey),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    Story.append(env_table)
    Story.append(Spacer(1, 0.1*inch))
    
    cmd_str = " ".join(sys.argv)
    cmd_para = Paragraph(f"Command: {cmd_str}", text_style)
    cmd_data = [[cmd_para]]
    cmd_table = Table(cmd_data, colWidths=[7*inch], hAlign='LEFT')
    cmd_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 8),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.darkgrey),
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    Story.append(cmd_table)
    Story.append(Spacer(1, 0.4*inch))

    # Signature line
    sig_data = [
        ["", "Reviewed By:  __________________________", "Date: _______________"]
    ]
    sig_table = Table(sig_data, colWidths=[2.5*inch, 3*inch, 1.5*inch])
    sig_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 10),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
    ]))
    Story.append(sig_table)

    doc.build(Story)
