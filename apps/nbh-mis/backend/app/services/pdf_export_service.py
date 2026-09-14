"""Management-ready PDF export: one-page executive dashboard + detail reports."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, NextPageTemplate, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

from app import config
from app.services import dashboard_service, report_service
from app.services.filters import Filters

styles = getSampleStyleSheet()
TITLE = ParagraphStyle("TitleC", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#1f2937"))
H2 = ParagraphStyle("H2C", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#1f2937"), spaceBefore=8)
SMALL = ParagraphStyle("SmallC", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#4b5563"))
BODY = ParagraphStyle("BodyC", parent=styles["Normal"], fontSize=9)

RAG_HEX = {"green": colors.HexColor("#1e8e5a"), "amber": colors.HexColor("#c98a11"),
           "orange": colors.HexColor("#cc6a1e"), "red": colors.HexColor("#c0392b"),
           "grey": colors.HexColor("#6b7280")}


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(20 * mm, 10 * mm, f"Generated {datetime.now().strftime('%d-%b-%Y %H:%M')} | {config.APP_TITLE}")
    canvas.drawRightString(landscape(A4)[0] - 20 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _table(data, col_widths=None, header_bg="#1f2937"):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _filters_line(f: Filters) -> str:
    parts = []
    for label, val in [("Year", f.year), ("Month", f.month), ("Project", f.project),
                        ("Status", f.status), ("Priority", f.priority), ("Category", f.category)]:
        if val not in (None, "", "ALL", "All"):
            parts.append(f"{label}: {val}")
    return " | ".join(parts) if parts else "All Data (no filters applied)"


def build_pdf(df, meta, f: Filters) -> bytes:
    buf = io.BytesIO()
    pagesize = landscape(A4)
    doc = BaseDocTemplate(buf, pagesize=pagesize, topMargin=15 * mm, bottomMargin=15 * mm,
                           leftMargin=15 * mm, rightMargin=15 * mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_footer)])

    story = []
    story.append(Paragraph(config.APP_TITLE, TITLE))
    story.append(Paragraph(
        f"As of: {meta.as_of} &nbsp;|&nbsp; Filters: {_filters_line(f)} &nbsp;|&nbsp; "
        f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", SMALL))
    story.append(Spacer(1, 6))

    kpis = dashboard_service.kpi_summary(df, f)
    kpi_data = [["Metric", "Value", "vs Previous", "RAG"]]
    for v in kpis.values():
        chg = f"{v['change_pct']:+.1f}%" if v["change_pct"] is not None else "-"
        kpi_data.append([v["label"], str(v["value"]), chg, v["rag"].upper()])
    story.append(Paragraph("Executive KPI Summary", H2))
    story.append(_table(kpi_data, col_widths=[70 * mm, 30 * mm, 30 * mm, 25 * mm]))
    story.append(Spacer(1, 8))

    ageing = dashboard_service.ageing_distribution(df, f)
    ageing_data = [["Ageing Slab", "Open Cases", "% of Open"]]
    for row in ageing["rows"]:
        ageing_data.append([row["slab"], str(row["count"]), f"{row['pct']}%"])
    story.append(Paragraph("Open Cases by Ageing", H2))
    story.append(_table(ageing_data, col_widths=[50 * mm, 40 * mm, 40 * mm]))
    story.append(Spacer(1, 8))

    insights = dashboard_service.management_insights(df, f)
    story.append(Paragraph("Management Attention Required", H2))
    for ins in insights:
        story.append(Paragraph(f"&bull; {ins['message']}", BODY))

    story.append(NextPageTemplate("main"))
    from reportlab.platypus import PageBreak
    story.append(PageBreak())

    # Page 2+: detail reports
    proj = report_service.project_wise_report(df, f)
    story.append(Paragraph("Project Wise Analysis (Open Cases by Ageing)", H2))
    header = ["Project"] + config.AGEING_BUCKET_ORDER + ["Total"]
    rows = [header]
    for r in proj["rows"][:25]:
        rows.append([r["project"]] + [str(r[c]) for c in config.AGEING_BUCKET_ORDER] + [str(r["Grand Total"])])
    story.append(_table(rows))
    story.append(PageBreak())

    cat = report_service.category_wise_report(df, f)
    story.append(Paragraph("Category Wise Analysis (Open Cases by Ageing)", H2))
    rows = [header]
    for r in cat["rows"][:25]:
        rows.append([r["category"]] + [str(r[c]) for c in config.AGEING_BUCKET_ORDER] + [str(r["Grand Total"])])
    story.append(_table(rows))
    story.append(PageBreak())

    trend = report_service.trend_report(df, f)
    story.append(Paragraph("Monthly Complaint Trend", H2))
    trend_rows = [["Period", "Received", "Closed", "Opening Backlog", "Closing Backlog", "Net Change", "Closure %"]]
    for r in trend["rows"]:
        trend_rows.append([r["period"], str(r["received"]), str(r["closed"]), str(r["opening_backlog"]),
                            str(r["closing_backlog"]), str(r["net_change"]), f"{r['closure_pct']}%"])
    story.append(_table(trend_rows))
    story.append(PageBreak())

    assignee = report_service.assignee_report(df, f)
    story.append(Paragraph("Assignee Performance", H2))
    a_rows = [["Assignee", "Total", "Open", "Closed", "Closure %", "Avg Ageing (Open)", ">30 Open"]]
    for r in assignee["rows"][:25]:
        a_rows.append([r["assignee"], str(r["total"]), str(r["open"]), str(r["closed"]),
                        f"{r['closure_pct']}%", str(r["avg_ageing_open"]), str(r["over_30_open"])])
    story.append(_table(a_rows))
    story.append(PageBreak())

    esc = report_service.escalation_report(df, f)
    pr = report_service.priority_report(df, f)
    story.append(Paragraph("Escalation Analysis", H2))
    e_rows = [["Escalation Level", "Total", "Open", "Closed", "Closure %"]]
    for r in esc["rows"]:
        e_rows.append([str(r["escalation_level"]), str(r["total"]), str(r["open"]), str(r["closed"]), f"{r['closure_pct']}%"])
    story.append(_table(e_rows))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Priority Analysis", H2))
    p_rows = [["Priority", "Total", "Open", "Closed", ">30 Days", "Closure %"]]
    for r in pr["rows"]:
        p_rows.append([r["priority"], str(r["total"]), str(r["open"]), str(r["closed"]), str(r["over_30"]), f"{r['closure_pct']}%"])
    story.append(_table(p_rows))
    story.append(PageBreak())

    tickets = report_service.tickets_list(df, f, page=1, page_size=200)
    story.append(Paragraph(f"Detailed Open/Filtered Cases (showing {len(tickets['rows'])} of {tickets['total']})", H2))
    cols = ["ticket_id", "society_name", "priority", "category_raw", "status_raw", "ageing_days", "ageing_slab"]
    t_rows = [["Ticket ID", "Project", "Priority", "Category", "Status", "Ageing (d)", "Slab"]]
    for r in tickets["rows"][:60]:
        t_rows.append([str(r.get(c, "")) for c in cols])
    story.append(_table(t_rows))

    doc.build(story)
    return buf.getvalue()
