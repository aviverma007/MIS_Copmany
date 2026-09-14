const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, BorderStyle, PageBreak, ExternalHyperlink,
  Header, Footer, PageNumber, NumberFormat,
} = require("docx");

const NAVY = "1F3864";
const TEAL = "0F9B8E";
const LIGHTGREY = "F2F5FA";
const DARKGREY = "4A5568";

function h1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 140 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 260, after: 120 } });
}
function p(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, ...opts })],
    spacing: { after: 140 },
  });
}
function bullet(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, ...opts })],
    bullet: { level: 0 },
    spacing: { after: 60 },
  });
}

function cellHeader(text, width) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: NAVY },
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: "FFFFFF", size: 18 })] })],
  });
}
function cell(text, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    shading: opts.shade ? { type: ShadingType.CLEAR, fill: LIGHTGREY } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text: String(text), size: 18, ...opts })] })],
  });
}

function fieldTable(rows, widths, headers) {
  const headerRow = new TableRow({ children: headers.map((h, i) => cellHeader(h, widths[i])), tableHeader: true });
  const bodyRows = rows.map((r, idx) => new TableRow({
    children: r.map((val, i) => cell(val, widths[i], { shade: idx % 2 === 1 })),
  }));
  return new Table({ width: { size: 9350, type: WidthType.DXA }, rows: [headerRow, ...bodyRows] });
}

// ---------------------------------------------------------------------------
// Field mapping data (canonical field -> detected column in the sample file,
// description, and where it is used in the application)
// ---------------------------------------------------------------------------
const FIELD_ROWS = [
  ["Case Number", "Case Number", "Unique case/ticket identifier.", "Primary key for every count (KPIs use a unique-case-number count)"],
  ["Account Name", "Account Name", "Customer / account name.", "Case table, case detail view"],
  ["Subject", "Subject", "Free-text case subject line.", "Case table, case detail view, search"],
  ["Priority", "Priority", "Priority assigned in the source system.", "Priority analysis, Management Attention (high-priority pending)"],
  ["M_Category", "M_Category", "Management-level rollup category.", "M_Category analysis, category charts"],
  ["Service Category", "Service Category", "Detailed service category.", "Service Category analysis, Top/Bottom 5, category charts"],
  ["Opened Date", "Opened Date", "Date the case was received/opened.", "Default date used for all trend, ageing and date-range filtering"],
  ["Closed Date", "Closed Date", "Date the case was closed.", "TAT / resolution-trend calculations"],
  ["Case Owner", "Case Owner", "Individual handling the case.", "Case Owner analysis, filters, Management Attention (missing owner)"],
  ["Case Type", "Case Type", "Query / Complaint classification.", "Case table, filters"],
  ["Case Status", "Case Status", "Raw status text (Closed, In progress, New, Re-Open...).", "Normalized into the Open/Closed status bucket used for every KPI"],
  ["Sub Category", "Sub Category", "Granular category under Service Category.", "Sub Category analysis, filters"],
  ["Case Source", "Case Source", "Originating inbound channel/address.", "Filters, case detail view"],
  ["Case Origin", "Case Origin", "Channel the case arrived through.", "Case detail view, filters"],
  ["Case Ageing", "Case Ageing", "Days the case has been open (as supplied).", "Avg Case Age KPI, ageing bucket analysis, Attention (30+ days)"],
  ["Escalation", "Is Escalated closure", "Escalation / closure-quality text.", "Parsed into the Escalated / Not Escalated flag used everywhere"],
  ["Project Name", "Project Name", "M3M project / property.", "Project analysis, Top/Bottom 5, cross-filtering"],
  ["Project Unit", "Project Unit", "Unit number within the project.", "Case table, case detail view"],
  ["Team Leader", "Team Leader", "Team Leader over the case owner.", "Team Leader analysis, filters"],
  ["HOD", "HOD 1", "Head of Department.", "HOD analysis, filters"],
  ["Client Category", "Client Category", "VIP / Legal / Blacklisted / Whitelisted / HWC.", "Client Category analysis, filters"],
  ["Updated Status", "Updated Status", "Simplified status (fallback if Case Status is absent).", "Status bucket fallback, filters"],
  ["TAT Days", "TAT Days", "Turnaround time in days.", "Avg TAT KPI, SLA breach fallback, Attention (unusually high TAT)"],
  ["SLAB", "SLAB", "SLA bucket label (e.g. \u201c0 to 2\u201d, \u201cMore than 30\u201d).", "SLA analysis, SLA Breach % KPI"],
  ["IA Status", "IA Status", "Internal Audit status, where present.", "Case detail view, filters"],
  ["IA Remarks", "IA Remarks", "Internal Audit remarks, where present.", "Case detail view"],
];

const DERIVED_ROWS = [
  ["year / month_num / month_name / quarter / week / day / day_name", "Calendar breakdown of Opened Date.", "Year/Month filters, Monthly & Yearly analysis"],
  ["status_bucket / Updated Status", "\u201cOpen\u201d if Case Status is In Progress, New, Submit For Approval, or Re-Open; \u201cClosed\u201d otherwise \u2014 the exact rule from the source workbook's Updated Status formula (see Section 6).", "Every KPI and report (Open/Closed/Pending/Resolved counts)"],
  ["is_new / is_reopen / is_in_progress", "Booleans parsed from Case Status text.", "New Cases KPI, Pending Cases KPI"],
  ["is_escalated / escalated_label", "Boolean + label parsed from the Escalation field.", "Escalated Cases KPI, Escalation analysis, Attention (escalated open)"],
  ["is_sla_breach", "True when SLAB is outside the configured \u201cwithin-SLA\u201d bucket(s) (default: \u201c0 to 2\u201d).", "SLA Breach % KPI, SLA analysis"],
  ["ageing_bucket", "Case Ageing (SFDC's own field) grouped into 0-2 / 3-7 / 8-15 / 16-30 / 30+ days.", "Case Ageing analysis"],
  ["received_bucket", "\u201cToday\u201d if Opened Date is the most recent date in this upload, else \u201cOlder\u201d.", "Filters, case detail view"],
  ["closed_bucket", "\u201cToday\u201d if Closed Date equals Opened Date (resolved same day), else \u201cOlder\u201d.", "Filters, case detail view"],
];

const KPI_ROWS = [
  ["Total Cases", "Count of distinct Case Number in the filtered data."],
  ["Open Cases", "Distinct cases where status_bucket = Open."],
  ["Closed Cases", "Distinct cases where status_bucket = Closed."],
  ["Pending Cases", "Open cases excluding those marked New (i.e. already picked up but not yet resolved)."],
  ["New Cases", "Cases whose Case Status indicates \u201cNew\u201d."],
  ["Resolved Cases", "Same population as Closed Cases (the source data has no separate \u201cResolved\u201d state)."],
  ["Escalated Cases", "Distinct cases where is_escalated is True."],
  ["Avg Case Age", "Mean Case Ageing across currently Open cases."],
  ["Avg TAT", "Mean TAT Days across Closed cases."],
  ["SLA Breach %", "Share of Closed cases flagged is_sla_breach."],
  ["Resolution %", "Closed cases \u00f7 Total cases."],
  ["Closure %", "Same calculation as Resolution % (both KPIs are shown per the spec; they will diverge if a future workbook distinguishes \u201cresolved\u201d from \u201cclosed\u201d)."],
];

const BUSINESS_RULE_ROWS = [
  ["F_Closed / Closed Date", "=IF(Closed_Date<>\"\",Closed_Date,\"\")", "Closed Date if the case is closed, otherwise blank \u2014 a clean copy, not a new value."],
  ["Received bucket", "=IF(MAX(all Open Dates)=this row's Open Date,\"Today\",\"Older\")", "Flags cases opened on the most recent date present in the upload."],
  ["Closed bucket", "=IF(Closed_Date=Open_Date,\"Today\",\"Older\")", "Flags cases resolved the same day they were opened."],
  ["Updated Status", "=IF(Case_Status is In Progress/New/Submit For Approval/Re-Open,\"OPEN\",\"Closed\")", "The authoritative Open/Closed state used by every KPI."],
  ["TAT Days", "=IF(Closed,Closed_Date\u2212Opened_Date,TODAY()\u2212Opened_Date)", "Final resolution time for closed cases; running age for still-open cases \u2014 recalculated every time the app is used, never a stale saved number."],
  ["SLAB", "=IF(TAT>30,\"More than 30\",IF(TAT>15,\"16 to 30\",IF(TAT>7,\"8 to 15\",IF(TAT>2,\"3 to 7\",\"0 to 2\"))))", "Buckets the freshly-computed TAT Days above."],
  ["M_Category", "=XLOOKUP(Service_Category, LIST!Category, LIST!M_Category, \"Others/Misc\")", "Looked up from the current Manage Lists Category mapping (Section 15), not read from the source file."],
];

const RAG_ROWS = [
  ["Resolution %", "\u2265 90%", "75% \u2013 89.99%", "< 75%"],
  ["Closure %", "\u2265 90%", "75% \u2013 89.99%", "< 75%"],
  ["SLA Breach %  (lower is better)", "\u2264 10%", "10.01% \u2013 25%", "> 25%"],
  ["Data Quality Score", "\u2265 95%", "85% \u2013 94.99%", "< 85%"],
];

const REPORT_ROWS = [
  ["Project Analysis", "project_name", "Case volume, resolution and SLA performance per M3M project."],
  ["Service Category Analysis", "service_category", "Volume and performance per detailed service category."],
  ["M_Category Analysis", "m_category", "Volume and performance per management rollup category."],
  ["SLA (SLAB) Analysis", "slab", "Case distribution across the SLA buckets supplied in the workbook."],
  ["Priority Analysis", "priority", "Volume and performance per priority level."],
  ["Escalation Analysis", "escalated_label", "Escalated vs Not Escalated volumes and outcomes."],
  ["Case Owner Analysis", "case_owner", "Per-individual caseload and performance."],
  ["Team Leader Analysis", "team_leader", "Roll-up of case owner performance by Team Leader."],
  ["HOD Analysis", "hod", "Roll-up by Head of Department."],
  ["Client Category Analysis", "client_category", "Performance split for VIP / Legal / Blacklisted / Whitelisted / HWC customers."],
  ["Sub Category Analysis", "sub_category", "Volume per granular sub-category."],
  ["Case Status Analysis", "case_status", "Raw status distribution."],
  ["Case Ageing Analysis", "ageing_bucket", "Distribution of open cases across ageing buckets."],
  ["Top 5 / Bottom 5", "project_name, service_category", "Highest- and lowest-volume projects and categories."],
];

const DQ_ROWS = [
  ["Blank Case Number", "Rows with no case identifier."],
  ["Duplicate Case Number", "Case numbers appearing more than once."],
  ["Blank Project", "Rows with no Project Name."],
  ["Blank Case Owner", "Rows with no Case Owner."],
  ["Blank Service Category", "Rows with no Service Category."],
  ["Invalid Opened Date", "Rows where Opened Date could not be parsed."],
  ["Invalid / Missing Closed Date", "Closed cases with no Closed Date."],
  ["Open With Closed Date Set", "Cases still marked Open but carrying a Closed Date."],
  ["Negative TAT", "TAT Days less than zero (Closed Date earlier than Opened Date)."],
  ["Missing SLAB", "Rows with no SLA bucket assigned."],
  ["Missing HOD", "Rows with no HOD assigned."],
  ["Missing Team Leader", "Rows with no Team Leader assigned."],
];

const ATTENTION_ROWS = [
  ["Over 30 Days", "Open cases with Case Ageing > 30 days."],
  ["High Priority Pending", "Open cases whose Priority contains \u201cHigh\u201d."],
  ["Escalated Open", "Open cases flagged is_escalated."],
  ["Missing Owner", "Cases with no Case Owner assigned."],
  ["Missing Project", "Cases with no Project Name assigned."],
  ["Closed Without Date", "Closed cases with no Closed Date."],
  ["Unusually High TAT", "Closed cases with TAT Days above the configured threshold (default 15 days)."],
  ["Missing Mandatory Info", "Cases missing Case Owner, Project Name, or Service Category."],
];

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 21, color: "1A2233" } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: NAVY, font: "Calibri" },
        paragraph: { spacing: { before: 320, after: 140 }, border: { bottom: { color: TEAL, space: 4, style: BorderStyle.SINGLE, size: 8 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: NAVY, font: "Calibri" },
        paragraph: { spacing: { before: 260, after: 120 } } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "M3M Customer Complaint MIS \u2014 Field Mapping & Reference Guide", size: 15, color: DARKGREY })],
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Page ", size: 15, color: DARKGREY }), new TextRun({ children: [PageNumber.CURRENT], size: 15, color: DARKGREY })],
      })] }),
    },
    children: [
      new Paragraph({
        children: [new TextRun({ text: "M3M Customer Complaint MIS", bold: true, size: 48, color: NAVY })],
        spacing: { after: 80 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Field Mapping & Application Reference Guide", size: 26, color: TEAL, bold: true })],
        spacing: { after: 40 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Version 2 \u2014 adds SFDC date normalization, business-rule formulas, and the Manage Lists admin screen", size: 15, color: TEAL, bold: true })],
        spacing: { after: 12 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Companion document to m3m_mis_app.py \u00b7 Generated from M3M_Sample_Template.xlsx, Compile_M3M_Data.xlsx, and LIST.xlsx", size: 18, color: DARKGREY, italics: true })],
        spacing: { after: 400 },
      }),

      h1("1. What This Document Is"),
      p("This is the supporting reference for the M3M Customer Complaint MIS application (m3m_mis_app.py). It explains exactly how each column in the \u201cCompile M3M Data\u201d sheet is detected and used, what every KPI and report means, how the app normalizes SFDC's date formats and replicates the workbook's formula fields, how the Manage Lists admin screen works, and how to adjust the built-in business rules. It was generated against the attached sample workbooks, on which every field below was detected \u2014 or, for the formula fields, independently verified against the workbook's own Excel formulas \u2014 automatically, with no manual mapping required."),

      h1("2. Quick Start"),
      bullet("Install Python 3.9+ (Windows: python.org, tick \u201cAdd python.exe to PATH\u201d)."),
      bullet("Double-click m3m_mis_app.py, or run:  python m3m_mis_app.py"),
      bullet("The first run installs a few Python packages automatically (needs internet once)."),
      bullet("A browser tab opens automatically at http://127.0.0.1:8000 once the server is ready."),
      bullet("Upload your M3M workbook (.xlsx) \u2014 it must contain a sheet named \u201cCompile M3M Data\u201d."),
      bullet("Press Ctrl+C in the terminal window to stop the app. Nothing is written to disk except the app\u2019s own program files \u2014 uploaded data lives only in memory for that session."),

      h1("3. How Column Detection Works"),
      p("The app never assumes column position. On upload, it normalizes every header in \u201cCompile M3M Data\u201d (lower-cased, punctuation-stripped) and matches it against a list of accepted aliases for each of the 26 fields below \u2014 first trying an exact match, then a \u201ccontains\u201d match. Each source column can only be claimed by one field, so duplicate or derived helper columns in the workbook (for example the leftover pivot-style columns some exports include) are never mistaken for the real data. If a workbook uses different wording \u2014 \u201cTicket No.\u201d instead of \u201cCase Number,\u201d for example \u2014 it will usually still be recognized; fields that truly can\u2019t be found are listed back to the user after upload rather than silently ignored."),

      h1("4. Field Mapping (Detected From the Attached Sample File)"),
      fieldTable(
        FIELD_ROWS,
        [1750, 1750, 3600, 2250],
        ["Canonical Field", "Detected Column (this file)", "Description", "Used In"]
      ),

      new Paragraph({ children: [new PageBreak()] }),

      h1("5. SFDC Date Normalization"),
      p("Salesforce report exports commonly deliver Opened Date and Closed Date as plain text rather than real Excel dates \u2014 typically \u201c08/09/2026\u201d or \u201c08/09/2026, 11:05 am\u201d \u2014 and a single export often mixes both shapes in the same column (some rows with a time-of-day, some without). Read literally with the wrong assumption, \u201c08/09/2026\u201d is ambiguous between 8-Sep and 9-Aug; this workbook's convention is day-first (dd/mm/yyyy), confirmed by dates such as \u201c31/05/2026\u201d that are only valid one way."),
      p("The app parses every date field with that day-first convention, using a fast vectorized pass for a whole column at once and falling back to a slower, exact element-by-element parse only for the specific values that need it (typically the mixed date+time rows) \u2014 so accuracy does not come at the cost of speed on large files. Once parsed, every date displays as DD-MMM-YYYY (e.g. 08-Sep-2026) throughout the dashboard, case table, case detail view, and both exports."),

      h1("6. Business-Rule Formulas (Computed Fresh Each Time)"),
      p("The original Excel template computed several fields with live formulas \u2014 =TODAY(), =XLOOKUP(...) against the LIST sheet, and so on \u2014 which only stay correct while the workbook itself is open and recalculating. A raw data export carries none of that logic, so the app recreates each formula itself in Python, computed fresh every time data is uploaded and again whenever the Category mapping is edited (Section 15) \u2014 never a stale value copied from a file that can no longer recalculate."),
      fieldTable(
        BUSINESS_RULE_ROWS,
        [2200, 3550, 3600],
        ["Field", "Formula (source workbook)", "What It Means"]
      ),
      p("Every one of these was verified field-for-field against the actual Excel formulas in the source workbook and against its computed output on real rows \u2014 the Python logic and the original spreadsheet agree exactly.", { italics: true, size: 18, color: DARKGREY }),

      new Paragraph({ children: [new PageBreak()] }),

      h1("7. Derived Fields (Computed, Not in the Source File)"),
      p("These fields do not exist in the workbook \u2014 the app computes them from the fields above every time data is uploaded or filtered."),
      fieldTable(
        DERIVED_ROWS,
        [3200, 4150, 2000],
        ["Derived Field", "How It's Calculated", "Used In"]
      ),

      h1("8. KPI Definitions"),
      fieldTable(
        KPI_ROWS.map(r => [r[0], r[1]]),
        [2400, 6950],
        ["KPI", "Definition"]
      ),

      h1("9. RAG (Red / Amber / Green) Thresholds"),
      p("All thresholds live in one CONFIG dictionary near the top of the embedded engine module, so they can be tuned without touching any calculation logic."),
      fieldTable(
        RAG_ROWS,
        [2900, 2150, 2150, 2150],
        ["Metric", "Green", "Amber", "Red"]
      ),

      new Paragraph({ children: [new PageBreak()] }),

      h1("10. Reports & Analysis"),
      fieldTable(
        REPORT_ROWS,
        [2400, 2150, 4800],
        ["Report", "Grouped By", "What It Shows"]
      ),

      h2("Daily Trend"),
      p("Reproduces and extends the workbook\u2019s \u201cDate Wise summary\u201d, computed fresh from the transactional data (not copied from the sheet). For every day in the Opened Date range it calculates:"),
      bullet("Carry Forward \u2014 cases opened before that day and still open going into it."),
      bullet("Today Received \u2014 cases opened on that day."),
      bullet("Old Resolved / Current Resolved \u2014 cases closed that day, split by whether they were opened on an earlier day or the same day."),
      bullet("Total Pending \u2014 cases opened on/before that day that remain open as of that day."),
      bullet("%Cont (Recd vs Closed) \u2014 total resolved that day \u00f7 total complaints that day."),
      p("This calculation is fully vectorized (no per-row Python loop) so it stays fast even at 500,000+ records.", { italics: true, size: 18, color: DARKGREY }),

      h1("11. Management Attention (Exceptions)"),
      fieldTable(
        ATTENTION_ROWS,
        [2400, 6950],
        ["Area", "Definition"]
      ),

      h1("12. Data Quality Checks"),
      p("The Data Quality Score = (records with none of the issues below) \u00f7 (total records) \u00d7 100."),
      fieldTable(
        DQ_ROWS,
        [2900, 6450],
        ["Check", "Definition"]
      ),

      new Paragraph({ children: [new PageBreak()] }),

      h1("13. Filters"),
      p("Every dimension below supports multi-select. Selecting several values within one dimension is an OR (e.g. Project = Crown OR Capital); selections across different dimensions combine with AND (e.g. (Project = Crown OR Capital) AND (Priority = High)). A Date Range filter on Opened Date is also available. The Active Filters bar shows every selection as a removable chip, plus a one-click Reset All."),
      p("Project, Month, and Year options are the union of the current upload and the master lists maintained on the Manage Lists screen (Section 15) \u2014 so a project with zero current cases can still be selected, e.g. to confirm there are none."),
      bullet("Project Name, Case Status, Updated Status, Priority, Service Category, M_Category, Sub Category"),
      bullet("Case Owner, Team Leader, HOD, Client Category, Case Source, Case Type"),
      bullet("Escalation, SLAB, IA Status, Year, Month, Received Today?, Closed Same Day?"),

      h1("14. Exports"),
      h2("Excel Report (Download Excel)"),
      p("A formatted, multi-sheet workbook built from whatever is currently filtered on screen: Executive Summary, Filter Summary, Project Analysis, Category Analysis, SLA Analysis, Date Wise Analysis, Monthly Analysis, Owner Analysis, HOD/TL Analysis, and Detailed Data \u2014 with frozen header rows, auto-sized columns, and a formatted data table."),
      h2("PDF Report (Download PDF Report)"),
      p("A complete multi-page report: executive dashboard, project analysis, category/SLA analysis, daily/monthly trend charts, priority/escalation analysis, owner/TL/HOD analysis, data quality, and management attention."),
      h2("Executive One-Pager (Download One-Pager)"),
      p("A single printable page \u2014 KPI cards, top-project and category charts, the received-vs-resolved trend, SLA distribution, management attention, and key insights \u2014 designed for a quick daily/weekly leadership read."),

      new Paragraph({ children: [new PageBreak()] }),

      h1("15. Manage Lists (Admin Screen)"),
      p("A \u201cManage Lists\u201d tab in the main navigation lets an authorized user maintain the data that drives the Project/Month/Year filter dropdowns and the Category \u2192 M_Category lookup (Section 6), without touching this document or the application's source code."),
      h2("Viewer vs Admin"),
      p("By default the screen opens in read-only Viewer mode \u2014 anyone can see the current lists and mapping, but cannot change them. Clicking \u201cUnlock Admin to Edit\u201d prompts for a passcode; entering it correctly switches the whole app into Admin mode (shown by a green \u201cAdmin\u201d badge in the header) until it is switched back with \u201cSwitch to Viewer\u201d or the app is restarted."),
      p("The default passcode is m3madmin, set in CONFIG[\"admin_passcode\"] near the top of the application's embedded engine module \u2014 change it there and rebuild if a different passcode is wanted. This is intentionally lightweight access control appropriate for a local, single-user desktop tool, not enterprise authentication: anyone with access to the application's source (or this document) can see or change the passcode. It exists to prevent accidental edits, not to secure sensitive data.", { italics: true, size: 18, color: DARKGREY }),
      h2("What Can Be Edited"),
      bullet("Category \u2192 M_Category mapping \u2014 add, edit, or remove rows in place."),
      bullet("Project, Month, and Year lists \u2014 edit as one value per line."),
      bullet("Upload Replacement LIST.xlsx \u2014 replaces the entire list/mapping in one step, using the same header-based detection as the main data upload (columns named Project, Month, Year, Category, M_Category are found by name, not position)."),
      p("Saving any change immediately re-applies the Category mapping to the currently loaded data and refreshes the dashboard \u2014 M_Category values update everywhere without needing to re-upload the Compile M3M Data workbook."),

      h1("16. Customizing Business Rules"),
      p("Everything in Sections 5\u201312 is controlled from a single CONFIG dictionary and a FIELD_ALIASES list near the top of the application\u2019s embedded \u201cengine\u201d module \u2014 nothing is hard-coded inline in the calculation logic. To change, for example, the SLA target, the \u201cunusually high TAT\u201d threshold, the admin passcode, or the wording an uploaded workbook must match for a given field, edit the corresponding entry there; the rest of the application (KPIs, RAG colors, reports, exports) will pick up the change automatically on the next upload."),

      h1("17. Data Privacy"),
      p("This application runs entirely on the local machine. Uploaded workbooks are processed in memory only and are never written to disk, sent to any external server, or retained after the app is closed. No database, cloud service, or internet connection is required once the one-time Python package installation is complete."),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(require("path").join(__dirname, "M3M_MIS_Field_Mapping_Reference.docx"), buf);
  console.log("wrote docx", buf.length, "bytes");
});
