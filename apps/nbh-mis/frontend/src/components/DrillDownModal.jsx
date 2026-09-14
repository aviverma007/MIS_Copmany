import React from "react";
import { X, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { useDrilldown } from "../context/DrilldownContext.jsx";
import { useFilters } from "../context/FilterContext.jsx";
import TicketsTable from "./TicketsTable.jsx";

export default function DrillDownModal() {
  const { state, closeDrilldown } = useDrilldown();
  const { filters } = useFilters();

  if (!state) return null;
  const combinedFilters = { ...filters, ...state.extraFilters };
  const qs = new URLSearchParams(
    Object.entries(combinedFilters).filter(([, v]) => v && String(v).toUpperCase() !== "ALL")
  ).toString();

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-ink-900/40 p-4" onClick={closeDrilldown}>
      <div
        className="bg-surface rounded-lg shadow-xl w-full max-w-6xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-ink-900">Ticket Drill-Down</h2>
            <p className="text-xs text-ink-500">{state.title}</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/reports/tickets?${qs}`}
              onClick={closeDrilldown}
              className="btn !py-1 !px-2 text-xs"
              title="Open full ticket list page"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open Full Page
            </Link>
            <button className="btn !py-1 !px-2" onClick={closeDrilldown} aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="p-4 overflow-y-auto">
          <TicketsTable filters={combinedFilters} pageSize={25} />
        </div>
      </div>
    </div>
  );
}
