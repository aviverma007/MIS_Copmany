import axios from "axios";
import { publishError, publishUnauthenticated } from "../utils/errorBus.js";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

client.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status;
    const detail = error?.response?.data?.detail;
    if (status === 409) {
      // No dataset uploaded yet -- app-wide signal to show the Upload screen.
      publishUnauthenticated(detail || "No dataset has been uploaded yet.");
    } else if (status >= 500) {
      publishError(detail || "An unexpected error occurred. Please try again.");
    }
    return Promise.reject(error);
  }
);

/**
 * Build a query string from the shared filter-state object, dropping any
 * dimension that is unset or "ALL" (meaning "no filter" per the backend
 * contract). Pure serialization helper -- no business rules live here.
 */
export function buildQueryParams(filters = {}, extra = {}) {
  const merged = { ...filters, ...extra };
  const params = new URLSearchParams();
  Object.entries(merged).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === "string" && (value === "" || value.toUpperCase() === "ALL")) return;
    params.set(key, value);
  });
  return params;
}

export function exportUrl(kind, filters = {}, extra = {}) {
  const qs = buildQueryParams(filters, extra).toString();
  return `${API_BASE_URL}/api/export/${kind}${qs ? `?${qs}` : ""}`;
}

export function templateDownloadUrl() {
  return `${API_BASE_URL}/api/upload/template`;
}

// ---------------------------------------------------------------------------
// Upload & setup
// ---------------------------------------------------------------------------
export async function uploadFile(file, onUploadProgress) {
  const form = new FormData();
  form.append("file", file);
  const res = await client.post("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return res.data;
}

export async function getDataQuality() {
  const res = await client.get("/api/data-quality");
  return res.data;
}

// ---------------------------------------------------------------------------
// Master data
// ---------------------------------------------------------------------------
const MASTER_ENDPOINTS = {
  projects: "/api/master/projects",
  categories: "/api/master/categories",
  managementCategories: "/api/master/management-categories",
  assignees: "/api/master/assignees",
  statuses: "/api/master/statuses",
  sources: "/api/master/sources",
  priorities: "/api/master/priorities",
  ageingSlabs: "/api/master/ageing-slabs",
  years: "/api/master/years",
};

export async function getAllMasterData() {
  const entries = Object.entries(MASTER_ENDPOINTS);
  const [results, escalationRes] = await Promise.all([
    Promise.all(entries.map(([, path]) => client.get(path))),
    // There is no dedicated master endpoint for escalation levels, so derive
    // the distinct set from the (unfiltered) escalation-wise report instead
    // of hardcoding a range in the UI.
    client.get(`/api/reports/escalation-wise`),
  ]);
  const out = {};
  entries.forEach(([key], i) => {
    const data = results[i].data;
    // Each endpoint returns { <key>: [...] } -- flatten to the array.
    const arrVal = Object.values(data)[0];
    out[key] = arrVal;
  });
  const levels = (escalationRes.data?.rows || [])
    .map((r) => r.escalation_level)
    .sort((a, b) => a - b);
  out.escalationLevels = ["ALL", ...levels];
  return out;
}

// ---------------------------------------------------------------------------
// Executive dashboard
// ---------------------------------------------------------------------------
export async function getSummary(filters) {
  const res = await client.get(`/api/dashboard/summary?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getAgeing(filters) {
  const res = await client.get(`/api/dashboard/ageing?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getTrends(filters) {
  const res = await client.get(`/api/dashboard/trends?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getInsights(filters) {
  const res = await client.get(`/api/dashboard/insights?${buildQueryParams(filters)}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Detail reports
// ---------------------------------------------------------------------------
export async function getOpenCases(filters) {
  const res = await client.get(`/api/reports/open-cases?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getProjectWise(filters) {
  const res = await client.get(`/api/reports/project-wise?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getCategoryWise(filters) {
  const res = await client.get(`/api/reports/category-wise?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getManagementCategoryWise(filters) {
  const res = await client.get(`/api/reports/management-category-wise?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getAssigneeWise(filters) {
  const res = await client.get(`/api/reports/assignee-wise?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getPriorityWise(filters) {
  const res = await client.get(`/api/reports/priority-wise?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getEscalationWise(filters) {
  const res = await client.get(`/api/reports/escalation-wise?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getSourceWise(filters) {
  const res = await client.get(`/api/reports/source-wise?${buildQueryParams(filters)}`);
  return res.data;
}

export async function getRating(filters) {
  const res = await client.get(`/api/reports/rating?${buildQueryParams(filters)}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Ticket-level drill-down
// ---------------------------------------------------------------------------
export async function getTickets(filters, { page = 1, pageSize = 50, sortBy = "ageing_days", sortDir = "desc" } = {}) {
  const params = buildQueryParams(filters, {
    page,
    page_size: pageSize,
    sort_by: sortBy,
    sort_dir: sortDir,
  });
  const res = await client.get(`/api/tickets?${params}`);
  return res.data;
}

export async function getTicketDetail(ticketId) {
  const res = await client.get(`/api/tickets/${encodeURIComponent(ticketId)}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Management Action Tracker
// ---------------------------------------------------------------------------
export async function listActions() {
  const res = await client.get("/api/actions");
  return res.data.actions;
}

export async function createAction(payload) {
  const res = await client.post("/api/actions", payload);
  return res.data;
}

export async function updateAction(id, payload) {
  const res = await client.put(`/api/actions/${id}`, payload);
  return res.data;
}

export async function deleteAction(id) {
  const res = await client.delete(`/api/actions/${id}`);
  return res.data;
}
