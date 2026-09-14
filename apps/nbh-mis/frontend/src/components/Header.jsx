import React from "react";
import { NavLink } from "react-router-dom";
import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { useFilters } from "../context/FilterContext.jsx";
import { useSummary } from "../context/SummaryContext.jsx";
import { exportUrl } from "../services/api.js";

const navLinkClass = ({ isActive }) =>
  `px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
    isActive ? "bg-brand-700 text-white" : "text-ink-600 hover:bg-canvas"
  }`;

export default function Header() {
  const { filters } = useFilters();
  const { summary } = useSummary();
  const meta = summary?.meta;
  const dataset = summary?.dataset;

  return (
    <header className="bg-surface border-b border-line">
      <div className="max-w-[1920px] mx-auto px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-bold text-ink-900 leading-tight">
            NBH Customer Complaint Management Dashboard
          </h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-ink-500 mt-0.5">
            {meta?.as_of && <span>Data Updated Till: <strong className="text-ink-700">{meta.as_of}</strong></span>}
            {meta?.filename && <span className="truncate max-w-[16rem]" title={meta.filename}>File: {meta.filename}</span>}
            {meta?.total_records !== undefined && <span>Total Records: {meta.total_records.toLocaleString("en-IN")}</span>}
            {dataset?.selected_records !== undefined && (
              <span>
                Selected: {dataset.selected_records.toLocaleString("en-IN")} records
                {dataset.selected_projects ? ` · ${dataset.selected_projects} project(s)` : ""}
              </span>
            )}
            {dataset?.selected_date_min && dataset?.selected_date_max && (
              <span>
                Period: {dataset.selected_date_min} to {dataset.selected_date_max}
              </span>
            )}
          </div>
        </div>

        <nav className="flex items-center gap-1">
          <NavLink to="/dashboard" className={navLinkClass}>Dashboard</NavLink>
          <NavLink to="/reports" className={navLinkClass}>Reports</NavLink>
          <NavLink to="/data-quality" className={navLinkClass}>Data Quality</NavLink>
          <NavLink to="/" end className={navLinkClass}>Upload</NavLink>
        </nav>

        <div className="flex items-center gap-2">
          <a className="btn-primary" href={exportUrl("excel", filters)} target="_blank" rel="noreferrer">
            <FileSpreadsheet className="h-4 w-4" />
            Download Excel
          </a>
          <a className="btn" href={exportUrl("pdf", filters)} target="_blank" rel="noreferrer">
            <FileText className="h-4 w-4" />
            Download PDF
          </a>
        </div>
      </div>
    </header>
  );
}
