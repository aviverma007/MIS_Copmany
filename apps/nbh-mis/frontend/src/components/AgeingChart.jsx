import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from "recharts";
import SectionCard from "./SectionCard.jsx";
import { formatNumber, formatPct } from "../utils/format.js";
import { useDrilldown } from "../context/DrilldownContext.jsx";

export default function AgeingChart({ ageing }) {
  const { openDrilldown } = useDrilldown();
  if (!ageing) return null;
  const { rows, total_open } = ageing;

  return (
    <SectionCard title="Ageing Distribution (Open Cases)" subtitle={`Total Open: ${formatNumber(total_open)}`}>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
            <XAxis type="number" hide />
            <YAxis dataKey="slab" type="category" width={90} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, name, props) => [`${formatNumber(value)} (${formatPct(props.payload.pct)})`, "Count"]}
            />
            <Bar
              dataKey="count"
              radius={[0, 3, 3, 0]}
              cursor="pointer"
              onClick={(d) => d?.slab && openDrilldown(`Ageing Slab: ${d.slab}`, { ageing_slab: d.slab })}
            >
              {rows.map((row) => (
                <Cell key={row.slab} fill={row.is_critical_bucket ? "#c0392b" : "#2f5f8f"} fillOpacity={row.is_critical_bucket ? 1 : 0.75} />
              ))}
              <LabelList dataKey="count" position="right" style={{ fontSize: 11, fill: "#374151" }} formatter={(v) => formatNumber(v)} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="table-scroll mt-2">
        <table className="mis-table text-xs">
          <thead>
            <tr>
              <th>Ageing Slab</th>
              <th className="text-right">Count</th>
              <th className="text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.slab}
                className={`cursor-pointer ${row.is_critical_bucket ? "bg-red-50/60" : ""}`}
                onClick={() => openDrilldown(`Ageing Slab: ${row.slab}`, { ageing_slab: row.slab })}
              >
                <td className={row.is_critical_bucket ? "font-semibold text-red-700" : ""}>{row.slab}</td>
                <td className="text-right">{formatNumber(row.count)}</td>
                <td className="text-right">{formatPct(row.pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
