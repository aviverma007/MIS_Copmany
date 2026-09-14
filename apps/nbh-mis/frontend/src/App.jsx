import React, { useEffect } from "react";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";

import { FilterProvider } from "./context/FilterContext.jsx";
import { MasterDataProvider } from "./context/MasterDataContext.jsx";
import { RagColorsProvider } from "./context/RagColorsContext.jsx";
import { DrilldownProvider } from "./context/DrilldownContext.jsx";
import { TicketDetailProvider } from "./context/TicketDetailContext.jsx";
import { SummaryProvider } from "./context/SummaryContext.jsx";

import Header from "./components/Header.jsx";
import ToastHost from "./components/ToastHost.jsx";
import DrillDownModal from "./components/DrillDownModal.jsx";
import TicketDetailModal from "./components/TicketDetailModal.jsx";

import Upload from "./pages/Upload.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Reports from "./pages/Reports.jsx";
import DataQuality from "./pages/DataQuality.jsx";

import OpenCases from "./pages/reports/OpenCases.jsx";
import ProjectWise from "./pages/reports/ProjectWise.jsx";
import CategoryWise from "./pages/reports/CategoryWise.jsx";
import AssigneeWise from "./pages/reports/AssigneeWise.jsx";
import PriorityWise from "./pages/reports/PriorityWise.jsx";
import EscalationWise from "./pages/reports/EscalationWise.jsx";
import SourceWise from "./pages/reports/SourceWise.jsx";
import Rating from "./pages/reports/Rating.jsx";
import TicketsPage from "./pages/reports/TicketsPage.jsx";

import { onUnauthenticated } from "./utils/errorBus.js";

function UnauthenticatedWatcher() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    return onUnauthenticated(() => {
      if (location.pathname !== "/") {
        navigate("/", { replace: true });
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  return null;
}

function AppLayout({ children }) {
  return (
    <SummaryProvider>
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
      </div>
    </SummaryProvider>
  );
}

export default function App() {
  return (
    <FilterProvider>
      <MasterDataProvider>
        <RagColorsProvider>
          <DrilldownProvider>
            <TicketDetailProvider>
              <UnauthenticatedWatcher />
              <ToastHost />
              <DrillDownModal />
              <TicketDetailModal />
              <Routes>
                <Route path="/" element={<Upload />} />
                <Route
                  path="/dashboard"
                  element={
                    <AppLayout>
                      <Dashboard />
                    </AppLayout>
                  }
                />
                <Route
                  path="/data-quality"
                  element={
                    <AppLayout>
                      <DataQuality />
                    </AppLayout>
                  }
                />
                <Route
                  path="/reports"
                  element={
                    <AppLayout>
                      <Reports />
                    </AppLayout>
                  }
                >
                  <Route index element={<Navigate to="open-cases" replace />} />
                  <Route path="open-cases" element={<OpenCases />} />
                  <Route path="projects" element={<ProjectWise />} />
                  <Route path="categories" element={<CategoryWise />} />
                  <Route path="assignees" element={<AssigneeWise />} />
                  <Route path="priority" element={<PriorityWise />} />
                  <Route path="escalation" element={<EscalationWise />} />
                  <Route path="source" element={<SourceWise />} />
                  <Route path="rating" element={<Rating />} />
                  <Route path="tickets" element={<TicketsPage />} />
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </TicketDetailProvider>
          </DrilldownProvider>
        </RagColorsProvider>
      </MasterDataProvider>
    </FilterProvider>
  );
}
