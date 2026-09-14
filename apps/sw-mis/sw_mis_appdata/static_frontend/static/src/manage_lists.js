/* global React */
(function () {
  "use strict";
  const { useState, useEffect } = React;
  const html = window.MIS.html;
  const { Modal, Spinner } = window.MIS.components;

  // ---------------- Admin unlock modal ----------------
  function AdminUnlockModal({ onClose, onUnlocked }) {
    const [passcode, setPasscode] = useState("");
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);

    async function submit(e) {
      e.preventDefault();
      setBusy(true); setError(null);
      try {
        const res = await window.MIS.api.authUnlock(passcode);
        if (res.is_admin) onUnlocked();
        else setError("Incorrect passcode.");
      } catch (err) {
        setError(err.message || "Incorrect passcode.");
      } finally {
        setBusy(false);
      }
    }

    return html`
      <${Modal} title="Unlock Admin Mode" onClose=${onClose}>
        <form class="passcode-modal" onSubmit=${submit}>
          <p style=${{ fontSize: "13px", color: "var(--text-600)", margin: 0 }}>
            Enter the admin passcode to edit or upload the Project / Category list data.
          </p>
          <input type="password" autoFocus placeholder="Admin passcode"
            value=${passcode} onChange=${(e) => setPasscode(e.target.value)} />
          ${error ? html`<div class="upload-error" style=${{ marginTop: 0 }}>${error}</div>` : null}
          <button type="submit" class="btn btn-primary" disabled=${busy} style=${{ width: "100%", justifyContent: "center" }}>
            ${busy ? "Checking…" : "Unlock"}
          </button>
        </form>
      </${Modal}>
    `;
  }

  // ---------------- Editable Category -> M_Category mapping table ----------------
  function CategoryMappingEditor({ rows, isAdmin, onChange }) {
    function setCell(i, key, val) {
      const next = rows.slice();
      next[i] = { ...next[i], [key]: val };
      onChange(next);
    }
    function removeRow(i) {
      onChange(rows.filter((_, idx) => idx !== i));
    }
    function addRow() {
      onChange([...rows, { category: "", m_category: "" }]);
    }
    return html`
      <div>
        <div class="editable-table-wrap">
          <table class="editable-table">
            <thead><tr><th>Category</th><th>M_Category</th>${isAdmin ? html`<th style=${{ width: "40px" }}></th>` : null}</tr></thead>
            <tbody>
              ${rows.map((r, i) => html`
                <tr key=${i}>
                  <td><input type="text" value=${r.category} disabled=${!isAdmin}
                    onChange=${(e) => setCell(i, "category", e.target.value)} /></td>
                  <td><input type="text" value=${r.m_category} disabled=${!isAdmin}
                    onChange=${(e) => setCell(i, "m_category", e.target.value)} /></td>
                  ${isAdmin ? html`<td><button class="row-remove-btn" title="Remove row" onClick=${() => removeRow(i)}>×</button></td>` : null}
                </tr>
              `)}
            </tbody>
          </table>
        </div>
        ${isAdmin ? html`<button class="btn btn-outline btn-sm" style=${{ marginTop: "10px" }} onClick=${addRow}>+ Add Category</button>` : null}
      </div>
    `;
  }

  // ---------------- Simple one-value-per-line list editor (Project/Month/Year) ----------------
  function SimpleListEditor({ label, values, isAdmin, onChange }) {
    const [text, setText] = useState(values.join("\n"));
    useEffect(() => { setText(values.join("\n")); }, [values]);
    function handleBlur() {
      const list = text.split("\n").map((v) => v.trim()).filter(Boolean);
      onChange(list);
    }
    return html`
      <div>
        <textarea class="list-editor-textarea" disabled=${!isAdmin} value=${text}
          onChange=${(e) => setText(e.target.value)} onBlur=${handleBlur}
          placeholder=${`One ${label.toLowerCase()} per line`} />
        <div class="text-muted" style=${{ fontSize: "11px", marginTop: "4px" }}>${values.length} ${label.toLowerCase()}(s) — one per line</div>
      </div>
    `;
  }

  // ---------------- Main Manage Lists tab ----------------
  function ManageListsTab({ isAdmin, onRequestUnlock, onLock, onListsChanged }) {
    const [data, setData] = useState(null);
    const [draft, setDraft] = useState(null);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [uploadBusy, setUploadBusy] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = React.useRef(null);

    function load() {
      window.MIS.api.getLists().then((d) => { setData(d); setDraft(d); });
    }
    useEffect(() => { load(); }, []);

    function updateDraft(patch) {
      setDraft((d) => ({ ...d, ...patch }));
      setSaved(false);
    }

    async function save() {
      setSaving(true); setError(null);
      try {
        const result = await window.MIS.api.updateLists({
          projects: draft.projects, months: draft.months, years: draft.years,
          category_rows: draft.category_rows,
        });
        setData(result); setDraft(result); setSaved(true);
        onListsChanged();
      } catch (e) {
        setError(e.message || "Could not save changes.");
      } finally {
        setSaving(false);
      }
    }

    async function handleUploadFile(file) {
      if (!file) return;
      setUploadBusy(true); setError(null);
      try {
        const result = await window.MIS.api.uploadList(file);
        setData(result); setDraft(result); setSaved(true);
        onListsChanged();
      } catch (e) {
        setError(e.message || "Upload failed.");
      } finally {
        setUploadBusy(false);
      }
    }

    if (!draft) return html`<${Spinner} />`;

    return html`
      <div>
        <div class="section-title">
          Manage Lists
          <span class="hint">Project / Month / Year dropdowns and the Category → M_Category mapping used throughout the app</span>
        </div>

        <div class="manage-lists-toolbar">
          ${isAdmin ? html`
            <span class="badge" style=${{ background: "var(--teal-100)", color: "var(--teal-600)" }}>🔓 Admin mode</span>
            <button class="btn btn-outline btn-sm" onClick=${onLock}>Switch to Viewer</button>
            <input ref=${fileInputRef} type="file" accept=".xlsx,.xls" style=${{ display: "none" }}
              onChange=${(e) => handleUploadFile(e.target.files[0])} />
            <button class="btn btn-outline btn-sm" disabled=${uploadBusy} onClick=${() => fileInputRef.current.click()}>
              ${uploadBusy ? "Uploading…" : "⇪ Upload Replacement LIST.xlsx"}
            </button>
            <button class="btn btn-primary btn-sm" disabled=${saving} onClick=${save}>
              ${saving ? "Saving…" : "💾 Save Changes"}
            </button>
          ` : html`
            <span class="badge">🔒 Viewer mode (read-only)</span>
            <button class="btn btn-outline btn-sm" onClick=${onRequestUnlock}>Unlock Admin to Edit</button>
          `}
        </div>

        ${!isAdmin ? html`<div class="viewer-note">You're viewing the current lists read-only. Unlock admin mode to edit values inline or upload a replacement LIST.xlsx file.</div>` : null}
        ${saved ? html`<div class="save-banner">✓ Saved — M_Category values across the dashboard have been refreshed.</div>` : null}
        ${error ? html`<div class="upload-error">${error}</div>` : null}
        <div class="list-source-note">Current source: <strong>${data.source}</strong></div>

        <div class="section-title" style=${{ marginTop: "22px" }}>Category → M_Category Mapping</div>
        <${CategoryMappingEditor} rows=${draft.category_rows} isAdmin=${isAdmin}
          onChange=${(rows) => updateDraft({ category_rows: rows })} />

        <div class="grid grid-3" style=${{ marginTop: "22px" }}>
          <div class="card">
            <div class="card-title">Project List</div>
            <${SimpleListEditor} label="Project" values=${draft.projects} isAdmin=${isAdmin}
              onChange=${(v) => updateDraft({ projects: v })} />
          </div>
          <div class="card">
            <div class="card-title">Month List</div>
            <${SimpleListEditor} label="Month" values=${draft.months} isAdmin=${isAdmin}
              onChange=${(v) => updateDraft({ months: v })} />
          </div>
          <div class="card">
            <div class="card-title">Year List</div>
            <${SimpleListEditor} label="Year" values=${draft.years.map(String)} isAdmin=${isAdmin}
              onChange=${(v) => updateDraft({ years: v })} />
          </div>
        </div>
      </div>
    `;
  }

  window.MIS.manageLists = { AdminUnlockModal, ManageListsTab };
})();
