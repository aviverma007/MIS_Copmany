import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import FilterPanel from "../components/FilterPanel.jsx";

const TABS = [
  { to: "open-cases", label: "Open Cases" },
  { to: "projects", label: "Project Wise" },
  { to: "categories", label: "Category Wise" },
  { to: "assignees", label: "Assignee Performance" },
  { to: "priority", label: "Priority Dashboard" },
  { to: "escalation", label: "Escalation Dashboard" },
  { to: "source", label: "Source Analysis" },
  { to: "rating", label: "Customer Experience" },
  { to: "tickets", label: "Ticket Drill-Down" },
];

const tabClass = ({ isActive }) =>
  `px-3 py-1.5 text-xs font-semibold rounded-md whitespace-nowrap transition-colors ${
    isActive ? "bg-brand-700 text-white" : "text-ink-600 hover:bg-canvas border border-line"
  }`;

export default function Reports() {
  return (
    <div className="max-w-[1920px] mx-auto px-4 py-4 flex flex-col gap-4">
      <FilterPanel />
      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {TABS.map((tab) => (
          <NavLink key={tab.to} to={tab.to} className={tabClass}>
            {tab.label}
          </NavLink>
        ))}
      </div>
      <Outlet />
    </div>
  );
}
