"""Shared query-parameter filtering, used by every dashboard/report endpoint
so that "all dashboard components must update automatically" from the same
filter set (spec section 11)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class Filters:
    year: Optional[int] = None
    month: Optional[str] = None
    project: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    management_category: Optional[str] = None
    source: Optional[str] = None
    assignee: Optional[str] = None
    ageing_slab: Optional[str] = None
    escalation_level: Optional[int] = None
    management_status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None

    def is_empty(self) -> bool:
        return not any(
            v not in (None, "", "ALL", "All", "all")
            for v in [
                self.year, self.month, self.project, self.status, self.priority,
                self.category, self.management_category, self.source, self.assignee,
                self.ageing_slab, self.escalation_level, self.date_from, self.date_to,
                self.search, self.management_status,
            ]
        )


def _is_all(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip().lower() in ("", "all"))


def apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    out = df
    if not _is_all(f.year):
        out = out[out["year"] == int(f.year)]
    if not _is_all(f.month):
        out = out[out["month"].str.lower() == str(f.month).lower()]
    if not _is_all(f.project):
        out = out[out["society_name"] == f.project]
    if not _is_all(f.status):
        out = out[out["status_raw"].astype(str).str.lower() == str(f.status).lower()]
    if not _is_all(f.priority):
        out = out[out["priority_bucket"].str.lower() == str(f.priority).lower()]
    if not _is_all(f.category):
        out = out[out["category_raw"].astype(str).str.lower() == str(f.category).lower()]
    if not _is_all(f.management_category):
        out = out[out["management_category"] == f.management_category]
    if not _is_all(f.source) and "source" in out.columns:
        out = out[out["source"].astype(str).str.lower() == str(f.source).lower()]
    if not _is_all(f.assignee) and "current_assignee" in out.columns:
        out = out[out["current_assignee"].astype(str).str.lower() == str(f.assignee).lower()]
    if not _is_all(f.ageing_slab):
        out = out[out["ageing_slab"] == f.ageing_slab]
    if not _is_all(f.management_status):
        out = out[out["management_status"].str.upper() == str(f.management_status).upper()]
    if f.escalation_level is not None:
        out = out[out["escalated_level"] >= int(f.escalation_level)]
    if not _is_all(f.date_from):
        out = out[out["open_date"] >= pd.Timestamp(f.date_from)]
    if not _is_all(f.date_to):
        out = out[out["open_date"] <= pd.Timestamp(f.date_to)]
    if not _is_all(f.search):
        s = str(f.search).lower()
        cols = [c for c in ["ticket_id", "description", "society_name", "category_raw",
                             "current_assignee", "sub_category"] if c in out.columns]
        mask = False
        for c in cols:
            mask = mask | out[c].astype(str).str.lower().str.contains(s, na=False)
        out = out[mask]
    return out


def previous_period_mask(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    """Best-effort 'previous period' comparison set: same length window
    immediately preceding the current filtered date range, honoring all
    non-date filters. Falls back to the previous calendar month when a
    year/month filter is active.
    """
    base = df
    for name, val in [
        ("project", f.project), ("status", f.status), ("priority", f.priority),
        ("category", f.category), ("management_category", f.management_category),
        ("source", f.source), ("assignee", f.assignee),
    ]:
        pass  # non-date filters re-applied below via a stripped Filters copy

    stripped = Filters(
        project=f.project, status=f.status, priority=f.priority, category=f.category,
        management_category=f.management_category, source=f.source, assignee=f.assignee,
        management_status=f.management_status,
    )
    base = apply_filters(df, stripped)

    if not _is_all(f.year) and not _is_all(f.month):
        try:
            cur = pd.Timestamp(year=int(f.year), month=_month_num(f.month), day=1)
        except Exception:
            return base.iloc[0:0]
        prev_month_end = cur - pd.Timedelta(days=1)
        prev_start = prev_month_end.replace(day=1)
        return base[(base["open_date"] >= prev_start) & (base["open_date"] <= prev_month_end)]

    if not _is_all(f.date_from) and not _is_all(f.date_to):
        start = pd.Timestamp(f.date_from)
        end = pd.Timestamp(f.date_to)
        span = end - start
        prev_end = start - pd.Timedelta(days=1)
        prev_start = prev_end - span
        return base[(base["open_date"] >= prev_start) & (base["open_date"] <= prev_end)]

    # No date scoping at all: compare last 30 days vs prior 30 days as a
    # sensible default so the KPI comparison arrows are never empty.
    max_date = base["open_date"].max()
    if pd.isna(max_date):
        return base.iloc[0:0]
    cur_start = max_date - pd.Timedelta(days=29)
    prev_end = cur_start - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=29)
    return base[(base["open_date"] >= prev_start) & (base["open_date"] <= prev_end)]


def _month_num(month_abbr: str) -> int:
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    return months.index(str(month_abbr).lower()[:3]) + 1
