import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import SectionCard from "../components/SectionCard.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";
import { getDataQuality } from "../services/api.js";
import { formatNumber } from "../utils/format.js";

function Stat({ label, value, warn }) {
  return (
    <div className={`card p-3 flex flex-col gap-0.5 ${warn && value ? "border-amber-300 bg-amber-50/60" : ""}`}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">{label}</span>
      <span className={`text-lg font-bold ${warn && value ? "text-amber-700" : "text-ink-900"}`}>{formatNumber(value)}</span>
    </div>
  );
}

function ChipList({ title, items, tone = "amber" }) {
  const toneCls = tone === "amber" ? "bg-amber-100 text-amber-800 border-amber-200" : "bg-red-100 text-red-800 border-red-200";
  return (
    <div>
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-1.5">{title}</h3>
      {!items || items.length === 0 ? (
        <p className="text-xs text-ink-400">None.</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {items.map((item) => (
            <span key={item} className={`text-[11px] px-2 py-0.5 rounded-full border ${toneCls}`}>{item}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DataQuality() {
  const [dq, setDq] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDataQuality()
      .then(setDq)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load data quality report."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="max-w-[1400px] mx-auto px-4 py-6"><LoadingSpinner label="Loading data quality report…" /></div>;
  if (error) return <div className="max-w-[1400px] mx-auto px-4 py-6"><ErrorBanner message={error} /></div>;
  if (!dq) return null;

  const detectedCols = Object.entries(dq.detected_columns || {});

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-6 flex flex-col gap-4">
      <h1 className="text-lg font-bold text-ink-900">Data Quality Report</h1>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2.5">
        <Stat label="Total Rows" value={dq.total_rows} />
        <Stat label="Valid Rows" value={dq.valid_rows} />
        <Stat label="Blank Rows Removed" value={dq.blank_rows_removed} warn />
        <Stat label="Duplicate Ticket IDs" value={dq.duplicate_ticket_ids} warn />
        <Stat label="Missing Ticket ID" value={dq.missing_ticket_id} warn />
        <Stat label="Invalid Dates" value={dq.invalid_dates} warn />
        <Stat label="Missing Created On" value={dq.missing_created_on} warn />
        <Stat label="Missing Status" value={dq.missing_status} warn />
        <Stat label="Missing Project" value={dq.missing_project} warn />
        <Stat label="Missing Category" value={dq.missing_category} warn />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title="Unmapped Categories" subtitle="Fell back to the default management category">
          <ChipList items={dq.unmapped_categories} title="" />
        </SectionCard>
        <SectionCard title="Unmapped Statuses" subtitle="Not in the configured closed-status set (treated as OPEN)">
          <ChipList items={dq.unmapped_statuses} title="" />
        </SectionCard>
      </div>

      <SectionCard title="Columns">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-1.5">Detected Columns</h3>
            {detectedCols.length === 0 ? (
              <p className="text-xs text-ink-400">None reported.</p>
            ) : (
              <ul className="text-xs text-ink-700 flex flex-col gap-1">
                {detectedCols.map(([canonical, raw]) => (
                  <li key={canonical} className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                    <span className="font-medium">{canonical}</span>
                    <span className="text-ink-400">← {raw}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-1.5">Missing Optional Columns</h3>
            {(!dq.missing_optional_columns || dq.missing_optional_columns.length === 0) ? (
              <p className="text-xs text-ink-400">None — all optional columns present.</p>
            ) : (
              <ul className="text-xs text-ink-700 flex flex-col gap-1">
                {dq.missing_optional_columns.map((c) => (
                  <li key={c} className="flex items-center gap-1.5">
                    <AlertTriangle className="h-3 w-3 text-amber-600 shrink-0" />
                    {c}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </SectionCard>

      {dq.notes && dq.notes.length > 0 && (
        <SectionCard title="Notes">
          <ul className="text-sm text-ink-700 list-disc pl-5 flex flex-col gap-1">
            {dq.notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </SectionCard>
      )}
    </div>
  );
}
