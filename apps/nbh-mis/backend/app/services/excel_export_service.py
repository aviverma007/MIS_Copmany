"""Builds the multi-sheet Excel export reflecting the currently active filters."""
from __future__ import annotations

import io

import pandas as pd

from app.services import dashboard_service, report_service
from app.services.filters import Filters, apply_filters


def build_export_workbook(df: pd.DataFrame, meta, f: Filters, data_quality: dict, actions: list[dict]) -> bytes:
    cur = apply_filters(df, f)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Executive Dashboard Data
        kpis = dashboard_service.kpi_summary(df, f)
        kpi_rows = [{"metric": v["label"], "value": v["value"], "previous": v["previous_value"],
                     "change_pct": v["change_pct"], "rag": v["rag"]} for v in kpis.values()]
        pd.DataFrame(kpi_rows).to_excel(writer, sheet_name="KPI Summary", index=False)

        summary_rows = [
            {"field": "Uploaded File", "value": meta.filename},
            {"field": "Uploaded At", "value": str(meta.uploaded_at)},
            {"field": "Total Records (all data)", "value": meta.total_records},
            {"field": "Records After Filters", "value": len(cur)},
            {"field": "Data Updated Till", "value": meta.as_of},
        ]
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Executive Dashboard Data", index=False)

        pd.DataFrame(report_service.open_cases_report(df, f)["by_status_slab"]).to_excel(
            writer, sheet_name="Open Cases", index=False)
        pd.DataFrame(report_service.project_wise_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Project Wise", index=False)
        pd.DataFrame(report_service.category_wise_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Category Wise", index=False)
        pd.DataFrame(report_service.management_category_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Management Category Wise", index=False)
        pd.DataFrame(report_service.trend_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Date Wise Summary", index=False)
        pd.DataFrame(report_service.assignee_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Assignee Performance", index=False)
        pd.DataFrame(report_service.priority_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Priority Analysis", index=False)
        pd.DataFrame(report_service.escalation_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Escalation Analysis", index=False)
        pd.DataFrame(report_service.source_report(df, f)["rows"]).to_excel(
            writer, sheet_name="Source Analysis", index=False)

        tb = dashboard_service.top_bottom(df, f)
        tb_frames = []
        for key, label in [("top_open_backlog", "Top 5 Open Backlog"), ("top_over_30", "Top 5 >30 Days"),
                             ("best_closure_pct", "Top 5 Closure %"), ("worst_closure_pct", "Bottom 5 Closure %"),
                             ("top_categories", "Top 5 Categories")]:
            for row in tb[key]:
                tb_frames.append({"section": label, **row})
        pd.DataFrame(tb_frames).to_excel(writer, sheet_name="Top 5 Bottom 5", index=False)

        ticket_cols = [c for c in report_service.DRILLDOWN_COLUMNS if c in cur.columns]
        detail = report_service._drilldown_frame(cur)
        detail.to_excel(writer, sheet_name="Filtered Ticket Details", index=False)

        dq_rows = [{"check": k, "value": (", ".join(v) if isinstance(v, list) else v)}
                   for k, v in data_quality.items() if k != "detected_columns"]
        pd.DataFrame(dq_rows).to_excel(writer, sheet_name="Data Quality Report", index=False)

        if actions:
            pd.DataFrame(actions).to_excel(writer, sheet_name="Management Actions", index=False)

    return output.getvalue()


def build_sample_template() -> bytes:
    """Sample Excel Template with expected headers only, for the
    'Download Sample Template' feature."""
    from app import config
    output = io.BytesIO()
    headers = []
    for canonical, aliases in config.COLUMN_ALIASES.items():
        headers.append(aliases[0].title() if aliases else canonical.replace("_", " ").title())
    df = pd.DataFrame(columns=headers)
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Compile NBH Data", index=False)
    return output.getvalue()
