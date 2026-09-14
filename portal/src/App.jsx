import { useEffect, useState } from "react";
import { ACCOUNTS, authenticate } from "./accounts.js";

const SESSION_KEY = "mis_portal_session";

function loadSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const { id } = JSON.parse(raw);
    return ACCOUNTS.find((a) => a.id === id) || null;
  } catch {
    return null;
  }
}

function Login({ onSignedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function submit() {
    const account = authenticate(username, password);
    if (!account) {
      setError("Username or password is incorrect for all three applications.");
      return;
    }
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ id: account.id }));
    onSignedIn(account);
  }

  function onKeyDown(e) {
    if (e.key === "Enter") submit();
  }

  return (
    <div className="login">
      <div className="login-left">
        <div className="wordmark">
          MIS Company <span>/ complaint management suite</span>
        </div>

        <div className="left-body">
          <h1>One sign-in, three dashboards.</h1>
          <p className="lede">
            Each account opens the MIS it belongs to. Sign in with your team's
            credentials and you land directly in your application.
          </p>

          <div className="ledger">
            {ACCOUNTS.map((a) => (
              <div className="ledger-row" key={a.id}>
                <span
                  className="ledger-rail"
                  style={{ background: a.accent }}
                />
                <span className="ledger-name">{a.app}</span>
                <span className="ledger-desc">{a.description}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="left-foot">
          Internal tool · runs on your local network · sessions end when the
          tab closes
        </div>
      </div>

      <div className="login-right">
        <div className="card">
          <h2>Sign in</h2>
          <p className="hint">
            Your username decides which application opens.
          </p>

          <div className="field">
            <label htmlFor="u">Username</label>
            <input
              id="u"
              autoFocus
              autoComplete="username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError("");
              }}
              onKeyDown={onKeyDown}
            />
          </div>

          <div className="field">
            <label htmlFor="p">Password</label>
            <input
              id="p"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError("");
              }}
              onKeyDown={onKeyDown}
            />
          </div>

          {error && <p className="error">{error}</p>}

          <button className="primary" onClick={submit}>
            Open my application
          </button>

          <div className="demo-creds">
            Default accounts — change them in{" "}
            <code>portal/src/accounts.js</code>:
            <br />
            <code>m3m / M3M@123</code> · <code>smartworld / SW@123</code> ·{" "}
            <code>nbh / NBH@123</code>
          </div>
        </div>
      </div>
    </div>
  );
}

function Shell({ account, onSignOut }) {
  useEffect(() => {
    document.title = `${account.app} — MIS Company`;
  }, [account]);

  return (
    <div className="shell">
      <div className="topbar">
        <span className="dot" style={{ background: account.accent }} />
        <span className="app-name">{account.fullName}</span>
        <span className="who">signed in as {account.username}</span>
        <span className="spacer" />
        <a href={account.url} target="_blank" rel="noreferrer">
          Open in new tab
        </a>
        <button className="ghost" onClick={onSignOut}>
          Sign out
        </button>
      </div>
      <div className="frame-wrap">
        <iframe title={account.fullName} src={account.url} />
      </div>
      <div className="frame-note">
        If the dashboard shows a connection error, its backend isn't running —
        start everything with <b>python start_all.py</b> from the repository
        root ({account.url}).
      </div>
    </div>
  );
}

export default function App() {
  const [account, setAccount] = useState(loadSession);

  function signOut() {
    sessionStorage.removeItem(SESSION_KEY);
    setAccount(null);
  }

  return account ? (
    <Shell account={account} onSignOut={signOut} />
  ) : (
    <Login onSignedIn={setAccount} />
  );
}
