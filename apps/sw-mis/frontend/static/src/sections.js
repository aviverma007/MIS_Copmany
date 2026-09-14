/* global React */
(function () {
  "use strict";
  const { useState, useMemo, useRef } = React;
  const html = window.MIS.html;
  const { fmtInt, fmtPct, fmtNum1, FIELD_LABELS, FILTER_DIM_ORDER } = window.MIS.util;
  const { Chip, Modal, Spinner } = window.MIS.components;

  // ---------------- Filter drawer ----------------
  function FilterBlock({ dim, options, selected, onChange }) {
    const [open, setOpen] = useState(selected.length > 0);
    const [search, setSearch] = useState("");
    const filtered = useMemo(() => {
      if (!search.trim()) return options;
      const s = search.toLowerCase();
      return options.filter((o) => String(o).toLowerCase().includes(s));
    }, [options, search]);
    const selectedSet = new Set(selected);
    function toggle(opt) {
      const s = String(opt);
      const next = selectedSet.has(s) ? selected.filter((x) => x !== s) : [...selected, s];
      onChange(next);
    }
    function selectAll() {
      const merged = new Set([...selected, ...filtered.map(String)]);
      onChange([...merged]);
    }
    function clearAll() { onChange([]); }
    if (!options || options.length === 0) return null;
    return html`
      <div class="filter-block">
        <div class="filter-block-head" onClick=${() => setOpen(!open)}>
          <span class="name">${FIELD_LABELS[dim] || dim} ${open ? "▾" : "▸"}</span>
          <span class="count">${selected.length > 0 ? `${selected.length} selected` : ""}</span>
        </div>
        ${open ? html`
          <div class="filter-block-body">
            ${options.length > 6 ? html`<input class="filter-search" placeholder="Search ${(FIELD_LABELS[dim] || dim).toLowerCase()}..." value=${search} onInput=${(e) => setSearch(e.target.value)} />` : null}
            <div class="filter-actions">
              <button onClick=${selectAll}>Select All</button>
              <button onClick=${clearAll}>Clear All</button>
            </div>
            <div class="filter-options">
              ${filtered.map((opt) => html`
                <div class="filter-opt" key=${opt}>
                  <input type="checkbox" id=${`f-${dim}-${opt}`} checked=${selectedSet.has(String(opt))} onChange=${() => toggle(opt)} />
                  <label for=${`f-${dim}-${opt}`}>${String(opt)}</label>
                </div>
              `)}
            </div>
          </div>
        ` : null}
      </div>
    `;
  }

  function FilterDrawer({ filterOptions, filters, onApply, onClose }) {
    const [draft, setDraft] = useState(filters);
    function setDim(dim, values) { setDraft((d) => ({ ...d, [dim]: values })); }
    function resetAll() { setDraft({}); onApply({}); onClose(); }
    function apply() { onApply(draft); onClose(); }
    const activeCount = Object.entries(draft).filter(([k, v]) => k !== "date_from" && k !== "date_to" && v && v.length).length
      + ((draft.date_from || draft.date_to) ? 1 : 0);
    return html`
      <div class="overlay" onClick=${onClose}></div>
      <div class="drawer">
        <div class="drawer-header">
          <h2>Filters ${activeCount ? `(${activeCount} active)` : ""}</h2>
          <button class="close-x" onClick=${onClose}>×</button>
        </div>
        <div class="drawer-body">
          <div class="filter-block">
            <div class="filter-block-head"><span class="name">Date Range (Opened Date)</span></div>
            <div class="filter-block-body" style=${{ paddingTop: "10px" }}>
              <div class="date-range-row">
                <input type="date" value=${draft.date_from || ""} onChange=${(e) => setDraft((d) => ({ ...d, date_from: e.target.value }))} />
                <input type="date" value=${draft.date_to || ""} onChange=${(e) => setDraft((d) => ({ ...d, date_to: e.target.value }))} />
              </div>
            </div>
          </div>
          ${FILTER_DIM_ORDER.map((dim) => html`
            <${FilterBlock} key=${dim} dim=${dim} options=${filterOptions[dim] || []}
              selected=${draft[dim] || []} onChange=${(v) => setDim(dim, v)} />
          `)}
        </div>
        <div class="drawer-footer">
          <button class="btn btn-outline" onClick=${resetAll}>Reset All Filters</button>
          <button class="btn btn-primary" onClick=${apply}>Apply Filters</button>
        </div>
      </div>
    `;
  }

  function ActiveFiltersBar({ filters, onRemoveValue, onRemoveDim, onResetAll, onOpenDrawer, recordCount, caseCount }) {
    const chips = [];
    Object.entries(filters).forEach(([dim, vals]) => {
      if (dim === "date_from" || dim === "date_to") return;
      (vals || []).forEach((v) => chips.push({ dim, v }));
    });
    const hasDate = filters.date_from || filters.date_to;
    return html`
      <div class="active-filters-bar">
        <button class="btn btn-outline btn-sm" onClick=${onOpenDrawer}>⚙ Filters</button>
        ${chips.length === 0 && !hasDate ? html`<span class="text-muted" style=${{ fontSize: "12px" }}>No filters applied — showing full dataset</span>` : null}
        ${chips.map((c) => html`
          <${Chip} key=${`${c.dim}:${c.v}`} text=${`${FIELD_LABELS[c.dim] || c.dim}: ${c.v}`} onRemove=${() => onRemoveValue(c.dim, c.v)} />
        `)}
        ${hasDate ? html`<${Chip} text=${`Date: ${filters.date_from || "…"} → ${filters.date_to || "…"}`} onRemove=${() => onRemoveDim("date_from", "date_to")} />` : null}
        ${(chips.length > 0 || hasDate) ? html`<button class="btn btn-outline btn-sm" onClick=${onResetAll}>Reset All</button>` : null}
        <span style=${{ marginLeft: "auto", fontSize: "11.5px" }} class="text-muted">
          ${fmtInt(caseCount)} of ${fmtInt(recordCount)} cases shown
        </span>
      </div>
    `;
  }

  // ---------------- Upload panel ----------------
  function UploadPanel({ onUploaded }) {
    const [drag, setDrag] = useState(false);
    const [progress, setProgress] = useState(null);
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    const inputRef = useRef(null);

    async function handleFile(file) {
      if (!file) return;
      setError(null); setBusy(true); setProgress(0);
      try {
        const result = await window.MIS.api.upload(file, setProgress);
        onUploaded(result.meta);
      } catch (e) {
        setError(e.message || "Upload failed.");
      } finally {
        setBusy(false); setProgress(null);
      }
    }
    return html`
      <div class="upload-screen">
        <div class="upload-card">
          <div class="dropzone ${drag ? "drag" : ""}"
            onDragOver=${(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave=${() => setDrag(false)}
            onDrop=${(e) => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]); }}
            onClick=${() => inputRef.current && inputRef.current.click()}>
            <div class="icon">📊</div>
            <h3>Smartworld Customer Complaint MIS</h3>
            <p>${busy ? `Uploading… ${progress !== null ? progress + "%" : ""}` : "Drop your Smartworld workbook here, or click to browse (.xlsx / .xls)"}</p>
            <input ref=${inputRef} type="file" accept=".xlsx,.xls" style=${{ display: "none" }}
              onChange=${(e) => handleFile(e.target.files[0])} />
          </div>
          ${error ? html`<div class="upload-error"><strong>Upload failed.</strong> ${error}</div>` : null}
          <p class="text-muted" style=${{ fontSize: "11.5px", marginTop: "14px" }}>
            The workbook must contain a "Compile SW Data" sheet — this is treated as the single source of truth. All KPIs, reports, and charts are computed dynamically from it.
          </p>
        </div>
      </div>
    `;
  }

  // ---------------- Report table (sortable) ----------------
  function ReportTable({ rows, onRowClick, dimLabel }) {
    const [sortKey, setSortKey] = useState("total");
    const [sortDir, setSortDir] = useState("desc");
    const cols = [
      { key: "name", label: dimLabel || "Name" }, { key: "total", label: "Total" },
      { key: "closed", label: "Closed" }, { key: "open", label: "Open" },
      { key: "escalated", label: "Escalated" }, { key: "resolution_pct", label: "Resolution %" },
      { key: "avg_tat", label: "Avg TAT" }, { key: "sla_breach_pct", label: "SLA Breach %" },
    ];
    const sorted = useMemo(() => {
      const copy = [...rows];
      copy.sort((a, b) => {
        const av = a[sortKey], bv = b[sortKey];
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        if (typeof av === "string") return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
        return sortDir === "asc" ? av - bv : bv - av;
      });
      return copy;
    }, [rows, sortKey, sortDir]);
    function headerClick(key) {
      if (key === sortKey) setSortDir(sortDir === "asc" ? "desc" : "asc");
      else { setSortKey(key); setSortDir("desc"); }
    }
    if (!rows || rows.length === 0) return html`<div class="empty-state">No data for the current filters.</div>`;
    return html`
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              ${cols.map((c) => html`
                <th key=${c.key} class=${sortKey === c.key ? `sorted ${sortDir}` : ""} onClick=${() => headerClick(c.key)}>${c.label}</th>
              `)}
            </tr>
          </thead>
          <tbody>
            ${sorted.map((r) => html`
              <tr key=${r.name} class=${onRowClick ? "clickable" : ""} onClick=${() => onRowClick && onRowClick(r.name)}>
                <td>${r.name}</td><td>${fmtInt(r.total)}</td><td>${fmtInt(r.closed)}</td>
                <td>${fmtInt(r.open)}</td><td>${fmtInt(r.escalated)}</td>
                <td>${fmtPct(r.resolution_pct)}</td><td>${r.avg_tat !== null ? fmtNum1(r.avg_tat) : "–"}</td>
                <td>${r.sla_breach_pct !== null ? fmtPct(r.sla_breach_pct) : "–"}</td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    `;
  }

  // ---------------- Case detail modal ----------------
  function CaseDetailModal({ caseNumber, onClose }) {
    const [data, setData] = useState(null);
    const [err, setErr] = useState(null);
    React.useEffect(() => {
      let cancelled = false;
      window.MIS.api.caseDetail(caseNumber).then((d) => { if (!cancelled) setData(d); })
        .catch((e) => { if (!cancelled) setErr(e.message); });
      return () => { cancelled = true; };
    }, [caseNumber]);
    const groups = [
      { title: "Customer", fields: ["account_name", "subject", "priority", "case_source", "case_origin"] },
      { title: "Case", fields: ["case_number", "case_status", "updated_status", "case_type", "sub_category", "escalated_label"] },
      { title: "Timeline", fields: ["opened_date", "closed_date", "case_ageing", "tat_days", "slab", "received_bucket", "closed_bucket"] },
      { title: "Ownership", fields: ["case_owner", "team_leader", "hod", "client_category"] },
      { title: "Classification", fields: ["project_name", "project_unit", "service_category", "area", "sub_area", "m_category"] },
      { title: "Internal Audit", fields: ["ia_status", "ia_remarks"] },
    ];
    return html`
      <${Modal} title=${`Case ${caseNumber}`} onClose=${onClose} wide=${true}>
        ${err ? html`<div class="upload-error">${err}</div>` : null}
        ${!data && !err ? html`<${Spinner} />` : null}
        ${data ? groups.map((g) => html`
          <div key=${g.title}>
            <div class="detail-section-title">${g.title}</div>
            <div class="detail-grid">
              ${g.fields.filter((f) => f in data.case).map((f) => html`
                <div class="detail-field" key=${f}>
                  <div class="k">${FIELD_LABELS[f] || f}</div>
                  <div class="v">${data.case[f] === null || data.case[f] === undefined || data.case[f] === "" ? "–" : String(data.case[f])}</div>
                </div>
              `)}
            </div>
          </div>
        `) : null}
      </${Modal}>
    `;
  }

  // ---------------- Attention detail modal ----------------
  function AttentionModal({ area, label, filters, onClose, onOpenCase }) {
    const [data, setData] = useState(null);
    React.useEffect(() => {
      let cancelled = false;
      window.MIS.api.attentionDetail(area, filters).then((d) => { if (!cancelled) setData(d); });
      return () => { cancelled = true; };
    }, [area, JSON.stringify(filters)]);
    return html`
      <${Modal} title=${`${label} (${data ? fmtInt(data.count) : "…"})`} onClose=${onClose} wide=${true}>
        ${!data ? html`<${Spinner} />` : (
          data.cases.length === 0 ? html`<div class="empty-state">No cases in this category — nice and clean.</div>` : html`
            <div class="table-wrap">
              <table class="data-table">
                <thead><tr><th>Case Number</th><th>Account</th><th>Project</th><th>Owner</th><th>Status</th><th>Ageing</th></tr></thead>
                <tbody>
                  ${data.cases.slice(0, 200).map((c) => html`
                    <tr key=${c.case_number} class="clickable" onClick=${() => onOpenCase(c.case_number)}>
                      <td><span class="case-link">${c.case_number}</span></td>
                      <td>${c.account_name || "–"}</td><td>${c.project_name || "–"}</td>
                      <td>${c.case_owner || "–"}</td><td>${c.case_status || "–"}</td>
                      <td>${c.case_ageing !== undefined && c.case_ageing !== null ? c.case_ageing : "–"}</td>
                    </tr>
                  `)}
                </tbody>
              </table>
            </div>
          `
        )}
      </${Modal}>
    `;
  }

  window.MIS.sections = { FilterDrawer, ActiveFiltersBar, UploadPanel, ReportTable, CaseDetailModal, AttentionModal };
})();
