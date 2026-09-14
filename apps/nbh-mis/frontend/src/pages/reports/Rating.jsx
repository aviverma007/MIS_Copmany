import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Star } from "lucide-react";
import SectionCard from "../../components/SectionCard.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ErrorBanner from "../../components/ErrorBanner.jsx";
import { getRating } from "../../services/api.js";
import { useFilters } from "../../context/FilterContext.jsx";
import { formatNumber } from "../../utils/format.js";

export default function Rating() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notAvailable, setNotAvailable] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setNotAvailable(false);
    getRating(filters)
      .then((res) => !cancelled && setData(res))
      .catch((err) => {
        if (cancelled) return;
        if (err?.response?.status === 404) setNotAvailable(true);
        else setError(err?.response?.data?.detail || "Failed to load rating report.");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  if (loading) return <LoadingSpinner label="Loading customer experience report…" />;
  if (notAvailable) {
    return (
      <SectionCard title="Customer Experience">
        <p className="text-sm text-ink-500">No Rating column was found in the uploaded data, so this report is unavailable.</p>
      </SectionCard>
    );
  }
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        <div className="card p-3 flex items-center gap-2">
          <Star className="h-5 w-5 text-amber-500 fill-amber-500" />
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Average Rating</div>
            <div className="text-lg font-bold text-ink-900">{data.average_rating ?? "—"}</div>
          </div>
        </div>
        <div className="card p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Rated Cases</div>
          <div className="text-lg font-bold text-ink-900">{formatNumber(data.rated_cases)}</div>
        </div>
        <div className="card p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">Unrated Cases</div>
          <div className="text-lg font-bold text-ink-900">{formatNumber(data.unrated_cases)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Rating Distribution">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.distribution} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
                <CartesianGrid stroke="#eef0f3" vertical={false} />
                <XAxis dataKey="rating" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => formatNumber(v)} />
                <Bar dataKey="count" fill="#c98a11" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>
        <div className="flex flex-col gap-4">
          <SectionCard title="Lowest Rated Projects">
            <ul className="flex flex-col gap-1">
              {(data.worst_projects || []).map((p) => (
                <li key={p.project} className="flex items-center justify-between text-xs px-1 py-1">
                  <span>{p.project}</span>
                  <span className="font-semibold">{p.avg_rating}</span>
                </li>
              ))}
            </ul>
          </SectionCard>
          <SectionCard title="Lowest Rated Categories">
            <ul className="flex flex-col gap-1">
              {(data.worst_categories || []).map((c) => (
                <li key={c.category} className="flex items-center justify-between text-xs px-1 py-1">
                  <span>{c.category}</span>
                  <span className="font-semibold">{c.avg_rating}</span>
                </li>
              ))}
            </ul>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
