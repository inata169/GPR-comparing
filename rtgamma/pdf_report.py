"""PDF generation module for rtgamma."""

import json
import os
from datetime import datetime

import numpy as np
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
    cfg_dir = os.path.join(base_dir, 'config')
    cfg_path = os.path.join(cfg_dir, 'report_template.json')
    
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                user_conf = json.load(f)
                def_conf.update(user_conf)
        except Exception:
            pass
    else:
        # Create default config file if it does not exist
        try:
            os.makedirs(cfg_dir, exist_ok=True)
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(def_conf, f, indent=4, ensure_ascii=False)
            import logging
            logging.info(f"Created default PDF report template at {cfg_path}. You can edit this file to customize your facility details.")
        except Exception:
            pass
            
    return def_conf


def save_summary_pdf(path: str, summary: dict):
    """Generate a research-use gamma-analysis PDF report."""
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
    Story.append(Paragraph("Gamma Analysis Research Report", title_style))
    Story.append(Spacer(1, 0.2*inch))

    # Output directory for charts
    output_dir = os.path.dirname(path)
    chart_dir = os.path.join(output_dir, 'chart')
    os.makedirs(chart_dir, exist_ok=True)

    # Patient Info & Run Info Table
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Extract data from summary
    ref_base = os.path.basename(summary.get('ref', ''))
    eval_base = os.path.basename(summary.get('eval', ''))
    patient_id_str = str(summary.get('patient_id', os.path.splitext(ref_base)[0]))

    # Wrap inside Paragraphs to enable word-wrapping and prevent horizontal overlap
    ref_para = Paragraph(ref_base, text_style)
    eval_para = Paragraph(eval_base, text_style)
    patient_para = Paragraph(patient_id_str, text_style)

    gpr = summary.get('pass_rate_percent', 'N/A')
    if isinstance(gpr, float):
        gpr_str = f"{gpr:.2f} %"
    else:
        gpr_str = str(gpr)

    dta = summary.get('dta_mm', 'N/A')
    dd = summary.get('dd_percent', 'N/A')
    cutoff = summary.get('cutoff_percent', 'N/A')
    interp = summary.get('interp_fraction', 1)
    engine = summary.get('gamma_engine', 'unknown')
    engine_version = summary.get('gamma_engine_version', 'unknown')
    criteria_str = f"{dd}%, {dta}mm, TH: {cutoff}%, Interp: {interp}"

    # Statistics extraction
    g_mean = summary.get('gamma_mean', 'N/A')
    g_median = summary.get('gamma_median', 'N/A')
    g_max = summary.get('gamma_max', 'N/A')
    g_p95 = summary.get('gamma_p95', 'N/A')
    g_p99 = summary.get('gamma_p99', 'N/A')
    cutoff_qualified = summary.get('cutoff_qualified_points', 'N/A')
    common_spatial = summary.get('common_spatial_points', 'N/A')
    spatially_excluded = summary.get('spatially_excluded_points', 'N/A')
    evaluated_points = summary.get('evaluated_points', 'N/A')

    def fmt_num(val, prec=3):
        if isinstance(val, (float, int)):
            return f"{val:.{prec}f}"
        return str(val)

    info_data = [
        ["Patient ID:", patient_para, "Date:", date_str],
        ["Reference:", ref_para, "Machine:", config.get('machine_name', '')],
        ["Evaluation:", eval_para, "Physicist:", config.get('physicist_name', '')],
        ["Criteria:", criteria_str, "Overall GPR:", gpr_str],
        ["Gamma Engine:", f"{engine} {engine_version}", "", ""],
    ]

    info_table = Table(info_data, colWidths=[1.1*inch, 2.7*inch, 1.2*inch, 2.4*inch])
    info_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 10),
        ('FONT', (0,0), (0,-1), bold_font, 10),
        ('FONT', (2,0), (2,-1), bold_font, 10),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    Story.append(info_table)
    Story.append(Spacer(1, 0.4*inch))

    # Research result block. A GPR alone is not a clinical acceptance decision.
    status_color = colors.black
    status_style = ParagraphStyle(
        'StatusText',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=16,
        textColor=status_color,
        alignment=1
    )
    Story.append(Paragraph(f"OBSERVED GPR: {gpr_str}", status_style))
    Story.append(Paragraph(
        "Research and education use only. This report is not a patient-QA, "
        "commissioning, treatment-decision, certification, or vendor-approval record.",
        text_style,
    ))
    Story.append(Spacer(1, 0.2*inch))

    # Global Statistics Table
    Story.append(Paragraph("Global Gamma Statistics", bold_style))
    stats_data = [
        ["Metric", "Value", "Metric", "Value"],
        ["Mean", fmt_num(g_mean), "P95", fmt_num(g_p95)],
        ["Median", fmt_num(g_median), "P99", fmt_num(g_p99)],
        ["Maximum", fmt_num(g_max), "", ""],
    ]
    stats_table = Table(stats_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch], hAlign='LEFT')
    stats_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 9),
        ('FONT', (0,0), (-1,0), bold_font, 9),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('ALIGN', (3,0), (3,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    Story.append(stats_table)
    Story.append(Spacer(1, 0.3*inch))

    Story.append(Paragraph("Evaluation Coverage", bold_style))
    coverage_data = [
        ["Cutoff-qualified", str(cutoff_qualified), "Common spatial", str(common_spatial)],
        ["Excluded outside Eval", str(spatially_excluded), "Evaluated", str(evaluated_points)],
    ]
    coverage_table = Table(
        coverage_data,
        colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch],
        hAlign='LEFT',
    )
    coverage_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 9),
        ('FONT', (0,0), (0,-1), bold_font, 9),
        ('FONT', (2,0), (2,-1), bold_font, 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    Story.append(coverage_table)
    Story.append(Spacer(1, 0.3*inch))

    # Gamma Histogram
    hist = summary.get('histogram', None)
    if hist:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            hist_filename = os.path.basename(path).replace('.pdf', '_autohist.png')
            hist_path = os.path.join(chart_dir, hist_filename)
            edges = hist['bin_edges']
            counts = hist['counts']
            c_pass = hist['cumulative_pass']

            fig, ax1 = plt.subplots(figsize=(6, 3))

            # Prepare bar data
            x_pos = []
            labels = []
            for i in range(len(edges) - 1):
                x_pos.append(i)
                labels.append(f"{edges[i]:.2f}-{edges[i+1]:.2f}")
            x_pos.append(len(edges) - 1)
            labels.append(f">{edges[-1]:.2f}")

            ax1.bar(x_pos, counts, color='steelblue', edgecolor='black', zorder=3)
            ax1.set_xticks(x_pos)
            ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
            ax1.set_xlabel('Gamma Value', fontsize=9)
            ax1.set_ylabel('Voxel Count', fontsize=9, color='steelblue')
            ax1.tick_params(axis='y', labelcolor='steelblue', labelsize=8)
            ax1.grid(True, linestyle='--', alpha=0.5, axis='y', zorder=0)

            # Cumulative pass rate line
            if len(c_pass) == len(counts):
                ax2 = ax1.twinx()
                ax2.plot(x_pos, c_pass, color='darkorange', marker='o', markersize=4, zorder=4)
                ax2.set_ylabel('Cumulative Pass (%)', fontsize=9, color='darkorange')
                ax2.tick_params(axis='y', labelcolor='darkorange', labelsize=8)
                ax2.set_ylim([0, 105])

            # Draw gamma=1.0 line
            try:
                idx_1 = edges.index(1.0)
                ax1.axvline(x=idx_1 - 0.5, color='red', linestyle='--', linewidth=1.5, zorder=5, label='Pass/Fail (g=1.0)')
                ax1.legend(loc='upper left', fontsize=8)
            except ValueError:
                pass

            plt.title('Gamma Histogram', fontsize=10)
            plt.tight_layout()
            plt.savefig(hist_path, dpi=150)
            plt.close(fig)

            Story.append(Paragraph("Gamma Histogram", bold_style))
            Story.append(Spacer(1, 0.1*inch))
            img_hist = Image(hist_path, width=5.5*inch, height=2.75*inch, kind='proportional')
            img_hist.hAlign = 'CENTER'
            Story.append(img_hist)
            Story.append(Spacer(1, 0.3*inch))
        except Exception as e:
            pass

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

        # --- ROI DVH Comparison Plots ---
        for s in per_struct:
            roi_name = s.get('roi_name', 'ROI')
            ref_dvh = s.get('ref_dvh')
            eval_dvh = s.get('eval_dvh')

            if ref_dvh and eval_dvh and 'dvh_bins' in ref_dvh:
                try:
                    import matplotlib.pyplot as plt
                    plt.figure(figsize=(6, 4))
                    
                    ref_name = summary.get('ref', 'Reference')
                    eval_name = summary.get('eval', 'Evaluation')
                    
                    plt.plot(ref_dvh['dvh_bins'], ref_dvh['dvh_vol'], 'k-', label=f'Ref: {ref_name}', linewidth=2)
                    plt.plot(eval_dvh['dvh_bins'], eval_dvh['dvh_vol'], 'r--', label=f'Eval: {eval_name}', linewidth=1.5)
                    
                    plt.title(f"DVH Comparison: {roi_name}", fontsize=12)
                    plt.xlabel("Dose", fontsize=10)
                    plt.ylabel("Volume (%)", fontsize=10)
                    plt.grid(True, linestyle=':', alpha=0.6)
                    plt.legend(loc='upper right', fontsize=8) # Smaller font to fit filenames
                    plt.ylim(0, 105)
                    plt.xlim(left=0)
                    
                    # Sanitize ROI name for filename
                    safe_roi = "".join([c if c.isalnum() or c in '.-' else '_' for c in roi_name])
                    dvh_filename = os.path.basename(path).replace('.pdf', f'_dvh_{safe_roi}.png')
                    dvh_plot_path = os.path.join(chart_dir, dvh_filename)
                    
                    plt.tight_layout()
                    plt.savefig(dvh_plot_path, dpi=120)
                    plt.close()

                    Story.append(Paragraph(f"DVH: {roi_name}", bold_style))
                    img_dvh = Image(dvh_plot_path, width=5*inch, height=3.3*inch, kind='proportional')
                    img_dvh.hAlign = 'CENTER'
                    Story.append(img_dvh)
                    
                    # Add metrics table for this ROI
                    metrics_headers = ["Metric", "Reference", "Evaluation", "Diff"]
                    metrics_data = [metrics_headers]
                    
                    for m in ['mean', 'max', 'd98', 'd95', 'd50', 'd2']:
                        r_val = ref_dvh.get(m, float('nan'))
                        e_val = eval_dvh.get(m, float('nan'))
                        diff = e_val - r_val if (not np.isnan(r_val) and not np.isnan(e_val)) else float('nan')
                        
                        metrics_data.append([
                            m.upper(),
                            fmt_num(r_val),
                            fmt_num(e_val),
                            fmt_num(diff)
                        ])
                    
                    m_table = Table(metrics_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch], hAlign='CENTER')
                    m_table.setStyle(TableStyle([
                        ('FONT', (0,0), (-1,0), bold_font, 9),
                        ('FONT', (0,1), (-1,-1), font_name, 8),
                        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ]))
                    Story.append(Spacer(1, 0.1*inch))
                    Story.append(m_table)
                    Story.append(Spacer(1, 0.4*inch))
                    
                except Exception as e:
                    import logging
                    logging.error(f"Failed to generate DVH plot for {roi_name}: {e}")

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
    provenance = summary.get('provenance', {})
    application = provenance.get('application', {})
    execution = provenance.get('execution', {})
    runtime = provenance.get('runtime', {})
    inputs = provenance.get('inputs', {})
    env_info = [
        ["Schema", provenance.get('schema_version', 'unknown'), "Application", application.get('version', 'unknown')],
        ["Git commit", application.get('git_commit', 'unknown'), "Dirty", application.get('git_dirty', 'unknown')],
        ["Python", runtime.get('python_version', 'unknown'), "Platform", f"{runtime.get('os', 'unknown')} {runtime.get('os_release', '')}"],
        ["Started UTC", execution.get('started_utc', 'unknown'), "Elapsed (s)", execution.get('elapsed_seconds', 'unknown')],
        ["Ref SHA-256", inputs.get('reference', {}).get('sha256', 'unknown'), "Eval SHA-256", inputs.get('evaluation', {}).get('sha256', 'unknown')],
    ]

    env_table = Table(env_info, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch], hAlign='LEFT')
    env_table.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), font_name, 8),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.darkgrey),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    Story.append(env_table)
    Story.append(Spacer(1, 0.1*inch))
    
    cmd_para = Paragraph(
        "Absolute command-line paths are intentionally omitted. Complete "
        "calculation settings are stored in the structured provenance block.",
        text_style,
    )
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
