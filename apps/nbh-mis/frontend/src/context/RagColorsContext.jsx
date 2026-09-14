import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getSummary } from "../services/api.js";

// Fetches the canonical RAG -> color mapping once (from an unfiltered
// dashboard summary's rag_scorecard.rows) and shares it app-wide, so no
// component ever invents its own RAG hex codes.
const RagColorsContext = createContext(null);

const NEUTRAL = "#9ca3af";

export function RagColorsProvider({ children }) {
  const [colors, setColors] = useState({});
  const [loaded, setLoaded] = useState(false);

  const reload = useCallback(() => {
    getSummary({})
      .then((summary) => {
        const map = {};
        (summary?.rag_scorecard?.rows || []).forEach((row) => {
          map[row.rag] = row.color;
        });
        setColors(map);
        setLoaded(true);
      })
      .catch(() => {
        setLoaded(true);
      });
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const colorFor = useCallback((rag) => colors[rag] || NEUTRAL, [colors]);

  return (
    <RagColorsContext.Provider value={{ colors, loaded, colorFor, reload }}>
      {children}
    </RagColorsContext.Provider>
  );
}

export function useRagColors() {
  const ctx = useContext(RagColorsContext);
  if (!ctx) throw new Error("useRagColors must be used within a RagColorsProvider");
  return ctx;
}
