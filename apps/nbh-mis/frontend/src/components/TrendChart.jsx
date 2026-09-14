import React from "react";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid,
} from "recharts";
import SectionCard from "./SectionCard.jsx";
import { formatNumber, formatPct } from "../utils/format.js";

export default function TrendChart({ trends }) {
  if (!trends) return null;
  const { rows, daily_stats } = trends;

  return (
    <SectionCard
      title="Monthly Trend"
      subtitle={
        daily_stats
          ? `Avg received/day: ${daily_stats.avg_received_per_day} · Avg closed/day: ${daily_stats.avg_closed_per_day} · Peak: ${daily_stats.peak_day} (${formatNumber(daily_stats.peak_day_count)})`
          : undefined
      }
    >
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
            <CartesianGrid stroke="#eef0f3" vertical={false} />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, name) =>
                name === "closure_pct" ? [formatPct(value), "Closure %"] : [formatNumber(value), name]
              }
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar yAxisId="left" dataKey="received" name="Received" fill="#2f5f8f" radius={[2, 2, 0, 0]} />
            <Bar yAxisId="left" dataKey="closed" name="Closed" fill="#1e8e5a" radius={[2, 2, 0, 0]} />
            <Line yAxisId="left" type="monotone" dataKey="closing_backlog" name="Closing Backlog" stroke="#c0392b" strokeWidth={2} dot={false} />
            <Line yAxisId="right" type="monotone" dataKey="closure_pct" name="Closure %" stroke="#c98a11" strokeWidth={2} dot={false} strokeDasharray="4 3" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}
