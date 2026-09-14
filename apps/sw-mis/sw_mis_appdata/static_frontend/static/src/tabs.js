/* global React */
(function () {
  "use strict";
  const { useState, useEffect, useMemo } = React;
  const html = window.MIS.html;
  const { fmtInt, fmtPct, fmtNum1, fmtDays, titleCase, FIELD_LABELS } = window.MIS.util;
  const { KpiCard, ChartCanvas, ChartCard, RankList, EmptyState, Spinner, AttentionCard } = window.MIS.components;
  const { ReportTable } = window.MIS.sections;

  const PALETTE = ["#1F3864", "#0F9B8E", "#F0A202", "#C62828", "#6C5CE7", "#00A8CC", "#8D6E63", "#5D8AA8", "#B67B00", "#2E7D32", "#9C27B0", "#607D8B"];

  function barData(labels, values, color) {
    return { labels, datasets: [{ data: values, backgroundColor: color || PALETTE[0], borderRadius: 4, maxBarThickness: 26 }] };
  }
  function multiLineData(labels, series) {
    return {
      labels,
      datasets: series.map((s, i) => ({
        label: s.label, data: s.data, borderColor: PALETTE[i % PALETTE.length],
        backgroundColor: PALETTE[i % PALETTE.length], tension: 0.3, pointRadius: 0, borderWidth: 2,
      })),
    };
  }
  function doughnutData(labels, values) {
    return { labels, datasets: [{ data: values, backgroundColor: PALETTE, borderWidth: 1, borderColor: "#fff" }] };
  }

  // ---------------- Overview ----------------
  function OverviewTab({ dash, onToggleFilter, onOpenAttention }) {
    const k = dash.kpis;
    const proj = dash.reports.project.slice(0, 10);
    // Whichever category field actually carries data for this workbook -
    // Service Category (the original field) or Area (Smartworld's export
    // leaves Service Category blank and categorizes via Area instead).
    const catField = dash.reports.service_category.length ? "service_category" : "area";
    const catLabel = catField === "area" ? "Area" : "Service Category";
    const cat = dash.reports[catField].slice(0, 8);
    const slab = dash.reports.slab;
    const daily = dash.daily_trend;
    const attn = dash.attention;
    const attnEntries = Object.entries(attn).sort((a, b) => b[1].count - a[1].count).slice(0, 6);

    return html`
      <div>
        <div class="section-title">Key Performance Indicators</div>
        <div class="grid grid-kpi">
          <${KpiCard} label="Total Cases" value=${k.total_cases} />
          <${KpiCard} label="Open Cases" value=${k.open_cases} />
          <${KpiCard} label="Closed Cases" value=${k.closed_cases} />
          <${KpiCard} label="Pending Cases" value=${k.pending_cases} />
          <${KpiCard} label="New Cases" value=${k.new_cases} />
          <${KpiCard} label="Resolved Cases" value=${k.resolved_cases} />
          <${KpiCard} label="Escalated Cases" value=${k.escalated_cases} />
          <${KpiCard} label="Avg Case Age" value=${k.avg_case_age} format="days" />
          <${KpiCard} label="Avg TAT" value=${k.avg_tat} format="days" />
          <${KpiCard} label="SLA Breach %" value=${k.sla_breach_pct} format="pct" rag=${k.rag.sla_breach_pct} />
          <${KpiCard} label="Resolution %" value=${k.resolution_pct} format="pct" rag=${k.rag.resolution_pct} />
          <${KpiCard} label="Closure %" value=${k.closure_pct} format="pct" rag=${k.rag.closure_pct} />
        </div>

        <div class="section-title">Trends & Distribution <span class="hint">click a bar to filter the dashboard</span></div>
        <div class="grid grid-2">
          <${ChartCard} title="Received vs Resolved vs Pending" sub="daily">
            <${ChartCanvas} type="line" height="270px"
              data=${multiLineData(daily.map((d) => d.date.slice(5)), [
                { label: "Received", data: daily.map((d) => d.today_received) },
                { label: "Resolved", data: daily.map((d) => d.total_resolved) },
                { label: "Pending", data: daily.map((d) => d.total_pending) },
              ])} />
          <//>
          <${ChartCard} title="Top Projects by Volume" sub="click to filter">
            <${ChartCanvas} type="bar" height="270px"
              data=${barData(proj.map((p) => p.name), proj.map((p) => p.total), "#1F3864")}
              options=${{ indexAxis: "y", scales: { x: { ticks: { font: { size: 9 } } }, y: { ticks: { font: { size: 9 } } } } }}
              onElementClick=${(label) => onToggleFilter("project_name", label)} />
          <//>
          <${ChartCard} title=${`${catLabel} Split`} sub="click to filter">
            <${ChartCanvas} type="doughnut" height="270px"
              data=${doughnutData(cat.map((c) => c.name), cat.map((c) => c.total))}
              options=${{ plugins: { legend: { display: true, position: "right", labels: { boxWidth: 9, font: { size: 9.5 } } } } }}
              onElementClick=${(label) => onToggleFilter(catField, label)} />
          <//>
          <${ChartCard} title="SLA (SLAB) Distribution" sub="click to filter">
            <${ChartCanvas} type="bar" height="270px"
              data=${barData(slab.map((s) => s.name), slab.map((s) => s.total), "#F0A202")}
              onElementClick=${(label) => onToggleFilter("slab", label)} />
          <//>
        </div>

        <div class="section-title">Management Attention <span class="hint">click a card to see the cases</span></div>
        <div class="grid grid-3">
          ${attnEntries.map(([key, v]) => html`
            <${AttentionCard} key=${key} label=${titleCase(key)} count=${v.count} onClick=${() => onOpenAttention(key)} />
          `)}
        </div>

        <div class="section-title">Management Insights</div>
        <ul class="insight-list">
          ${dash.insights.map((ins, i) => html`<li key=${i}>${ins}</li>`)}
        </ul>

        <div class="section-title">Top 5 / Bottom 5</div>
        <div class="grid grid-2">
          <${ChartCard} title="Top 5 Projects">
            <${RankList} rows=${dash.reports.top5_projects} valueKey="total" labelKey="name" />
          <//>
          <${ChartCard} title="Bottom 5 Projects">
            <${RankList} rows=${dash.reports.bottom5_projects} valueKey="total" labelKey="name" />
          <//>
          <${ChartCard} title="Top 5 Categories">
            <${RankList} rows=${dash.reports.top5_categories} valueKey="total" labelKey="name" />
          <//>
          <${ChartCard} title="Bottom 5 Categories">
            <${RankList} rows=${dash.reports.bottom5_categories} valueKey="total" labelKey="name" />
          <//>
        </div>
      </div>
    `;
  }

  // ---------------- Analysis ----------------
  function AnalysisTab({ dash, onToggleFilter }) {
    const r = dash.reports;
    const blocks = [
      ["project_name", "Project Analysis", r.project],
      ["service_category", "Service Category Analysis", r.service_category],
      ["m_category", "M_Category Analysis", r.m_category],
      ["area", "Area Analysis", r.area],
      ["sub_area", "Sub Area Analysis", r.sub_area],
      ["slab", "SLA (SLAB) Analysis", r.slab],
      ["priority", "Priority Analysis", r.priority],
      ["escalated_label", "Escalation Analysis", r.escalation],
      ["case_owner", "Case Owner Analysis", r.case_owner],
      ["team_leader", "Team Leader Analysis", r.team_leader],
      ["hod", "HOD Analysis", r.hod],
      ["client_category", "Client Category Analysis", r.client_category],
      ["sub_category", "Sub Category Analysis", r.sub_category],
      ["case_status", "Case Status Analysis", r.case_status],
      ["ageing_bucket", "Case Ageing Analysis", r.ageing_bucket],
    ];
    return html`
      <div>
        ${blocks.map(([dim, title, rows]) => html`
          <div key=${dim}>
            <div class="section-title">${title}</div>
            <${ReportTable} rows=${rows} dimLabel=${FIELD_LABELS[dim] || title}
              onRowClick=${dim !== "ageing_bucket" && dim !== "escalated_label" ? (name) => onToggleFilter(dim, name) : null} />
          </div>
        `)}
      </div>
    `;
  }

  // ---------------- Trends ----------------
  function TrendsTab({ dash }) {
    const daily = dash.daily_trend;
    const monthly = dash.monthly_yearly.monthly;
    const yearly = dash.monthly_yearly.yearly;
    return html`
      <div>
        <div class="section-title">Daily Trend</div>
        <${ChartCard} title="Carry Forward / Received / Resolved / Pending">
          <${ChartCanvas} type="line" height="300px"
            data=${multiLineData(daily.map((d) => d.date.slice(5)), [
              { label: "Carry Forward", data: daily.map((d) => d.carry_forward) },
              { label: "Today Received", data: daily.map((d) => d.today_received) },
              { label: "Total Resolved", data: daily.map((d) => d.total_resolved) },
              { label: "Total Pending", data: daily.map((d) => d.total_pending) },
            ])} />
        <//>
        <div class="table-wrap" style=${{ marginTop: "12px", maxHeight: "360px", overflowY: "auto" }}>
          <table class="data-table">
            <thead><tr>
              <th>Date</th><th>Carry Fwd</th><th>Today Recd</th><th>Total</th><th>Old Resolved</th>
              <th>Current Resolved</th><th>Total Resolved</th><th>Total Pending</th><th>%Cont</th>
            </tr></thead>
            <tbody>
              ${daily.map((d) => html`
                <tr key=${d.date}>
                  <td>${d.date}</td><td>${fmtInt(d.carry_forward)}</td><td>${fmtInt(d.today_received)}</td>
                  <td>${fmtInt(d.total_complaints)}</td><td>${fmtInt(d.old_resolved)}</td>
                  <td>${fmtInt(d.current_resolved)}</td><td>${fmtInt(d.total_resolved)}</td>
                  <td>${fmtInt(d.total_pending)}</td><td>${fmtPct(d.contribution_pct)}</td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>

        <div class="section-title">Monthly Analysis</div>
        ${monthly.length ? html`
          <div class="grid grid-2">
            <${ChartCard} title="Received vs Closed by Month">
              <${ChartCanvas} type="bar" height="260px"
                data=${{ labels: monthly.map((m) => m.period), datasets: [
                  { label: "Received", data: monthly.map((m) => m.received), backgroundColor: "#1F3864" },
                  { label: "Closed", data: monthly.map((m) => m.closed), backgroundColor: "#0F9B8E" },
                ] }} />
            <//>
            <${ChartCard} title="Monthly Table">
              <div class="table-wrap"><table class="data-table">
                <thead><tr><th>Month</th><th>Received</th><th>Closed</th><th>Resolution %</th></tr></thead>
                <tbody>${monthly.map((m) => html`<tr key=${m.period}><td>${m.period}</td><td>${fmtInt(m.received)}</td><td>${fmtInt(m.closed)}</td><td>${fmtPct(m.resolution_pct)}</td></tr>`)}</tbody>
              </table></div>
            <//>
          </div>
        ` : html`<${EmptyState} text="No monthly data available for the current filters." />`}

        <div class="section-title">Yearly Analysis</div>
        ${yearly.length > 1 ? html`
          <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Year</th><th>Received</th><th>Closed</th><th>Resolution %</th></tr></thead>
            <tbody>${yearly.map((y) => html`<tr key=${y.period}><td>${y.period}</td><td>${fmtInt(y.received)}</td><td>${fmtInt(y.closed)}</td><td>${fmtPct(y.resolution_pct)}</td></tr>`)}</tbody>
          </table></div>
        ` : html`<div class="empty-state">Not enough historical data available across multiple years for the current filters.</div>`}
      </div>
    `;
  }

  // ---------------- Data Quality ----------------
  function DataQualityTab({ dash }) {
    const dq = dash.data_quality;
    const ragColor = { green: "#2E7D32", amber: "#B67B00", red: "#C62828", grey: "#7A8699" }[dq.rag];
    const checkLabels = {
      blank_case_number: "Blank Case Number", duplicate_case_number: "Duplicate Case Number",
      blank_project: "Blank Project", blank_case_owner: "Blank Case Owner",
      blank_service_category: "Blank Service Category", invalid_opened_date: "Invalid Opened Date",
      invalid_closed_date: "Invalid Closed Date", closed_without_closed_date: "Closed Without Closed Date",
      open_with_closed_date: "Open With Closed Date Set", negative_tat: "Negative TAT",
      missing_slab: "Missing SLAB", missing_hod: "Missing HOD", missing_team_leader: "Missing Team Leader",
    };
    return html`
      <div>
        <div class="section-title">Data Quality Score</div>
        <div class="card">
          <div class="dq-score-wrap">
            <div class="dq-score" style=${{ color: ragColor }}>${dq.score}%</div>
            <div style=${{ flex: 1 }}>
              <div class="progress-bar"><div style=${{ width: `${dq.score}%`, background: ragColor }}></div></div>
              <div class="text-muted" style=${{ fontSize: "11.5px", marginTop: "6px" }}>
                ${fmtInt(dq.valid_records)} of ${fmtInt(dq.total_records)} records pass all data quality checks.
              </div>
            </div>
          </div>
        </div>
        <div class="section-title">Checks</div>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>Check</th><th>Issue Count</th></tr></thead>
          <tbody>
            ${Object.entries(dq.checks).map(([k, v]) => html`
              <tr key=${k}><td>${checkLabels[k] || titleCase(k)}</td><td>${v > 0 ? html`<strong style=${{ color: v > 0 ? "#C62828" : "inherit" }}>${fmtInt(v)}</strong>` : fmtInt(v)}</td></tr>
            `)}
          </tbody>
        </table></div>
      </div>
    `;
  }

  // ---------------- Cases (detailed table) ----------------
  function CasesTab({ filters, onOpenCase }) {
    const [search, setSearch] = useState("");
    const [debounced, setDebounced] = useState("");
    const [sortBy, setSortBy] = useState("opened_date");
    const [sortDir, setSortDir] = useState("desc");
    const [page, setPage] = useState(1);
    const [pageSize] = useState(25);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => { const t = setTimeout(() => setDebounced(search), 350); return () => clearTimeout(t); }, [search]);
    useEffect(() => { setPage(1); }, [debounced, JSON.stringify(filters), sortBy, sortDir]);
    useEffect(() => {
      let cancelled = false;
      setLoading(true);
      window.MIS.api.table({ filters, search: debounced, sort_by: sortBy, sort_dir: sortDir, page, page_size: pageSize })
        .then((d) => { if (!cancelled) { setData(d); setLoading(false); } });
      return () => { cancelled = true; };
    }, [filters, debounced, sortBy, sortDir, page, pageSize]);

    const cols = ["case_number", "account_name", "subject", "priority", "area", "opened_date",
      "closed_date", "case_owner", "case_status", "project_name", "team_leader", "hod", "updated_status",
      "tat_days", "slab", "escalated_label"];

    function headerClick(key) {
      if (key === sortBy) setSortDir(sortDir === "asc" ? "desc" : "asc");
      else { setSortBy(key); setSortDir("desc"); }
    }

    return html`
      <div>
        <div class="section-title">Detailed Case Table <span class="hint">click a case number for full details</span></div>
        <div class="toolbar">
          <input class="search-input" placeholder="Search cases (account, subject, case number...)"
            value=${search} onInput=${(e) => setSearch(e.target.value)} />
          ${data ? html`<${window.MIS.components.Pagination} page=${page} pageSize=${pageSize} total=${data.total} onPage=${setPage} />` : null}
        </div>
        ${loading && !data ? html`<${Spinner} />` : (
          !data || data.rows.length === 0 ? html`<${EmptyState} text="No cases match the current filters/search." />` : html`
            <div class="table-wrap" style=${{ maxHeight: "620px", overflowY: "auto" }}>
              <table class="data-table">
                <thead><tr>
                  ${cols.map((c) => html`
                    <th key=${c} class=${sortBy === c ? `sorted ${sortDir}` : ""} onClick=${() => headerClick(c)}>${FIELD_LABELS[c] || c}</th>
                  `)}
                </tr></thead>
                <tbody>
                  ${data.rows.map((row, i) => html`
                    <tr key=${row.case_number || i}>
                      ${cols.map((c) => html`
                        <td key=${c}>${c === "case_number"
                          ? html`<a class="case-link" href="#" onClick=${(e) => { e.preventDefault(); onOpenCase(row.case_number); }}>${row[c] || "–"}</a>`
                          : (row[c] === null || row[c] === undefined || row[c] === "" ? "–" : String(row[c]))}</td>
                      `)}
                    </tr>
                  `)}
                </tbody>
              </table>
            </div>
          `
        )}
      </div>
    `;
  }

  window.MIS.tabs = { OverviewTab, AnalysisTab, TrendsTab, DataQualityTab, CasesTab };
})();
