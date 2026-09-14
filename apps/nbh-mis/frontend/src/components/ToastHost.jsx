import React, { useEffect, useState, useCallback } from "react";
import { AlertCircle, X } from "lucide-react";
import { onError } from "../utils/errorBus.js";

export default function ToastHost() {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    return onError((message) => {
      const id = Date.now() + Math.random();
      setToasts((prev) => [...prev, { id, message }]);
      setTimeout(() => dismiss(id), 8000);
    });
  }, [dismiss]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="flex items-start gap-2 rounded-md border border-red-200 bg-white shadow-lg px-3 py-2.5 text-sm text-ink-800"
        >
          <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
          <span className="flex-1">{t.message}</span>
          <button onClick={() => dismiss(t.id)} className="text-ink-400 hover:text-ink-700">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
