/* global htm, React */
(function () {
  "use strict";
  window.MIS = window.MIS || {};
  const html = htm.bind(React.createElement);
  MIS.html = html;
  MIS.h = React.createElement;

  // ---------------- formatting ----------------
  const fmtInt = (n) => (n === null || n === undefined || Number.isNaN(n)) ? "–" : Number(n).toLocaleString("en-IN");
  const fmtPct = (n) => (n === null || n === undefined || Number.isNaN(n)) ? "–" : `${n}%`;
  const fmtNum1 = (n) => (n === null || n === undefined || Number.isNaN(n)) ? "–" : Number(n).toFixed(1);
  const fmtDays = (n) => (n === null || n === undefined || Number.isNaN(n)) ? "–" : `${Number(n).toFixed(1)}d`;
  const titleCase = (s) => (s || "").toString().replace(/_/g, " ").replace(/\w\S*/g, (t) => t[0].toUpperCase() + t.slice(1));

  const FIELD_LABELS = {
    case_number: "Case Number", account_name: "Account Name", subject: "Subject",
    priority: "Priority", m_category: "M_Category", service_category: "Service Category",
    opened_date: "Opened Date", closed_date: "Closed Date", case_owner: "Case Owner",
    case_type: "Case Type", case_status: "Case Status", sub_category: "Sub Category",
    case_source: "Case Source", case_origin: "Case Origin", case_ageing: "Case Ageing",
    escalation: "Escalation", escalated_label: "Escalation", project_name: "Project Name",
    project_unit: "Project Unit", team_leader: "Team Leader", hod: "HOD",
    client_category: "Client Category", updated_status: "Updated Status", tat_days: "TAT Days",
    slab: "SLAB", ia_status: "IA Status", ia_remarks: "IA Remarks",
    year: "Year", month_name: "Month",
    received_bucket: "Received Today?", closed_bucket: "Closed Same Day?",
  };

  const FILTER_DIM_ORDER = [
    "project_name", "case_status", "updated_status", "priority", "service_category",
    "m_category", "sub_category", "case_owner", "team_leader", "hod", "client_category",
    "case_source", "case_type", "escalated_label", "slab", "ia_status", "year", "month_name",
    "received_bucket", "closed_bucket",
  ];

  MIS.util = { fmtInt, fmtPct, fmtNum1, fmtDays, titleCase, FIELD_LABELS, FILTER_DIM_ORDER };

  // ---------------- API ----------------
  const API_BASE = "";
  async function apiFetch(path, opts) {
    const res = await fetch(API_BASE + path, opts);
    if (!res.ok) {
      let detail = res.statusText;
      try { const j = await res.json(); detail = j.detail || detail; } catch (e) {}
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return res;
  }
  const api = {
    async status() { return (await apiFetch("/api/status")).json(); },
    async upload(file, onProgress) {
      const form = new FormData();
      form.append("file", file);
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload");
        xhr.upload.onprogress = (e) => { if (onProgress && e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100)); };
        xhr.onload = () => {
          try {
            const body = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) resolve(body);
            else reject(new Error(body.detail || "Upload failed"));
          } catch (e) { reject(new Error("Upload failed")); }
        };
        xhr.onerror = () => reject(new Error("Network error during upload"));
        xhr.send(form);
      });
    },
    async filterOptions() { return (await apiFetch("/api/filters/options")).json(); },
    async dashboard(filters) {
      return (await apiFetch("/api/dashboard", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filters }),
      })).json();
    },
    async attentionDetail(area, filters) {
      return (await apiFetch(`/api/attention/${area}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filters }),
      })).json();
    },
    async table(payload) {
      return (await apiFetch("/api/table", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })).json();
    },
    async caseDetail(caseNumber) {
      return (await apiFetch(`/api/case/${encodeURIComponent(caseNumber)}`)).json();
    },
    async exportFile(path, filters, filename) {
      const res = await apiFetch(path, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filters }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    // ---- auth (lightweight local admin gate for Manage Lists) ----
    async authStatus() { return (await apiFetch("/api/auth/status")).json(); },
    async authUnlock(passcode) {
      return (await apiFetch("/api/auth/unlock", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passcode }),
      })).json();
    },
    async authLock() { return (await apiFetch("/api/auth/lock", { method: "POST" })).json(); },
    // ---- LIST management (Project/Month/Year dropdowns + Category mapping) ----
    async getLists() { return (await apiFetch("/api/lists")).json(); },
    async updateLists(payload) {
      return (await apiFetch("/api/lists/update", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })).json();
    },
    async uploadList(file) {
      const form = new FormData();
      form.append("file", file);
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/lists/upload");
        xhr.onload = () => {
          try {
            const body = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) resolve(body);
            else reject(new Error(body.detail || "Upload failed"));
          } catch (e) { reject(new Error("Upload failed")); }
        };
        xhr.onerror = () => reject(new Error("Network error during upload"));
        xhr.send(form);
      });
    },
  };
  MIS.api = api;
})();
