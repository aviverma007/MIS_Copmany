import React from "react";
import SectionCard from "./SectionCard.jsx";
import { formatNumber, formatPct } from "../utils/format.js";
import { useFilters } from "../context/FilterContext.jsx";
import { useDrilldown } from "../context/DrilldownContext.jsx";

function MiniList({ title, items, valueKey, valueFormat, onItemClick }) {
  if (!items || items.length === 0) {
    return (
      <div>
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-1.5">{title}</h3>
        <p className="text-xs text-ink-400">No data.</p>
      </div>
    );
  }
  return (
    <div>
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-1.5">{title}</h3>
      <ul className="flex flex-col gap-1">
        {items.map((item, i) => (
          <li key={item.name}>
            <button
              className="w-full flex items-center justify-between text-xs px-2 py-1 rounded hover:bg-canvas text-left"
              onClick={() => onItemClick && onItemClick(item)}
            >
              <span className="text-ink-700 truncate">
                <span className="text-ink-400 mr-1.5 tabular-nums">{i + 1}.</span>
                {item.name}
              </span>
              <span className="font-semibold text-ink-900 tabular-nums shrink-0 ml-2">
                {valueFormat === "pct" ? formatPct(item[valueKey]) : formatNumber(item[valueKey])}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function TopBottomPanel({ topBottom }) {
  const { setFilter } = useFilters();
  const { openDrilldown } = useDrilldown();
  if (!topBottom) return null;
  const { top_open_backlog, top_over_30, best_closure_pct, worst_closure_pct, top_categories } = topBottom;

  return (
    <SectionCard title="Top / Bottom Performers">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <MiniList
          title="Top Open Backlog (Project)"
          items={top_open_backlog}
          valueKey="count"
          onItemClick={(item) => setFilter("project", item.name)}
        />
        <MiniList
          title="Top >30 Days (Project)"
          items={top_over_30}
          valueKey="count"
          onItemClick={(item) => openDrilldown(`${item.name} · More than 30`, { project: item.name, ageing_slab: "More than 30" })}
        />
        <MiniList
          title="Best Closure % (Project)"
          items={best_closure_pct}
          valueKey="closure_pct"
          valueFormat="pct"
          onItemClick={(item) => setFilter("project", item.name)}
        />
        <MiniList
          title="Worst Closure % (Project)"
          items={worst_closure_pct}
          valueKey="closure_pct"
          valueFormat="pct"
          onItemClick={(item) => setFilter("project", item.name)}
        />
        <div className="sm:col-span-2">
          <MiniList
            title="Top Categories"
            items={top_categories}
            valueKey="count"
            onItemClick={(item) => openDrilldown(`Category: ${item.name}`, { category: item.name })}
          />
        </div>
      </div>
    </SectionCard>
  );
}
