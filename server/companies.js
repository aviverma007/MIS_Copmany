// ---------------------------------------------------------------------------
// Company + account configuration.
//
// THREE LOGINS -> THREE COMPANIES -> THREE EXCEL FOLDERS.
// Change passwords here. Drop each company's Excel into its data/ folder
// (any .xlsx file; the newest one in the folder is used).
//
// Column aliases below are taken from the original M3M / Smartworld / NBH
// applications, so the real SFDC / NBH exports map automatically.
// ---------------------------------------------------------------------------

const ACCOUNTS = {
  m3m:        { password: "M3M@123", company: "m3m" },
  smartworld: { password: "SW@123",  company: "smartworld" },
  nbh:        { password: "NBH@123", company: "nbh" },
};

// Raw status values (lowercased) treated as CLOSED for management reporting.
// Anything unrecognized counts as OPEN - the safer default.
const CLOSED_STATUSES = [
  "closed", "resolved", "completed", "complete", "done",
  "closed - resolved", "resolved - closed", "cancelled", "canceled",
  "closed_resolved", "rejected",
];

// Canonical record fields every company maps into:
//   id, customer, subject, project, unit, category, subCategory, status,
//   priority, owner, source, opened, closed
// (statusClass, tatDays, ageBucket, openedMonth are derived by the loader.)

const COMPANIES = {
  m3m: {
    title: "M3M Customer Complaint MIS",
    short: "M3M",
    accent: "#C9A648",
    dataDir: "m3m",
    dayFirstDates: true,
    aliases: {
      id:          ["case number", "case no", "ticket number", "ticket no", "complaint number"],
      customer:    ["account name", "customer name", "client name", "customer"],
      subject:     ["subject"],
      priority:    ["priority"],
      category:    ["m_category", "m category", "mcategory", "management category", "service category"],
      subCategory: ["sub category", "subcategory", "sub-category"],
      opened:      ["opened date", "open date", "date opened", "received date", "created date", "case created date"],
      closed:      ["closed date", "close date", "date closed", "resolution date", "resolved date"],
      owner:       ["case owner", "owner name", "assigned to", "owner"],
      status:      ["case status"],
      source:      ["case source", "case origin", "channel"],
      project:     ["project name"],
      unit:        ["project unit", "unit number", "unit no"],
    },
  },

  smartworld: {
    title: "Smartworld Customer Complaint MIS",
    short: "SW",
    accent: "#2BAE8E",
    dataDir: "smartworld",
    dayFirstDates: true,
    aliases: {
      id:          ["case number", "case no", "ticket number", "ticket no", "complaint number"],
      customer:    ["account name", "customer name", "client name", "customer"],
      subject:     ["subject"],
      priority:    ["priority"],
      category:    ["m_category", "m category", "mcategory", "management category", "service category"],
      subCategory: ["sub category", "subcategory", "sub-category"],
      // "Date/Time Opened" normalizes to "date time opened"
      opened:      ["opened date", "open date", "date opened", "received date", "created date", "date time opened"],
      closed:      ["closed date", "close date", "date closed", "resolution date", "resolved date"],
      owner:       ["case owner", "owner name", "assigned to", "owner"],
      status:      ["case status", "status"],
      source:      ["case source", "case origin", "channel"],
      project:     ["project name", "project"],
      unit:        ["project unit", "unit number", "unit no", "property"],
    },
  },

  nbh: {
    title: "NBH Complaint Management Dashboard",
    short: "NBH",
    accent: "#E4572E",
    dataDir: "nbh",
    dayFirstDates: true,
    aliases: {
      id:          ["ticket id", "ticket no", "ticket number", "id"],
      customer:    ["created by"],
      subject:     ["description", "last comment"],
      priority:    ["priority"],
      category:    ["category"],
      subCategory: ["sub category", "subcategory"],
      opened:      ["created on", "created date", "creation date"],
      // F_Closed priority from the original workbook: Closed Time, then
      // Resolved Time, then Last updated on (first non-blank wins).
      closed:      ["closed time", "resolved time", "last updated on", "last update", "updated on"],
      owner:       ["current assignee", "assignee"],
      status:      ["status"],
      source:      ["source"],
      project:     ["society name", "project", "project name", "site name"],
      unit:        ["reported_from(apartment)", "reported from apartment", "apartment"],
    },
  },
};

module.exports = { ACCOUNTS, COMPANIES, CLOSED_STATUSES };
