import React, { useMemo } from "react";
import SectionCard from "../../components/SectionCard.jsx";
import StatsTable from "../../components/StatsTable.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ErrorBanner from "../../components/ErrorBanner.jsx";
import { useFilteredData } from "../../hooks/useFilteredData.js";
import { getAssigneeWise } from "../../services/api.js";
import { useFilters } from "../../context/FilterContext.jsx";

const COLUMNS = [
  { key: "assignee", label: "Assignee" },
  { key: "total", label: "Total", format: "number" },
  { key: "open", label: "Open", format: "number" },
  { key: "closed", label: "Closed", format: "number" },
  { key: "closure_pct", label: "Closure %", format: "pct" },
  { key: "avg_ageing_open", label: "Avg Ageing (Open)", format: "days" },
  { key: "over_30_open", label: ">30 Days Open", format: "number" },
];

export default function AssigneeWise() {
  const { filters, setFilter } = useFilters();
  const { data, loading, error } = useFilteredData(getAssigneeWise, filters);

  const highlights = useMemo(() => {
    const rows = data?.rows || [];
    if (rows.length === 0) return {};
    const highestBacklog = rows.reduce((a, b) => (b.open > (a?.open ?? -1) ? b : a), null);
    const highestAgeing = rows.reduce((a, b) => (b.avg_ageing_open > (a?.avg_ageing_open ?? -1) ? b : a), null);
    const lowestClosure = rows.reduce((a, b) => (b.closure_pct < (a?.closure_pct ?? 101) ? b : a), null);
    return {
      highestBacklog: highestBacklog?.assignee,
      highestAgeing: highestAgeing?.assignee,
      lowestClosure: lowestClosure?.assignee,
    };
  }, [data]);

  if (loading) return <LoadingSpinner label="Loading assignee performance…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <SectionCard
      title="Assignee Performance"
      subtitle="Highlighted: highest open backlog (red), highest average ageing (amber), lowest closure % (grey) · click a row to filter by assignee"
    >
      <StatsTable
        rows={data.rows}
        rowKey="assignee"
        columns={COLUMNS}
        defaultSortKey="open"
        onRowClick={(row) => setFilter("assignee", row.assignee)}
        highlightFn={(row) => {
          if (row.assignee === highlights.highestBacklog) return "border-l-2 border-l-red-500";
          if (row.assignee === highlights.highestAgeing) return "border-l-2 border-l-amber-500";
          if (row.assignee === highlights.lowestClosure) return "border-l-2 border-l-ink-400";
          return "";
        }}
      />
    </SectionCard>
  );
}
