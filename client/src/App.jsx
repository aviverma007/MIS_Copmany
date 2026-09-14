import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from "recharts";

const COMPANIES = [
  { id: "m3m", name: "M3M MIS", accent: "#C9A648", desc: "Customer complaint dashboard for M3M SFDC exports." },
  { id: "smartworld", name: "Smartworld MIS", accent: "#2BAE8E", desc: "Same engine on the Compile SW Data schema." },
  { id: "nbh", name: "NBH MIS", accent: "#E4572E", desc: "NoBrokerHood facility-management complaint data." },
];

const NAVY = "#1F3864";
const TEAL = "#0F9B8E";
const RED = "#C62828";
const GREEN = "#2E7D32";
const PALETTE = ["#1F3864", "#0F9B8E", "#C9A648", "#E4572E", "#2C4A7C", "#7A8699", "#B67B00", "#2BAE8E"];

// ---------------------------------------------------------------- Login

function Login({ onSignedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) onSignedIn();
      else setError(data.error || "Sign-in failed.");
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  const onKey = (e) => e.key === "Enter" && submit();

  return (
    <div className="login-page">
      <div className="login-hero">
        <div className="wordmark">
          MIS Company <span>/ complaint management suite</span>
        </div>
        <div>
          <h1>One link, three dashboards.</h1>
          <p className="lede">
            Everyone opens the same address. Your username decides which
            company's data and dashboard you see.
          </p>
          <div className="company-list">
            {COMPANIES.map((c) => (
              <div className="company-row" key={c.id}>
                <span className="rail" style={{ background: c.accent }} />
                <span className="cname">{c.name}</span>
                <span className="cdesc">{c.desc}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="foot">
          Internal tool · data comes from the Excel in each company's data
          folder on the server
        </div>
      </div>

      <div className="login-side">
        <div className="login-card">
          <h2>Sign in</h2>
          <p className="hint">Your username decides which application opens.</p>
          <div className="field">
            <label htmlFor="u">Username</label>
            <input id="u" autoFocus autoComplete="username" value={username}
              onChange={(e) => { setUsername(e.target.value); setError(""); }}
              onKeyDown={onKey} />
          </div>
          <div className="field">
            <label htmlFor="p">Password</label>
            <input id="p" type="password" autoComplete="current-password" value={password}
              onChange={(e) => { setPassword(e.target.value); setError(""); }}
              onKeyDown={onKey} />
          </div>
          {error && <p className="login-error">{error}</p>}
          <button className="btn-primary" onClick={submit} disabled={busy}>
            {busy ? "Signing in…" : "Open my dashboard"}
          </button>
          <div className="demo-note">
            Default accounts — change in <code>server/companies.js</code>:<br />
            <code>m3m / M3M@123</code> · <code>smartworld / SW@123</code> ·{" "}
            <code>nbh / NBH@123</code>
          </div>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------ Dashboard

const EMPTY_FILTERS = { project: "", category: "", status: "", priority: "", from: "", to: "", search: "" };

function Dashboard({ me, onSignedOut }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [pageNum, setPageNum] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const query = useMemo(() => {
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && p.set(k, v));
    p.set("page", String(pageNum));
    return p.toString();
  }, [filters, pageNum]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/data?${query}`);
      if (res.status === 401) return onSignedOut();
      setData(await res.json());
    } finally {
      setLoading(false);
    }
  }, [query, onSignedOut]);

  useEffect(() => { fetchData(); }, [fetchData]);

  function setFilter(k, v) {
    setPageNum(1);
    setFilters((f) => ({ ...f, [k]: v }));
  }

  async function reload() {
    await fetch("/api/reload", { method: "POST" });
    fetchData();
  }

  async function signOut() {
    await fetch("/api/logout", { method: "POST" });
    onSignedOut();
  }

  const s = data?.summary;
  const meta = data?.meta;
  const opts = data?.filters;
  const table = data?.table;

  return (
    <div className="shell">
      <header className="app-header">
        <div className="brand">
          <div className="mark" style={{ background: me.accent }}>{me.short}</div>
          <div>
            <h1>{me.title}</h1>
            <div className="meta">
              {meta ? `Source: ${meta.source} · ${meta.totalRecords} records · loaded ${new Date(meta.loadedAt).toLocaleString()}` : "Loading…"}
            </div>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn" onClick={reload}>Reload data</button>
          <a className="btn" style={{ textDecoration: "none" }}
            href={`/api/export?${query}`}>Export Excel</a>
          <button className="btn" onClick={signOut}>Sign out · {me.username}</button>
        </div>
      </header>

      <main className="main">
        {meta?.warnings?.length > 0 && (
          <div className="warnings">{meta.warnings.join(" ")}</div>
        )}

        {!data && loading && <div className="loading">Loading dashboard…</div>}

        {s && (
          <>
            <div className="kpi-row">
              <div className="kpi teal">
                <div className="label">Total Complaints</div>
                <div className="value">{s.kpis.total.toLocaleString()}</div>
                <div className="sub">in current filter</div>
              </div>
              <div className="kpi red">
                <div className="label">Open</div>
                <div className="value">{s.kpis.open.toLocaleString()}</div>
                <div className="sub">need attention</div>
              </div>
              <div className="kpi green">
                <div className="label">Closed</div>
                <div className="value">{s.kpis.closed.toLocaleString()}</div>
                <div className="sub">resolved cases</div>
              </div>
              <div className="kpi amber">
                <div className="label">Closure Rate</div>
                <div className="value">{s.kpis.closureRate}%</div>
                <div className="sub">closed / total</div>
              </div>
              <div className="kpi">
                <div className="label">Avg TAT (closed)</div>
                <div className="value">{s.kpis.avgTat ?? "—"}</div>
                <div className="sub">days to close</div>
              </div>
            </div>

            <div className="filters">
              <div className="f">
                <label>Project</label>
                <select value={filters.project} onChange={(e) => setFilter("project", e.target.value)}>
                  <option value="">All projects</option>
                  {opts.projects.map((p) => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="f">
                <label>Category</label>
                <select value={filters.category} onChange={(e) => setFilter("category", e.target.value)}>
                  <option value="">All categories</option>
                  {opts.categories.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="f">
                <label>Status</label>
                <select value={filters.status} onChange={(e) => setFilter("status", e.target.value)}>
                  <option value="">All</option>
                  <option value="OPEN">Open</option>
                  <option value="CLOSED">Closed</option>
                </select>
              </div>
              <div className="f">
                <label>Priority</label>
                <select value={filters.priority} onChange={(e) => setFilter("priority", e.target.value)}>
                  <option value="">All</option>
                  {opts.priorities.map((p) => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="f">
                <label>Opened from</label>
                <input type="date" value={filters.from} onChange={(e) => setFilter("from", e.target.value)} />
              </div>
              <div className="f">
                <label>Opened to</label>
                <input type="date" value={filters.to} onChange={(e) => setFilter("to", e.target.value)} />
              </div>
              <div className="f">
                <label>Search</label>
                <input placeholder="case no, customer, unit…" value={filters.search}
                  onChange={(e) => setFilter("search", e.target.value)} />
              </div>
              <button className="clear" onClick={() => { setFilters(EMPTY_FILTERS); setPageNum(1); }}>
                Clear filters
              </button>
            </div>

            <div className="grid">
              <div className="panel span-8">
                <h3>Monthly trend — opened vs closed</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={s.trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e3e8f0" />
                    <XAxis dataKey="month" fontSize={11} />
                    <YAxis fontSize={11} allowDecimals={false} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="opened" stroke={RED} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="closed" stroke={GREEN} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="panel span-4">
                <h3>Open vs Closed</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={s.statusSplit} dataKey="count" nameKey="name"
                      innerRadius={55} outerRadius={85} paddingAngle={2}>
                      <Cell fill={RED} />
                      <Cell fill={GREEN} />
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="panel span-4">
                <h3>Open-case ageing</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={s.ageing}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e3e8f0" />
                    <XAxis dataKey="name" fontSize={10} />
                    <YAxis fontSize={11} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#B67B00" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="panel span-4">
                <h3>Top projects</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={s.topProjects} layout="vertical" margin={{ left: 30 }}>
                    <XAxis type="number" fontSize={11} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" fontSize={10} width={110} />
                    <Tooltip />
                    <Bar dataKey="count" fill={NAVY} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="panel span-4">
                <h3>Top categories</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={s.topCategories} layout="vertical" margin={{ left: 30 }}>
                    <XAxis type="number" fontSize={11} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" fontSize={10} width={110} />
                    <Tooltip />
                    <Bar dataKey="count" fill={TEAL} radius={[0, 4, 4, 0]}>
                      {s.topCategories.map((_, i) => (
                        <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="panel span-12">
                <h3>Complaints ({table.total.toLocaleString()})</h3>
                <div style={{ overflowX: "auto" }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Case/Ticket</th><th>Customer</th><th>Project</th><th>Unit</th>
                        <th>Category</th><th>Priority</th><th>Owner</th>
                        <th>Opened</th><th>Closed</th><th>TAT</th><th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {table.rows.map((r) => (
                        <tr key={r.id + r.opened}>
                          <td>{r.id}</td>
                          <td>{r.customer}</td>
                          <td>{r.project}</td>
                          <td>{r.unit}</td>
                          <td>{r.category}</td>
                          <td>{r.priority}</td>
                          <td>{r.owner}</td>
                          <td>{r.opened}</td>
                          <td>{r.closed || "—"}</td>
                          <td>{r.tatDays ?? "—"}</td>
                          <td>
                            <span className={`pill ${r.statusClass === "CLOSED" ? "closed" : "open"}`}>
                              {r.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pager">
                  <span>Page {table.page} of {table.pages}</span>
                  <button disabled={table.page <= 1} onClick={() => setPageNum((p) => p - 1)}>Prev</button>
                  <button disabled={table.page >= table.pages} onClick={() => setPageNum((p) => p + 1)}>Next</button>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

// ------------------------------------------------------------------ App

export default function App() {
  const [me, setMe] = useState(undefined); // undefined = checking

  const check = useCallback(async () => {
    try {
      const res = await fetch("/api/me");
      const data = await res.json();
      setMe(data.signedIn ? data : null);
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => { check(); }, [check]);

  if (me === undefined) return <div className="loading">Loading…</div>;
  if (!me) return <Login onSignedIn={check} />;
  return <Dashboard me={me} onSignedOut={() => setMe(null)} />;
}
