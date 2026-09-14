import React from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import SectionCard from "../../components/SectionCard.jsx";
import StatsTable from "../../components/StatsTable.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ErrorBanner from "../../components/ErrorBanner.jsx";
import { useFilteredData } from "../../hooks/useFilteredData.js";
import { getSourceWise } from "../../services/api.js";
import { useFilters } from "../../context/FilterContext.jsx";
import { formatNumber } from "../../utils/format.js";

const COLUMNS = [
  { key: "source", label: "Source" },
  { key: "total", label: "Total", format: "number" },
  { key: "pct_of_total", label: "% of Total", format: "pct" },
  { key: "closure_pct", label: "Closure %", format: "pct" },
];

const PALETTE = ["#2f5f8f", "#1e8e5a", "#c98a11", "#cc6a1e", "#c0392b", "#6b7280"];

export default function SourceWise() {
  const { filters, setFilter } = useFilters();
  const { data, loading, error } = useFilteredData(getSourceWise, filters);

  if (loading) return <LoadingSpinner label="Loading source analysis…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!data || !data.rows || data.rows.length === 0) {
    return (
      <SectionCard title="Source Analysis">
        <p className="text-sm text-ink-500">No Source column was found in the uploaded data, so this report is unavailable.</p>
      </SectionCard>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <SectionCard title="Complaints by Source">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data.rows} dataKey="total" nameKey="source" innerRadius={50} outerRadius={85} paddingAngle={2}>
                {data.rows.map((row, i) => (
                  <Cell key={row.source} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatNumber(v)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>
      <SectionCard title="Source Detail" subtitle="Click a row to filter by source">
        <StatsTable rows={data.rows} rowKey="source" columns={COLUMNS} defaultSortKey="total" onRowClick={(row) => setFilter("source", row.source)} />
      </SectionCard>
    </div>
  );
}
