import React, { useEffect, useState } from "react";
import { ArrowUpDown } from "lucide-react";
import { getTickets } from "../services/api.js";
import { formatNumber, truncate } from "../utils/format.js";
import { useTicketDetail } from "../context/TicketDetailContext.jsx";
import LoadingSpinner from "./LoadingSpinner.jsx";
import ErrorBanner from "./ErrorBanner.jsx";
import Pagination from "./Pagination.jsx";

const SORTABLE_COLUMNS = [
  { key: "ageing_days", label: "Ageing (days)" },
  { key: "open_date", label: "Open Date" },
  { key: "society_name", label: "Project" },
  { key: "category_raw", label: "Category" },
  { key: "priority", label: "Priority" },
  { key: "status_raw", label: "Status" },
  { key: "current_assignee", label: "Assignee" },
  { key: "escalated_level", label: "Escalation" },
];

export default function TicketsTable({ filters, pageSize = 25 }) {
  const { openTicket } = useTicketDetail();
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("ageing_days");
  const [sortDir, setSortDir] = useState("desc");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setPage(1);
  }, [JSON.stringify(filters)]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTickets(filters, { page, pageSize, sortBy, sortDir })
      .then((res) => !cancelled && setData(res))
      .catch((err) => !cancelled && setError(err?.response?.data?.detail || "Failed to load tickets."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters), page, pageSize, sortBy, sortDir]);

  const toggleSort = (key) => {
    if (sortBy === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortBy(key);
      setSortDir("desc");
    }
  };

  return (
    <div className="flex flex-col gap-2">
      {error && <ErrorBanner message={error} compact />}
      {loading ? (
        <LoadingSpinner compact />
      ) : (
        <>
          <div className="table-scroll">
            <table className="mis-table text-xs">
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  {SORTABLE_COLUMNS.map((col) => (
                    <th key={col.key} className="cursor-pointer" onClick={() => toggleSort(col.key)}>
                      <span className="inline-flex items-center gap-1">{col.label} <ArrowUpDown className="h-3 w-3" /></span>
                    </th>
                  ))}
                  <th>Mgmt. Status</th>
                  <th>Ageing Slab</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {(data?.rows || []).map((t) => (
                  <tr key={t.ticket_id}>
                    <td>
                      <button className="text-brand-600 font-semibold hover:underline" onClick={() => openTicket(t.ticket_id)}>
                        {t.ticket_id}
                      </button>
                    </td>
                    <td>{formatNumber(t.ageing_days)}</td>
                    <td>{t.open_date}</td>
                    <td>{t.society_name}</td>
                    <td>{t.category_raw}</td>
                    <td>{t.priority}</td>
                    <td>{t.status_raw}</td>
                    <td>{t.current_assignee || "—"}</td>
                    <td>{t.escalated_level}</td>
                    <td>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${t.management_status === "OPEN" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
                        {t.management_status}
                      </span>
                    </td>
                    <td>{t.ageing_slab}</td>
                    <td className="max-w-xs truncate" title={t.description}>{truncate(t.description, 60)}</td>
                  </tr>
                ))}
                {(data?.rows || []).length === 0 && (
                  <tr>
                    <td colSpan={SORTABLE_COLUMNS.length + 4} className="text-center text-ink-400 py-4">
                      No matching tickets.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {data && <Pagination page={page} pageSize={pageSize} total={data.total} onPageChange={setPage} />}
        </>
      )}
    </div>
  );
}
