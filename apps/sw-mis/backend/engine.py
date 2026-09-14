"""
Smartworld Customer Complaint MIS - Data Engine
Dynamic column detection + cleaning + filtering + KPI/report computation.
'Compile SW Data' is treated as the single source of truth. Nothing here
is hard-coded to specific project/category/owner values - everything is
derived from whatever is present in the uploaded workbook.

This engine was adapted from the M3M Customer Complaint MIS application for
Smartworld's own SFDC export (Compile_SW_Data / SW_List). The core design is
identical - alias-based column detection, business-rule formulas recomputed
fresh, LIST-driven dropdowns/mapping - only the field aliases, default LIST
data, and a couple of Smartworld-specific business rules differ. See the
"Smartworld-specific" comments below for exactly what changed and why.

  - SFDC date-string normalization (dd/mm/yyyy, with or without a time part)
  - apply_business_rules(): replicates the source template's Excel formulas
    (F_Closed, Open/Closed Date, Received/Closed "Today vs Older" buckets,
    Updated Status, TAT Days, SLAB, M_Category) as real Python functions, so
    they are always freshly computed - never stale values copied from a
    workbook that can't recalculate itself.
  - LIST management: parse_list_workbook() / default_list_state() load the
    Project / Month / Year dropdown lists and the Category -> M_Category
    lookup table used by apply_business_rules() and by the filter UI.
"""
import re
import io
import math
import unicodedata
from datetime import datetime, date
import numpy as np
import pandas as pd

REQUIRED_SHEET = "Compile SW Data"
LIST_SHEET_NAME = "LIST"

# ---------------------------------------------------------------------------
# CONFIG - single place for business rules / thresholds (per prompt section 8)
# ---------------------------------------------------------------------------
CONFIG = {
    "rag": {
        "resolution_pct": {"green": 90, "amber": 75},   # >=green -> Green, >=amber -> Amber, else Red
        "closure_pct":    {"green": 90, "amber": 75},
        "sla_breach_pct": {"green": 10, "amber": 25},   # LOWER is better here (inverted RAG)
        "data_quality":   {"green": 95, "amber": 85},
    },
    "sla_within_buckets": ["0 to 2"],   # SLAB values considered "within SLA"
    "sla_target_days": 2,               # fallback when SLAB column is absent
    "ageing_buckets": [
        (0, 2, "0-2 days"), (3, 7, "3-7 days"), (8, 15, "8-15 days"),
        (16, 30, "16-30 days"), (31, math.inf, "30+ days"),
    ],
    # exact thresholds/labels from the source workbook's SLAB formula:
    # =IF(TAT>30,"More than 30",IF(TAT>15,"16 to 30",IF(TAT>7,"8 to 15",IF(TAT>2,"3 to 7","0 to 2"))))
    "slab_buckets": [
        (30, math.inf, "More than 30"), (15, 30, "16 to 30"),
        (7, 15, "8 to 15"), (2, 7, "3 to 7"), (-math.inf, 2, "0 to 2"),
    ],
    "attention_ageing_days": 30,
    "attention_high_tat_days": 15,
    # Case Status values the source workbook's "Updated Status" array formula
    # treats as OPEN. Smartworld-specific: confirmed from Compile_SW_Data.xlsx's
    # own formula - =IF(OR(Status={"In Progress","Re-Open","New","Pending for
    # Clarification"}),"OPEN","Closed") - note "Pending for Clarification"
    # replaces M3M's "Submit For Approval" here; this is a genuine difference
    # in Smartworld's workflow, not an oversight.
    "open_case_statuses": ["in progress", "re-open", "new", "pending for clarification", "reopen"],
    # Local-admin passcode gating the "Manage Lists" screen (edit/upload of
    # LIST.xlsx). This is a lightweight access gate appropriate for a local,
    # single-user desktop tool - not enterprise auth. Change it here if
    # needed; it applies the next time the app is rebuilt/started.
    "admin_passcode": "swadmin",
    # Smartworld-specific: Compile_SW_Data.xlsx's M_Category formula looks up
    # against the "Area" field (=XLOOKUP(Area, LIST!Category, LIST!M_Category,
    # "Others/Misc")), not "Service Category" - Service Category/Category are
    # both present in the schema but blank/unused in Smartworld's export;
    # "Area" is where the real categorization data lives. Set this back to
    # "service_category" if adapting the engine for a workbook that uses that
    # field instead.
    "m_category_lookup_field": "area",
}

# Canonical field -> ordered alias patterns (normalized: lowercase, single-spaced).
# Matching is a single left-to-right pass over the header row; each source
# column is consumed by at most one canonical field so duplicate/derived
# helper columns never silently overwrite the real field.
FIELD_ALIASES = [
    ("case_number",       ["case number", "case no", "ticket number", "ticket no", "complaint number"]),
    ("account_name",      ["account name", "customer name", "client name", "customer"]),
    ("subject",           ["subject"]),
    ("priority",          ["priority"]),
    ("m_category",        ["m_category", "m category", "mcategory", "management category"]),
    ("service_category",  ["service category"]),
    # "date time opened" matches Smartworld's "Date/Time Opened" header (the
    # normalizer turns "/" into a space, so "Date/Time Opened" -> "date time opened").
    ("opened_date",       ["opened date", "open date", "date opened", "received date", "created date", "case created date", "date time opened"]),
    ("closed_date",       ["closed date", "close date", "date closed", "resolution date", "resolved date"]),
    ("case_owner",        ["case owner", "owner name", "assigned to", "owner"]),
    ("case_type",         ["case type"]),
    # "status" alone matches Smartworld's "Status" header. Safe to add: the
    # exact-match pass claims "Updated Status" for the updated_status field
    # first (its own alias list matches it exactly), before this field's
    # "contains" pass ever gets a chance to look at "status" as a substring.
    ("case_status",       ["case status", "status"]),
    ("sub_category",      ["sub category", "subcategory", "sub-category"]),
    ("case_source",       ["case source"]),
    ("case_origin",       ["case origin", "channel"]),
    # "age" matches Smartworld's "Age" header.
    ("case_ageing",       ["case ageing", "case aging", "ageing", "aging", "age"]),
    ("escalation",        ["is escalated closure", "escalation status", "escalated"]),
    # "project" alone matches Smartworld's "Project" header.
    ("project_name",      ["project name", "project"]),
    # "property" matches Smartworld's "Property" header (the unit identifier,
    # e.g. "N-71D" - the same role M3M's "Project Unit" field plays).
    ("project_unit",      ["project unit", "unit number", "unit no", "property"]),
    ("team_leader",       ["team leader", "team lead", "tl name"]),
    ("hod",               ["hod 1", "hod name", "hod"]),
    # "hni customer" matches Smartworld's "HNI Customer" boolean field - used
    # here as Smartworld's customer-tier classification, the same role M3M's
    # text-based "Client Category" (VIP/Legal/...) field plays.
    ("client_category",   ["client category", "hni customer"]),
    ("updated_status",    ["updated status"]),
    ("tat_days",          ["tat days", "tat (days)", "turnaround time", "tat"]),
    ("slab",              ["slab"]),
    ("ia_status",         ["ia status"]),
    ("ia_remarks",        ["ia remarks"]),
    # Smartworld-specific fields with no M3M equivalent - "Area" is the field
    # Smartworld's own M_Category XLOOKUP formula is keyed on (see CONFIG
    # above); "Sub Area" is the finer-grained field alongside it. Both are
    # additional fields layered on top of the (blank, for Smartworld)
    # Service Category / Sub Category fields already above, not a replacement
    # for them, so the overall field set matches the original application.
    ("area",              ["area"]),
    ("sub_area",          ["sub area", "subarea", "sub-area"]),
]

FIELD_LABELS = {
    "case_number": "Case Number", "account_name": "Account Name", "subject": "Subject",
    "priority": "Priority", "m_category": "M_Category", "service_category": "Service Category",
    "opened_date": "Opened Date", "closed_date": "Closed Date", "case_owner": "Case Owner",
    "case_type": "Case Type", "case_status": "Case Status", "sub_category": "Sub Category",
    "case_source": "Case Source", "case_origin": "Case Origin", "case_ageing": "Case Ageing",
    "escalation": "Escalation", "project_name": "Project Name", "project_unit": "Project Unit",
    "team_leader": "Team Leader", "hod": "HOD", "client_category": "Client Category (HNI)",
    "updated_status": "Updated Status", "tat_days": "TAT Days", "slab": "SLAB",
    "ia_status": "IA Status", "ia_remarks": "IA Remarks",
    "received_bucket": "Received Today?", "closed_bucket": "Closed Same Day?",
    "area": "Area", "sub_area": "Sub Area",
}

FILTER_DIMENSIONS = [
    "project_name", "updated_status", "case_status", "service_category", "m_category",
    "priority", "case_owner", "team_leader", "hod", "client_category", "case_source",
    "case_type", "sub_category", "escalated_label", "slab", "ia_status", "year", "month_name",
    "received_bucket", "closed_bucket", "area", "sub_area",
]

DETAIL_TABLE_FIELDS = [
    "case_number", "account_name", "subject", "priority", "service_category", "area", "sub_area",
    "opened_date", "closed_date", "case_owner", "case_status", "sub_category", "case_source",
    "case_ageing", "escalated_label", "project_name", "project_unit", "team_leader", "hod",
    "client_category", "updated_status", "tat_days", "slab", "m_category", "ia_status", "ia_remarks",
]

# Full column set for the Excel "Detailed Data" export - mirrors the original
# template's structure (adds the two computed buckets that the on-screen
# case table keeps out of the way to avoid clutter, per DETAIL_TABLE_FIELDS).
EXPORT_DETAIL_FIELDS = DETAIL_TABLE_FIELDS + ["received_bucket", "closed_bucket"]


def _norm(s):
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("_", " ").replace("-", " ").replace("/", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def detect_columns(raw_columns):
    """Left-to-right single-pass alias matching. Returns
    (mapping canonical->original_col_name, list of unmatched canonical fields)."""
    normed = [(_norm(c), c) for c in raw_columns]
    used = set()
    mapping = {}
    # exact-match pass first (across all fields), then contains-match pass
    for pass_type in ("exact", "contains"):
        for canon, aliases in FIELD_ALIASES:
            if canon in mapping:
                continue
            for norm_col, orig_col in normed:
                if orig_col in used or not norm_col:
                    continue
                for alias in aliases:
                    if pass_type == "exact" and norm_col == alias:
                        mapping[canon] = orig_col
                        used.add(orig_col)
                        break
                    if pass_type == "contains" and alias in norm_col:
                        mapping[canon] = orig_col
                        used.add(orig_col)
                        break
                if canon in mapping:
                    break
    missing = [c for c, _ in FIELD_ALIASES if c not in mapping]
    return mapping, missing


def _parse_dates(series):
    """Normalizes SFDC-exported date fields.

    SFDC/report exports for this org come through as plain text in
    day-first format - "08/09/2026" or "08/09/2026, 11:05 am" - which
    pandas would otherwise silently misread as month-first (turning
    8-Sep into "Aug 9"). Real Excel date cells (already datetime64) are
    left untouched; everything else is parsed with dayfirst=True, which is
    the confirmed convention for this data source (e.g. "31/05/2026" only
    parses at all as 31 May, which matches the source workbook).

    A single column commonly holds BOTH date-only ("08/09/2026") and
    date+time ("08/09/2026, 11:05 am") values together. pandas' normal
    vectorized parser infers one fixed format from the first values and
    silently turns every differently-shaped value into NaT instead of
    parsing it - i.e. it fails quietly, which is worse than failing loudly.
    format="mixed" parses correctly but element-by-element (slow at scale),
    so it's only used as a targeted second pass over whatever the fast
    vectorized attempt couldn't parse, not the whole column.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    fast = pd.to_datetime(series, errors="coerce", dayfirst=True)
    still_missing = fast.isna() & series.notna() & (series.astype(str).str.strip() != "")
    if still_missing.any():
        fast.loc[still_missing] = pd.to_datetime(
            series[still_missing], errors="coerce", dayfirst=True, format="mixed"
        )
    return fast


def format_date_ddmmmyyyy(series_or_ts):
    """Render a datetime Series/Timestamp as 'DD-MMM-YYYY' (e.g. 08-Sep-2026),
    the display format requested for this application. NaT/None -> None."""
    if isinstance(series_or_ts, pd.Series):
        return series_or_ts.dt.strftime("%d-%b-%Y").where(series_or_ts.notna(), None)
    if pd.isna(series_or_ts):
        return None
    return pd.Timestamp(series_or_ts).strftime("%d-%b-%Y")


def _clean_text(series):
    return (series.astype(str)
                  .str.strip()
                  .replace({"nan": np.nan, "None": np.nan, "": np.nan, "NaT": np.nan}))


def load_and_process(file_bytes: bytes, filename: str):
    """Loads the workbook, validates the required sheet, detects columns,
    cleans & derives fields. Returns (df, meta_dict) or raises ValueError.

    Note: this does NOT compute the "formula fields" (Updated Status, TAT
    Days, SLAB, M_Category, received/closed buckets) - those depend on
    today's date and the current LIST mapping, so they are computed
    separately by apply_business_rules(), which can be re-run on its own
    (e.g. after an admin edits the Category -> M_Category mapping) without
    re-uploading the source workbook.
    """
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Could not read the uploaded file as an Excel workbook: {e}")

    sheet_names = xls.sheet_names
    target_sheet = None
    for s in sheet_names:
        if _norm(s) == _norm(REQUIRED_SHEET):
            target_sheet = s
            break
    if target_sheet is None:
        for s in sheet_names:
            if "compile" in _norm(s):
                target_sheet = s
                break
    if target_sheet is None:
        raise ValueError(f"Required sheet '{REQUIRED_SHEET}' was not found in the uploaded workbook.")

    raw = pd.read_excel(xls, sheet_name=target_sheet, dtype=object)
    raw = raw.dropna(how="all")
    raw.columns = [str(c) if not str(c).startswith("Unnamed") else "" for c in raw.columns]
    raw = raw.loc[:, [c for c in raw.columns if c != ""]]

    mapping, missing = detect_columns(list(raw.columns))
    if "case_number" not in mapping:
        raise ValueError(
            "Could not detect a 'Case Number' column in the 'Compile SW Data' sheet. "
            "Please ensure the sheet has a case/ticket identifier column."
        )

    df = pd.DataFrame(index=raw.index)
    for canon, orig in mapping.items():
        df[canon] = raw[orig]

    # ---- cleaning -------------------------------------------------------
    text_fields = ["case_number", "account_name", "subject", "priority", "m_category",
                    "service_category", "case_owner", "case_type", "case_status",
                    "sub_category", "case_source", "case_origin", "escalation",
                    "project_name", "project_unit", "team_leader", "hod",
                    "client_category", "updated_status", "slab", "ia_status", "ia_remarks"]
    for f in text_fields:
        if f in df.columns:
            df[f] = _clean_text(df[f])

    # Dates: normalize SFDC's dd/mm/yyyy (with optional time-of-day) text
    # into proper datetime64 values. Everything downstream (ageing, TAT,
    # trend charts, filters) then works off real dates instead of strings.
    for f in ["opened_date", "closed_date"]:
        if f in df.columns:
            df[f] = _parse_dates(df[f])

    for f in ["case_ageing", "tat_days"]:
        if f in df.columns:
            df[f] = pd.to_numeric(df[f], errors="coerce")

    # drop rows with completely blank case number (still keep for data-quality count separately)
    total_rows_before = len(df)
    df["_row_id"] = range(total_rows_before)

    # de-duplicate case number blanks -> keep as NaN, don't fabricate ids
    if "case_number" in df.columns:
        df["case_number"] = df["case_number"].astype(str).str.strip()
        df.loc[df["case_number"].isin(["", "nan", "None", "NaT"]), "case_number"] = np.nan

    # ---- derived fields (independent of "today" / LIST mapping) -----------
    if "opened_date" in df.columns:
        od = df["opened_date"]
        df["year"] = od.dt.year
        df["month_num"] = od.dt.month
        df["month_name"] = od.dt.strftime("%b")
        df["quarter"] = "Q" + od.dt.quarter.astype("Int64").astype(str)
        df["week"] = od.dt.isocalendar().week
        df["day"] = od.dt.day
        df["day_name"] = od.dt.strftime("%A")
    else:
        for c in ["year", "month_num", "month_name", "quarter", "week", "day", "day_name"]:
            df[c] = np.nan

    # informational flags parsed straight from the raw Case Status text
    # (status_bucket / Updated Status itself is computed authoritatively in
    # apply_business_rules, matching the source workbook's exact formula)
    if "case_status" in df.columns:
        s = df["case_status"].fillna("").str.lower()
        df["is_new"] = s.str.contains("new")
        df["is_reopen"] = s.str.contains("re-open") | s.str.contains("reopen")
        df["is_in_progress"] = s.str.contains("progress") | s.str.contains("submit for approval")
    else:
        df["is_new"] = False
        df["is_reopen"] = False
        df["is_in_progress"] = False

    # escalation flag derived from the escalation text field
    if "escalation" in df.columns:
        esc = df["escalation"].fillna("").str.lower()
        df["is_escalated"] = esc.str.contains("escalat") & ~esc.str.contains("closed within tat")
        # "closed within tat" never counts even though it doesn't contain 'escalat', kept for clarity
        df["escalated_label"] = np.where(df["is_escalated"], "Escalated", "Not Escalated")
    else:
        df["is_escalated"] = False
        df["escalated_label"] = "Not Escalated"

    # case ageing bucket (SFDC's own Case Ageing field - separate from the
    # workbook's computed TAT Days/SLAB, which apply_business_rules handles)
    def _bucket(v):
        if pd.isna(v):
            return "Unknown"
        for lo, hi, label in CONFIG["ageing_buckets"]:
            if lo <= v <= hi:
                return label
        return "Unknown"
    if "case_ageing" in df.columns:
        df["ageing_bucket"] = df["case_ageing"].apply(_bucket)
    else:
        df["ageing_bucket"] = "Unknown"

    meta = {
        "filename": filename,
        "sheet_used": target_sheet,
        "sheet_names": sheet_names,
        "record_count": int(len(df)),
        "column_count": int(raw.shape[1]),
        "detected_fields": {FIELD_LABELS.get(k, k): v for k, v in mapping.items()},
        "missing_fields": [FIELD_LABELS.get(m, m) for m in missing],
        "date_min": (df["opened_date"].min().strftime("%Y-%m-%d") if "opened_date" in df.columns and df["opened_date"].notna().any() else None),
        "date_max": (df["opened_date"].max().strftime("%Y-%m-%d") if "opened_date" in df.columns and df["opened_date"].notna().any() else None),
        "project_count": int(df["project_name"].nunique()) if "project_name" in df.columns else 0,
        "processed_at": datetime.now().isoformat(),
    }
    return df, meta


# ===========================================================================
# Business-rule formula replication (v2)
#
# The original Excel template computed these fields with live formulas
# (=TODAY(), =XLOOKUP(...) against the LIST sheet, etc.) which only stay
# correct while the workbook is open and recalculating. A raw data export
# carries none of that - so the app computes them itself, fresh, every time
# data is uploaded or the Category -> M_Category mapping is edited.
# ===========================================================================

def _slab_for(tat_days):
    if pd.isna(tat_days):
        return None
    for lo, hi, label in CONFIG["slab_buckets"]:
        if lo < tat_days <= hi or (lo == -math.inf and tat_days <= hi):
            return label
    return None


def apply_business_rules(df: pd.DataFrame, list_state: dict, as_of_date=None) -> pd.DataFrame:
    """Computes/overrides the workbook's formula-driven fields:
        F_Closed          = Closed Date if present, else blank
        Open Date         = clean copy of Opened Date
        Closed Date (48)  = same as F_Closed
        Received bucket   = "Today" if Opened Date is the most recent date
                             in this upload, else "Older"
                             (source: =IF($AT$1=Open_Date,"Today","Older"),
                              where $AT$1 = MAX of all Open Dates)
        Closed bucket     = "Today" if Closed Date = Opened Date (resolved
                             same day), else "Older"
        Updated Status    = "OPEN" if Case Status is one of In Progress /
                             New / Submit For Approval / Re-Open, else
                             "Closed"
        TAT Days          = Closed Date - Opened Date if closed, else
                             (as_of_date - Opened Date) if still open
        SLAB              = TAT Days bucketed into 0 to 2 / 3 to 7 / 8 to 15
                             / 16 to 30 / More than 30
        M_Category        = looked up from Service Category via the LIST
                             sheet's Category -> M_Category table, default
                             "Others/Misc" if no match (or no mapping loaded)
    as_of_date defaults to the real current date (matching the workbook's
    own =TODAY()); pass an explicit date for reproducible testing.
    """
    if as_of_date is None:
        as_of_date = date.today()
    as_of_ts = pd.Timestamp(as_of_date)

    df = df.copy()
    has_opened = "opened_date" in df.columns
    has_closed = "closed_date" in df.columns

    # --- Updated Status / status_bucket (authoritative) ---------------------
    open_set = set(CONFIG["open_case_statuses"])
    if "case_status" in df.columns:
        s = df["case_status"].fillna("").str.strip().str.lower()
        is_open = s.isin(open_set)
        df["status_bucket"] = np.where(is_open, "Open", "Closed")
    elif "updated_status" in df.columns:
        s = df["updated_status"].fillna("").str.lower()
        df["status_bucket"] = np.where(s.str.contains("open"), "Open", "Closed")
    else:
        df["status_bucket"] = "Unknown"
    df["updated_status"] = np.where(df["status_bucket"] == "Open", "OPEN", "Closed")

    # --- F_Closed / Open Date / Closed Date (formula parity fields) --------
    if has_closed:
        df["f_closed"] = df["closed_date"]
    else:
        df["f_closed"] = pd.NaT
    df["open_date_calc"] = df["opened_date"] if has_opened else pd.NaT
    df["closed_date_calc"] = df["f_closed"]

    # --- Received / Closed "Today vs Older" buckets -------------------------
    if has_opened and df["opened_date"].notna().any():
        latest_open = df["opened_date"].max()
        df["received_bucket"] = np.where(df["opened_date"] == latest_open, "Today", "Older")
    else:
        df["received_bucket"] = "Older"
    if has_opened and has_closed:
        same_day = df["closed_date"].notna() & (df["closed_date"] == df["opened_date"])
        df["closed_bucket"] = np.where(same_day, "Today", "Older")
    else:
        df["closed_bucket"] = "Older"

    # --- TAT Days (recomputed, dynamic for open cases) ----------------------
    if has_opened:
        closed_mask = (df["status_bucket"] == "Closed") & has_closed & df["closed_date"].notna()
        tat = pd.Series(np.nan, index=df.index, dtype="float64")
        if has_closed:
            tat.loc[closed_mask] = (df.loc[closed_mask, "closed_date"] - df.loc[closed_mask, "opened_date"]).dt.days
        open_mask = df["opened_date"].notna() & ~closed_mask
        tat.loc[open_mask] = (as_of_ts - df.loc[open_mask, "opened_date"]).dt.days
        df["tat_days"] = tat
    # else: leave whatever was detected from source (no opened_date to compute from)

    # --- SLAB (recomputed from the freshly computed TAT Days) --------------
    if "tat_days" in df.columns:
        df["slab"] = df["tat_days"].apply(_slab_for)
        df["is_sla_breach"] = ~df["slab"].isin(CONFIG["sla_within_buckets"]) & df["slab"].notna()
    else:
        df["is_sla_breach"] = False

    # --- M_Category (recomputed via the LIST Category mapping) -------------
    # The field the mapping is keyed on is configurable (CONFIG["m_category_
    # lookup_field"]) since different source workbooks key their XLOOKUP on
    # different columns - Service Category for the original M3M template,
    # Area for Smartworld's.
    category_map = (list_state or {}).get("category_map") or {}
    lookup_field = CONFIG.get("m_category_lookup_field", "service_category")
    if lookup_field in df.columns:
        def _lookup(cat):
            if pd.isna(cat) or not str(cat).strip():
                return "Others/Misc"
            return category_map.get(str(cat).strip().lower(), "Others/Misc")
        if category_map:
            df["m_category"] = df[lookup_field].apply(_lookup)
        elif "m_category" not in df.columns:
            df["m_category"] = "Others/Misc"
        # if no mapping is loaded but the source already had M_Category values,
        # leave them as-is rather than overwriting with a guess

    return df


# ===========================================================================
# LIST management (Project / Month / Year dropdowns + Category mapping)
# ===========================================================================

# Shipped default, extracted from the Smartworld-provided SW_List.xlsx so the
# app works correctly out of the box. An admin can replace all of this at any
# time from the "Manage Lists" screen (upload a new LIST.xlsx, or edit
# in-app) without needing to touch this file.
_DEFAULT_PROJECTS = [
    "ALL", "Smartworld Gems", "Smartworld Orchard", "Smartworld Gems 2",
    "Trump Residences Gurgaon", "Smartworld SKY ARC", "Smartworld One DXP",
    "Smartworld The Edition", "Smartworld Orchard Street", "Smartworld One DXP Street",
]
_DEFAULT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_DEFAULT_YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027]
# The Area -> M_Category column pair in SW_List.xlsx (columns G/H, matching
# the source workbook's XLOOKUP) currently has the Area list filled in but
# the M_Category column empty. Rather than leave every case defaulting to
# "Others/Misc" - which the one populated data sample shows is NOT what the
# workbook actually produces (its M_Category matched Area exactly, e.g.
# Area="Possessions" -> M_Category="Possessions") - each Area is defaulted
# to map to itself here. This is the best-evidenced default given what was
# provided; edit it (or upload a filled-in LIST.xlsx) from Manage Lists if
# Smartworld wants coarser groupings instead, the same way M3M's mapping
# groups several categories under one M_Category.
_DEFAULT_CATEGORY_ROWS = [
    ("Pre Sales", "Pre Sales"), ("Account Related", "Account Related"),
    ("Possessions", "Possessions"), ("Payment & Receipts", "Payment & Receipts"),
    ("Special Occasion", "Special Occasion"), ("Demands & Reminders", "Demands & Reminders"),
    ("Transfer / Name Change", "Transfer / Name Change"), ("Documentation", "Documentation"),
    ("Bank Loan", "Bank Loan"), ("KYC Updation", "KYC Updation"),
    ("Rental Benefit- Comfort Letter", "Rental Benefit- Comfort Letter"),
    ("Collection Call", "Collection Call"), ("Cancellation", "Cancellation"),
    ("CRM Feedback", "CRM Feedback"), ("Unit Layout", "Unit Layout"), ("Legal", "Legal"),
    ("Construction", "Construction"), ("Leasing", "Leasing"), ("Channel Partner", "Channel Partner"),
    ("R.M. Related", "R.M. Related"), ("Mobile App", "Mobile App"), ("Email", "Email"),
]


def default_list_state():
    """The built-in LIST data, used until an admin uploads/edits their own."""
    return {
        "projects": list(_DEFAULT_PROJECTS),
        "months": list(_DEFAULT_MONTHS),
        "years": list(_DEFAULT_YEARS),
        "category_rows": [{"category": c, "m_category": m} for c, m in _DEFAULT_CATEGORY_ROWS],
        "category_map": {c.strip().lower(): m for c, m in _DEFAULT_CATEGORY_ROWS},
        "source": "built-in default",
    }


def list_state_from_rows(projects, months, years, category_rows, source="edited in-app"):
    """Builds a list_state dict from plain lists/rows (used by the in-app
    editor, which sends JSON rather than a workbook)."""
    category_rows = [
        {"category": str(r.get("category", "")).strip(), "m_category": str(r.get("m_category", "")).strip()}
        for r in category_rows if str(r.get("category", "")).strip()
    ]
    return {
        "projects": [str(p).strip() for p in projects if str(p).strip()],
        "months": [str(m).strip() for m in months if str(m).strip()],
        "years": sorted({int(y) for y in years if str(y).strip().isdigit()}),
        "category_rows": category_rows,
        "category_map": {r["category"].lower(): r["m_category"] for r in category_rows if r["m_category"]},
        "source": source,
    }


def parse_list_workbook(file_bytes: bytes, filename: str = "LIST.xlsx"):
    """Parses an uploaded LIST workbook. Expects a sheet (any name matching
    'list', falling back to the first sheet) with header columns named
    Project, Month, Year, and a category column - matched by header text,
    not position, the same way the main data columns are detected. The
    category column is named "Category" in the original M3M-style LIST
    layout, or "Area" in Smartworld's - both are recognized."""
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Could not read the uploaded file as an Excel workbook: {e}")

    target_sheet = None
    for s in xls.sheet_names:
        if _norm(s) == _norm(LIST_SHEET_NAME):
            target_sheet = s
            break
    if target_sheet is None:
        target_sheet = xls.sheet_names[0]

    raw = pd.read_excel(xls, sheet_name=target_sheet, dtype=object, header=0)
    norm_cols = [_norm(c) for c in raw.columns]

    def _col(*names):
        for name in names:
            for i, nc in enumerate(norm_cols):
                if nc == name:
                    return raw.iloc[:, i]
        return None

    proj_col = _col("project")
    month_col = _col("month")
    year_col = _col("year")
    cat_col = _col("category", "area")
    mcat_col = _col("m category", "m_category")

    projects = [str(v).strip() for v in (proj_col.dropna().tolist() if proj_col is not None else []) if str(v).strip()]
    months = [str(v).strip() for v in (month_col.dropna().tolist() if month_col is not None else []) if str(v).strip()]
    years = []
    if year_col is not None:
        for v in year_col.dropna().tolist():
            try:
                years.append(int(v))
            except (TypeError, ValueError):
                pass

    category_rows = []
    if cat_col is not None:
        n = max(len(cat_col), len(mcat_col)) if mcat_col is not None else len(cat_col)
        for i in range(n):
            c = cat_col.iloc[i] if i < len(cat_col) else None
            m = mcat_col.iloc[i] if (mcat_col is not None and i < len(mcat_col)) else None
            if c is not None and not pd.isna(c) and str(c).strip():
                # If the workbook has no dedicated M_Category column at all (Smartworld's
                # LIST.xlsx as provided only has the Area list filled in, no M_Category
                # column), default each category to map to itself rather than leaving it
                # blank - see the _DEFAULT_CATEGORY_ROWS comment above for the reasoning;
                # this keeps an uploaded file behaving the same way as the built-in default.
                if mcat_col is None:
                    m_val = str(c).strip()
                else:
                    m_val = "" if (m is None or pd.isna(m)) else str(m).strip()
                category_rows.append({"category": str(c).strip(), "m_category": m_val})

    if not projects and not category_rows:
        raise ValueError(
            "Could not find recognizable Project / Category (or Area) / M_Category columns in this workbook. "
            "Expected header names like Project, Month, Year, and Category or Area."
        )

    return {
        "projects": projects or list(_DEFAULT_PROJECTS),
        "months": months or list(_DEFAULT_MONTHS),
        "years": sorted(set(years)) or list(_DEFAULT_YEARS),
        "category_rows": category_rows,
        "category_map": {r["category"].lower(): r["m_category"] for r in category_rows if r["m_category"]},
        "source": f"uploaded: {filename}",
    }
