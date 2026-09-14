import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ page, pageSize, total, onPageChange }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);

  return (
    <div className="flex items-center justify-between px-1 py-2 text-xs text-ink-500">
      <span>
        {from}–{to} of {total.toLocaleString("en-IN")}
      </span>
      <div className="flex items-center gap-1">
        <button
          className="btn !px-2 !py-1"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </button>
        <span className="px-2">
          Page {page} of {totalPages}
        </span>
        <button
          className="btn !px-2 !py-1"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
