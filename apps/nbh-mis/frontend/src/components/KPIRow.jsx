import React from "react";
import KPICard from "./KPICard.jsx";

export default function KPIRow({ kpis }) {
  if (!kpis) return null;
  const entries = Object.entries(kpis);
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
      {entries.map(([id, kpi]) => (
        <KPICard key={id} id={id} kpi={kpi} />
      ))}
    </div>
  );
}
