/* global React, ReactDOM */
(function () {
  "use strict";
  const { useState, useEffect, useCallback } = React;
  const html = window.MIS.html;
  const { fmtInt } = window.MIS.util;
  const { UploadPanel, FilterDrawer, ActiveFiltersBar, CaseDetailModal, AttentionModal } = window.MIS.sections;
  const { OverviewTab, AnalysisTab, TrendsTab, DataQualityTab, CasesTab } = window.MIS.tabs;
  const { Spinner } = window.MIS.components;
  const { AdminUnlockModal, ManageListsTab } = window.MIS.manageLists;

  const TABS = [
    { key: "overview", label: "Overview" },
    { key: "analysis", label: "Analysis" },
    { key: "trends", label: "Trends" },
    { key: "cases", label: "Case Table" },
    { key: "quality", label: "Data Quality" },
    { key: "manage-lists", label: "Manage Lists" },
  ];

  function App() {
    const [phase, setPhase] = useState("checking"); // checking | upload | ready
    const [meta, setMeta] = useState(null);
    const [filterOptions, setFilterOptions] = useState({});
    const [filters, setFilters] = useState({});
    const [dash, setDash] = useState(null);
    const [dashLoading, setDashLoading] = useState(false);
    const [tab, setTab] = useState("overview");
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [caseModal, setCaseModal] = useState(null);
    const [attnModal, setAttnModal] = useState(null);
    const [exporting, setExporting] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);
    const [showUnlock, setShowUnlock] = useState(false);

    const loadAfterData = useCallback(async () => {
      const [opts] = await Promise.all([window.MIS.api.filterOptions()]);
      setFilterOptions(opts);
      setPhase("ready");
    }, []);

    useEffect(() => {
      window.MIS.api.status().then((s) => {
        setIsAdmin(!!s.is_admin);
        if (s.loaded) { setMeta(s.meta); loadAfterData(); }
        else setPhase("upload");
      }).catch(() => setPhase("upload"));
    }, [loadAfterData]);

    const refreshDashboard = useCallback((f) => {
      setDashLoading(true);
      window.MIS.api.dashboard(f).then((d) => { setDash(d); setDashLoading(false); });
    }, []);

    useEffect(() => {
      if (phase === "ready") refreshDashboard(filters);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [phase]);

    function onUploaded(newMeta) {
      setMeta(newMeta);
      setFilters({});
      loadAfterData().then(() => refreshDashboard({}));
    }

    function applyFilters(next) { setFilters(next); refreshDashboard(next); }
    function removeValue(dim, val) {
      const next = { ...filters, [dim]: (filters[dim] || []).filter((v) => v !== val) };
      applyFilters(next);
    }
    function removeDim(...dims) {
      const next = { ...filters };
      dims.forEach((d) => delete next[d]);
      applyFilters(next);
    }
    function resetAll() { applyFilters({}); }
    function toggleFilter(dim, value) {
      if (value === undefined || value === null) return;
      const cur = filters[dim] || [];
      const next = cur.includes(String(value)) ? cur.filter((v) => v !== String(value)) : [...cur, String(value)];
      applyFilters({ ...filters, [dim]: next });
    }

    async function doExport(kind) {
      setExporting(kind);
      try {
        const map = {
          excel: ["/api/export/excel", "M3M_MIS_Report.xlsx"],
          pdf: ["/api/export/pdf", "M3M_MIS_Full_Report.pdf"],
          onepager: ["/api/export/pdf-onepager", "M3M_MIS_Executive_OnePager.pdf"],
        };
        const [path, filename] = map[kind];
        await window.MIS.api.exportFile(path, filters, filename);
      } catch (e) {
        alert("Export failed: " + e.message);
      } finally {
        setExporting(null);
      }
    }

    async function handleLock() {
      await window.MIS.api.authLock();
      setIsAdmin(false);
    }

    function handleListsChanged() {
      // Category mapping may have changed M_Category values - refresh
      // both the filter dropdowns (Project/Month/Year union) and the
      // dashboard (KPIs/reports that group by M_Category).
      window.MIS.api.filterOptions().then(setFilterOptions);
      refreshDashboard(filters);
    }

    if (phase === "checking") {
      return html`<div class="loading-wrap" style=${{ paddingTop: "120px" }}><${Spinner} /></div>`;
    }
    if (phase === "upload") {
      return html`<${UploadPanel} onUploaded=${onUploaded} />`;
    }

    const attnTotal = dash ? Object.values(dash.attention).reduce((s, v) => s + v.count, 0) : 0;

    return html`
      <div class="app-shell">
        <header class="app-header">
          <div class="brand">
            <div class="mark">M3</div>
            <div>
              <h1>M3M Customer Complaint MIS</h1>
              <div class="meta-line">
                <span>📁 ${meta.filename}</span>
                <span>🗓 ${meta.date_min || "–"} to ${meta.date_max || "–"}</span>
                <span>🏢 ${fmtInt(meta.project_count)} projects</span>
                <span>🕒 ${new Date(meta.processed_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
          <div class="header-actions">
            <button class=${`role-badge ${isAdmin ? "admin" : "viewer"}`}
              onClick=${() => (isAdmin ? handleLock() : setShowUnlock(true))}
              title=${isAdmin ? "Click to switch back to Viewer" : "Click to unlock Admin mode"}>
              ${isAdmin ? "🔓 Admin" : "🔒 Viewer"}
            </button>
            <button class="btn btn-ghost" onClick=${() => refreshDashboard(filters)} disabled=${dashLoading}>↻ Refresh</button>
            <button class="btn btn-ghost" onClick=${() => setPhase("upload")}>⇪ Upload New File</button>
            <button class="btn btn-outline" onClick=${() => doExport("excel")} disabled=${exporting}>${exporting === "excel" ? "Exporting…" : "⬇ Excel"}</button>
            <button class="btn btn-outline" onClick=${() => doExport("onepager")} disabled=${exporting}>${exporting === "onepager" ? "Exporting…" : "⬇ One-Pager"}</button>
            <button class="btn btn-primary" onClick=${() => doExport("pdf")} disabled=${exporting}>${exporting === "pdf" ? "Exporting…" : "⬇ PDF Report"}</button>
          </div>
        </header>

        <${ActiveFiltersBar} filters=${filters} onRemoveValue=${removeValue} onRemoveDim=${removeDim}
          onResetAll=${resetAll} onOpenDrawer=${() => setDrawerOpen(true)}
          recordCount=${meta.record_count} caseCount=${dash ? dash.filtered_case_count : meta.record_count} />

        <nav class="tab-bar">
          ${TABS.map((t) => html`
            <button key=${t.key} class=${`tab-btn ${tab === t.key ? "active" : ""}`} onClick=${() => setTab(t.key)}>
              ${t.label}
              ${t.key === "overview" && attnTotal > 0 ? html`<span class="tab-badge">${fmtInt(attnTotal)}</span>` : null}
            </button>
          `)}
        </nav>

        <main class="main-content">
          ${tab === "manage-lists" ? html`
            <${ManageListsTab} isAdmin=${isAdmin} onRequestUnlock=${() => setShowUnlock(true)}
              onLock=${handleLock} onListsChanged=${handleListsChanged} />
          ` : (!dash ? html`<${Spinner} />` : html`
            ${tab === "overview" ? html`<${OverviewTab} dash=${dash} onToggleFilter=${toggleFilter} onOpenAttention=${setAttnModal} />` : null}
            ${tab === "analysis" ? html`<${AnalysisTab} dash=${dash} onToggleFilter=${toggleFilter} />` : null}
            ${tab === "trends" ? html`<${TrendsTab} dash=${dash} />` : null}
            ${tab === "cases" ? html`<${CasesTab} filters=${filters} onOpenCase=${setCaseModal} />` : null}
            ${tab === "quality" ? html`<${DataQualityTab} dash=${dash} />` : null}
          `)}
        </main>

        <footer class="app-footer">M3M Customer Complaint MIS — runs locally, no data leaves this machine.</footer>

        ${drawerOpen ? html`<${FilterDrawer} filterOptions=${filterOptions} filters=${filters}
          onApply=${applyFilters} onClose=${() => setDrawerOpen(false)} />` : null}
        ${caseModal ? html`<${CaseDetailModal} caseNumber=${caseModal} onClose=${() => setCaseModal(null)} />` : null}
        ${attnModal ? html`<${AttentionModal} area=${attnModal} label=${attnModal.replace(/_/g, " ")} filters=${filters}
          onClose=${() => setAttnModal(null)} onOpenCase=${(c) => { setAttnModal(null); setCaseModal(c); }} />` : null}
        ${showUnlock ? html`<${AdminUnlockModal} onClose=${() => setShowUnlock(false)}
          onUnlocked=${() => { setIsAdmin(true); setShowUnlock(false); }} />` : null}
      </div>
    `;
  }

  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(html`<${App} />`);
})();
