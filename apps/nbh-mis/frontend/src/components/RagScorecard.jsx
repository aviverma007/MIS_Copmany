import React from "react";
import SectionCard from "./SectionCard.jsx";
import { RagDot } from "./RAGIndicator.jsx";
import { formatNumber, formatPct } from "../utils/format.js";

export default function RagScorecard({ ragScorecard }) {
  if (!ragScorecard) return null;
  const { rows, total_open } = ragScorecard;

  return (
    <SectionCard title="RAG Management Scorecard" subtitle={`Total Open: ${formatNumber(total_open)}`}>
      <div className="flex flex-col gap-2">
        {rows.map((row) => (
          <div key={row.rag} className="w-full">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="flex items-center gap-1.5 font-semibold uppercase tracking-wide text-ink-600">
                <RagDot rag={row.rag} size={9} />
                {row.rag}
              </span>
              <span className="text-ink-700">
                {formatNumber(row.count)} <span className="text-ink-400">({formatPct(row.pct)})</span>
              </span>
            </div>
            <div className="h-2 rounded-full bg-canvas overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${Math.max(row.pct, row.count > 0 ? 2 : 0)}%`, backgroundColor: row.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
