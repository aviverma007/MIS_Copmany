// Pure presentation helpers. No business rules (ageing thresholds, status
// classification, category mapping, RAG rules) live here -- those all come
// from the API.

export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString("en-IN");
}

export function formatPct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toFixed(digits)}%`;
}

export function formatDays(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toFixed(1)}d`;
}

export function formatChangePct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const v = Number(value);
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

export function changeDirection(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "flat";
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

export function formatValue(value) {
  // Generic KPI value formatter -- integers render plain, decimals to 1dp.
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (Number.isInteger(value)) return formatNumber(value);
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
}

export function titleCase(str) {
  if (!str) return "";
  return String(str)
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function truncate(str, len = 80) {
  if (!str) return "";
  return str.length > len ? `${str.slice(0, len)}…` : str;
}
