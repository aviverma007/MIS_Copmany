import React, { createContext, useContext, useState, useCallback } from "react";

// Any clickable number in the app calls openDrilldown({ title, extraFilters })
// to pop the universal ticket drill-down table pre-filtered accordingly,
// without leaving the current page or disturbing the global filter state.
const DrilldownContext = createContext(null);

export function DrilldownProvider({ children }) {
  const [state, setState] = useState(null); // { title, extraFilters }

  const openDrilldown = useCallback((title, extraFilters = {}) => {
    setState({ title, extraFilters });
  }, []);

  const closeDrilldown = useCallback(() => setState(null), []);

  return (
    <DrilldownContext.Provider value={{ state, openDrilldown, closeDrilldown }}>
      {children}
    </DrilldownContext.Provider>
  );
}

export function useDrilldown() {
  const ctx = useContext(DrilldownContext);
  if (!ctx) throw new Error("useDrilldown must be used within a DrilldownProvider");
  return ctx;
}
