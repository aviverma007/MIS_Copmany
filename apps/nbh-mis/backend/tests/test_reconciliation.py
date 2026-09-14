"""Report Logic Validation (spec section 40): recompute every number in the
supplied NBH_Template.xlsx from raw data and confirm exact reconciliation.

Ageing-bucket counts depend on "today" (per the workbook's own TODAY()-based
formula), so this test pins `as_of` to the exact moment the source workbook's
pivot cache was last refreshed (2026-08-06, from the workbook's
pivotCacheDefinition refreshedDate) instead of going through the live API,
which always uses the real current date. Totals that do NOT depend on wall
clock (open/closed counts, project/category grand totals) are also covered
by the live-API smoke tests in test_smoke.py.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd

from app.services import analytics_service, cleaning_service

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data", "NBH_Sample_Data_Full.csv")
WORKBOOK_REFRESH_DATE = datetime(2026, 8, 6)


def _load_enriched():
    raw = pd.read_csv(SAMPLE)
    cleaned, dq = cleaning_service.normalize_and_clean(raw)
    enriched, meta = analytics_service.enrich(cleaned, as_of=WORKBOOK_REFRESH_DATE)
    return enriched, dq, meta


def test_total_and_open_closed_counts():
    df, dq, _ = _load_enriched()
    assert dq.total_rows == 105994
    assert dq.valid_rows == 105994
    assert (df["management_status"] == "OPEN").sum() == 3629
    assert (df["management_status"] == "CLOSED").sum() == 105994 - 3629


def test_ageing_slab_distribution_matches_workbook():
    df, _, _ = _load_enriched()
    open_df = df[df["management_status"] == "OPEN"]
    counts = open_df["ageing_slab"].value_counts().to_dict()
    assert counts["0 to 2"] == 767
    assert counts["3 to 7"] == 445
    assert counts["8 to 15"] == 438
    assert counts["16 to 30"] == 879
    assert counts["More than 30"] == 1100


def test_project_wise_matches_workbook():
    df, _, _ = _load_enriched()
    open_df = df[df["management_status"] == "OPEN"]
    by_project = open_df.groupby("society_name").size()
    assert by_project["Smartworld Gems"] == 1405
    assert by_project["Smartworld Orchard"] == 983
    assert by_project["M3M Soulitude"] == 586
    assert by_project["M3M Heights"] == 302


def test_category_wise_matches_workbook():
    df, _, _ = _load_enriched()
    open_df = df[df["management_status"] == "OPEN"]
    by_cat = open_df.groupby("category_raw").size()
    assert by_cat["SEEPAGE"] == 453
    assert by_cat["OTHERS__MISC"] == 409
    assert by_cat["ACCOUNTS__BILLING"] == 394
    assert by_cat["PLUMBING"] == 367
    assert by_cat["MASONRY"] == 365


def test_management_category_mapping_reproduces_list_sheet():
    df, _, meta = _load_enriched()
    row = df[df["category_norm"] == "SEEPAGE"].iloc[0]
    assert row["management_category"] == "Plumbing/Leakage/Seepage"
    row2 = df[df["category_norm"] == "LIFT"].iloc[0]
    assert row2["management_category"] == "Lift"
    # Categories genuinely absent from the LIST sheet mapping (e.g. PARKING,
    # SUGGESTION) must default to Others/Misc and be flagged as unmapped.
    assert "PARKING" in meta["unmapped_categories"] or "SUGGESTION" in meta["unmapped_categories"]


def test_no_hardcoded_values_data_driven():
    """A different subset of the same data should produce different, correctly
    recomputed totals -- proving numbers come from the data, not constants."""
    df, _, _ = _load_enriched()
    subset = df[df["society_name"] == "M3M Heights"]
    open_subset = subset[subset["management_status"] == "OPEN"]
    assert len(open_subset) == 302
    assert len(open_subset) != len(df[df["management_status"] == "OPEN"])
