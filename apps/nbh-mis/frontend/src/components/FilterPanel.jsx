import React from "react";
import { RotateCcw } from "lucide-react";
import { useFilters } from "../context/FilterContext.jsx";
import { useMasterData } from "../context/MasterDataContext.jsx";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function Select({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-1 min-w-[9rem]">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">{label}</span>
      <select className="input !py-1.5 text-xs" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={String(opt.value)} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function FilterPanel({ compact = false }) {
  const { filters, setFilter, resetFilters, isActive } = useFilters();
  const { data: master, loading } = useMasterData();

  const opts = (arr) => (arr || ["ALL"]).map((v) => ({ value: v, label: v === "ALL" ? "All" : v }));

  const yearOptions = [{ value: "ALL", label: "All" }, ...((master?.years || []).map((y) => ({ value: String(y), label: String(y) })))];
  const monthOptions = [{ value: "ALL", label: "All" }, ...MONTHS.map((m) => ({ value: m, label: m }))];

  return (
    <div className="card p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">Filters</span>
        <button
          className="btn !py-1 !px-2 text-xs"
          onClick={resetFilters}
          disabled={!isActive}
          title="Reset all filters"
        >
          <RotateCcw className="h-3 w-3" />
          Reset Filters
        </button>
      </div>
      {loading ? (
        <div className="text-xs text-ink-400">Loading filter options…</div>
      ) : (
        <div className="flex flex-wrap gap-2.5">
          <Select label="Year" value={filters.year} onChange={(v) => setFilter("year", v)} options={yearOptions} />
          <Select label="Month" value={filters.month} onChange={(v) => setFilter("month", v)} options={monthOptions} />
          <Select label="Project" value={filters.project} onChange={(v) => setFilter("project", v)} options={opts(master?.projects)} />
          <Select label="Status" value={filters.status} onChange={(v) => setFilter("status", v)} options={opts(master?.statuses)} />
          <Select label="Priority" value={filters.priority} onChange={(v) => setFilter("priority", v)} options={opts(master?.priorities)} />
          <Select label="Category" value={filters.category} onChange={(v) => setFilter("category", v)} options={opts(master?.categories)} />
          <Select
            label="Mgmt. Category"
            value={filters.management_category}
            onChange={(v) => setFilter("management_category", v)}
            options={opts(master?.managementCategories)}
          />
          <Select label="Source" value={filters.source} onChange={(v) => setFilter("source", v)} options={opts(master?.sources)} />
          <Select label="Assignee" value={filters.assignee} onChange={(v) => setFilter("assignee", v)} options={opts(master?.assignees)} />
          <Select
            label="Ageing Slab"
            value={filters.ageing_slab}
            onChange={(v) => setFilter("ageing_slab", v)}
            options={opts(master?.ageingSlabs)}
          />
          <Select
            label="Escalation Level"
            value={filters.escalation_level}
            onChange={(v) => setFilter("escalation_level", v)}
            options={opts((master?.escalationLevels || ["ALL"]).map((v) => String(v)))}
          />
          {!compact && (
            <>
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Date From</span>
                <input
                  type="date"
                  className="input !py-1.5 text-xs"
                  value={filters.date_from}
                  onChange={(e) => setFilter("date_from", e.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Date To</span>
                <input
                  type="date"
                  className="input !py-1.5 text-xs"
                  value={filters.date_to}
                  onChange={(e) => setFilter("date_to", e.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 min-w-[12rem] flex-1">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Search</span>
                <input
                  type="text"
                  placeholder="Ticket ID, description, comment…"
                  className="input !py-1.5 text-xs"
                  value={filters.search}
                  onChange={(e) => setFilter("search", e.target.value)}
                />
              </label>
            </>
          )}
        </div>
      )}
    </div>
  );
}
