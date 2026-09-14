import React, { useEffect, useState, useCallback } from "react";
import { Plus, Trash2, Check, X, Pencil } from "lucide-react";
import SectionCard from "./SectionCard.jsx";
import LoadingSpinner from "./LoadingSpinner.jsx";
import ErrorBanner from "./ErrorBanner.jsx";
import { listActions, createAction, updateAction, deleteAction } from "../services/api.js";

const STATUSES = ["Open", "In Progress", "Closed", "Overdue"];

const emptyDraft = { title: "", owner: "", target_date: "", status: "Open" };

function isOverdue(action) {
  return action.status === "Overdue";
}

export default function ActionTracker() {
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState(emptyDraft);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listActions()
      .then(setActions)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load action tracker."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    if (!draft.title.trim() || !draft.owner.trim() || !draft.target_date) return;
    setBusy(true);
    try {
      await createAction(draft);
      setDraft(emptyDraft);
      setAdding(false);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create action.");
    } finally {
      setBusy(false);
    }
  };

  const startEdit = (action) => {
    setEditingId(action.id);
    setEditDraft({ title: action.title, owner: action.owner, target_date: action.target_date, status: action.status });
  };

  const handleSaveEdit = async (id) => {
    setBusy(true);
    try {
      await updateAction(id, editDraft);
      setEditingId(null);
      setEditDraft(null);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to update action.");
    } finally {
      setBusy(false);
    }
  };

  const handleStatusChange = async (id, status) => {
    setBusy(true);
    try {
      await updateAction(id, { status });
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to update status.");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id) => {
    setBusy(true);
    try {
      await deleteAction(id);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to delete action.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionCard
      title="Management Action Tracker"
      action={
        <button className="btn !py-1 !px-2 text-xs" onClick={() => setAdding((a) => !a)}>
          <Plus className="h-3.5 w-3.5" />
          Add Action
        </button>
      }
    >
      {error && <ErrorBanner message={error} compact />}
      {loading ? (
        <LoadingSpinner compact />
      ) : (
        <div className="table-scroll">
          <table className="mis-table text-xs">
            <thead>
              <tr>
                <th>Title</th>
                <th>Owner</th>
                <th>Target Date</th>
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {adding && (
                <tr className="bg-blue-50/40">
                  <td>
                    <input className="input !py-1 text-xs" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="Action title" />
                  </td>
                  <td>
                    <input className="input !py-1 text-xs" value={draft.owner} onChange={(e) => setDraft({ ...draft, owner: e.target.value })} placeholder="Owner" />
                  </td>
                  <td>
                    <input type="date" className="input !py-1 text-xs" value={draft.target_date} onChange={(e) => setDraft({ ...draft, target_date: e.target.value })} />
                  </td>
                  <td>
                    <select className="input !py-1 text-xs" value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </td>
                  <td className="text-right">
                    <div className="flex justify-end gap-1">
                      <button className="btn !py-1 !px-2" disabled={busy} onClick={handleAdd} title="Save">
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button className="btn !py-1 !px-2" onClick={() => { setAdding(false); setDraft(emptyDraft); }} title="Cancel">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              )}
              {actions.map((action) => {
                const editing = editingId === action.id;
                return (
                  <tr key={action.id} className={isOverdue(action) ? "border-l-2 border-l-red-500 bg-red-50/40" : ""}>
                    <td>
                      {editing ? (
                        <input className="input !py-1 text-xs" value={editDraft.title} onChange={(e) => setEditDraft({ ...editDraft, title: e.target.value })} />
                      ) : (
                        action.title
                      )}
                    </td>
                    <td>
                      {editing ? (
                        <input className="input !py-1 text-xs" value={editDraft.owner} onChange={(e) => setEditDraft({ ...editDraft, owner: e.target.value })} />
                      ) : (
                        action.owner
                      )}
                    </td>
                    <td>
                      {editing ? (
                        <input type="date" className="input !py-1 text-xs" value={editDraft.target_date} onChange={(e) => setEditDraft({ ...editDraft, target_date: e.target.value })} />
                      ) : (
                        action.target_date
                      )}
                    </td>
                    <td>
                      {editing ? (
                        <select className="input !py-1 text-xs" value={editDraft.status} onChange={(e) => setEditDraft({ ...editDraft, status: e.target.value })}>
                          {STATUSES.map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      ) : (
                        <select
                          className={`input !py-1 text-xs ${isOverdue(action) ? "border-red-300 text-red-700 font-semibold" : ""}`}
                          value={action.status}
                          onChange={(e) => handleStatusChange(action.id, e.target.value)}
                        >
                          {STATUSES.map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="text-right">
                      <div className="flex justify-end gap-1">
                        {editing ? (
                          <>
                            <button className="btn !py-1 !px-2" disabled={busy} onClick={() => handleSaveEdit(action.id)} title="Save">
                              <Check className="h-3.5 w-3.5" />
                            </button>
                            <button className="btn !py-1 !px-2" onClick={() => { setEditingId(null); setEditDraft(null); }} title="Cancel">
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </>
                        ) : (
                          <>
                            <button className="btn !py-1 !px-2" onClick={() => startEdit(action)} title="Edit">
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                            <button className="btn !py-1 !px-2" disabled={busy} onClick={() => handleDelete(action.id)} title="Delete">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {actions.length === 0 && !adding && (
                <tr>
                  <td colSpan={5} className="text-center text-ink-400 py-4">No action items yet. Click "Add Action" to create one.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
}
