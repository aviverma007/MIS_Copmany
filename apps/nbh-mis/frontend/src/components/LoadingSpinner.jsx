import React from "react";
import { Loader2 } from "lucide-react";

export default function LoadingSpinner({ label = "Loading…", compact = false }) {
  return (
    <div className={`flex items-center justify-center gap-2 text-ink-500 ${compact ? "py-4" : "py-16"}`}>
      <Loader2 className="h-4 w-4 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
