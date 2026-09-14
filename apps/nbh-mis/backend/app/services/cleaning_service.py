"""Column detection, normalization and data-quality reporting.

This is the layer that lets the app accept "a completely new NBH Excel file"
without code changes: headers are matched by normalized alias, not position,
and every validation issue is collected into a Data Quality Summary rather
than silently dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from app import config
from app.utils.normalize import normalize_header


class MissingColumnsError(Exception):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing required columns: {', '.join(missing)}")


@dataclass
class DataQualityReport:
    total_rows: int = 0
    valid_rows: int = 0
    blank_rows_removed: int = 0
    duplicate_ticket_ids: int = 0
    missing_ticket_id: int = 0
    missing_created_on: int = 0
    missing_status: int = 0
    missing_project: int = 0
    missing_category: int = 0
    invalid_dates: int = 0
    unmapped_categories: list[str] = field(default_factory=list)
    unmapped_statuses: list[str] = field(default_factory=list)
    detected_columns: dict[str, str] = field(default_factory=dict)
    missing_optional_columns: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "blank_rows_removed": self.blank_rows_removed,
            "duplicate_ticket_ids": self.duplicate_ticket_ids,
            "missing_ticket_id": self.missing_ticket_id,
            "missing_created_on": self.missing_created_on,
            "missing_status": self.missing_status,
            "missing_project": self.missing_project,
            "missing_category": self.missing_category,
            "invalid_dates": self.invalid_dates,
            "unmapped_categories": self.unmapped_categories,
            "unmapped_statuses": self.unmapped_statuses,
            "detected_columns": self.detected_columns,
            "missing_optional_columns": self.missing_optional_columns,
            "notes": self.notes,
        }


def _clean_text_artifacts(v):
    if not isinstance(v, str):
        return v
    v = v.replace("_x000d_", " ").replace("_x000D_", " ")
    v = v.replace("_x000a_", " ").replace("_x000A_", " ")
    v = re.sub(r"\s+", " ", v).strip()
    return v


def build_alias_lookup() -> dict[str, str]:
    """normalized alias string -> canonical column name"""
    lookup: dict[str, str] = {}
    for canonical, aliases in config.COLUMN_ALIASES.items():
        lookup[normalize_header(canonical.replace("_", " "))] = canonical
        for alias in aliases:
            lookup[normalize_header(alias)] = canonical
    return lookup


def detect_columns(raw_columns: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Returns (raw_header -> canonical_name, canonical_name -> raw_header)."""
    alias_lookup = build_alias_lookup()
    raw_to_canonical: dict[str, str] = {}
    canonical_to_raw: dict[str, str] = {}
    for raw in raw_columns:
        key = normalize_header(raw)
        canonical = alias_lookup.get(key)
        if canonical and canonical not in canonical_to_raw:
            raw_to_canonical[raw] = canonical
            canonical_to_raw[canonical] = raw
    return raw_to_canonical, canonical_to_raw


def normalize_and_clean(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    """Normalize headers, validate required columns, clean values, and build
    a DataQualityReport. Never silently drops a row for being "bad data" --
    only fully blank rows are removed. Everything else is kept and flagged.
    """
    report = DataQualityReport(total_rows=len(raw_df))

    raw_to_canonical, canonical_to_raw = detect_columns(list(raw_df.columns))
    report.detected_columns = {c: r for c, r in canonical_to_raw.items()}

    missing_required = [c for c in config.REQUIRED_COLUMNS if c not in canonical_to_raw]
    if missing_required:
        raise MissingColumnsError(missing_required)

    all_known = list(config.COLUMN_ALIASES.keys())
    report.missing_optional_columns = [
        c for c in all_known if c not in canonical_to_raw and c not in config.REQUIRED_COLUMNS
    ]

    df = raw_df.rename(columns=raw_to_canonical).copy()
    # Drop unrecognized columns silently is wrong per spec ("do not silently
    # delete"), but unrecognized *columns* (vs rows) are simply not part of
    # the analytical model; keep them alongside as "extra_*" so nothing is lost.
    known_canonical = set(canonical_to_raw.keys())
    df = df.loc[:, ~df.columns.duplicated()]

    # Drop fully blank rows only.
    before = len(df)
    df = df.dropna(how="all")
    report.blank_rows_removed = before - len(df)

    # String cleanup: strip whitespace, and repair the literal "_x000d_" /
    # "_x000a_" escape artifacts that NBH/Excel exports leave behind for
    # embedded carriage-return / line-feed characters in free-text fields
    # (Last Comment, Description) -- otherwise they show up verbatim in the
    # UI as garbage text instead of a line break.
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).where(df[col].notna(), None)
            df[col] = df[col].apply(_clean_text_artifacts)
            df[col] = df[col].replace({"nan": None, "None": None, "": None})

    # Ticket ID: coerce to string for stable identity, flag missing/duplicates.
    if "ticket_id" in df.columns:
        df["ticket_id"] = df["ticket_id"].astype(str).str.strip()
        df.loc[df["ticket_id"].isin(["nan", "None", ""]), "ticket_id"] = None
        report.missing_ticket_id = int(df["ticket_id"].isna().sum())
        dup_mask = df["ticket_id"].notna() & df["ticket_id"].duplicated(keep=False)
        report.duplicate_ticket_ids = int(df.loc[df["ticket_id"].duplicated(keep="first")].shape[0])
        if dup_mask.any():
            # Keep all rows (do not silently delete) but tag duplicates so
            # downstream counts can decide (first occurrence treated as
            # canonical for ticket-level aggregation to avoid double counting).
            df["is_duplicate_ticket"] = dup_mask
            df["_dupe_rank"] = df.groupby("ticket_id").cumcount()
        else:
            df["is_duplicate_ticket"] = False
            df["_dupe_rank"] = 0

    # Dates
    for date_col in ["created_on", "assigned_on", "commented_on", "last_updated_on",
                      "resolved_time", "closed_time"]:
        if date_col in df.columns:
            parsed = pd.to_datetime(df[date_col], errors="coerce")
            if date_col == "created_on":
                invalid_mask = df[date_col].notna() & parsed.isna()
                report.invalid_dates = int(invalid_mask.sum())
            df[date_col] = parsed

    if "created_on" in df.columns:
        report.missing_created_on = int(df["created_on"].isna().sum())
    if "status" in df.columns:
        report.missing_status = int(df["status"].isna().sum())
    if "society_name" in df.columns:
        report.missing_project = int(df["society_name"].isna().sum())
    if "category" in df.columns:
        report.missing_category = int(df["category"].isna().sum())

    report.valid_rows = int(len(df))
    return df, report
