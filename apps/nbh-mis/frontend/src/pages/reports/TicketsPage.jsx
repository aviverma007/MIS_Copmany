import React from "react";
import SectionCard from "../../components/SectionCard.jsx";
import TicketsTable from "../../components/TicketsTable.jsx";
import { useFilters } from "../../context/FilterContext.jsx";

export default function TicketsPage() {
  const { filters } = useFilters();

  return (
    <SectionCard title="Ticket Drill-Down" subtitle="Every global filter applies here too. Click a Ticket ID to view full details and timeline.">
      <TicketsTable filters={filters} pageSize={50} />
    </SectionCard>
  );
}
