import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getAllMasterData } from "../services/api.js";

const MasterDataContext = createContext(null);

export function MasterDataProvider({ children }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    getAllMasterData()
      .then((d) => setData(d))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return (
    <MasterDataContext.Provider value={{ data, loading, error, reload }}>
      {children}
    </MasterDataContext.Provider>
  );
}

export function useMasterData() {
  const ctx = useContext(MasterDataContext);
  if (!ctx) throw new Error("useMasterData must be used within a MasterDataProvider");
  return ctx;
}
