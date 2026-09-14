// The three portal logins, one per application.
// Change usernames/passwords here; change ports if you launch the
// backends elsewhere (keep in sync with start_all.py).

const HOST = window.location.hostname || "localhost";

export const ACCOUNTS = [
  {
    id: "m3m",
    username: "m3m",
    password: "M3M@123",
    app: "M3M MIS",
    fullName: "M3M Customer Complaint MIS",
    description: "Complaint dashboard, SLA/TAT tracking and exports for M3M SFDC data.",
    accent: "#C9A648",
    url: `http://${HOST}:8001/`,
  },
  {
    id: "sw",
    username: "smartworld",
    password: "SW@123",
    app: "Smartworld MIS",
    fullName: "Smartworld Customer Complaint MIS",
    description: "Same engine tuned to the Compile SW Data schema and Smartworld lists.",
    accent: "#2BAE8E",
    url: `http://${HOST}:8002/`,
  },
  {
    id: "nbh",
    username: "nbh",
    password: "NBH@123",
    app: "NBH MIS",
    fullName: "NBH Complaint Management Dashboard",
    description: "NoBrokerHood facility-management data: executive view, reports, tracker.",
    accent: "#E4572E",
    url: `http://${HOST}:8003/`,
  },
];

export function authenticate(username, password) {
  const u = username.trim().toLowerCase();
  return (
    ACCOUNTS.find((a) => a.username === u && a.password === password) || null
  );
}
