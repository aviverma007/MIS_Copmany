import React from "react";
import { useRagColors } from "../context/RagColorsContext.jsx";

export function RagDot({ rag, size = 8 }) {
  const { colorFor } = useRagColors();
  return (
    <span
      className="inline-block rounded-full shrink-0"
      style={{ width: size, height: size, backgroundColor: colorFor(rag) }}
    />
  );
}

export default function RAGIndicator({ rag, label, size = "sm" }) {
  const { colorFor } = useRagColors();
  const color = colorFor(rag);
  const pad = size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-1 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded font-semibold uppercase tracking-wide ${pad}`}
      style={{ color, backgroundColor: `${color}1a`, border: `1px solid ${color}55` }}
    >
      <RagDot rag={rag} size={6} />
      {label || rag}
    </span>
  );
}
