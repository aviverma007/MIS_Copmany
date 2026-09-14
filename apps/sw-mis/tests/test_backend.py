"""
Backend smoke test: exercises engine.load_and_process, analytics, and both
exporters directly against a sample workbook - no HTTP server involved.
Useful for fast iteration on the data-processing logic.

Usage:
    pip install -r ../requirements.txt
    python test_backend.py /path/to/SW_Data.xlsx
"""
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import engine       # noqa: E402
import analytics    # noqa: E402
import export_excel # noqa: E402
import export_pdf   # noqa: E402


def main(sample_file: str):
    data = Path(sample_file).read_bytes()

    t0 = time.time()
    df, meta = engine.load_and_process(data, Path(sample_file).name)
    print(f"load_and_process: {len(df):,} rows, {len(meta['missing_fields'])} missing fields "
          f"({time.time() - t0:.2f}s)")
    # Smartworld's export genuinely has no Escalation, Team Leader, HOD, IA
    # Status, or IA Remarks fields - this is documented (see README.md), not
    # a detection bug, so the test checks for exactly this expected set
    # rather than requiring zero missing fields.
    expected_missing = {"Escalation", "Team Leader", "HOD", "IA Status", "IA Remarks"}
    assert set(meta["missing_fields"]) == expected_missing, (
        f"Missing-fields set changed from what's expected for Smartworld's schema: {meta['missing_fields']}"
    )

    t0 = time.time()
    list_state = engine.default_list_state()
    df = engine.apply_business_rules(df, list_state)
    print(f"apply_business_rules: status_bucket/tat_days/slab/m_category computed "
          f"({time.time() - t0:.2f}s)")

    t0 = time.time()
    kpis = analytics.compute_kpis(df)
    print(f"compute_kpis: total_cases={kpis['total_cases']:,} ({time.time() - t0:.2f}s)")

    t0 = time.time()
    reports = analytics.build_reports(df)
    print(f"build_reports: {len(reports)} report groups ({time.time() - t0:.2f}s)")

    t0 = time.time()
    trend = analytics.daily_trend(df)
    print(f"daily_trend: {len(trend)} days ({time.time() - t0:.2f}s)")

    t0 = time.time()
    dq = analytics.data_quality(df)
    print(f"data_quality: score={dq['score']}% ({time.time() - t0:.2f}s)")

    t0 = time.time()
    xbytes = export_excel.build_excel_report(df, {}, meta)
    print(f"export_excel: {len(xbytes):,} bytes ({time.time() - t0:.2f}s)")

    t0 = time.time()
    pbytes = export_pdf.build_executive_onepager(df, {}, meta)
    print(f"export_pdf (one-pager): {len(pbytes):,} bytes ({time.time() - t0:.2f}s)")

    print("\nALL BACKEND CHECKS PASSED.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_backend.py /path/to/SW_Data.xlsx")
        sys.exit(1)
    main(sys.argv[1])
