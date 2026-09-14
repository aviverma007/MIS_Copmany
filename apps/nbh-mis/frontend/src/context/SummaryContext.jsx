import React, { createContext, useContext } from "react";
import { getSummary } from "../services/api.js";
import { useFilters } from "./FilterContext.jsx";
import { useFilteredData } from "../hooks/useFilteredData.js";

// Single shared /api/dashboard/summary fetch (keyed on the current global
// filters) reused by the Header (meta/dataset banner) and the Executive
// Dashboard page (KPIs, RAG scorecard, insights, top/bottom), so filter
// changes don't trigger duplicate summary requests.
const SummaryContext = createContext(null);

export function SummaryProvider({ children }) {
  const { filters } = useFilters();
  const { data, loading, error } = useFilteredData(getSummary, filters);

  return <SummaryContext.Provider value={{ summary: data, loading, error }}>{children}</SummaryContext.Provider>;
}

export function useSummary() {
  const ctx = useContext(SummaryContext);
  if (!ctx) throw new Error("useSummary must be used within a SummaryProvider");
  return ctx;
}
