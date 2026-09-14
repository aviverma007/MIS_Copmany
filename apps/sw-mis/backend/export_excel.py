"""
Smartworld MIS - Excel report export (section 15).
Exports ONLY the currently-filtered data, with professional formatting:
freeze panes, auto-width, number/percentage formats, borders, RAG fills.
"""
import io
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

import analytics
from engine import EXPORT_DETAIL_FIELDS, FIELD_LABELS

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14, color="1F3864")
SUB_FONT = Font(italic=True, size=9, color="666666")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
RAG_FILLS = {
    "green": PatternFill("solid", fgColor="C6EFCE"),
    "amber": PatternFill("solid", fgColor="FFEB9C"),
    "red": PatternFill("solid", fgColor="FFC7CE"),
    "grey": PatternFill("solid", fgColor="F2F2F2"),
}


def _style_header_row(ws, row_idx, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row_idx, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def _autowidth(ws, max_width=42):
    for col_cells in ws.columns:
        length = 0
        col_letter = None
        for cell in col_cells:
            if col_letter is None:
                col_letter = cell.column_letter
            try:
                length = max(length, len(str(cell.value)) if cell.value is not None else 0)
            except Exception:
                pass
        if col_letter:
            ws.column_dimensions[col_letter].width = min(max(length + 3, 10), max_width)


def _write_table(ws, start_row, headers, rows, pct_cols=None, rag_col=None):
    pct_cols = pct_cols or []
    for j, h in enumerate(headers, start=1):
        ws.cell(row=start_row, column=j, value=h)
    _style_header_row(ws, start_row, len(headers))
    for i, row in enumerate(rows, start=1):
        for j, h in enumerate(headers, start=1):
            val = row.get(h) if isinstance(row, dict) else row[j - 1]
            cell = ws.cell(row=start_row + i, column=j, value=val)
            cell.border = BORDER
            if h in pct_cols and isinstance(val, (int, float)):
                cell.number_format = "0.0"
            if rag_col and h == rag_col and isinstance(row, dict):
                rag = row.get("_rag")
                if rag:
                    cell.fill = RAG_FILLS.get(rag, RAG_FILLS["grey"])
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    _autowidth(ws)
    return start_row + len(rows) + 1


def _title(ws, text, row=1):
    ws.cell(row=row, column=1, value=text).font = TITLE_FONT


def build_excel_report(df, filters, meta) -> bytes:
    kpis = analytics.compute_kpis(df)
    reports = analytics.build_reports(df)
    daily = analytics.daily_trend(df)
    myt = analytics.monthly_yearly_trend(df)

    wb = Workbook()

    # ---------------- Executive Summary ----------------
    ws = wb.active
    ws.title = "Executive Summary"
    _title(ws, "Smartworld Customer Complaint MIS - Executive Summary")
    ws.cell(row=2, column=1, value=f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}").font = SUB_FONT
    ws.cell(row=3, column=1, value=f"Source file: {meta.get('filename', '')}").font = SUB_FONT
    kpi_items = [
        ("Total Cases", kpis["total_cases"]), ("Open Cases", kpis["open_cases"]),
        ("Closed Cases", kpis["closed_cases"]), ("Pending Cases", kpis["pending_cases"]),
        ("New Cases", kpis["new_cases"]), ("Resolved Cases", kpis["resolved_cases"]),
        ("Escalated Cases", kpis["escalated_cases"]),
        ("Avg Case Age (days)", kpis["avg_case_age"]), ("Avg TAT (days)", kpis["avg_tat"]),
        ("SLA Breach %", kpis["sla_breach_pct"]), ("Resolution %", kpis["resolution_pct"]),
        ("Closure %", kpis["closure_pct"]),
    ]
    r = 5
    ws.cell(row=r, column=1, value="KPI").font = HEADER_FONT
    ws.cell(row=r, column=2, value="Value").font = HEADER_FONT
    ws.cell(row=r, column=1).fill = HEADER_FILL
    ws.cell(row=r, column=2).fill = HEADER_FILL
    for label, val in kpi_items:
        r += 1
        ws.cell(row=r, column=1, value=label).border = BORDER
        c = ws.cell(row=r, column=2, value=val)
        c.border = BORDER
    _autowidth(ws)

    insights = analytics.management_insights(df)
    r += 2
    ws.cell(row=r, column=1, value="Management Insights").font = Font(bold=True, size=12)
    for ins in insights:
        r += 1
        ws.cell(row=r, column=1, value=f"- {ins}")

    # ---------------- Filter Summary ----------------
    ws2 = wb.create_sheet("Filter Summary")
    _title(ws2, "Active Filters Applied to This Export")
    r = 3
    if filters:
        for dim, vals in filters.items():
            if not vals:
                continue
            ws2.cell(row=r, column=1, value=FIELD_LABELS.get(dim, dim)).font = Font(bold=True)
            ws2.cell(row=r, column=2, value=", ".join(str(v) for v in vals) if isinstance(vals, list) else str(vals))
            r += 1
    else:
        ws2.cell(row=r, column=1, value="No filters applied - full dataset exported.")
    _autowidth(ws2)

    # ---------------- Project Analysis ----------------
    ws3 = wb.create_sheet("Project Analysis")
    _title(ws3, "Project-wise Analysis")
    headers = ["name", "total", "closed", "open", "escalated", "resolution_pct", "avg_tat", "sla_breach_pct"]
    disp = ["Project", "Total", "Closed", "Open", "Escalated", "Resolution %", "Avg TAT", "SLA Breach %"]
    rows = [[r_.get(h) for h in headers] for r_ in reports["project"]]
    _write_table(ws3, 3, disp, rows, pct_cols=["Resolution %", "SLA Breach %"])

    # ---------------- Category Analysis ----------------
    ws4 = wb.create_sheet("Category Analysis")
    _title(ws4, "Service Category / M_Category Analysis")
    rows = [[r_.get(h) for h in headers] for r_ in reports["service_category"]]
    next_row = _write_table(ws4, 3, disp, rows, pct_cols=["Resolution %", "SLA Breach %"])
    ws4.cell(row=next_row + 1, column=1, value="M_Category").font = Font(bold=True, size=12)
    rows2 = [[r_.get(h) for h in headers] for r_ in reports["m_category"]]
    _write_table(ws4, next_row + 3, disp, rows2, pct_cols=["Resolution %", "SLA Breach %"])

    # ---------------- SLA Analysis ----------------
    ws5 = wb.create_sheet("SLA Analysis")
    _title(ws5, "SLA (SLAB) Analysis")
    rows = [[r_.get(h) for h in headers] for r_ in reports["slab"]]
    _write_table(ws5, 3, disp, rows, pct_cols=["Resolution %", "SLA Breach %"])

    # ---------------- Date Wise Analysis ----------------
    ws6 = wb.create_sheet("Date Wise Analysis")
    _title(ws6, "Daily Trend (Carry Forward / Received / Resolved / Pending)")
    dheaders = ["date", "carry_forward", "today_received", "total_complaints", "old_resolved",
                "current_resolved", "total_resolved", "total_pending", "contribution_pct"]
    ddisp = ["Date", "Carry Forward", "Today Received", "Total Complaints", "Old Resolved",
             "Current Resolved", "Total Resolved", "Total Pending", "%Cont (Recd vs Closed)"]
    drows = [[r_.get(h) for h in dheaders] for r_ in daily]
    _write_table(ws6, 3, ddisp, drows, pct_cols=["%Cont (Recd vs Closed)"])

    # ---------------- Monthly Analysis ----------------
    ws7 = wb.create_sheet("Monthly Analysis")
    _title(ws7, "Monthly Analysis")
    mheaders = ["period", "received", "closed", "resolution_pct"]
    mdisp = ["Month", "Received", "Closed", "Resolution %"]
    mrows = [[r_.get(h) for h in mheaders] for r_ in myt["monthly"]]
    nr = _write_table(ws7, 3, mdisp, mrows, pct_cols=["Resolution %"])
    ws7.cell(row=nr + 1, column=1, value="Yearly Analysis").font = Font(bold=True, size=12)
    yheaders = ["period", "received", "closed", "resolution_pct"]
    ydisp = ["Year", "Received", "Closed", "Resolution %"]
    yrows = [[r_.get(h) for h in yheaders] for r_ in myt["yearly"]]
    _write_table(ws7, nr + 3, ydisp, yrows, pct_cols=["Resolution %"])

    # ---------------- Owner Analysis ----------------
    ws8 = wb.create_sheet("Owner Analysis")
    _title(ws8, "Case Owner Analysis")
    rows = [[r_.get(h) for h in headers] for r_ in reports["case_owner"]]
    _write_table(ws8, 3, disp, rows, pct_cols=["Resolution %", "SLA Breach %"])

    # ---------------- HOD / TL Analysis ----------------
    ws9 = wb.create_sheet("HOD-TL Analysis")
    _title(ws9, "HOD Analysis")
    rows = [[r_.get(h) for h in headers] for r_ in reports["hod"]]
    nr = _write_table(ws9, 3, disp, rows, pct_cols=["Resolution %", "SLA Breach %"])
    ws9.cell(row=nr + 1, column=1, value="Team Leader Analysis").font = Font(bold=True, size=12)
    rows2 = [[r_.get(h) for h in headers] for r_ in reports["team_leader"]]
    _write_table(ws9, nr + 3, disp, rows2, pct_cols=["Resolution %", "SLA Breach %"])

    # ---------------- Detailed Data ----------------
    # Bulk row writes via ws.append (not cell-by-cell) - this sheet can hold
    # tens of thousands of rows so per-cell writes/formatting are avoided.
    ws10 = wb.create_sheet("Detailed Data")
    fields = [f for f in EXPORT_DETAIL_FIELDS if f in df.columns]
    dispd = [FIELD_LABELS.get(f, f) for f in fields]
    out = df[fields].copy()
    for c in out.columns:
        if str(out[c].dtype).startswith("datetime"):
            out[c] = out[c].dt.strftime("%d-%b-%Y")
    out = out.astype(object).where(pd.notna(out), None)

    ws10.append(dispd)
    _style_header_row(ws10, 1, len(dispd))
    for row in out.itertuples(index=False, name=None):
        ws10.append(row)
    ws10.freeze_panes = "A2"
    last_col = get_column_letter(len(dispd))
    n = len(out)
    if n > 0:
        try:
            tab = Table(displayName="DetailedData", ref=f"A1:{last_col}{n + 1}")
            tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
            ws10.add_table(tab)
        except Exception:
            pass
    # fixed, generous column widths instead of scanning every cell (fast even at scale)
    for j in range(1, len(dispd) + 1):
        ws10.column_dimensions[get_column_letter(j)].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
