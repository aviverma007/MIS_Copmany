import React from "react";
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from "recharts";
import SectionCard from "../../components/SectionCard.jsx";
import AgeingPivotTable from "../../components/AgeingPivotTable.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ErrorBanner from "../../components/ErrorBanner.jsx";
import { useFilteredData } from "../../hooks/useFilteredData.js";
import { getCategoryWise } from "../../services/api.js";
import { useFilters } from "../../context/FilterContext.jsx";
import { useDrilldown } from "../../context/DrilldownContext.jsx";
import { formatNumber, formatPct } from "../../utils/format.js";

function RankList({ title, items, valueKey, onItemClick }) {
  return (
    <div>
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-1.5">{title}</h3>
      <ul className="flex flex-col gap-1">
        {(items || []).map((item, i) => (
          <li key={item.category}>
            <button className="w-full flex items-center justify-between text-xs px-2 py-1 rounded hover:bg-canvas" onClick={() => onItemClick?.(item)}>
              <span><span className="text-ink-400 mr-1.5">{i + 1}.</span>{item.category}</span>
              <span className="font-semibold">{formatNumber(item[valueKey])}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function CategoryWise() {
  const { filters, setFilter } = useFilters();
  const { openDrilldown } = useDrilldown();
  const { data, loading, error } = useFilteredData(getCategoryWise, filters);

  if (loading) return <LoadingSpinner label="Loading category wise report…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <div className="card p-3">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Highest Ageing Category</span>
          <div className="text-base font-bold text-ink-900">{data.highest_ageing_category || "—"}</div>
        </div>
        <div className="card p-3">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Highest Open Category</span>
          <div className="text-base font-bold text-ink-900">{data.highest_open_category || "—"}</div>
        </div>
      </div>

      <SectionCard title="Category Wise: Open Cases by Ageing Slab" subtitle="Click a category to filter the whole dashboard · click a cell to drill down">
        <AgeingPivotTable
          rows={data.rows}
          rowKey="category"
          rowLabel="Category"
          onRowClick={(row) => setFilter("category", row.category)}
          onCellClick={(row, slab) => openDrilldown(`${row.category} · ${slab}`, { category: row.category, ageing_slab: slab })}
        />
      </SectionCard>

      <SectionCard title="Pareto Analysis" subtitle="Categories ranked by total volume with cumulative %">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.pareto} margin={{ top: 8, right: 24, bottom: 55, left: -12 }}>
              <CartesianGrid stroke="#eef0f3" vertical={false} />
              <XAxis dataKey="category" tick={{ fontSize: 9 }} interval={0} angle={-45} textAnchor="end" height={70} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value, name) => (name === "cumulative_pct" ? [formatPct(value), "Cumulative %"] : [formatNumber(value), "Count"])} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar
                yAxisId="left"
                dataKey="count"
                name="Count"
                fill="#2f5f8f"
                radius={[3, 3, 0, 0]}
                cursor="pointer"
                onClick={(d) => d?.category && openDrilldown(`Category: ${d.category}`, { category: d.category })}
              />
              <Line yAxisId="right" type="monotone" dataKey="cumulative_pct" name="Cumulative %" stroke="#c0392b" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <SectionCard>
          <RankList title="Top 10 Categories" items={data.top10} valueKey="count" onItemClick={(item) => openDrilldown(`Category: ${item.category}`, { category: item.category })} />
        </SectionCard>
        <SectionCard>
          <RankList title="Bottom 10 Categories" items={data.bottom10} valueKey="count" onItemClick={(item) => openDrilldown(`Category: ${item.category}`, { category: item.category })} />
        </SectionCard>
      </div>
    </div>
  );
}
