import React from "react";
import { AlertTriangle } from "lucide-react";

export default function ErrorBanner({ message, compact = false }) {
  if (!message) return null;
  return (
    <div
      className={`flex items-start gap-2 rounded-md border border-red-200 bg-red-50 text-red-800 ${
        compact ? "px-3 py-2 text-xs" : "px-4 py-3 text-sm"
      }`}
    >
      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
