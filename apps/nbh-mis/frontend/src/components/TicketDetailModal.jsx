import React, { useEffect, useState } from "react";
import { X, Circle } from "lucide-react";
import { useTicketDetail } from "../context/TicketDetailContext.jsx";
import { getTicketDetail } from "../services/api.js";
import LoadingSpinner from "./LoadingSpinner.jsx";
import ErrorBanner from "./ErrorBanner.jsx";
import RAGIndicator from "./RAGIndicator.jsx";

function Field({ label, value }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">{label}</div>
      <div className="text-sm text-ink-800">{value === null || value === undefined || value === "" ? "—" : value}</div>
    </div>
  );
}

export default function TicketDetailModal() {
  const { ticketId, closeTicket } = useTicketDetail();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticketId) {
      setTicket(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTicketDetail(ticketId)
      .then((res) => !cancelled && setTicket(res))
      .catch((err) => !cancelled && setError(err?.response?.data?.detail || "Failed to load ticket."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [ticketId]);

  if (!ticketId) return null;

  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center bg-ink-900/40 p-4" onClick={closeTicket}>
      <div
        className="bg-surface rounded-lg shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold text-ink-900">Ticket {ticketId}</h2>
          <button className="btn !py-1 !px-2" onClick={closeTicket} aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4 overflow-y-auto flex flex-col gap-4">
          {loading && <LoadingSpinner compact />}
          {!loading && error && <ErrorBanner message={error} />}
          {!loading && ticket && (
            <>
              <div className="flex items-center gap-2">
                {ticket.rag && <RAGIndicator rag={ticket.rag} size="md" />}
                <span className={`px-2 py-1 rounded text-xs font-semibold ${ticket.management_status === "OPEN" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
                  {ticket.management_status}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <Field label="Project" value={ticket.society_name} />
                <Field label="Location" value={ticket.issue_location} />
                <Field label="Priority" value={ticket.priority} />
                <Field label="Category" value={ticket.category} />
                <Field label="Sub Category" value={ticket.sub_category} />
                <Field label="Status" value={ticket.status} />
                <Field label="Management Category" value={ticket.management_category} />
                <Field label="Assignee" value={ticket.current_assignee} />
                <Field label="Escalation Level" value={ticket.escalated_level} />
                <Field label="Ageing (days)" value={ticket.ageing_days} />
                <Field label="Ageing Slab" value={ticket.ageing_slab} />
                <Field label="Source" value={ticket.source} />
                <Field label="Rating" value={ticket.rating} />
                <Field label="Created On" value={ticket.created_on} />
                <Field label="Last Updated" value={ticket.last_updated_on} />
                <Field label="Closed Date" value={ticket.closed_date} />
              </div>
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500 mb-1">Description</div>
                <p className="text-sm text-ink-800 whitespace-pre-wrap">{ticket.description || "—"}</p>
              </div>
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500 mb-1">Last Comment</div>
                <p className="text-sm text-ink-800 whitespace-pre-wrap">{ticket.last_comment || "—"}</p>
              </div>
              {ticket.timeline?.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500 mb-2">Timeline</div>
                  <ol className="relative border-l border-line ml-1.5 flex flex-col gap-3">
                    {ticket.timeline.map((stage, i) => (
                      <li key={i} className="pl-4 relative">
                        <Circle className="h-2.5 w-2.5 fill-brand-600 text-brand-600 absolute -left-[5px] top-1" />
                        <div className="text-xs font-semibold text-ink-800">{stage.stage}</div>
                        <div className="text-[11px] text-ink-500">{stage.timestamp}</div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
