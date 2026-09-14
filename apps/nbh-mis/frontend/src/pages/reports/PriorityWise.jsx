import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from "recharts";
import SectionCard from "../../components/SectionCard.jsx";
import StatsTable from "../../components/StatsTable.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ErrorBanner from "../../components/ErrorBanner.jsx";
import { useFilteredData } from "../../hooks/useFilteredData.js";
import { getPriorityWise } from "../../services/api.js";
import { useFilters } from "../../context/FilterContext.jsx";
import { useDrilldown } from "../../context/DrilldownContext.jsx";
import { formatNumber } from "../../utils/format.js";

const COLUMNS = [
  { key: "priority", label: "Priority" },
  { key: "total", label: "Total", format: "number" },
  { key: "open", label: "Open", format: "number" },
  { key: "closed", label: "Closed", format: "number" },
  { key: "over_30", label: ">30 Days", format: "number" },
  { key: "closure_pct", label: "Closure %", format: "pct" },
];

export default function PriorityWise() {
  const { filters, setFilter } = useFilters();
  const { openDrilldown } = useDrilldown();
  const { data, loading, error } = useFilteredData(getPriorityWise, filters);

  if (loading) return <LoadingSpinner label="Loading priority dashboard…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div className="flex flex-col gap-4">
      <SectionCard title="Priority Distribution">
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.rows} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid stroke="#eef0f3" vertical={false} />
              <XAxis dataKey="priority" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => formatNumber(v)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar
                dataKey="open"
                name="Open"
                fill="#c0392b"
                radius={[3, 3, 0, 0]}
                cursor="pointer"
                onClick={(d) => d?.priority && openDrilldown(`Priority: ${d.priority}`, { priority: d.priority })}
              />
              <Bar
                dataKey="closed"
                name="Closed"
                fill="#1e8e5a"
                radius={[3, 3, 0, 0]}
                cursor="pointer"
                onClick={(d) => d?.priority && openDrilldown(`Priority: ${d.priority}`, { priority: d.priority })}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>
      <SectionCard title="Priority Wise Detail" subtitle="Click a row to filter by priority">
        <StatsTable rows={data.rows} rowKey="priority" columns={COLUMNS} defaultSortKey="total" onRowClick={(row) => setFilter("priority", row.priority)} />
      </SectionCard>
    </div>
  );
}
