# NBH Data & Report Mapping Document

Reverse-engineered from `NBH Template.xlsx` (workbook contains a pivot cache with
105,994 live records, even though the visible `Compile NBH Data` sheet had been
trimmed to a header row + 2 example rows before distribution). All logic below
was derived from the sheet's real formulas and validated by recomputing every
number in `Open Cases`, `Project Wise` and `Category Wise` from the raw pivot
cache records — every total reconciled exactly (Open cases = 3,629; ageing
slab split 767 / 445 / 438 / 879 / 1,100; project and category splits matched
row-for-row). This document is the basis for `backend/app/config.py` and the
analytics services.

## 1. Worksheets found

| Sheet | Role |
|---|---|
| `Compile NBH Data` | Source-of-truth transaction table (one row per ticket). 33 columns, formula-derived helper columns in AA–AG. |
| `Open Cases` | Pivot: Count of Ticket ID, rows = Status, columns = Ageing SLAB, filtered to Updated Status = OPEN. |
| `Project Wise` | Pivot: Count of Ticket ID, rows = Society Name, columns = Ageing SLAB, filtered to Updated Status = OPEN. |
| `Category Wise` | Pivot: Count of Ticket ID, rows = Category, columns = Ageing SLAB, filtered to Updated Status = OPEN. |
| `Date Wise summary` | Day-by-day report (for a chosen Year/Month/Project) of received / resolved / backlog, plus open backlog split by Management Category. |
| `Project wise Wise summary` | Same metric set as Date Wise summary, but one row per project for a single as-of date. |
| `LIST` | Master data: Project list, Month list, Category → Management Category lookup table (46 raw categories mapped, XLOOKUP default = "Others/Misc"), Management Category head list. |

## 2. Source columns (`Compile NBH Data`, columns A–T)

Society Name, Issue Location, Ticket ID, Created On, Created By, Priority,
Category, Sub Category, Description, Assigned On, Status, Commented On,
Commented By, Last Comment, Escalated Level, Current Assignee, Visibility,
Rating, Last updated on, Source.

The real data additionally carries: `Reported_from(Apartment)`,
`support_ticket_closed_type`, `Resolved Time`, `Closed Time`. The last two are
**required for correct closure/ageing logic** (see §4) even though they are
not in the prompt's headline field list, so the app treats them as optional-
but-important columns: used when present, degrades gracefully when absent.

Statuses actually observed: `OPEN, IN_PROGRESS, ON_HOLD, REOPEN` (management =
OPEN/PENDING) and `CLOSED, CANCELLED, RESOLVED, NOT_AN_ISSUE, AUTO_CLOSE`
(management = CLOSED/RESOLVED).

## 3. Derived columns in the workbook (columns Y–AG) and their formulas

```
Y  (F_Closed)      =IF(AD="Closed", IF(Closed Time<>"", Closed Time,
                                     IF(Resolved Time<>"", Resolved Time,
                                     IF(Last updated on<>"", Last updated on, ""))), "")
AA (Open Date)     =DATEVALUE(TEXT(Created On, "dd-mmm-yy"))          ' date part only
AC (Closed Date)   =IF(F_Closed<>"", DATEVALUE(TEXT(F_Closed,"dd-mmm-yy")), "")
AD (Updated Status)=IF(OR(Status={"IN_PROGRESS","ON_HOLD","OPEN","REOPEN"}), "OPEN", "Closed")
AE (TAT / Ageing)  =IF(Closed Date<>"", Closed Date - Open Date, TODAY() - Open Date)
AF (SLAB)          =IF(AE>30,"More than 30", IF(AE>15,"16 to 30",
                     IF(AE>7,"8 to 15", IF(AE>2,"3 to 7","0 to 2"))))
AG (M_Category)    =XLOOKUP(Category, LIST!J:J, LIST!K:K, "Others/Misc")
```

Plain-English restatement (this is exactly what `analytics_service.py` implements):

- **Closure timestamp** = first non-blank of `Closed Time`, `Resolved Time`,
  `Last updated on` — only looked at when the ticket's management status is
  Closed. If none of the three are present, the ticket is treated as not
  reliably closed (ageing keeps running from Created On to today); this
  assumption is documented and surfaced as a data-quality note.
- **Ageing Days** = (Closed Date − Created Date) for closed tickets, or
  (Today − Created Date) for open tickets. Dates are truncated to whole days
  before subtracting (time-of-day is ignored), matching the workbook.
- **Ageing Slab / SLAB** buckets: `0 to 2`, `3 to 7`, `8 to 15`, `16 to 30`,
  `More than 30` — boundaries are `> 2`, `> 7`, `> 15`, `> 30` days exactly as
  in the formula. Configurable in `config.py: AGEING_BUCKETS`.
- **Management Status** ("Updated Status"): a ticket is **CLOSED/RESOLVED**
  only if its raw `Status` is in the configured closed-status set (default:
  `CLOSED, CANCELLED, RESOLVED, NOT_AN_ISSUE, AUTO_CLOSE`); every other status,
  including any *new/unknown* status value in a future upload, is treated as
  **OPEN/PENDING** by default (safer for management visibility than silently
  calling an unrecognised status "closed"). This generalises the workbook's
  hard-coded OR-list without changing behaviour on the current data.
- **Management Category (M_Category)**: raw `Category` is looked up in the
  configured `CATEGORY_MAPPING` table (46 entries reproduced from the `LIST`
  sheet, see `config.py`); anything not found defaults to `Others/Misc` and is
  also reported under "Unmapped Categories" in the Data Quality summary.
- **RAG classification** (not present in the workbook, added per the prompt's
  §6): Green = 0–2 days, Amber = 3–7, Orange = 8–15, Red = 16+, with a
  separate "Critical" flag at > 30 days for management callouts. Configurable
  in `config.py: RAG_RULES`.

## 4. Report reconciliation (validated against the source workbook)

| Metric | Workbook value | Recomputed from raw data |
|---|---|---|
| Total records (pivot cache) | 105,994 | 105,994 |
| Open / Pending cases | 3,629 | 3,629 |
| Open ageing split (0-2/3-7/8-15/16-30/>30) | 767/445/438/879/1,100 | 767/445/438/879/1,100 |
| Top open project (Smartworld Gems) | 1,405 | 1,405 |
| Top open category (SEEPAGE) | 453 | 453 |

All four reconcile exactly, confirming the derived-column logic above is a
faithful reproduction of the workbook's business rules.

## 5. Date Wise / Project Wise Wise summary logic

For a selected `(Year, Month, Project)` and a given calendar date *d* within
that month:

```
Opening Backlog(d) = COUNT(Open Date < d AND Updated Status = OPEN [AND Society = Project])
Received(d)        = COUNT(Open Date = d [AND Society = Project])
Total(d)            = Opening Backlog(d) + Received(d)
Old Resolved(d)     = COUNT(Open Date < d AND Closed Date = d AND Updated Status = CLOSED [AND Society = Project])
Current Resolved(d) = COUNT(Open Date = d AND Closed Date = d AND Updated Status = CLOSED [AND Society = Project])
Total Resolved(d)   = Old Resolved(d) + Current Resolved(d)
Closing Backlog(d)  = Total(d) - Total Resolved(d)
Closure %(d)        = (Received(d) - Total Resolved(d)) / Total Resolved(d)     ' workbook's own definition
Open-by-MgmtCategory(d, cat) = COUNT(Open Date < d AND Updated Status = OPEN AND M_Category = cat [AND Society = Project])
Total Facility Related(d) = SUM(Open-by-MgmtCategory(d, cat)) for cat != "Project Related"
```

`Project wise Wise summary` is the same formula set evaluated once per
project for a single as-of date instead of once per date for a single/aggregate
project. The app's `GET /api/dashboard/trends` endpoint generalises this to a
monthly rollup (Received / Closed / Opening Backlog / Closing Backlog / Net
Change / Closure %) as requested in the prompt, while `report_service.py`
also exposes the literal daily grain for parity with the workbook.

## 6. Category → Management Category master mapping

Reproduced verbatim from the `LIST` sheet (`backend/app/config.py:
CATEGORY_MAPPING`, 46 entries) with default `Others/Misc` for anything not
listed, e.g. `ELECTRICAL/ELECTRICIAN/ELE → Electrical`, `PLUMBING/SEEPAGE/
LEAKAGE/PLUMBER/VANITY_MIRRORS → Plumbing/Leakage/Seepage`, `CARPENTERY/
CARPENTRY/CARPENTER → Carpentry`, `LIFT/LIFTS → Lift`, `MASONRY/MASONARY →
Masonary`, `SECURITY/SECURITY__PARKING → Security`, `PROJECT → Project
Related`, everything else → `Others/Misc`.

## 7. Project master

29 societies found in `LIST!A` (including the `ALL` pseudo-entry), all also
present in `Compile NBH Data`. The app does **not** hard-code this list — it
is derived at upload time from the distinct `Society Name` values in the
uploaded file, exactly as the prompt requires, so a new project in a future
file appears automatically.
