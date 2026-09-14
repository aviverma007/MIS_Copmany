"""Derived-column engine.

Reproduces, in pandas, the exact business logic reverse-engineered from
Compile NBH Data columns Y-AG (see docs/DATA_REPORT_MAPPING.md). Everything
here reads from app.config so behaviour changes by editing config, not code.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from app import config
from app.utils.normalize import normalize_token, title_case_label


def _ageing_slab(days) -> str:
    if pd.isna(days):
        return "Unknown"
    for low, high, label in config.AGEING_BUCKETS:
        if low <= days <= high:
            return label
    return "Unknown"


def _rag(days) -> str:
    if pd.isna(days):
        return "grey"
    for low, high, label in config.RAG_RULES:
        if low <= days <= high:
            return label
    return "grey"


def _priority_bucket(raw) -> str:
    tok = normalize_token(raw)
    return config.PRIORITY_ALIASES.get(tok, "MEDIUM" if not tok else "OTHER")


def enrich(df: pd.DataFrame, as_of: datetime | None = None) -> tuple[pd.DataFrame, dict]:
    """Add every derived analytical column. Returns (enriched_df, meta) where
    meta carries things the rest of the app needs (unmapped categories/statuses).
    """
    df = df.copy()
    as_of = pd.Timestamp(as_of or datetime.now()).normalize()
    meta: dict = {"unmapped_categories": set(), "unmapped_statuses": set(), "as_of": as_of}

    # --- normalized raw tokens (kept alongside originals for display) -----
    df["status_raw"] = df.get("status")
    df["status_norm"] = df.get("status", pd.Series(dtype=object)).apply(normalize_token)

    df["category_raw"] = df.get("category")
    df["category_norm"] = df.get("category", pd.Series(dtype=object)).apply(normalize_token)

    if "priority" in df.columns:
        df["priority_bucket"] = df["priority"].apply(_priority_bucket)
    else:
        df["priority_bucket"] = "UNKNOWN"

    # --- management status (Updated Status) --------------------------------
    df["management_status"] = np.where(
        df["status_norm"].isin(config.CLOSED_STATUSES),
        config.MANAGEMENT_STATUS_CLOSED,
        config.MANAGEMENT_STATUS_OPEN,
    )
    unknown_status_mask = (~df["status_norm"].isin(config.CLOSED_STATUSES)) & (
        ~df["status_norm"].isin({"IN_PROGRESS", "ON_HOLD", "OPEN", "REOPEN"})
    ) & (df["status_norm"] != "")
    meta["unmapped_statuses"] = set(df.loc[unknown_status_mask, "status_raw"].dropna().unique().tolist())

    # --- management category (M_Category via XLOOKUP-equivalent) -----------
    def map_category(tok: str) -> str:
        if not tok:
            return config.DEFAULT_MANAGEMENT_CATEGORY
        mapped = config.CATEGORY_MAPPING.get(tok)
        if mapped is None:
            meta["unmapped_categories"].add(tok)
            return config.DEFAULT_MANAGEMENT_CATEGORY
        return mapped

    df["management_category"] = df["category_norm"].apply(map_category)

    # --- dates: Open Date / Closure timestamp / Closed Date -----------------
    df["open_date"] = pd.to_datetime(df["created_on"]).dt.normalize()

    closure_ts = pd.Series(pd.NaT, index=df.index)
    for col in config.CLOSURE_TIMESTAMP_PRIORITY:
        if col in df.columns:
            candidate = pd.to_datetime(df[col], errors="coerce")
            closure_ts = closure_ts.fillna(candidate)
    df["closure_timestamp"] = closure_ts
    is_closed = df["management_status"] == config.MANAGEMENT_STATUS_CLOSED
    df["closed_date"] = pd.NaT
    df.loc[is_closed, "closed_date"] = df.loc[is_closed, "closure_timestamp"].dt.normalize()
    # Closed but no reliable closure timestamp found anywhere -> data quality note,
    # ageing keeps accruing from Created On to as_of (documented assumption).
    df["closure_date_missing"] = is_closed & df["closed_date"].isna()

    # --- ageing days / slab / RAG -------------------------------------------
    ageing = np.where(
        df["closed_date"].notna(),
        (df["closed_date"] - df["open_date"]).dt.days,
        (as_of - df["open_date"]).dt.days,
    )
    df["ageing_days"] = pd.to_numeric(pd.Series(ageing, index=df.index), errors="coerce")
    df.loc[df["open_date"].isna(), "ageing_days"] = np.nan
    df["ageing_slab"] = df["ageing_days"].apply(_ageing_slab)
    df["rag"] = df["ageing_days"].apply(_rag)
    df["is_critical"] = df["ageing_days"] >= config.CRITICAL_AGEING_THRESHOLD_DAYS

    # --- calendar breakdowns --------------------------------------------
    df["year"] = df["open_date"].dt.year
    df["month_num"] = df["open_date"].dt.month
    df["month"] = df["open_date"].dt.strftime("%b")
    df["month_year"] = df["open_date"].dt.strftime("%b-%Y")
    df["week"] = df["open_date"].dt.isocalendar().week.astype("Int64")
    df["day"] = df["open_date"].dt.day

    # --- escalation ----------------------------------------------------
    if "escalated_level" in df.columns:
        df["escalated_level"] = pd.to_numeric(df["escalated_level"], errors="coerce").fillna(0).astype(int)
    else:
        df["escalated_level"] = 0
    df["is_escalated"] = df["escalated_level"] > 0

    # --- reopened (best-effort: status literally REOPEN, or reopen count if present)
    df["is_reopened"] = df["status_norm"] == "REOPEN"

    # --- rating ----------------------------------------------------------
    if "rating" in df.columns:
        df["rating_value"] = pd.to_numeric(df["rating"], errors="coerce")
        df["is_rated"] = df["rating_value"].notna()
    else:
        df["rating_value"] = np.nan
        df["is_rated"] = False

    # --- TAT for closed tickets (management-facing "Average Closure TAT") --
    df["tat_days"] = np.where(df["closed_date"].notna(), (df["closed_date"] - df["open_date"]).dt.days, np.nan)

    meta["unmapped_categories"] = sorted(meta["unmapped_categories"])
    meta["unmapped_statuses"] = sorted(meta["unmapped_statuses"])
    return df, meta
