import React from "react";
import SectionCard from "../../components/SectionCard.jsx";
import AgeingPivotTable from "../../components/AgeingPivotTable.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ErrorBanner from "../../components/ErrorBanner.jsx";
import { useFilteredData } from "../../hooks/useFilteredData.js";
import { getProjectWise } from "../../services/api.js";
import { useFilters } from "../../context/FilterContext.jsx";
import { useDrilldown } from "../../context/DrilldownContext.jsx";
import { formatNumber } from "../../utils/format.js";

function MiniRank({ title, items }) {
  return (
    <div>
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-1.5">{title}</h3>
      <ul className="flex flex-col gap-1">
        {(items || []).map((item, i) => (
          <li key={item.project} className="flex items-center justify-between text-xs px-2 py-1">
            <span><span className="text-ink-400 mr-1.5">{i + 1}.</span>{item.project}</span>
            <span className="font-semibold">{formatNumber(item.count)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ProjectWise() {
  const { filters, setFilter } = useFilters();
  const { openDrilldown } = useDrilldown();
  const { data, loading, error } = useFilteredData(getProjectWise, filters);

  if (loading) return <LoadingSpinner label="Loading project wise report…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div className="flex flex-col gap-4">
      <SectionCard title="Project Wise: Open Cases by Ageing Slab" subtitle="Click a project to filter the whole dashboard · click a cell to drill down">
        <AgeingPivotTable
          rows={data.rows}
          rowKey="project"
          rowLabel="Project"
          extraColumns={[
            { key: "total_tickets", label: "Total Tickets" },
            { key: "closure_pct", label: "Closure %", format: "pct" },
          ]}
          onRowClick={(row) => setFilter("project", row.project)}
          onCellClick={(row, slab) => openDrilldown(`${row.project} · ${slab}`, { project: row.project, ageing_slab: slab })}
        />
      </SectionCard>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <SectionCard><MiniRank title="Top 5 Open Backlog" items={data.top5_open} /></SectionCard>
        <SectionCard><MiniRank title="Top 5 Over 30 Days" items={data.top5_over30} /></SectionCard>
      </div>
    </div>
  );
}
