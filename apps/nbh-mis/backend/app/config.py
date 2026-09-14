"""
Central configuration for the NBH Management MIS backend.

Every business rule that the prompt requires to be "configurable, not
hard-coded in React" lives here: required/optional columns, closed-status
set, ageing buckets, RAG rules, category -> management-category mapping, and
export settings. Changing behaviour for a new NBH export should mean editing
this file, not touching services or the frontend.

See docs/DATA_REPORT_MAPPING.md for how each rule was reverse engineered from
the supplied NBH_Template.xlsx.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Column handling
# ---------------------------------------------------------------------------

# Canonical (normalized) column name -> list of raw header spellings/aliases
# that should be recognized as that column. Matching is case/space/punctuation
# insensitive on top of this (see services/cleaning_service.normalize_columns).
COLUMN_ALIASES: dict[str, list[str]] = {
    "society_name": ["society name", "project", "project name", "site name"],
    "issue_location": ["issue location", "location"],
    "ticket_id": ["ticket id", "ticket no", "ticket number", "id"],
    "created_on": ["created on", "created date", "creation date"],
    "created_by": ["created by"],
    "priority": ["priority"],
    "category": ["category"],
    "sub_category": ["sub category", "subcategory"],
    "description": ["description"],
    "assigned_on": ["assigned on", "assigned date"],
    "status": ["status"],
    "commented_on": ["commented on"],
    "commented_by": ["commented by"],
    "last_comment": ["last comment"],
    "escalated_level": ["escalated level", "escalation level"],
    "current_assignee": ["current assignee", "assignee"],
    "visibility": ["visibility"],
    "rating": ["rating", "customer rating"],
    "last_updated_on": ["last updated on", "last update", "updated on"],
    "source": ["source"],
    "reported_from_apartment": ["reported_from(apartment)", "reported from apartment", "apartment"],
    "support_ticket_closed_type": ["support_ticket_closed_type", "closed type"],
    "resolved_time": ["resolved time"],
    "closed_time": ["closed time"],
}

# Columns the app cannot function without.
REQUIRED_COLUMNS: list[str] = [
    "society_name", "ticket_id", "created_on", "status", "category",
]

# Preferred priority order when computing the closure timestamp for a ticket
# whose management status is CLOSED. First non-blank wins. This reproduces
# the workbook's F_Closed formula:
#   =IF(Updated Status="Closed", IF(Closed Time<>"",Closed Time,
#                                 IF(Resolved Time<>"",Resolved Time,
#                                 IF(Last updated on<>"",Last updated on,""))),"")
CLOSURE_TIMESTAMP_PRIORITY: list[str] = ["closed_time", "resolved_time", "last_updated_on"]

# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------

# A raw Status value found in this set (case-insensitive, after normalizing
# spaces/hyphens to underscores) is classified CLOSED/RESOLVED for management
# reporting. Anything else -- including a brand-new status value the app has
# never seen before -- defaults to OPEN/PENDING, which is the safer default
# for management visibility (an unrecognised status should get attention, not
# quietly vanish from the open backlog).
CLOSED_STATUSES: set[str] = {
    "CLOSED", "CANCELLED", "RESOLVED", "NOT_AN_ISSUE", "AUTO_CLOSE",
}

MANAGEMENT_STATUS_OPEN = "OPEN"
MANAGEMENT_STATUS_CLOSED = "CLOSED"

# ---------------------------------------------------------------------------
# Ageing buckets (SLAB) -- reproduces Compile NBH Data column AF exactly.
# (low, high_inclusive_or_None, label)
# ---------------------------------------------------------------------------
AGEING_BUCKETS: list[tuple[int, float, str]] = [
    (0, 2, "0 to 2"),
    (3, 7, "3 to 7"),
    (8, 15, "8 to 15"),
    (16, 30, "16 to 30"),
    (31, float("inf"), "More than 30"),
]
AGEING_BUCKET_ORDER: list[str] = [b[2] for b in AGEING_BUCKETS]

# ---------------------------------------------------------------------------
# RAG (Red/Amber/Green) rules, keyed on ageing days. Suggested default per
# the prompt. "critical" is a separate boolean flag layered on top (>30 days).
# ---------------------------------------------------------------------------
RAG_RULES: list[tuple[int, float, str]] = [
    (0, 2, "green"),
    (3, 7, "amber"),
    (8, 15, "orange"),
    (16, float("inf"), "red"),
]
CRITICAL_AGEING_THRESHOLD_DAYS = 30

RAG_COLORS = {
    "green": "#1e8e5a",
    "amber": "#c98a11",
    "orange": "#cc6a1e",
    "red": "#c0392b",
    "grey": "#6b7280",
}

# ---------------------------------------------------------------------------
# Category -> Management Category mapping, reproduced from the LIST sheet
# (XLOOKUP default was "Others/Misc"). 46 raw categories mapped from the
# supplied workbook; unmapped categories fall back to DEFAULT_MANAGEMENT_CATEGORY
# and are surfaced under the Data Quality "Unmapped Categories" warning.
# ---------------------------------------------------------------------------
DEFAULT_MANAGEMENT_CATEGORY = "Others/Misc"

CATEGORY_MAPPING: dict[str, str] = {
    "ELECTRICAL": "Electrical",
    "ELECTRICIAN": "Electrical",
    "ELE": "Electrical",
    "PLUMBING": "Plumbing/Leakage/Seepage",
    "SEEPAGE": "Plumbing/Leakage/Seepage",
    "LEAKAGE": "Plumbing/Leakage/Seepage",
    "PLUMBER": "Plumbing/Leakage/Seepage",
    "VANITY_MIRRORS": "Plumbing/Leakage/Seepage",
    "HOUSEKEEPING": "Others/Misc",
    "HOUSE_KEEPING": "Others/Misc",
    "MASONRY": "Masonary",
    "MASONARY": "Masonary",
    "PAINTER": "Others/Misc",
    "PROJECT": "Project Related",
    "COMMON_AREA_OR_OTHERS": "Others/Misc",
    "COMMON_AREA__OTHER": "Others/Misc",
    "COMMON_AREA": "Others/Misc",
    "CARPENTERY": "Carpentry",
    "CARPENTRY": "Carpentry",
    "CARPENTER": "Carpentry",
    "LIFT": "Lift",
    "LIFTS": "Lift",
    "SECURITY__PARKING": "Security",
    "SECURITY": "Security",
    "ACCOUNTS__BILLING": "Others/Misc",
    "ACCOUNTS_BILLING": "Others/Misc",
    "FIRE": "Others/Misc",
    "FIRE__SAFETY_HAZARD": "Others/Misc",
    "TELEPHONE_INTERCOM": "Others/Misc",
    "INTERCOM": "Others/Misc",
    "CLUBHOUSE__FACILITIES": "Others/Misc",
    "CLUB_HOUSE": "Others/Misc",
    "CLUB_HOUSES__FACILITIES": "Others/Misc",
    "NBH_APP_ISSUES": "Others/Misc",
    "NBH_APP_ISSUE": "Others/Misc",
    "GAS_BANKLPG": "Others/Misc",
    "GAS": "Others/Misc",
    "FACADE_REPAIR": "Others/Misc",
    "CIVIL_WORK": "Others/Misc",
    "CLEANING": "Others/Misc",
    "HORTICULTURE": "Others/Misc",
    "PARKING_M3M": "Others/Misc",
    "ANY_OTHER": "Others/Misc",
    "GROUTING": "Others/Misc",
    "AC": "Others/Misc",
    "TECHNICAL": "Others/Misc",
}

MANAGEMENT_CATEGORY_HEADS: list[str] = [
    "Plumbing/Leakage/Seepage", "Electrical", "Carpentry", "Lift",
    "Masonary", "Security", "Others/Misc", "Project Related",
]

# ---------------------------------------------------------------------------
# Priority normalization (workbook uses free text; app buckets to 3 levels
# for the Priority Dashboard while keeping the raw value for drill-down)
# ---------------------------------------------------------------------------
PRIORITY_ORDER = ["HIGH", "MEDIUM", "LOW"]
PRIORITY_ALIASES = {
    "HIGH": "HIGH", "CRITICAL": "HIGH", "URGENT": "HIGH",
    "MEDIUM": "MEDIUM", "MED": "MEDIUM", "NORMAL": "MEDIUM",
    "LOW": "LOW", "MINOR": "LOW",
}

# ---------------------------------------------------------------------------
# Upload / security limits
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB = 100
ALLOWED_UPLOAD_EXTENSIONS = {".xlsx", ".xls", ".csv"}
COMPILE_SHEET_NAME_CANDIDATES = ["compile nbh data", "compile data", "raw data", "data"]

# ---------------------------------------------------------------------------
# Export settings
# ---------------------------------------------------------------------------
EXPORT_SHEET_ORDER = [
    "Executive Dashboard Data", "KPI Summary", "Open Cases", "Project Wise",
    "Category Wise", "Management Category Wise", "Date Wise Summary",
    "Assignee Performance", "Priority Analysis", "Escalation Analysis",
    "Source Analysis", "Top 5 Bottom 5", "Filtered Ticket Details",
    "Data Quality Report",
]

APP_TITLE = "NBH Customer Complaint Management Dashboard"
ORGANIZATION_NAME = "M3M India"
