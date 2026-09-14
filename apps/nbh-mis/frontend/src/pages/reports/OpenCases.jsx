import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import SectionCard from "../../components/SectionCard.jsx";
import AgeingPivotTable from "../../components/AgeingPivotTable.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ErrorBanner from "../../components/ErrorBanner.jsx";
import { useFilteredData } from "../../hooks/useFilteredData.js";
import { getOpenCases } from "../../services/api.js";
import { useFilters } from "../../context/FilterContext.jsx";
import { useDrilldown } from "../../context/DrilldownContext.jsx";
import { formatNumber } from "../../utils/format.js";

export default function OpenCases() {
  const { filters } = useFilters();
  const { openDrilldown } = useDrilldown();
  const { data, loading, error } = useFilteredData(getOpenCases, filters);

  if (loading) return <LoadingSpinner label="Loading open cases…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div className="flex flex-col gap-4">
      <SectionCard title="Open Cases: Status × Ageing Slab" subtitle={`Grand Total: ${formatNumber(data.grand_total?.["Grand Total"])}`}>
        <AgeingPivotTable
          rows={data.by_status_slab}
          rowKey="status"
          rowLabel="Status"
          onCellClick={(row, slab) => openDrilldown(`${row.status} · ${slab}`, { status: row.status, ageing_slab: slab })}
          searchable={false}
        />
      </SectionCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Open Cases by Priority">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.by_priority} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
                <CartesianGrid stroke="#eef0f3" vertical={false} />
                <XAxis dataKey="priority" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => formatNumber(v)} />
                <Bar
                  dataKey="count"
                  fill="#2f5f8f"
                  radius={[3, 3, 0, 0]}
                  cursor="pointer"
                  onClick={(d) => d?.priority && openDrilldown(`Priority: ${d.priority} (open)`, { priority: d.priority })}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>
        <SectionCard title="Open Cases by Escalation Level">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.by_escalation_level} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
                <CartesianGrid stroke="#eef0f3" vertical={false} />
                <XAxis dataKey="level" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => formatNumber(v)} />
                <Bar
                  dataKey="count"
                  fill="#c98a11"
                  radius={[3, 3, 0, 0]}
                  cursor="pointer"
                  onClick={(d) => d?.level !== undefined && openDrilldown(`Escalation Level: ${d.level} (open)`, { escalation_level: d.level })}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
