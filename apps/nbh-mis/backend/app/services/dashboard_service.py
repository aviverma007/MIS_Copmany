"""Executive dashboard aggregations: KPIs, RAG summary, ageing distribution,
top5/bottom5, and the dynamically-generated management insights."""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from app import config
from app.services.filters import Filters, apply_filters, previous_period_mask
from app.utils.numeric import safe_float


def _pct_change(cur: float, prev: float) -> Optional[float]:
    if prev in (0, None) or pd.isna(prev):
        return None
    return round(((cur - prev) / prev) * 100, 1)


def kpi_summary(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    prev = previous_period_mask(df, f)

    total = len(cur)
    open_cnt = int((cur["management_status"] == "OPEN").sum())
    closed_cnt = int((cur["management_status"] == "CLOSED").sum())
    closure_pct = round((closed_cnt / total) * 100, 1) if total else 0.0
    over30 = int(((cur["management_status"] == "OPEN") & (cur["ageing_days"] > 30)).sum())
    critical_high = int(((cur["management_status"] == "OPEN") & (cur["priority_bucket"] == "HIGH")).sum())
    reopened = int(cur["is_reopened"].sum())
    avg_ageing_open = safe_float(cur.loc[cur["management_status"] == "OPEN", "ageing_days"].mean())
    avg_tat_closed = safe_float(cur.loc[cur["management_status"] == "CLOSED", "tat_days"].mean())
    new_complaints = int(cur.shape[0])  # complaints created within the current filtered window

    p_total = len(prev)
    p_open = int((prev["management_status"] == "OPEN").sum())
    p_closed = int((prev["management_status"] == "CLOSED").sum())
    p_closure_pct = round((p_closed / p_total) * 100, 1) if p_total else 0.0
    p_over30 = int(((prev["management_status"] == "OPEN") & (prev["ageing_days"] > 30)).sum())
    p_critical_high = int(((prev["management_status"] == "OPEN") & (prev["priority_bucket"] == "HIGH")).sum())
    p_reopened = int(prev["is_reopened"].sum())
    p_avg_ageing = safe_float(prev.loc[prev["management_status"] == "OPEN", "ageing_days"].mean())
    p_avg_tat = safe_float(prev.loc[prev["management_status"] == "CLOSED", "tat_days"].mean())

    def card(label, value, prev_value, higher_is_bad=True, fmt="int"):
        change = _pct_change(value, prev_value)
        rag = "grey"
        if change is not None:
            if higher_is_bad:
                rag = "red" if change > 5 else ("amber" if change > 0 else "green")
            else:
                rag = "green" if change >= 0 else ("amber" if change > -5 else "red")
        return {
            "label": label,
            "value": round(value, 1) if fmt == "float" else int(value),
            "previous_value": round(prev_value, 1) if fmt == "float" else int(prev_value),
            "change_pct": change,
            "rag": rag,
        }

    return {
        "total_complaints": card("Total Complaints", total, p_total, higher_is_bad=True),
        "open_pending": card("Open / Pending", open_cnt, p_open, higher_is_bad=True),
        "closed_resolved": card("Closed / Resolved", closed_cnt, p_closed, higher_is_bad=False),
        "closure_pct": card("Closure %", closure_pct, p_closure_pct, higher_is_bad=False, fmt="float"),
        "new_complaints": card("New Complaints", new_complaints, p_total, higher_is_bad=True),
        "old_pending_over_30": card("Old Pending >30 Days", over30, p_over30, higher_is_bad=True),
        "critical_high_priority": card("Critical / High Priority", critical_high, p_critical_high, higher_is_bad=True),
        "reopened_cases": card("Reopened Cases", reopened, p_reopened, higher_is_bad=True),
        "avg_ageing_open": card("Average Ageing (Open)", avg_ageing_open, p_avg_ageing, higher_is_bad=True, fmt="float"),
        "avg_closure_tat": card("Average Closure TAT", avg_tat_closed, p_avg_tat, higher_is_bad=True, fmt="float"),
    }


def rag_scorecard(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    open_df = cur[cur["management_status"] == "OPEN"]
    counts = open_df["rag"].value_counts().to_dict()
    total = len(open_df)
    rows = []
    for rag in ["green", "amber", "orange", "red"]:
        n = int(counts.get(rag, 0))
        rows.append({
            "rag": rag,
            "color": config.RAG_COLORS[rag],
            "count": n,
            "pct": round((n / total) * 100, 1) if total else 0.0,
        })
    return {"rows": rows, "total_open": total}


def ageing_distribution(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    open_df = cur[cur["management_status"] == "OPEN"]
    total = len(open_df)
    counts = open_df["ageing_slab"].value_counts().to_dict()
    rows = []
    for label in config.AGEING_BUCKET_ORDER:
        n = int(counts.get(label, 0))
        rag = next((r for lo, hi, r in config.RAG_RULES if False), None)
        rows.append({
            "slab": label,
            "count": n,
            "pct": round((n / total) * 100, 1) if total else 0.0,
            "is_critical_bucket": label == "More than 30",
        })
    return {"rows": rows, "total_open": total}


def top_bottom(df: pd.DataFrame, f: Filters, n: int = 5) -> dict:
    cur = apply_filters(df, f)
    open_df = cur[cur["management_status"] == "OPEN"]

    by_project_open = open_df.groupby("society_name").size().sort_values(ascending=False)
    by_project_over30 = open_df[open_df["ageing_days"] > 30].groupby("society_name").size().sort_values(ascending=False)

    proj_total = cur.groupby("society_name").size()
    proj_closed = cur[cur["management_status"] == "CLOSED"].groupby("society_name").size()
    closure_rate = (proj_closed.reindex(proj_total.index, fill_value=0) / proj_total * 100).round(1)
    closure_rate = closure_rate[proj_total >= 5]  # ignore near-empty projects for ranking noise

    by_category = cur.groupby("category_raw").size().sort_values(ascending=False)

    def to_list(series, value_name="value"):
        return [{"name": str(k), value_name: (float(v) if isinstance(v, float) else int(v))} for k, v in series.items()]

    return {
        "top_open_backlog": to_list(by_project_open.head(n), "count"),
        "top_over_30": to_list(by_project_over30.head(n), "count"),
        "best_closure_pct": to_list(closure_rate.sort_values(ascending=False).head(n), "closure_pct"),
        "worst_closure_pct": to_list(closure_rate.sort_values(ascending=True).head(n), "closure_pct"),
        "top_categories": to_list(by_category.head(n), "count"),
    }


def management_insights(df: pd.DataFrame, f: Filters) -> list[dict]:
    """Dynamically generated 'Management Attention Required' bullets."""
    cur = apply_filters(df, f)
    prev = previous_period_mask(df, f)
    insights: list[dict] = []

    open_df = cur[cur["management_status"] == "OPEN"]
    total_open = len(open_df)
    if total_open:
        over30 = int((open_df["ageing_days"] > 30).sum())
        pct = round(over30 / total_open * 100, 1)
        if pct >= 20:
            top_proj = open_df[open_df["ageing_days"] > 30]["society_name"].value_counts()
            proj_name = top_proj.index[0] if len(top_proj) else "N/A"
            insights.append({
                "severity": "high" if pct >= 35 else "medium",
                "message": f"{pct}% of current open cases are older than 30 days, with the highest backlog concentrated in {proj_name}.",
            })

    p_open = int((prev["management_status"] == "OPEN").sum())
    if p_open and total_open > p_open:
        insights.append({
            "severity": "medium",
            "message": f"Open backlog increased from {p_open} to {total_open} versus the previous period.",
        })

    total_cur, total_prev = len(cur), len(prev)
    closure_cur = (cur["management_status"] == "CLOSED").sum() / total_cur * 100 if total_cur else 0
    closure_prev = (prev["management_status"] == "CLOSED").sum() / total_prev * 100 if total_prev else 0
    if total_prev and closure_cur < closure_prev - 2:
        insights.append({
            "severity": "medium",
            "message": f"Closure % fell from {closure_prev:.1f}% to {closure_cur:.1f}% versus the previous period.",
        })

    if total_open:
        proj_share = open_df["society_name"].value_counts(normalize=True)
        if len(proj_share) and proj_share.iloc[0] >= 0.30:
            insights.append({
                "severity": "medium",
                "message": f"{proj_share.index[0]} accounts for {proj_share.iloc[0]*100:.0f}% of the open backlog, disproportionate to other projects.",
            })
        cat_share = cur["category_raw"].value_counts(normalize=True)
        if len(cat_share) and cat_share.iloc[0] >= 0.25:
            insights.append({
                "severity": "low",
                "message": f"{cat_share.index[0]} dominates complaint volume at {cat_share.iloc[0]*100:.0f}% of all tickets in the selected period.",
            })

    high_open = int(((open_df["priority_bucket"] == "HIGH")).sum())
    if high_open:
        insights.append({
            "severity": "high",
            "message": f"{high_open} high-priority case(s) remain open and require immediate attention.",
        })

    esc_cur = int(cur["is_escalated"].sum())
    esc_prev = int(prev["is_escalated"].sum())
    if esc_prev and esc_cur > esc_prev:
        insights.append({
            "severity": "medium",
            "message": f"Escalated cases increased from {esc_prev} to {esc_cur} versus the previous period.",
        })

    if not insights:
        insights.append({"severity": "low", "message": "No material deterioration detected for the current filter selection."})

    return insights


def dataset_summary(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    return {
        "selected_records": int(len(cur)),
        "selected_projects": int(cur["society_name"].nunique()),
        "selected_date_min": cur["open_date"].min().strftime("%d-%b-%Y") if len(cur) and cur["open_date"].notna().any() else None,
        "selected_date_max": cur["open_date"].max().strftime("%d-%b-%Y") if len(cur) and cur["open_date"].notna().any() else None,
    }
