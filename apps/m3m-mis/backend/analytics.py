"""
M3M MIS - Filtering, KPI, report, insight, attention & data-quality logic.
Operates on the cleaned DataFrame produced by engine.load_and_process().
"""
import math
from datetime import datetime
import numpy as np
import pandas as pd
from engine import CONFIG, FILTER_DIMENSIONS, DETAIL_TABLE_FIELDS, FIELD_LABELS


# ---------------------------------------------------------------------------
# FILTERING  (OR within a dimension, AND across dimensions)
# ---------------------------------------------------------------------------
def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """filters = {
        "project_name": ["A","B"], ... (OR within list)
        "date_from": "2026-01-01", "date_to": "2026-01-31"
    }
    All present dimensions are AND-ed together.
    """
    mask = pd.Series(True, index=df.index)
    if not filters:
        return df
    for dim, values in filters.items():
        if dim in ("date_from", "date_to"):
            continue
        if not values:
            continue
        if dim not in df.columns:
            continue
        mask &= df[dim].isin(values)

    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if (date_from or date_to) and "opened_date" in df.columns:
        if date_from:
            mask &= df["opened_date"] >= pd.to_datetime(date_from)
        if date_to:
            mask &= df["opened_date"] <= pd.to_datetime(date_to) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    return df[mask]


def filter_options(df: pd.DataFrame, list_state: dict = None) -> dict:
    """Unique values per filter dimension, dynamically from the data, sorted.

    When list_state is supplied, the Project/Month/Year dropdowns are the
    union of the master LIST values and whatever appears in the uploaded
    data - so a user can still filter by a project with zero current cases
    (e.g. to confirm there are none), and the dropdown doesn't depend on
    what happens to be in this particular upload.
    """
    out = {}
    for dim in FILTER_DIMENSIONS:
        if dim not in df.columns:
            out[dim] = []
            continue
        vals = df[dim].dropna().unique().tolist()
        vals = [v for v in vals if str(v).strip() != ""]
        try:
            vals = sorted(vals, key=lambda x: str(x))
        except Exception:
            pass
        out[dim] = vals
    # year should be numeric sort
    if "year" in df.columns:
        yrs = sorted([int(y) for y in df["year"].dropna().unique().tolist()])
        out["year"] = yrs

    if list_state:
        master_projects = [p for p in list_state.get("projects", []) if p and p.upper() != "ALL"]
        if master_projects:
            out["project_name"] = sorted(set(out.get("project_name", [])) | set(master_projects), key=str)
        master_months = list_state.get("months") or []
        if master_months:
            # keep calendar order (Jan..Dec) rather than alphabetical
            seen = set(out.get("month_name", [])) | set(master_months)
            out["month_name"] = [m for m in master_months if m in seen] or sorted(seen)
        master_years = list_state.get("years") or []
        if master_years:
            out["year"] = sorted(set(out.get("year", [])) | set(int(y) for y in master_years))
    return out


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
def _rag(value, thresholds, invert=False):
    green, amber = thresholds["green"], thresholds["amber"]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "grey"
    if invert:  # lower is better (e.g. SLA breach %)
        if value <= green:
            return "green"
        if value <= amber:
            return "amber"
        return "red"
    if value >= green:
        return "green"
    if value >= amber:
        return "amber"
    return "red"


def compute_kpis(df: pd.DataFrame) -> dict:
    total = df["case_number"].nunique() if "case_number" in df.columns else len(df)
    closed = df[df["status_bucket"] == "Closed"]
    opened = df[df["status_bucket"] == "Open"]
    n_closed = closed["case_number"].nunique()
    n_open = opened["case_number"].nunique()
    n_new = df[df.get("is_new", False) == True]["case_number"].nunique()
    n_pending = df[(df["status_bucket"] == "Open") & (df.get("is_new", False) == False)]["case_number"].nunique()
    n_resolved = n_closed
    n_escalated = df[df.get("is_escalated", False) == True]["case_number"].nunique()

    avg_case_age = round(opened["case_ageing"].mean(), 1) if "case_ageing" in df.columns and len(opened) else None
    avg_tat = round(closed["tat_days"].mean(), 1) if "tat_days" in df.columns and len(closed) else None

    if "is_sla_breach" in df.columns and len(closed):
        breach_ct = closed["is_sla_breach"].sum()
        sla_breach_pct = round(100 * breach_ct / len(closed), 1) if len(closed) else None
    else:
        sla_breach_pct = None

    resolution_pct = round(100 * n_resolved / total, 1) if total else 0
    closure_pct = round(100 * n_closed / total, 1) if total else 0

    kpis = {
        "total_cases": int(total),
        "open_cases": int(n_open),
        "closed_cases": int(n_closed),
        "pending_cases": int(n_pending),
        "new_cases": int(n_new),
        "resolved_cases": int(n_resolved),
        "escalated_cases": int(n_escalated),
        "avg_case_age": avg_case_age,
        "avg_tat": avg_tat,
        "sla_breach_pct": sla_breach_pct,
        "resolution_pct": resolution_pct,
        "closure_pct": closure_pct,
    }
    kpis["rag"] = {
        "resolution_pct": _rag(resolution_pct, CONFIG["rag"]["resolution_pct"]),
        "closure_pct": _rag(closure_pct, CONFIG["rag"]["closure_pct"]),
        "sla_breach_pct": _rag(sla_breach_pct, CONFIG["rag"]["sla_breach_pct"], invert=True),
    }
    return kpis


# ---------------------------------------------------------------------------
# Generic group-by report helper
# ---------------------------------------------------------------------------
def _group_report(df, dim, top_n=None):
    """Vectorized group-by report: a handful of whole-frame groupby aggregations
    instead of a Python loop per group, so this stays fast at 500,000+ rows
    even across the ~13 report dimensions computed on every request."""
    if dim not in df.columns or df.empty:
        return []
    slim_cols = [c for c in [dim, "case_number", "status_bucket", "is_escalated", "tat_days", "is_sla_breach"] if c in df.columns]
    slim = df[slim_cols]
    valid = slim[slim[dim].notna() & (slim[dim].astype(str).str.strip() != "")]
    if valid.empty:
        return []

    total = valid.groupby(dim)["case_number"].nunique()
    closed_df = valid[valid["status_bucket"] == "Closed"]
    open_df = valid[valid["status_bucket"] == "Open"]
    closed = closed_df.groupby(dim)["case_number"].nunique()
    open_ = open_df.groupby(dim)["case_number"].nunique()
    escalated = valid[valid.get("is_escalated", False) == True].groupby(dim)["case_number"].nunique()
    avg_tat = closed_df.groupby(dim)["tat_days"].mean() if "tat_days" in valid.columns else pd.Series(dtype=float)
    breach = closed_df.groupby(dim)["is_sla_breach"].mean() if "is_sla_breach" in valid.columns else pd.Series(dtype=float)

    idx = total.index
    rows = []
    for key in idx:
        t = int(total.get(key, 0))
        c = int(closed.get(key, 0))
        o = int(open_.get(key, 0))
        e = int(escalated.get(key, 0))
        at = avg_tat.get(key, np.nan)
        br = breach.get(key, np.nan)
        rows.append({
            "name": str(key),
            "total": t,
            "closed": c,
            "open": o,
            "escalated": e,
            "resolution_pct": round(100 * c / t, 1) if t else 0,
            "avg_tat": round(float(at), 1) if pd.notna(at) else None,
            "sla_breach_pct": round(100 * float(br), 1) if pd.notna(br) else None,
        })
    rows.sort(key=lambda r: r["total"], reverse=True)
    if top_n:
        rows = rows[:top_n]
    return rows


def build_reports(df: pd.DataFrame) -> dict:
    reports = {
        "project": _group_report(df, "project_name"),
        "service_category": _group_report(df, "service_category"),
        "m_category": _group_report(df, "m_category"),
        "priority": _group_report(df, "priority"),
        "case_owner": _group_report(df, "case_owner"),
        "team_leader": _group_report(df, "team_leader"),
        "hod": _group_report(df, "hod"),
        "client_category": _group_report(df, "client_category"),
        "case_status": _group_report(df, "case_status"),
        "sub_category": _group_report(df, "sub_category"),
        "slab": _group_report(df, "slab"),
        "ageing_bucket": _group_report(df, "ageing_bucket"),
        "escalation": _group_report(df, "escalated_label"),
    }
    proj = reports["project"]
    reports["top5_projects"] = proj[:5]
    reports["bottom5_projects"] = sorted(proj, key=lambda r: r["total"])[:5]
    cat = reports["service_category"]
    reports["top5_categories"] = cat[:5]
    reports["bottom5_categories"] = sorted(cat, key=lambda r: r["total"])[:5]
    return reports


def monthly_yearly_trend(df):
    out = {"monthly": [], "yearly": []}
    if "opened_date" not in df.columns or df["opened_date"].isna().all():
        return out
    tmp = df.dropna(subset=["opened_date"]).copy()
    tmp["ym"] = tmp["opened_date"].dt.strftime("%Y-%m")
    g = tmp.groupby("ym")
    rows = []
    for key, sub in sorted(g, key=lambda kv: kv[0]):
        total = sub["case_number"].nunique()
        closed = sub[sub["status_bucket"] == "Closed"]["case_number"].nunique()
        rows.append({"period": key, "received": int(total), "closed": int(closed),
                      "resolution_pct": round(100 * closed / total, 1) if total else 0})
    out["monthly"] = rows

    ty = tmp.groupby(tmp["opened_date"].dt.year)
    yrows = []
    for key, sub in ty:
        total = sub["case_number"].nunique()
        closed = sub[sub["status_bucket"] == "Closed"]["case_number"].nunique()
        yrows.append({"period": str(int(key)), "received": int(total), "closed": int(closed),
                       "resolution_pct": round(100 * closed / total, 1) if total else 0})
    out["yearly"] = yrows
    return out


# ---------------------------------------------------------------------------
# Daily trend  (Carry Forward / Received / Resolved / Pending) - section 10
# ---------------------------------------------------------------------------
def daily_trend(df: pd.DataFrame) -> list:
    """Fully vectorized (no per-row / per-day Python loop over the dataframe)
    so this stays fast at 500,000+ records - required by section 17.

    Relies on the invariant close_day >= open_day (a closed case cannot close
    before it opened; rows that violate this are flagged separately by the
    Data Quality 'negative TAT' check), which lets each day's carry-forward /
    pending figures be derived from two independent cumulative counts rather
    than a per-day join.
    """
    if "opened_date" not in df.columns or df["opened_date"].isna().all():
        return []
    d = df.dropna(subset=["opened_date"])[["case_number", "opened_date", "closed_date"]].copy()
    d["open_day"] = d["opened_date"].dt.normalize()
    d["close_day"] = d["closed_date"].dt.normalize() if "closed_date" in d.columns else pd.NaT

    all_days = pd.date_range(d["open_day"].min(), d["open_day"].max(), freq="D")

    opened_ct = d.groupby("open_day")["case_number"].nunique().reindex(all_days, fill_value=0)
    closed_ct = d.dropna(subset=["close_day"]).groupby("close_day")["case_number"].nunique().reindex(all_days, fill_value=0)

    cum_open_before = opened_ct.cumsum().shift(1, fill_value=0)      # opened strictly before day D
    cum_closed_before = closed_ct.cumsum().shift(1, fill_value=0)    # closed strictly before day D
    cum_open_upto = opened_ct.cumsum()                               # opened on/before day D
    cum_closed_upto = closed_ct.cumsum()                             # closed on/before day D

    # old_resolved(D): closed on D but opened before D. current_resolved(D): closed and opened same day D.
    same_day = d.dropna(subset=["close_day"])
    same_day_ct = same_day[same_day["open_day"] == same_day["close_day"]].groupby("close_day")["case_number"].nunique().reindex(all_days, fill_value=0)
    current_resolved = same_day_ct
    total_resolved_today = closed_ct
    old_resolved = (total_resolved_today - current_resolved).clip(lower=0)

    carry_forward = (cum_open_before - cum_closed_before).clip(lower=0)
    today_received = opened_ct
    total_complaints = carry_forward + today_received
    total_pending = (cum_open_upto - cum_closed_upto).clip(lower=0)
    total_resolved = old_resolved + current_resolved
    contribution_pct = (100 * total_resolved / total_complaints.replace(0, np.nan)).fillna(0).round(1)

    rows = []
    for day in all_days:
        rows.append({
            "date": day.strftime("%Y-%m-%d"),
            "carry_forward": int(carry_forward[day]),
            "today_received": int(today_received[day]),
            "total_complaints": int(total_complaints[day]),
            "old_resolved": int(old_resolved[day]),
            "current_resolved": int(current_resolved[day]),
            "total_resolved": int(total_resolved[day]),
            "total_pending": int(total_pending[day]),
            "contribution_pct": float(contribution_pct[day]),
        })
    return rows


# ---------------------------------------------------------------------------
# Management Attention  - section 12
# ---------------------------------------------------------------------------
def management_attention(df: pd.DataFrame) -> dict:
    out = {}
    age_thresh = CONFIG["attention_ageing_days"]
    tat_thresh = CONFIG["attention_high_tat_days"]

    def _cases(sub):
        cols = [c for c in DETAIL_TABLE_FIELDS if c in sub.columns]
        return sub[cols].head(500).to_dict(orient="records")

    if "case_ageing" in df.columns:
        sub = df[(df["status_bucket"] == "Open") & (df["case_ageing"] > age_thresh)]
        out["over_30_days"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}
    else:
        out["over_30_days"] = {"count": 0, "cases": []}

    if "priority" in df.columns:
        sub = df[(df["status_bucket"] == "Open") & (df["priority"].fillna("").str.lower().str.contains("high"))]
        out["high_priority_pending"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}
    else:
        out["high_priority_pending"] = {"count": 0, "cases": []}

    sub = df[(df["status_bucket"] == "Open") & (df.get("is_escalated", False) == True)]
    out["escalated_open"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}

    if "case_owner" in df.columns:
        sub = df[df["case_owner"].isna()]
        out["missing_owner"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}
    else:
        out["missing_owner"] = {"count": 0, "cases": []}

    if "project_name" in df.columns:
        sub = df[df["project_name"].isna()]
        out["missing_project"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}
    else:
        out["missing_project"] = {"count": 0, "cases": []}

    if "closed_date" in df.columns:
        sub = df[(df["status_bucket"] == "Closed") & (df["closed_date"].isna())]
        out["closed_without_date"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}
    else:
        out["closed_without_date"] = {"count": 0, "cases": []}

    if "tat_days" in df.columns:
        sub = df[(df["status_bucket"] == "Closed") & (df["tat_days"] > tat_thresh)]
        out["unusually_high_tat"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}
    else:
        out["unusually_high_tat"] = {"count": 0, "cases": []}

    missing_cols = [c for c in ["case_owner", "project_name", "service_category"] if c in df.columns]
    if missing_cols:
        m = df[missing_cols].isna().any(axis=1)
        sub = df[m]
        out["missing_mandatory_info"] = {"count": int(sub["case_number"].nunique()), "cases": _cases(sub)}
    else:
        out["missing_mandatory_info"] = {"count": 0, "cases": []}

    return out


# ---------------------------------------------------------------------------
# Data Quality  - section 13
# ---------------------------------------------------------------------------
def data_quality(df: pd.DataFrame) -> dict:
    total = len(df)
    checks = {}
    checks["blank_case_number"] = int(df["case_number"].isna().sum()) if "case_number" in df.columns else 0
    checks["duplicate_case_number"] = int(df["case_number"].dropna().duplicated().sum()) if "case_number" in df.columns else 0
    checks["blank_project"] = int(df["project_name"].isna().sum()) if "project_name" in df.columns else 0
    checks["blank_case_owner"] = int(df["case_owner"].isna().sum()) if "case_owner" in df.columns else 0
    checks["blank_service_category"] = int(df["service_category"].isna().sum()) if "service_category" in df.columns else 0
    checks["invalid_opened_date"] = int(df["opened_date"].isna().sum()) if "opened_date" in df.columns else 0
    checks["invalid_closed_date"] = int((df["status_bucket"] == "Closed").sum() - df.loc[df["status_bucket"] == "Closed", "closed_date"].notna().sum()) if "closed_date" in df.columns else 0
    checks["closed_without_closed_date"] = checks["invalid_closed_date"]
    if "closed_date" in df.columns:
        checks["open_with_closed_date"] = int(((df["status_bucket"] == "Open") & df["closed_date"].notna()).sum())
    else:
        checks["open_with_closed_date"] = 0
    checks["negative_tat"] = int((df["tat_days"] < 0).sum()) if "tat_days" in df.columns else 0
    checks["missing_slab"] = int(df["slab"].isna().sum()) if "slab" in df.columns else 0
    checks["missing_hod"] = int(df["hod"].isna().sum()) if "hod" in df.columns else 0
    checks["missing_team_leader"] = int(df["team_leader"].isna().sum()) if "team_leader" in df.columns else 0

    issue_rows = pd.Series(False, index=df.index)
    for col, cond in [
        ("case_number", df["case_number"].isna() if "case_number" in df.columns else None),
        ("closed_date", (df["status_bucket"] == "Closed") & df["closed_date"].isna() if "closed_date" in df.columns else None),
        ("tat_days", df["tat_days"] < 0 if "tat_days" in df.columns else None),
    ]:
        if cond is not None:
            issue_rows |= cond.fillna(False)
    if "case_number" in df.columns:
        issue_rows |= df["case_number"].duplicated(keep=False).fillna(False)

    valid = total - int(issue_rows.sum())
    score = round(100 * valid / total, 1) if total else 100.0

    return {
        "score": score,
        "rag": _rag(score, CONFIG["rag"]["data_quality"]),
        "total_records": total,
        "valid_records": valid,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Management Insight Engine - section 23 (facts only, no fabrication)
# ---------------------------------------------------------------------------
def management_insights(df: pd.DataFrame) -> list:
    insights = []
    total = df["case_number"].nunique() if "case_number" in df.columns else len(df)
    if total == 0:
        return ["No data available for the selected filters."]

    if "case_ageing" in df.columns:
        open_df = df[df["status_bucket"] == "Open"]
        old_open = open_df[open_df["case_ageing"] > 30]
        if len(open_df):
            pct = round(100 * old_open["case_number"].nunique() / open_df["case_number"].nunique(), 1)
            insights.append(f"{pct}% of currently open cases are older than 30 days ({old_open['case_number'].nunique()} of {open_df['case_number'].nunique()} open cases).")

    if "service_category" in df.columns and df["service_category"].notna().any():
        top_cat = df.groupby("service_category")["case_number"].nunique().sort_values(ascending=False)
        if len(top_cat):
            insights.append(f"'{top_cat.index[0]}' is the highest-volume service category with {int(top_cat.iloc[0])} cases.")

    if "project_name" in df.columns:
        open_df = df[df["status_bucket"] == "Open"]
        if len(open_df) and open_df["project_name"].notna().any():
            top_proj = open_df.groupby("project_name")["case_number"].nunique().sort_values(ascending=False)
            if len(top_proj):
                insights.append(f"'{top_proj.index[0]}' has the highest number of pending cases ({int(top_proj.iloc[0])}).")

    if "is_escalated" in df.columns:
        open_esc = df[(df["status_bucket"] == "Open") & (df["is_escalated"] == True)]
        insights.append(f"{open_esc['case_number'].nunique()} escalated cases are currently open.")

    if "opened_date" in df.columns and df["opened_date"].notna().any():
        tmp = df.dropna(subset=["opened_date"]).copy()
        months = sorted(tmp["opened_date"].dt.to_period("M").unique())
        if len(months) >= 2:
            last, prev = months[-1], months[-2]
            last_df = tmp[tmp["opened_date"].dt.to_period("M") == last]
            prev_df = tmp[tmp["opened_date"].dt.to_period("M") == prev]
            last_res = 100 * last_df[last_df["status_bucket"] == "Closed"]["case_number"].nunique() / max(last_df["case_number"].nunique(), 1)
            prev_res = 100 * prev_df[prev_df["status_bucket"] == "Closed"]["case_number"].nunique() / max(prev_df["case_number"].nunique(), 1)
            delta = round(last_res - prev_res, 1)
            direction = "improved" if delta >= 0 else "declined"
            insights.append(f"Resolution rate {direction} by {abs(delta)} points versus the previous month ({prev} to {last}).")
        else:
            insights.append("Not enough historical data available for month-over-month resolution comparison.")

    return insights
