import React from "react";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import { useRagColors } from "../context/RagColorsContext.jsx";
import { formatValue, formatChangePct, changeDirection } from "../utils/format.js";
import { useDrilldown } from "../context/DrilldownContext.jsx";

// Each clickable KPI maps to the exact combination of ticket-list filters
// that reproduces its value, including the derived "management_status"
// (OPEN/CLOSED) dimension the ticket-list API now supports.
const KPI_DRILLDOWN_FILTERS = {
  total_complaints: {},
  new_complaints: {},
  open_pending: { management_status: "OPEN" },
  closed_resolved: { management_status: "CLOSED" },
  old_pending_over_30: { ageing_slab: "More than 30", management_status: "OPEN" },
  critical_high_priority: { priority: "HIGH", management_status: "OPEN" },
  reopened_cases: { status: "REOPEN" },
};

export default function KPICard({ id, kpi }) {
  const { colorFor } = useRagColors();
  const { openDrilldown } = useDrilldown();
  if (!kpi) return null;
  const dir = changeDirection(kpi.change_pct);
  const color = colorFor(kpi.rag);
  const clickable = id in KPI_DRILLDOWN_FILTERS;

  return (
    <button
      type="button"
      onClick={() => clickable && openDrilldown(kpi.label, KPI_DRILLDOWN_FILTERS[id])}
      className={`card p-3 flex flex-col gap-1.5 text-left relative overflow-hidden ${clickable ? "hover:shadow-md hover:-translate-y-0.5 transition-transform cursor-pointer" : "cursor-default"}`}
      style={{ borderLeft: `3px solid ${color}` }}
      title={clickable ? "Click to view matching tickets" : undefined}
    >
      <span className="text-[10.5px] font-semibold uppercase tracking-wide text-ink-500">{kpi.label}</span>
      <span className="text-xl font-bold text-ink-900 leading-none">{formatValue(kpi.value)}</span>
      <div className="flex items-center gap-1 text-[11px] text-ink-600">
        {dir === "up" && <ArrowUp className="h-3 w-3" />}
        {dir === "down" && <ArrowDown className="h-3 w-3" />}
        {dir === "flat" && <Minus className="h-3 w-3 text-ink-400" />}
        <span>{formatChangePct(kpi.change_pct)}</span>
        <span className="text-ink-400">vs prev.</span>
      </div>
    </button>
  );
}
