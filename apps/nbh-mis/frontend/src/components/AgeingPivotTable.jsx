import React, { useMemo, useState } from "react";
import { ArrowUpDown, Search } from "lucide-react";
import { formatNumber, formatPct } from "../utils/format.js";
import { useMasterData } from "../context/MasterDataContext.jsx";

const GRAND_TOTAL_KEY = "Grand Total";

/**
 * Generic ageing-slab pivot table: one row per dimension (project / category /
 * status / management category), one column per ageing slab (order/labels
 * fetched from /api/master/ageing-slabs, never hardcoded), a Grand Total
 * column, plus any extra numeric columns the caller wants rendered
 * (e.g. total_tickets, closure_pct). Cells in the ageing-slab columns get a
 * heatmap-style background intensity relative to the column max.
 */
export default function AgeingPivotTable({
  rows,
  rowKey,
  rowLabel,
  extraColumns = [], // [{ key, label, format }]
  onRowClick,
  onCellClick, // (row, slab) => void
  searchable = true,
  defaultSortKey = GRAND_TOTAL_KEY,
}) {
  const { data: master } = useMasterData();
  const slabs = useMemo(() => (master?.ageingSlabs || []).filter((s) => s.toUpperCase() !== "ALL"), [master]);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState(defaultSortKey);
  const [sortDir, setSortDir] = useState("desc");

  const columnMax = useMemo(() => {
    const max = {};
    slabs.forEach((slab) => {
      max[slab] = Math.max(1, ...rows.map((r) => Number(r[slab]) || 0));
    });
    return max;
  }, [rows, slabs]);

  const filtered = useMemo(() => {
    let out = rows;
    if (search.trim()) {
      const s = search.trim().toLowerCase();
      out = out.filter((r) => String(r[rowKey] ?? "").toLowerCase().includes(s));
    }
    out = [...out].sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      if (typeof av === "string") return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return out;
  }, [rows, search, sortKey, sortDir, rowKey]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const heat = (slab, value) => {
    const ratio = Math.min(1, (Number(value) || 0) / (columnMax[slab] || 1));
    if (!value) return "transparent";
    const isCritical = slab.toLowerCase().includes("more than 30");
    const base = isCritical ? [192, 57, 43] : [47, 95, 143];
    return `rgba(${base[0]}, ${base[1]}, ${base[2]}, ${0.08 + ratio * 0.35})`;
  };

  return (
    <div>
      {searchable && (
        <div className="flex items-center gap-2 mb-2">
          <div className="relative flex-1 max-w-xs">
            <Search className="h-3.5 w-3.5 text-ink-400 absolute left-2 top-1/2 -translate-y-1/2" />
            <input
              className="input !py-1.5 !pl-7 text-xs"
              placeholder={`Search ${rowLabel || rowKey}…`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <span className="text-xs text-ink-400">{filtered.length} of {rows.length} rows</span>
        </div>
      )}
      <div className="table-scroll">
        <table className="mis-table text-xs">
          <thead>
            <tr>
              <th className="cursor-pointer" onClick={() => toggleSort(rowKey)}>
                <span className="inline-flex items-center gap-1">{rowLabel || rowKey} <ArrowUpDown className="h-3 w-3" /></span>
              </th>
              {slabs.map((slab) => (
                <th key={slab} className="text-right cursor-pointer" onClick={() => toggleSort(slab)}>
                  <span className="inline-flex items-center gap-1 justify-end w-full">{slab} <ArrowUpDown className="h-3 w-3" /></span>
                </th>
              ))}
              <th className="text-right cursor-pointer" onClick={() => toggleSort(GRAND_TOTAL_KEY)}>
                <span className="inline-flex items-center gap-1 justify-end w-full">Total <ArrowUpDown className="h-3 w-3" /></span>
              </th>
              {extraColumns.map((col) => (
                <th key={col.key} className="text-right cursor-pointer" onClick={() => toggleSort(col.key)}>
                  <span className="inline-flex items-center gap-1 justify-end w-full">{col.label} <ArrowUpDown className="h-3 w-3" /></span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr
                key={row[rowKey]}
                className={onRowClick ? "cursor-pointer" : ""}
                onClick={() => onRowClick && onRowClick(row)}
              >
                <td className="font-medium text-ink-800">{row[rowKey]}</td>
                {slabs.map((slab) => (
                  <td
                    key={slab}
                    className="text-right cursor-pointer"
                    style={{ backgroundColor: heat(slab, row[slab]) }}
                    onClick={(e) => {
                      if (onCellClick) {
                        e.stopPropagation();
                        onCellClick(row, slab);
                      }
                    }}
                  >
                    {formatNumber(row[slab])}
                  </td>
                ))}
                <td className="text-right font-semibold">{formatNumber(row[GRAND_TOTAL_KEY])}</td>
                {extraColumns.map((col) => (
                  <td key={col.key} className="text-right">
                    {col.format === "pct" ? formatPct(row[col.key]) : formatNumber(row[col.key])}
                  </td>
                ))}
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={slabs.length + 2 + extraColumns.length} className="text-center text-ink-400 py-4">
                  No matching rows.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
