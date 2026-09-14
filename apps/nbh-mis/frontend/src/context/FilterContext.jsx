import React, { createContext, useCallback, useContext, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

const FILTER_KEYS = [
  "year",
  "month",
  "project",
  "status",
  "priority",
  "category",
  "management_category",
  "source",
  "assignee",
  "ageing_slab",
  "escalation_level",
  "date_from",
  "date_to",
  "search",
];

const DEFAULT_FILTERS = FILTER_KEYS.reduce((acc, k) => {
  acc[k] = k === "date_from" || k === "date_to" || k === "search" ? "" : "ALL";
  return acc;
}, {});

const FilterContext = createContext(null);

export function FilterProvider({ children }) {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => {
    const out = { ...DEFAULT_FILTERS };
    FILTER_KEYS.forEach((key) => {
      const v = searchParams.get(key);
      if (v !== null && v !== "") out[key] = v;
    });
    return out;
  }, [searchParams]);

  const setFilter = useCallback(
    (key, value) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value === null || value === undefined || value === "" || String(value).toUpperCase() === "ALL") {
            next.delete(key);
          } else {
            next.set(key, value);
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const setFilters = useCallback(
    (patch) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          Object.entries(patch).forEach(([key, value]) => {
            if (value === null || value === undefined || value === "" || String(value).toUpperCase() === "ALL") {
              next.delete(key);
            } else {
              next.set(key, value);
            }
          });
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const resetFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  const isActive = useMemo(
    () =>
      FILTER_KEYS.some((k) => {
        const v = filters[k];
        return v && v !== "" && String(v).toUpperCase() !== "ALL";
      }),
    [filters]
  );

  const value = useMemo(
    () => ({ filters, setFilter, setFilters, resetFilters, isActive, FILTER_KEYS }),
    [filters, setFilter, setFilters, resetFilters, isActive]
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

export function useFilters() {
  const ctx = useContext(FilterContext);
  if (!ctx) throw new Error("useFilters must be used within a FilterProvider");
  return ctx;
}
