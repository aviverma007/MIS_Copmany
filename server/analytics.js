// Filters + KPIs + breakdowns computed fresh from the loaded records on
// every request, exactly like the original apps: nothing is hard-coded,
// every number is recomputed from whatever Excel is currently in the folder.

function applyFilters(records, q) {
  let out = records;
  if (q.project) out = out.filter((r) => r.project === q.project);
  if (q.category) out = out.filter((r) => r.category === q.category);
  if (q.status === "OPEN" || q.status === "CLOSED")
    out = out.filter((r) => r.statusClass === q.status);
  if (q.priority) out = out.filter((r) => r.priority === q.priority);
  if (q.from) out = out.filter((r) => r.opened && r.opened >= q.from);
  if (q.to) out = out.filter((r) => r.opened && r.opened <= q.to);
  if (q.search) {
    const s = String(q.search).toLowerCase();
    out = out.filter(
      (r) =>
        r.id.toLowerCase().includes(s) ||
        r.customer.toLowerCase().includes(s) ||
        r.subject.toLowerCase().includes(s) ||
        r.unit.toLowerCase().includes(s) ||
        r.owner.toLowerCase().includes(s)
    );
  }
  return out;
}

function topCounts(records, key, limit = 8) {
  const m = new Map();
  for (const r of records) {
    const k = r[key] || "—";
    m.set(k, (m.get(k) || 0) + 1);
  }
  return [...m.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name, count]) => ({ name, count }));
}

function summary(records) {
  const total = records.length;
  const open = records.filter((r) => r.statusClass === "OPEN");
  const closed = records.filter((r) => r.statusClass === "CLOSED");
  const tats = closed.map((r) => r.tatDays).filter((t) => t != null);
  const avgTat = tats.length
    ? Math.round((tats.reduce((a, b) => a + b, 0) / tats.length) * 10) / 10
    : null;

  // monthly trend: opened + closed per month
  const months = new Map();
  for (const r of records) {
    if (r.openedMonth) {
      const e = months.get(r.openedMonth) || { month: r.openedMonth, opened: 0, closed: 0 };
      e.opened += 1;
      months.set(r.openedMonth, e);
    }
    if (r.closed) {
      const cm = r.closed.slice(0, 7);
      const e = months.get(cm) || { month: cm, opened: 0, closed: 0 };
      e.closed += 1;
      months.set(cm, e);
    }
  }
  const trend = [...months.values()].sort((a, b) => a.month.localeCompare(b.month)).slice(-12);

  // open-case ageing buckets
  const ageing = {};
  for (const r of open) ageing[r.ageBucket] = (ageing[r.ageBucket] || 0) + 1;
  const AGE_ORDER = ["0-3 days", "4-7 days", "8-15 days", "16-30 days", "30+ days", "Unknown"];
  const ageingList = AGE_ORDER.filter((b) => ageing[b]).map((b) => ({ name: b, count: ageing[b] }));

  return {
    kpis: {
      total,
      open: open.length,
      closed: closed.length,
      closureRate: total ? Math.round((closed.length / total) * 1000) / 10 : 0,
      avgTat,
    },
    statusSplit: [
      { name: "Open", count: open.length },
      { name: "Closed", count: closed.length },
    ],
    trend,
    ageing: ageingList,
    topProjects: topCounts(records, "project"),
    topCategories: topCounts(records, "category"),
    topOwners: topCounts(records, "owner", 6),
  };
}

function filterOptions(records) {
  const uniq = (key) =>
    [...new Set(records.map((r) => r[key]).filter((v) => v && v !== "—"))].sort();
  return {
    projects: uniq("project"),
    categories: uniq("category"),
    priorities: uniq("priority"),
  };
}

function page(records, pageNum = 1, pageSize = 25) {
  const p = Math.max(1, pageNum | 0);
  const size = Math.min(200, Math.max(5, pageSize | 0));
  const sorted = [...records].sort((a, b) => (b.opened || "").localeCompare(a.opened || ""));
  return {
    total: records.length,
    page: p,
    pageSize: size,
    pages: Math.max(1, Math.ceil(records.length / size)),
    rows: sorted.slice((p - 1) * size, p * size),
  };
}

module.exports = { applyFilters, summary, filterOptions, page };
