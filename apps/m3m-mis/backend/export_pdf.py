"""
M3M MIS - PDF export (section 16): full report + Executive One Pager.
Uses ReportLab for layout/tables and matplotlib (Agg backend, headless) for
the small chart images embedded in the PDF.
"""
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                 Spacer, Image, PageBreak, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

import analytics

NAVY = colors.HexColor("#1F3864")
LIGHT = colors.HexColor("#F2F5FA")
GREEN = colors.HexColor("#2E7D32")
AMBER = colors.HexColor("#F9A825")
RED = colors.HexColor("#C62828")
RAG_COLORS = {"green": GREEN, "amber": AMBER, "red": RED, "grey": colors.grey}

STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle("MISTitle", parent=STYLES["Title"], textColor=NAVY, fontSize=18, spaceAfter=2))
STYLES.add(ParagraphStyle("MISSub", parent=STYLES["Normal"], textColor=colors.grey, fontSize=9))
STYLES.add(ParagraphStyle("MISH2", parent=STYLES["Heading2"], textColor=NAVY, fontSize=12, spaceBefore=10, spaceAfter=4))
STYLES.add(ParagraphStyle("MISBody", parent=STYLES["Normal"], fontSize=8.5, leading=11))
STYLES.add(ParagraphStyle("MISKpiVal", parent=STYLES["Normal"], fontSize=15, alignment=TA_CENTER, textColor=NAVY, leading=17))
STYLES.add(ParagraphStyle("MISKpiLbl", parent=STYLES["Normal"], fontSize=7.5, alignment=TA_CENTER, textColor=colors.grey))


def _fig_to_image(fig, width=170 * mm):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    from PIL import Image as PILImage
    im = PILImage.open(buf)
    ratio = im.height / im.width
    return Image(buf, width=width, height=width * ratio)


def _bar_chart(labels, values, title, color="#1F3864", horizontal=False, width=170 * mm, figsize=(6.5, 3.2)):
    fig, ax = plt.subplots(figsize=figsize)
    if horizontal:
        ax.barh(labels[::-1], values[::-1], color=color)
        ax.tick_params(axis="y", labelsize=7)
    else:
        ax.bar(labels, values, color=color)
        plt.xticks(rotation=30, ha="right", fontsize=7)
    ax.set_title(title, fontsize=9, color="#1F3864", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    return _fig_to_image(fig, width=width)


def _line_chart(x, series_dict, title, width=170 * mm, figsize=(6.8, 3.0)):
    fig, ax = plt.subplots(figsize=figsize)
    for label, y in series_dict.items():
        ax.plot(x, y, label=label, linewidth=1.6)
    ax.set_title(title, fontsize=9, color="#1F3864", fontweight="bold")
    ax.legend(fontsize=7, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=6)
    plt.xticks(rotation=45, ha="right", fontsize=6)
    fig.tight_layout()
    return _fig_to_image(fig, width=width)


def _kpi_row(kpis):
    items = [
        ("Total Cases", kpis["total_cases"], None), ("Open", kpis["open_cases"], None),
        ("Closed", kpis["closed_cases"], None), ("Escalated", kpis["escalated_cases"], None),
        ("Resolution %", f"{kpis['resolution_pct']}%", kpis["rag"]["resolution_pct"]),
        ("SLA Breach %", f"{kpis['sla_breach_pct']}%" if kpis["sla_breach_pct"] is not None else "-", kpis["rag"]["sla_breach_pct"]),
    ]
    cells = []
    for label, val, rag in items:
        color = RAG_COLORS.get(rag, NAVY) if rag else NAVY
        cells.append([Paragraph(str(val), ParagraphStyle("v", parent=STYLES["MISKpiVal"], textColor=color)),
                      Paragraph(label, STYLES["MISKpiLbl"])])
    t = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[28 * mm] * len(cells))
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _report_table(rows, headers, keys, col_widths=None):
    data = [headers]
    for r in rows:
        data.append([r.get(k, "") for k in keys])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _header(meta, filters_desc):
    els = [
        Paragraph("M3M Customer Complaint MIS", STYLES["MISTitle"]),
        Paragraph(f"Generated {datetime.now().strftime('%d-%b-%Y %H:%M')} &nbsp;|&nbsp; "
                  f"Source: {meta.get('filename','')} &nbsp;|&nbsp; Filters: {filters_desc}", STYLES["MISSub"]),
        Spacer(1, 8),
    ]
    return els


def _filters_desc(filters):
    if not filters:
        return "None (full dataset)"
    parts = []
    for k, v in filters.items():
        if v and k not in ("date_from", "date_to"):
            parts.append(f"{k}={','.join(map(str, v))}")
    if filters.get("date_from") or filters.get("date_to"):
        parts.append(f"date {filters.get('date_from','')} to {filters.get('date_to','')}")
    return "; ".join(parts) if parts else "None (full dataset)"


def build_executive_onepager(df, filters, meta) -> bytes:
    kpis = analytics.compute_kpis(df)
    reports = analytics.build_reports(df)
    daily = analytics.daily_trend(df)
    insights = analytics.management_insights(df)
    attention = analytics.management_attention(df)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=12 * mm, bottomMargin=10 * mm,
                             leftMargin=12 * mm, rightMargin=12 * mm)
    story = []
    story += _header(meta, _filters_desc(filters))
    story.append(_kpi_row(kpis))
    story.append(Spacer(1, 8))

    HALF = 84 * mm
    proj = reports["project"][:7]
    if proj:
        img = _bar_chart([p["name"][:18] for p in proj], [p["total"] for p in proj],
                          "Top Projects by Case Volume", horizontal=True, width=HALF, figsize=(4.2, 2.3))
        cat = reports["service_category"][:7]
        img2 = _bar_chart([c["name"][:18] for c in cat], [c["total"] for c in cat],
                           "Service Category Split", color="#2E7D32", horizontal=True, width=HALF, figsize=(4.2, 2.3))
        t = Table([[img, img2]], colWidths=[HALF + 4 * mm, HALF + 4 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(t)

    if daily:
        dates = [d["date"][5:] for d in daily]
        img3 = _line_chart(dates, {"Received": [d["today_received"] for d in daily],
                                    "Resolved": [d["total_resolved"] for d in daily]},
                            "Received vs Resolved Trend", width=HALF, figsize=(4.2, 2.1))
        slab = reports["slab"]
        if slab:
            img4 = _bar_chart([s["name"] for s in slab], [s["total"] for s in slab], "SLA Distribution",
                               color="#F9A825", width=HALF, figsize=(4.2, 2.1))
            t2 = Table([[img3, img4]], colWidths=[HALF + 4 * mm, HALF + 4 * mm])
            t2.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(t2)

    story.append(Paragraph("Management Attention", STYLES["MISH2"]))
    att_rows = [{"area": k.replace("_", " ").title(), "count": v["count"]} for k, v in attention.items()]
    att_rows.sort(key=lambda r: r["count"], reverse=True)
    story.append(_report_table(att_rows[:6], ["Area", "Count"], ["area", "count"], col_widths=[130 * mm, 30 * mm]))

    story.append(Paragraph("Key Insights", STYLES["MISH2"]))
    for ins in insights:
        story.append(Paragraph(f"&bull; {ins}", STYLES["MISBody"]))

    doc.build(story)
    return buf.getvalue()


def build_full_pdf_report(df, filters, meta) -> bytes:
    kpis = analytics.compute_kpis(df)
    reports = analytics.build_reports(df)
    daily = analytics.daily_trend(df)
    myt = analytics.monthly_yearly_trend(df)
    insights = analytics.management_insights(df)
    dq = analytics.data_quality(df)
    attention = analytics.management_attention(df)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=12 * mm, bottomMargin=10 * mm,
                             leftMargin=12 * mm, rightMargin=12 * mm)
    story = []
    story += _header(meta, _filters_desc(filters))
    story.append(Paragraph("Executive Dashboard", STYLES["MISH2"]))
    story.append(_kpi_row(kpis))
    story.append(Spacer(1, 6))
    for ins in insights:
        story.append(Paragraph(f"&bull; {ins}", STYLES["MISBody"]))
    story.append(PageBreak())

    story.append(Paragraph("Project Analysis", STYLES["MISH2"]))
    rep_headers = ["Project", "Total", "Closed", "Open", "Escalated", "Resolution %", "Avg TAT", "SLA Breach %"]
    rep_keys = ["name", "total", "closed", "open", "escalated", "resolution_pct", "avg_tat", "sla_breach_pct"]
    story.append(_report_table(reports["project"][:25], rep_headers, rep_keys))
    story.append(PageBreak())

    story.append(Paragraph("Category / SLA Analysis", STYLES["MISH2"]))
    story.append(Paragraph("Service Category", STYLES["MISBody"]))
    story.append(_report_table(reports["service_category"], rep_headers, rep_keys))
    story.append(Spacer(1, 6))
    story.append(Paragraph("SLA (SLAB) Distribution", STYLES["MISBody"]))
    story.append(_report_table(reports["slab"], rep_headers, rep_keys))
    story.append(PageBreak())

    story.append(Paragraph("Daily / Monthly Trend", STYLES["MISH2"]))
    if daily:
        dates = [d["date"][5:] for d in daily]
        img = _line_chart(dates, {"Received": [d["today_received"] for d in daily],
                                   "Resolved": [d["total_resolved"] for d in daily],
                                   "Pending": [d["total_pending"] for d in daily]}, "Daily Trend")
        story.append(img)
    if myt["monthly"]:
        story.append(Paragraph("Monthly Summary", STYLES["MISBody"]))
        story.append(_report_table(myt["monthly"], ["Month", "Received", "Closed", "Resolution %"],
                                    ["period", "received", "closed", "resolution_pct"]))
    story.append(PageBreak())

    story.append(Paragraph("Priority / Escalation Analysis", STYLES["MISH2"]))
    story.append(_report_table(reports["priority"], rep_headers, rep_keys))
    story.append(Spacer(1, 6))
    story.append(_report_table(reports["escalation"], rep_headers, rep_keys))
    story.append(PageBreak())

    story.append(Paragraph("Owner / Team Leader / HOD Analysis", STYLES["MISH2"]))
    story.append(Paragraph("Case Owner (Top 15)", STYLES["MISBody"]))
    story.append(_report_table(reports["case_owner"][:15], rep_headers, rep_keys))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Team Leader", STYLES["MISBody"]))
    story.append(_report_table(reports["team_leader"], rep_headers, rep_keys))
    story.append(Spacer(1, 6))
    story.append(Paragraph("HOD", STYLES["MISBody"]))
    story.append(_report_table(reports["hod"], rep_headers, rep_keys))
    story.append(PageBreak())

    story.append(Paragraph("Data Quality", STYLES["MISH2"]))
    story.append(Paragraph(f"Data Quality Score: {dq['score']}% ({dq['valid_records']} of {dq['total_records']} records valid)", STYLES["MISBody"]))
    dq_rows = [{"check": k.replace("_", " ").title(), "count": v} for k, v in dq["checks"].items()]
    story.append(_report_table(dq_rows, ["Check", "Count"], ["check", "count"], col_widths=[130 * mm, 30 * mm]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Management Attention / Exceptions", STYLES["MISH2"]))
    att_rows = [{"area": k.replace("_", " ").title(), "count": v["count"]} for k, v in attention.items()]
    story.append(_report_table(att_rows, ["Area", "Count"], ["area", "count"], col_widths=[130 * mm, 30 * mm]))

    doc.build(story)
    return buf.getvalue()
