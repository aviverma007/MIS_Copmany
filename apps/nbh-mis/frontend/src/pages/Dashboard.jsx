import React from "react";
import FilterPanel from "../components/FilterPanel.jsx";
import KPIRow from "../components/KPIRow.jsx";
import RagScorecard from "../components/RagScorecard.jsx";
import AgeingChart from "../components/AgeingChart.jsx";
import TrendChart from "../components/TrendChart.jsx";
import ManagementCategoryChart from "../components/ManagementCategoryChart.jsx";
import ProjectTable from "../components/ProjectTable.jsx";
import TopBottomPanel from "../components/TopBottomPanel.jsx";
import InsightsPanel from "../components/InsightsPanel.jsx";
import ActionTracker from "../components/ActionTracker.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";
import { useSummary } from "../context/SummaryContext.jsx";
import { useFilteredData } from "../hooks/useFilteredData.js";
import { useFilters } from "../context/FilterContext.jsx";
import { getAgeing, getTrends } from "../services/api.js";

export default function Dashboard() {
  const { filters } = useFilters();
  const { summary, loading: summaryLoading, error: summaryError } = useSummary();
  const { data: ageing, loading: ageingLoading, error: ageingError } = useFilteredData(getAgeing, filters);
  const { data: trends, loading: trendsLoading, error: trendsError } = useFilteredData(getTrends, filters);

  return (
    <div className="max-w-[1920px] mx-auto px-4 py-4 flex flex-col gap-4">
      <FilterPanel />

      {summaryLoading && <LoadingSpinner label="Loading dashboard…" />}
      {!summaryLoading && summaryError && <ErrorBanner message={summaryError} />}

      {!summaryLoading && !summaryError && summary && (
        <>
          <KPIRow kpis={summary.kpis} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RagScorecard ragScorecard={summary.rag_scorecard} />
            {ageingLoading ? <LoadingSpinner /> : ageingError ? <ErrorBanner message={ageingError} /> : <AgeingChart ageing={ageing} />}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {trendsLoading ? <LoadingSpinner /> : trendsError ? <ErrorBanner message={trendsError} /> : <TrendChart trends={trends} />}
            <ManagementCategoryChart />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
            <ProjectTable />
            <TopBottomPanel topBottom={summary.top_bottom} />
          </div>

          <InsightsPanel insights={summary.insights} />

          <ActionTracker />
        </>
      )}
    </div>
  );
}
