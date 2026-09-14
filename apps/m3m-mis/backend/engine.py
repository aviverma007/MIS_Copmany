"""
M3M Customer Complaint MIS - Data Engine
Dynamic column detection + cleaning + filtering + KPI/report computation.
'Compile M3M Data' is treated as the single source of truth. Nothing here
is hard-coded to specific project/category/owner values - everything is
derived from whatever is present in the uploaded workbook.

v2 additions:
  - SFDC date-string normalization (dd/mm/yyyy, with or without a time part)
  - apply_business_rules(): replicates the original template's Excel
    formulas (F_Closed, Open/Closed Date, Received/Closed "Today vs Older"
    buckets, Updated Status, TAT Days, SLAB, M_Category) as real Python
    functions, so they are always freshly computed - never stale values
    copied from a workbook that can't recalculate itself.
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

REQUIRED_SHEET = "Compile M3M Data"
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
    # treats as OPEN: =IF(OR(Status={"In progress","New","Submit For
    # Approval","Re-Open"}),"OPEN","Closed") - anything else is Closed.
    "open_case_statuses": ["in progress", "new", "submit for approval", "re-open", "reopen"],
    # Local-admin passcode gating the "Manage Lists" screen (edit/upload of
    # LIST.xlsx). This is a lightweight access gate appropriate for a local,
    # single-user desktop tool - not enterprise auth. Change it here if
    # needed; it applies the next time the app is rebuilt/started.
    "admin_passcode": "m3madmin",
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
    ("opened_date",       ["opened date", "open date", "date opened", "received date", "created date", "case created date"]),
    ("closed_date",       ["closed date", "close date", "date closed", "resolution date", "resolved date"]),
    ("case_owner",        ["case owner", "owner name", "assigned to", "owner"]),
    ("case_type",         ["case type"]),
    ("case_status",       ["case status"]),
    ("sub_category",      ["sub category", "subcategory", "sub-category"]),
    ("case_source",       ["case source"]),
    ("case_origin",       ["case origin", "channel"]),
    ("case_ageing",       ["case ageing", "case aging", "ageing", "aging"]),
    ("escalation",        ["is escalated closure", "escalation status", "escalated"]),
    ("project_name",      ["project name"]),
    ("project_unit",      ["project unit", "unit number", "unit no"]),
    ("team_leader",       ["team leader", "team lead", "tl name"]),
    ("hod",               ["hod 1", "hod name", "hod"]),
    ("client_category",   ["client category"]),
    ("updated_status",    ["updated status"]),
    ("tat_days",          ["tat days", "tat (days)", "turnaround time", "tat"]),
    ("slab",              ["slab"]),
    ("ia_status",         ["ia status"]),
    ("ia_remarks",        ["ia remarks"]),
]

FIELD_LABELS = {
    "case_number": "Case Number", "account_name": "Account Name", "subject": "Subject",
    "priority": "Priority", "m_category": "M_Category", "service_category": "Service Category",
    "opened_date": "Opened Date", "closed_date": "Closed Date", "case_owner": "Case Owner",
    "case_type": "Case Type", "case_status": "Case Status", "sub_category": "Sub Category",
    "case_source": "Case Source", "case_origin": "Case Origin", "case_ageing": "Case Ageing",
    "escalation": "Escalation", "project_name": "Project Name", "project_unit": "Project Unit",
    "team_leader": "Team Leader", "hod": "HOD", "client_category": "Client Category",
    "updated_status": "Updated Status", "tat_days": "TAT Days", "slab": "SLAB",
    "ia_status": "IA Status", "ia_remarks": "IA Remarks",
    "received_bucket": "Received Today?", "closed_bucket": "Closed Same Day?",
}

FILTER_DIMENSIONS = [
    "project_name", "updated_status", "case_status", "service_category", "m_category",
    "priority", "case_owner", "team_leader", "hod", "client_category", "case_source",
    "case_type", "sub_category", "escalated_label", "slab", "ia_status", "year", "month_name",
    "received_bucket", "closed_bucket",
]

DETAIL_TABLE_FIELDS = [
    "case_number", "account_name", "subject", "priority", "service_category", "opened_date",
    "closed_date", "case_owner", "case_status", "sub_category", "case_source", "case_ageing",
    "escalated_label", "project_name", "project_unit", "team_leader", "hod", "client_category",
    "updated_status", "tat_days", "slab", "m_category", "ia_status", "ia_remarks",
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
            "Could not detect a 'Case Number' column in the 'Compile M3M Data' sheet. "
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
    category_map = (list_state or {}).get("category_map") or {}
    if "service_category" in df.columns:
        def _lookup(cat):
            if pd.isna(cat) or not str(cat).strip():
                return "Others/Misc"
            return category_map.get(str(cat).strip().lower(), "Others/Misc")
        if category_map:
            df["m_category"] = df["service_category"].apply(_lookup)
        elif "m_category" not in df.columns:
            df["m_category"] = "Others/Misc"
        # if no mapping is loaded but the source already had M_Category values,
        # leave them as-is rather than overwriting with a guess

    return df


# ===========================================================================
# LIST management (Project / Month / Year dropdowns + Category mapping)
# ===========================================================================

# Shipped default, extracted from the M3M-provided LIST.xlsx so the app
# works correctly out of the box. An admin can replace all of this at any
# time from the "Manage Lists" screen (upload a new LIST.xlsx, or edit
# in-app) without needing to touch this file.
_DEFAULT_PROJECTS = [
    "ALL", "M3M Antalya Hills", "M3M Capital Phase-1", "M3M ROUTE65", "M3M Crown",
    "M3M SOULITUDE 2", "M3M St. Andrews at SCDA", "M3M Golf Hills Phase-I", "Atrium57",
    "M3M Altitude", "M3M City of Dreams II", "Golf Hills", "M3M Mansion", "JEWEL CREST AVENUE",
    "Trump Towers Delhi NCR", "M3M Soulitude", "M3M Golf Estate - Fairway West", "M3M One-key",
    "M3M Broadway", "M3M 65TH Avenue", "M3M Skycity", "M3M THE LINE PENTSUITES", "M3M Loft 74",
    "M3M The Cullinan II", "M3M Jewel", "M3M SCO114", "M3M Prive 73", "M3M Urbana Business Park",
    "M3M Capital Phase-3", "M3M Capital walk Phase-2", "M3M Paragon 57",
    "M3M The Cullinan Avenue (Commercial)", "M3M Capital walk Phase-1",
    "M3M The Cullinan Emporium (LGF)", "M3M City of Dreams I", "M3M Heights", "Test Project",
    "M3m 57 suites", "M3M Myden", "M3M The Cullinan (Residential)", "M3M Corner walk",
    "M3M Sky Lofts", "M3M THE LINE AVENUE", "M3M XPRESSWAY 114", "M3M Capital walk Phase-3",
    "M3M Urbana Premium", "Internaltional Financial Center", "M3MCapital", "M3M Capital Phase-2",
    "M3M Golf Estate-Polo Suites", "M3M IFC", "M3M Woodshire", "M3M Latitude", "M3M Urbana",
    "EWS Golf Estate", "M3M 114 Market", "Trump Towers", "M3M The Cullinan Emporium",
    "JACOB & CO. RESIDENCES", "M3M Skywalk", "M3M Tee Point", "M3M Cosmopolitan", "M3M The Marina",
    "M3M Escala", "M3M Natura", "M3M Merlin", "M3M Sierra 68", "Flora68", "M3M Golf Hills Phase-2",
    "M3M Noida", "M3M Broadway Retail", "M3M Urbana Corporate Tower",
    "M3M Golf Estate - Fairway East", "M3M OPUS", "M3M 84 Market", "M3M Fairway West",
    "Pine at M3M Antalya Hills", "M3M SCO 84", "M3M Golf Estate-St. Andrews Golf Residences",
    "M3M Fairway East", "M3M Assured", "M3MGolfEstate", "ALL COMMERCIAL DELIVERED",
    "Test Project Mansion", "M3M 113 SCO", "M3M 113 Market", "Code 79", "EWS-Woodshire",
    "M3M Golf Estate-Panorama Suites", "M3M ST. Andrews", "M3M Panorama",
    "M3M St. Andrews Golf Residences", "Sector 79",
]
_DEFAULT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_DEFAULT_YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027]
_DEFAULT_CATEGORY_ROWS = [
    ("Proactive Customer Connect", "Proactive Customer Connect"), ("Payment Related", "Others/Misc"),
    ("Post Possession", "Post Possession"), ("Registration Related", "Others/Misc"),
    ("Customer Onboarding", "Others/Misc"), ("Transfer Related", "Others/Misc"),
    ("Profile Updation", "Others/Misc"), ("Possession", "Possession"), ("Cancellation", "Cancellation"),
    ("Project Information", "Others/Misc"), ("Documents Related", "Others/Misc"), ("Legal", "Legal"),
    ("Approvals Related", "Others/Misc"), ("Agreement Related", "Others/Misc"), ("SD Related", "Others/Misc"),
    ("Sales Related", "Others/Misc"), ("LOI", "Others/Misc"), ("AC Related Issue", "Post Possession"),
    ("Light Related Issue", "Post Possession"), ("Cleaning Related", "Post Possession"),
    ("Handover", "Others/Misc"), ("Leakage Related Issue", "Post Possession"),
    ("Seepage Related issue", "Post Possession"), ("Slope Related Issue", "Post Possession"),
    ("Elevator Related", "Post Possession"), ("Door Lock Related Issue", "Post Possession"),
    ("General", "Others/Misc"), ("Cracks Related Issue", "Post Possession"),
    ("Water Pressure Related Issue", "Post Possession"), ("Door Related", "Post Possession"),
    ("Internet Related Issue", "Others/Misc"), ("Shifting", "Others/Misc"),
    ("Water Purifier Related Issue", "Others/Misc"), ("Flush Related Issue", "Post Possession"),
    ("Drainage Choked issue", "Post Possession"), ("UPVC Windows/ Doors", "Post Possession"),
    ("Sliding Door Related", "Post Possession"), ("Tiles Related", "Post Possession"),
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
    Project, Month, Year, Category, M_Category - matched by header text,
    not position, the same way the main data columns are detected."""
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
    cat_col = _col("category")
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
    if cat_col is not None and mcat_col is not None:
        n = max(len(cat_col), len(mcat_col))
        for i in range(n):
            c = cat_col.iloc[i] if i < len(cat_col) else None
            m = mcat_col.iloc[i] if i < len(mcat_col) else None
            if c is not None and not pd.isna(c) and str(c).strip():
                m_val = "" if (m is None or pd.isna(m)) else str(m).strip()
                category_rows.append({"category": str(c).strip(), "m_category": m_val})

    if not projects and not category_rows:
        raise ValueError(
            "Could not find recognizable Project / Category / M_Category columns in this workbook. "
            "Expected header names like Project, Month, Year, Category, M_Category."
        )

    return {
        "projects": projects or list(_DEFAULT_PROJECTS),
        "months": months or list(_DEFAULT_MONTHS),
        "years": sorted(set(years)) or list(_DEFAULT_YEARS),
        "category_rows": category_rows,
        "category_map": {r["category"].lower(): r["m_category"] for r in category_rows if r["m_category"]},
        "source": f"uploaded: {filename}",
    }
