import { useEffect, useRef, useState } from "react";

/**
 * Generic "fetch this report whenever the shared filters change" hook.
 * fetchFn receives the filters object and must return a promise.
 * A 409 (no dataset) is surfaced via the axios interceptor globally, so we
 * just need to not blow up here -- treat it like any other error and let the
 * caller decide whether to render anything.
 */
export function useFilteredData(fetchFn, filters, extraDeps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestId = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const myId = ++requestId.current;
    setLoading(true);
    setError(null);
    fetchFn(filters)
      .then((res) => {
        if (cancelled || myId !== requestId.current) return;
        setData(res);
      })
      .catch((err) => {
        if (cancelled || myId !== requestId.current) return;
        setError(err?.response?.data?.detail || "Failed to load data.");
      })
      .finally(() => {
        if (cancelled || myId !== requestId.current) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters), ...extraDeps]);

  return { data, loading, error };
}
