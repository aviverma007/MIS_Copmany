import React from "react";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import SectionCard from "./SectionCard.jsx";

const SEVERITY_STYLE = {
  high: { icon: AlertTriangle, cls: "border-red-200 bg-red-50 text-red-800" },
  medium: { icon: AlertCircle, cls: "border-amber-200 bg-amber-50 text-amber-800" },
  low: { icon: Info, cls: "border-blue-200 bg-blue-50 text-blue-800" },
};

export default function InsightsPanel({ insights }) {
  return (
    <SectionCard title="Management Attention Required">
      {!insights || insights.length === 0 ? (
        <p className="text-xs text-ink-400">No notable issues flagged for the current filter selection.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {insights.map((item, i) => {
            const style = SEVERITY_STYLE[item.severity] || SEVERITY_STYLE.low;
            const Icon = style.icon;
            return (
              <li key={i} className={`flex items-start gap-2 rounded-md border px-3 py-2 text-xs ${style.cls}`}>
                <Icon className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                <span>{item.message}</span>
              </li>
            );
          })}
        </ul>
      )}
    </SectionCard>
  );
}
