import React, { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import SectionCard from "./SectionCard.jsx";
import { formatNumber } from "../utils/format.js";
import { useFilteredData } from "../hooks/useFilteredData.js";
import { getManagementCategoryWise } from "../services/api.js";
import { useFilters } from "../context/FilterContext.jsx";
import { useDrilldown } from "../context/DrilldownContext.jsx";
import LoadingSpinner from "./LoadingSpinner.jsx";
import ErrorBanner from "./ErrorBanner.jsx";

export default function ManagementCategoryChart() {
  const { filters } = useFilters();
  const { openDrilldown } = useDrilldown();
  const { data, loading, error } = useFilteredData(getManagementCategoryWise, filters);

  const rows = useMemo(
    () => (data?.rows || []).slice().sort((a, b) => b.total_pending - a.total_pending),
    [data]
  );

  return (
    <SectionCard title="Management Category Breakdown" subtitle="Open / pending by management category">
      {loading && <LoadingSpinner compact />}
      {!loading && error && <ErrorBanner message={error} compact />}
      {!loading && !error && (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid stroke="#eef0f3" vertical={false} />
              <XAxis dataKey="management_category" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={55} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value, name) => [formatNumber(value), name === "total_pending" ? "Total Pending" : ">30 Days"]} />
              <Bar
                dataKey="total_pending"
                name="Total Pending"
                fill="#2f5f8f"
                radius={[3, 3, 0, 0]}
                cursor="pointer"
                onClick={(d) => d?.management_category && openDrilldown(`Mgmt. Category: ${d.management_category}`, { management_category: d.management_category })}
              />
              <Bar
                dataKey="over_30_pending"
                name=">30 Days"
                fill="#c0392b"
                radius={[3, 3, 0, 0]}
                cursor="pointer"
                onClick={(d) =>
                  d?.management_category &&
                  openDrilldown(`Mgmt. Category: ${d.management_category} (>30 days)`, {
                    management_category: d.management_category,
                    ageing_slab: "More than 30",
                  })
                }
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </SectionCard>
  );
}
