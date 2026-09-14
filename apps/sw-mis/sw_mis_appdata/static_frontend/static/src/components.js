/* global React */
(function () {
  "use strict";
  const { useState, useEffect, useRef, useMemo } = React;
  const html = window.MIS.html;
  const { fmtInt, fmtPct, fmtNum1, fmtDays } = window.MIS.util;

  function RagDot({ rag }) {
    return html`<span class="dot rag-${rag || "grey"}"></span>`;
  }

  function KpiCard({ label, value, rag, format }) {
    const fmt = format || "int";
    let display = value;
    if (fmt === "int") display = fmtInt(value);
    else if (fmt === "pct") display = fmtPct(value);
    else if (fmt === "days") display = fmtDays(value);
    return html`
      <div class="kpi-card ${rag ? "rag-" + rag : ""}">
        ${rag ? html`<span class="rag-tag rag-${rag}">${rag}</span>` : null}
        <div class="val">${display}</div>
        <div class="lbl">${label}</div>
      </div>
    `;
  }

  function Chip({ text, onRemove }) {
    return html`
      <span class="chip">
        ${text}
        ${onRemove ? html`<button onClick=${onRemove} title="Remove filter">×</button>` : null}
      </span>
    `;
  }

  function Modal({ title, onClose, children, wide }) {
    useEffect(() => {
      function onKey(e) { if (e.key === "Escape") onClose(); }
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);
    return html`
      <div class="modal-overlay" onClick=${(e) => { if (e.target === e.currentTarget) onClose(); }}>
        <div class="modal" style=${wide ? { maxWidth: "980px" } : {}}>
          <div class="modal-head">
            <h2>${title}</h2>
            <button class="modal-close" onClick=${onClose}>×</button>
          </div>
          <div class="modal-body">${children}</div>
        </div>
      </div>
    `;
  }

  function Pagination({ page, pageSize, total, onPage }) {
    const pages = Math.max(1, Math.ceil(total / pageSize));
    return html`
      <div class="pagination">
        <span>${fmtInt(total)} records · page ${page} of ${fmtInt(pages)}</span>
        <button disabled=${page <= 1} onClick=${() => onPage(1)}>«</button>
        <button disabled=${page <= 1} onClick=${() => onPage(page - 1)}>‹</button>
        <button disabled=${page >= pages} onClick=${() => onPage(page + 1)}>›</button>
        <button disabled=${page >= pages} onClick=${() => onPage(pages)}>»</button>
      </div>
    `;
  }

  // Thin Chart.js wrapper - creates/destroys chart instance on data change.
  function ChartCanvas({ type, data, options, height, onElementClick }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);
    useEffect(() => {
      if (!canvasRef.current) return undefined;
      const ctx = canvasRef.current.getContext("2d");
      chartRef.current = new window.Chart(ctx, {
        type,
        data,
        options: Object.assign({
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: !!(data.datasets && data.datasets.length > 1), labels: { boxWidth: 10, font: { size: 10 } } } },
          onClick: (evt, elements) => {
            if (onElementClick && elements && elements.length) {
              const idx = elements[0].index;
              const label = data.labels && data.labels[idx];
              onElementClick(label);
            }
          },
        }, options || {}),
      });
      return () => { if (chartRef.current) chartRef.current.destroy(); };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [JSON.stringify(data), type]);
    return html`<div style=${{ height: height || "260px", position: "relative" }}><canvas ref=${canvasRef}></canvas></div>`;
  }

  function ChartCard({ title, sub, children }) {
    return html`
      <div class="card">
        <div class="card-title"><span>${title}</span>${sub ? html`<span class="sub">${sub}</span>` : null}</div>
        ${children}
      </div>
    `;
  }

  function RankList({ rows, valueKey, labelKey, format }) {
    const max = Math.max(1, ...rows.map((r) => Number(r[valueKey]) || 0));
    return html`
      <div>
        ${rows.map((r) => html`
          <div class="rank-row" key=${r[labelKey]}>
            <span class="name" title=${r[labelKey]}>${r[labelKey]}</span>
            <span class="bar-wrap"><span class="bar" style=${{ width: `${(Number(r[valueKey]) / max) * 100}%` }}></span></span>
            <span class="val">${format === "pct" ? fmtPct(r[valueKey]) : fmtInt(r[valueKey])}</span>
          </div>
        `)}
      </div>
    `;
  }

  function EmptyState({ text }) {
    return html`<div class="empty-state">${text}</div>`;
  }

  function Spinner() {
    return html`<div class="loading-wrap"><div class="spinner"></div></div>`;
  }

  function AttentionCard({ label, count, onClick }) {
    return html`
      <div class="card attn-card" onClick=${onClick}>
        <div>
          <div class="num ${count === 0 ? "zero" : ""}">${fmtInt(count)}</div>
          <div class="lbl">${label}</div>
        </div>
      </div>
    `;
  }

  window.MIS.components = { RagDot, KpiCard, Chip, Modal, Pagination, ChartCanvas, ChartCard, RankList, EmptyState, Spinner, AttentionCard };
})();
