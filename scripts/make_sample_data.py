"""
Generates realistic TEST excels for the three applications:

    data/m3m/M3M_Test_Data.xlsx          (M3M SFDC-style headers)
    data/smartworld/SW_Test_Data.xlsx    (Smartworld-style headers)
    data/nbh/NBH_Test_Data.xlsx          (NBH-style headers)

Run:   python scripts/make_sample_data.py
Replace these files with the real exports later - same folders, any filename.
"""
import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

DATA = Path(__file__).resolve().parent.parent / "data"
random.seed(42)
TODAY = date(2026, 9, 14)

FIRST = ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan",
         "Kavita", "Suresh", "Neha", "Arjun", "Pooja"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Mehta", "Jain", "Agarwal",
        "Kapoor", "Malhotra", "Reddy"]
CATS = ["Plumbing", "Electrical", "Civil Works", "Housekeeping", "Billing",
        "Possession", "Club & Amenities", "Security"]
SUBS = ["Leakage", "Wiring Fault", "Wall Crack", "Cleaning", "Invoice Query",
        "Handover Delay", "Gym Equipment", "Access Card"]
PRIO = ["High", "Medium", "Low"]
OWNERS = ["Ramesh Kumar", "Sunita Devi", "Manoj Tiwari", "Deepak Yadav",
          "Ritu Chauhan", "Ajay Bansal"]
SOURCES = ["Phone", "Email", "Web", "Walk-in", "App"]


def name():
    return f"{random.choice(FIRST)} {random.choice(LAST)}"


def dmy(d):
    return d.strftime("%d/%m/%Y")


def dates():
    opened = TODAY - timedelta(days=random.randint(0, 330))
    if random.random() < 0.72:
        closed = min(TODAY, opened + timedelta(days=random.randint(0, 45)))
    else:
        closed = None
    return opened, closed


def write(rows, headers, folder, filename, sheet):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h, "") for h in headers])
    out = DATA / folder / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"  wrote {out.relative_to(DATA.parent)}  ({len(rows)} rows)")


# ---- M3M ------------------------------------------------------------------
def m3m(n=320):
    projects = ["M3M Golf Estate", "M3M Merlin", "M3M Sierra", "M3M Heights",
                "M3M Skywalk", "M3M Latitude"]
    headers = ["Case Number", "Account Name", "Subject", "Priority", "M_Category",
               "Sub Category", "Opened Date", "Closed Date", "Case Owner",
               "Case Status", "Case Source", "Project Name", "Project Unit"]
    rows = []
    for i in range(1, n + 1):
        opened, closed = dates()
        rows.append({
            "Case Number": f"M3M-{10000 + i}",
            "Account Name": name(),
            "Subject": f"{random.choice(SUBS)} issue reported",
            "Priority": random.choice(PRIO),
            "M_Category": random.choice(CATS),
            "Sub Category": random.choice(SUBS),
            "Opened Date": dmy(opened),
            "Closed Date": dmy(closed) if closed else "",
            "Case Owner": random.choice(OWNERS),
            "Case Status": random.choice(["Closed", "Resolved"]) if closed
                           else random.choice(["Open", "In Progress", "Pending Customer"]),
            "Case Source": random.choice(SOURCES),
            "Project Name": random.choice(projects),
            "Project Unit": f"{random.choice('ABCT')}-{random.randint(101, 2404)}",
        })
    write(rows, headers, "m3m", "M3M_Test_Data.xlsx", "Compile M3M Data")


# ---- Smartworld -----------------------------------------------------------
def sw(n=280):
    projects = ["Smartworld Orchard", "Smartworld Gems", "Smartworld One DXP",
                "Smartworld The Edition", "Smartworld Sky Arc"]
    headers = ["Case Number", "Account Name", "Subject", "Priority", "M_Category",
               "Sub Category", "Date/Time Opened", "Closed Date", "Case Owner",
               "Status", "Case Source", "Project", "Property", "Age"]
    rows = []
    for i in range(1, n + 1):
        opened, closed = dates()
        rows.append({
            "Case Number": f"SW-{50000 + i}",
            "Account Name": name(),
            "Subject": f"{random.choice(SUBS)} complaint",
            "Priority": random.choice(PRIO),
            "M_Category": random.choice(CATS),
            "Sub Category": random.choice(SUBS),
            "Date/Time Opened": f"{dmy(opened)}, {random.randint(9, 18)}:{random.randint(0, 59):02d}",
            "Closed Date": dmy(closed) if closed else "",
            "Case Owner": random.choice(OWNERS),
            "Status": random.choice(["Closed", "Resolved"]) if closed
                      else random.choice(["Open", "In Progress", "Escalated"]),
            "Case Source": random.choice(SOURCES),
            "Project": random.choice(projects),
            "Property": f"{random.choice('NSEW')}-{random.randint(1, 99)}{random.choice('ABCD')}",
            "Age": (TODAY - opened).days,
        })
    write(rows, headers, "smartworld", "SW_Test_Data.xlsx", "Compile SW Data")


# ---- NBH ------------------------------------------------------------------
def nbh(n=400):
    societies = ["M3M Woodshire", "M3M Escala", "M3M Marina", "M3M Duo High",
                 "M3M Sierra 68"]
    headers = ["Ticket Id", "Society Name", "Created On", "Created By", "Priority",
               "Category", "Sub Category", "Description", "Status",
               "Current Assignee", "Source", "Reported_From(Apartment)",
               "Closed Time", "Rating"]
    rows = []
    for i in range(1, n + 1):
        opened, closed = dates()
        rows.append({
            "Ticket Id": f"NBH-{900000 + i}",
            "Society Name": random.choice(societies),
            "Created On": dmy(opened),
            "Created By": name(),
            "Priority": random.choice(PRIO),
            "Category": random.choice(CATS),
            "Sub Category": random.choice(SUBS),
            "Description": f"{random.choice(SUBS)} in {random.choice(['tower', 'flat', 'common area', 'basement'])}",
            "Status": random.choice(["Closed", "Resolved"]) if closed
                      else random.choice(["Open", "Assigned", "In Progress"]),
            "Current Assignee": random.choice(OWNERS),
            "Source": random.choice(["App", "Helpdesk", "Call"]),
            "Reported_From(Apartment)": f"T{random.randint(1, 4)}-{random.randint(101, 1804)}",
            "Closed Time": dmy(closed) if closed else "",
            "Rating": random.randint(1, 5) if closed and random.random() < 0.6 else "",
        })
    write(rows, headers, "nbh", "NBH_Test_Data.xlsx", "Compile NBH Data")


if __name__ == "__main__":
    m3m()
    sw()
    nbh()
    print("Done.")
