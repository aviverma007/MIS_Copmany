import React, { useMemo, useState } from "react";
import { ArrowUpDown } from "lucide-react";
import { formatNumber, formatPct, formatDays } from "../utils/format.js";

const FORMATTERS = {
  number: formatNumber,
  pct: formatPct,
  days: formatDays,
};

/**
 * Small generic sortable stats table: columns = [{ key, label, format }].
 * highlightFn(row) may return a className applied to the row (e.g. to flag
 * "highest backlog" / "lowest closure %" outliers).
 */
export default function StatsTable({ rows, rowKey, columns, defaultSortKey, defaultSortDir = "desc", onRowClick, highlightFn }) {
  const [sortKey, setSortKey] = useState(defaultSortKey || columns[0]?.key);
  const [sortDir, setSortDir] = useState(defaultSortDir);

  const sorted = useMemo(() => {
    return [...(rows || [])].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "string") return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortDir === "asc" ? (av ?? 0) - (bv ?? 0) : (bv ?? 0) - (av ?? 0);
    });
  }, [rows, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  return (
    <div className="table-scroll">
      <table className="mis-table text-xs">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`cursor-pointer ${col.format ? "text-right" : ""}`}
                onClick={() => toggleSort(col.key)}
              >
                <span className={`inline-flex items-center gap-1 ${col.format ? "justify-end w-full" : ""}`}>
                  {col.label} <ArrowUpDown className="h-3 w-3" />
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr
              key={row[rowKey] ?? i}
              className={`${onRowClick ? "cursor-pointer" : ""} ${highlightFn ? highlightFn(row) : ""}`}
              onClick={() => onRowClick && onRowClick(row)}
            >
              {columns.map((col) => (
                <td key={col.key} className={col.format ? "text-right" : "font-medium"}>
                  {col.format ? (FORMATTERS[col.format] || ((v) => v))(row[col.key]) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="text-center text-ink-400 py-4">No data.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
