"""Detail reports: Open Cases, Project Wise, Category Wise, Management
Category Wise, Date Wise trend, Assignee Performance, Priority, Escalation,
Source, Rating, and the ticket-level drill-down / detail lookups.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from app import config
from app.services.filters import Filters, apply_filters
from app.utils.numeric import safe_float

DRILLDOWN_COLUMNS = [
    "ticket_id", "society_name", "issue_location", "open_date", "priority",
    "category_raw", "sub_category", "description", "status_raw",
    "current_assignee", "escalated_level", "ageing_days", "ageing_slab",
    "last_comment", "last_updated_on", "source", "management_status",
    "management_category", "closed_date", "rating_value",
]


def _pivot_slab(df: pd.DataFrame, index_col: str) -> pd.DataFrame:
    open_df = df[df["management_status"] == "OPEN"]
    pivot = pd.pivot_table(
        open_df, index=index_col, columns="ageing_slab", values="ticket_id",
        aggfunc="count", fill_value=0,
    )
    for label in config.AGEING_BUCKET_ORDER:
        if label not in pivot.columns:
            pivot[label] = 0
    pivot = pivot[config.AGEING_BUCKET_ORDER]
    pivot["Grand Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Grand Total", ascending=False)
    return pivot


def open_cases_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    pivot = _pivot_slab(cur, "status_raw")
    rows = pivot.reset_index().rename(columns={"status_raw": "status"}).to_dict("records")
    grand_total = {label: int(pivot[label].sum()) for label in config.AGEING_BUCKET_ORDER}
    grand_total["Grand Total"] = int(pivot["Grand Total"].sum())

    open_df = cur[cur["management_status"] == "OPEN"]
    by_priority = open_df.groupby("priority_bucket").size().reindex(config.PRIORITY_ORDER, fill_value=0)
    by_escalation = open_df.groupby("escalated_level").size().sort_index()

    return {
        "by_status_slab": rows,
        "grand_total": grand_total,
        "by_priority": [{"priority": k, "count": int(v)} for k, v in by_priority.items()],
        "by_escalation_level": [{"level": int(k), "count": int(v)} for k, v in by_escalation.items()],
    }


def project_wise_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    pivot = _pivot_slab(cur, "society_name")
    rows = pivot.reset_index().rename(columns={"society_name": "project"}).to_dict("records")

    total_by_project = cur.groupby("society_name").size()
    closed_by_project = cur[cur["management_status"] == "CLOSED"].groupby("society_name").size()
    closure_pct = (closed_by_project.reindex(total_by_project.index, fill_value=0) / total_by_project * 100).round(1)
    for row in rows:
        row["total_tickets"] = int(total_by_project.get(row["project"], 0))
        row["closure_pct"] = float(closure_pct.get(row["project"], 0.0))

    open_df = cur[cur["management_status"] == "OPEN"]
    top5_open = open_df.groupby("society_name").size().sort_values(ascending=False).head(5)
    top5_over30 = open_df[open_df["ageing_days"] > 30].groupby("society_name").size().sort_values(ascending=False).head(5)

    return {
        "rows": rows,
        "top5_open": [{"project": k, "count": int(v)} for k, v in top5_open.items()],
        "top5_over30": [{"project": k, "count": int(v)} for k, v in top5_over30.items()],
    }


def category_wise_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    pivot = _pivot_slab(cur, "category_raw")
    rows = pivot.reset_index().rename(columns={"category_raw": "category"}).to_dict("records")

    total_by_cat = cur.groupby("category_raw").size().sort_values(ascending=False)
    open_by_cat = cur[cur["management_status"] == "OPEN"].groupby("category_raw").size()
    avg_ageing_by_cat = cur[cur["management_status"] == "OPEN"].groupby("category_raw")["ageing_days"].mean()

    # Pareto: cumulative % of total complaints by category, sorted desc.
    pareto_total = int(total_by_cat.sum())
    cum = 0
    pareto = []
    for name, count in total_by_cat.items():
        cum += int(count)
        pareto.append({
            "category": name,
            "count": int(count),
            "cumulative_pct": round(cum / pareto_total * 100, 1) if pareto_total else 0.0,
        })

    return {
        "rows": rows,
        "top10": [{"category": k, "count": int(v)} for k, v in total_by_cat.head(10).items()],
        "bottom10": [{"category": k, "count": int(v)} for k, v in total_by_cat.tail(10).items()],
        "highest_ageing_category": (avg_ageing_by_cat.idxmax() if len(avg_ageing_by_cat) else None),
        "highest_open_category": (open_by_cat.idxmax() if len(open_by_cat) else None),
        "pareto": pareto,
    }


def management_category_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    open_df = cur[cur["management_status"] == "OPEN"]
    total_pending = open_df.groupby("management_category").size().reindex(config.MANAGEMENT_CATEGORY_HEADS, fill_value=0)
    over30_pending = open_df[open_df["ageing_days"] > 30].groupby("management_category").size().reindex(config.MANAGEMENT_CATEGORY_HEADS, fill_value=0)
    return {
        "rows": [
            {"management_category": head, "total_pending": int(total_pending.get(head, 0)),
             "over_30_pending": int(over30_pending.get(head, 0))}
            for head in config.MANAGEMENT_CATEGORY_HEADS
        ],
    }


def trend_report(df: pd.DataFrame, f: Filters) -> dict:
    """Monthly trend: Received / Closed / Opening Backlog / Closing Backlog /
    Net Change / Closure %, generalising the workbook's Date Wise summary
    (see docs/DATA_REPORT_MAPPING.md section 5) to a monthly grain.
    """
    stripped = Filters(project=f.project, category=f.category, management_category=f.management_category,
                        priority=f.priority, source=f.source, assignee=f.assignee)
    base = apply_filters(df, stripped)
    if base.empty or base["open_date"].isna().all():
        return {"rows": []}

    base = base.copy()
    base["period"] = base["open_date"].dt.to_period("M")
    periods = sorted(base["period"].dropna().unique())

    rows = []
    running_backlog = 0
    for i, period in enumerate(periods):
        month_mask = base["period"] == period
        received = int(month_mask.sum())
        closed_this_month = int((base["closed_date"].dt.to_period("M") == period).sum())
        opening_backlog = running_backlog
        closing_backlog = opening_backlog + received - closed_this_month
        running_backlog = closing_backlog
        closure_pct = round(closed_this_month / received * 100, 1) if received else 0.0
        rows.append({
            "period": str(period),
            "received": received,
            "closed": closed_this_month,
            "opening_backlog": opening_backlog,
            "closing_backlog": closing_backlog,
            "net_change": received - closed_this_month,
            "closure_pct": closure_pct,
        })

    # Daily average stats over the selected/available window
    daily = base.groupby(base["open_date"].dt.date).size()
    avg_per_day = round(float(daily.mean()), 1) if len(daily) else 0.0
    peak_day = daily.idxmax().strftime("%d-%b-%Y") if len(daily) else None
    peak_day_count = int(daily.max()) if len(daily) else 0
    low_day = daily.idxmin().strftime("%d-%b-%Y") if len(daily) else None
    low_day_count = int(daily.min()) if len(daily) else 0
    closed_daily = base.dropna(subset=["closed_date"]).groupby(base["closed_date"].dt.date).size()
    avg_closed_per_day = round(float(closed_daily.mean()), 1) if len(closed_daily) else 0.0

    return {
        "rows": rows,
        "daily_stats": {
            "avg_received_per_day": avg_per_day,
            "avg_closed_per_day": avg_closed_per_day,
            "avg_cases_per_day": avg_per_day,
            "peak_day": peak_day,
            "peak_day_count": peak_day_count,
            "lowest_day": low_day,
            "lowest_day_count": low_day_count,
            "period_start": base["open_date"].min().strftime("%d-%b-%Y") if base["open_date"].notna().any() else None,
            "period_end": base["open_date"].max().strftime("%d-%b-%Y") if base["open_date"].notna().any() else None,
        },
    }


def assignee_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    if "current_assignee" not in cur.columns:
        return {"rows": []}
    cur = cur[cur["current_assignee"].notna()]
    total = cur.groupby("current_assignee").size()
    open_n = cur[cur["management_status"] == "OPEN"].groupby("current_assignee").size()
    closed_n = cur[cur["management_status"] == "CLOSED"].groupby("current_assignee").size()
    avg_ageing = cur[cur["management_status"] == "OPEN"].groupby("current_assignee")["ageing_days"].mean()
    over30 = cur[(cur["management_status"] == "OPEN") & (cur["ageing_days"] > 30)].groupby("current_assignee").size()

    rows = []
    for name, tot in total.items():
        o = int(open_n.get(name, 0))
        c = int(closed_n.get(name, 0))
        rows.append({
            "assignee": name,
            "total": int(tot),
            "open": o,
            "closed": c,
            "closure_pct": round(c / tot * 100, 1) if tot else 0.0,
            "avg_ageing_open": round(safe_float(avg_ageing.get(name)), 1),
            "over_30_open": int(over30.get(name, 0)),
        })
    rows.sort(key=lambda r: r["open"], reverse=True)
    return {"rows": rows}


def priority_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    rows = []
    for p in config.PRIORITY_ORDER:
        sub = cur[cur["priority_bucket"] == p]
        total = len(sub)
        open_n = int((sub["management_status"] == "OPEN").sum())
        closed_n = int((sub["management_status"] == "CLOSED").sum())
        over30 = int(((sub["management_status"] == "OPEN") & (sub["ageing_days"] > 30)).sum())
        rows.append({
            "priority": p, "total": total, "open": open_n, "closed": closed_n,
            "over_30": over30,
            "closure_pct": round(closed_n / total * 100, 1) if total else 0.0,
        })
    return {"rows": rows}


def escalation_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    rows = []
    for level in sorted(cur["escalated_level"].unique()):
        sub = cur[cur["escalated_level"] == level]
        total = len(sub)
        open_n = int((sub["management_status"] == "OPEN").sum())
        closed_n = int((sub["management_status"] == "CLOSED").sum())
        over30 = int(((sub["management_status"] == "OPEN") & (sub["ageing_days"] > 30)).sum())
        rows.append({
            "escalation_level": int(level), "total": total, "open": open_n, "closed": closed_n,
            "over_30": over30,
            "closure_pct": round(closed_n / total * 100, 1) if total else 0.0,
        })
    return {"rows": rows}


def source_report(df: pd.DataFrame, f: Filters) -> dict:
    cur = apply_filters(df, f)
    if "source" not in cur.columns:
        return {"rows": []}
    cur = cur[cur["source"].notna()]
    total = cur.groupby("source").size()
    closed = cur[cur["management_status"] == "CLOSED"].groupby("source").size()
    rows = []
    for name, tot in total.items():
        c = int(closed.get(name, 0))
        rows.append({
            "source": name, "total": int(tot),
            "pct_of_total": round(int(tot) / len(cur) * 100, 1) if len(cur) else 0.0,
            "closure_pct": round(c / tot * 100, 1) if tot else 0.0,
        })
    rows.sort(key=lambda r: r["total"], reverse=True)
    return {"rows": rows}


def rating_report(df: pd.DataFrame, f: Filters) -> Optional[dict]:
    cur = apply_filters(df, f)
    if "rating_value" not in cur.columns or not cur["is_rated"].any():
        return None
    rated = cur[cur["is_rated"]]
    dist = rated["rating_value"].value_counts().sort_index()
    by_project = rated.groupby("society_name")["rating_value"].mean().sort_values()
    by_category = rated.groupby("category_raw")["rating_value"].mean().sort_values()
    return {
        "average_rating": round(float(rated["rating_value"].mean()), 2),
        "rated_cases": int(len(rated)),
        "unrated_cases": int((~cur["is_rated"]).sum()),
        "distribution": [{"rating": int(k), "count": int(v)} for k, v in dist.items()],
        "worst_projects": [{"project": k, "avg_rating": round(float(v), 2)} for k, v in by_project.head(5).items()],
        "worst_categories": [{"category": k, "avg_rating": round(float(v), 2)} for k, v in by_category.head(5).items()],
    }


def _drilldown_frame(cur: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in DRILLDOWN_COLUMNS if c in cur.columns]
    out = cur[cols].copy()
    for datecol in ["open_date", "closed_date", "last_updated_on"]:
        if datecol in out.columns:
            out[datecol] = pd.to_datetime(out[datecol]).dt.strftime("%d-%b-%Y").replace("NaT", None)
    # Replace NaN/NaT with None everywhere so the frame is JSON-safe (NaN is
    # not valid JSON and would otherwise crash FastAPI's default encoder).
    out = out.astype(object).where(pd.notnull(out), None)
    return out


def tickets_list(df: pd.DataFrame, f: Filters, page: int = 1, page_size: int = 50,
                  sort_by: str = "ageing_days", sort_dir: str = "desc") -> dict:
    cur = apply_filters(df, f)
    total = len(cur)
    ascending = sort_dir == "asc"
    if sort_by in cur.columns:
        cur = cur.sort_values(sort_by, ascending=ascending, na_position="last")
    start = (page - 1) * page_size
    page_df = cur.iloc[start:start + page_size]
    frame = _drilldown_frame(page_df)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "rows": frame.to_dict("records"),
    }


def ticket_detail(df: pd.DataFrame, ticket_id: str) -> Optional[dict]:
    match = df[df["ticket_id"].astype(str) == str(ticket_id)]
    if match.empty:
        return None
    row = match.iloc[0]
    timeline = []
    for label, col in [
        ("Created", "created_on"), ("Assigned", "assigned_on"),
        ("Commented", "commented_on"), ("Last Updated", "last_updated_on"),
        ("Closed", "closed_date"),
    ]:
        if col in row and pd.notna(row[col]):
            ts = pd.to_datetime(row[col])
            timeline.append({"stage": label, "timestamp": ts.strftime("%d-%b-%Y %H:%M")})
    timeline.sort(key=lambda t: t["timestamp"])

    def g(col, default=None):
        v = row.get(col, default)
        if pd.isna(v) if not isinstance(v, str) else False:
            return default
        return v

    return {
        "ticket_id": str(row.get("ticket_id")),
        "society_name": g("society_name"),
        "issue_location": g("issue_location"),
        "created_on": pd.to_datetime(row.get("created_on")).strftime("%d-%b-%Y %H:%M") if pd.notna(row.get("created_on")) else None,
        "priority": g("priority"),
        "category": g("category_raw"),
        "sub_category": g("sub_category"),
        "description": g("description"),
        "status": g("status_raw"),
        "management_status": g("management_status"),
        "management_category": g("management_category"),
        "current_assignee": g("current_assignee"),
        "escalated_level": int(row.get("escalated_level", 0) or 0),
        "ageing_days": (None if pd.isna(row.get("ageing_days")) else int(row.get("ageing_days"))),
        "ageing_slab": g("ageing_slab"),
        "rag": g("rag"),
        "last_comment": g("last_comment"),
        "last_updated_on": pd.to_datetime(row.get("last_updated_on")).strftime("%d-%b-%Y %H:%M") if pd.notna(row.get("last_updated_on")) else None,
        "source": g("source"),
        "rating": (None if pd.isna(row.get("rating_value")) else float(row.get("rating_value"))),
        "closed_date": pd.to_datetime(row.get("closed_date")).strftime("%d-%b-%Y") if pd.notna(row.get("closed_date")) else None,
        "timeline": timeline,
    }
