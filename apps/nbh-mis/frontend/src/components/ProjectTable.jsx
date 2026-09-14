import React from "react";
import SectionCard from "./SectionCard.jsx";
import AgeingPivotTable from "./AgeingPivotTable.jsx";
import LoadingSpinner from "./LoadingSpinner.jsx";
import ErrorBanner from "./ErrorBanner.jsx";
import { useFilteredData } from "../hooks/useFilteredData.js";
import { getProjectWise } from "../services/api.js";
import { useFilters } from "../context/FilterContext.jsx";
import { useDrilldown } from "../context/DrilldownContext.jsx";

export default function ProjectTable({ compact = false }) {
  const { filters, setFilter } = useFilters();
  const { openDrilldown } = useDrilldown();
  const { data, loading, error } = useFilteredData(getProjectWise, filters);

  return (
    <SectionCard
      title="Project Performance"
      subtitle="Click a project to filter the whole dashboard · click a cell to view matching tickets"
    >
      {loading && <LoadingSpinner compact />}
      {!loading && error && <ErrorBanner message={error} compact />}
      {!loading && !error && data && (
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
      )}
    </SectionCard>
  );
}
