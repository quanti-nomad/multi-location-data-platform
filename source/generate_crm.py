"""Build a deliberately messy CRM database for a fictional two-brand clinic chain.

This stands in for the operational CRM that, before a data platform exists,
gets exported to Excel and summed by hand. The mess is intentional and
realistic:

- location names with stray spaces and inconsistent casing
- duplicate customers (same person, email typed differently)
- test accounts mixed in with real customers
- appointment statuses in five different spellings
- payment amounts stored as text, some formatted like "$1,234.50"
- voided payments and refunds sitting next to real sales
- lead sources typed by hand ("FB", "facebook", "Facebook Ads")

Brands, people and numbers are invented. No real company or patient data.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

START = date(2025, 1, 1)
END = date(2026, 6, 30)

PLANS = [("Core", 199.0), ("Plus", 349.0), ("Premium", 599.0)]
SERVICES = [
    ("IV Therapy - Hydration", "iv_therapy", 179.0),
    ("IV Therapy - NAD+", "iv_therapy", 449.0),
    ("Cryotherapy", "recovery", 69.0),
    ("Infrared Sauna", "recovery", 49.0),
    ("Hyperbaric Oxygen", "recovery", 129.0),
    ("Full Diagnostic Panel", "diagnostics", 399.0),
    ("Body Composition Scan", "diagnostics", 99.0),
    ("Medical Weight Consult", "weight_loss", 149.0),
    ("Aesthetic Injectable", "aesthetics", 525.0),
]
STATUS_SPELLINGS = {
    "completed": ["Completed", "completed", "COMPLETED", "Complete"],
    "cancelled": ["Cancelled", "canceled", "CANCELLED"],
    "no_show": ["No Show", "no-show", "NoShow"],
}
LEAD_SOURCES = {
    "paid_search": ["Google Ads", "google", "adwords"],
    "paid_social": ["Facebook Ads", "FB", "facebook", "Instagram", "IG"],
    "referral": ["Referral", "referral", "Friend"],
    "organic": ["Website", "organic", "SEO"],
    "walk_in": ["Walk-in", "walkin"],
}
CITIES = [
    "Austin", "Dallas", "Houston", "Phoenix", "Denver", "Miami", "Tampa", "Atlanta",
    "Nashville", "Charlotte", "Scottsdale", "San Diego", "Irvine", "Las Vegas",
    "Boise", "Salt Lake City", "Raleigh", "Orlando", "Plano", "Frisco",
    "Boca Raton", "Naples", "Sarasota", "Chandler",
]
FIRST = ["Ana", "Ben", "Carla", "Dev", "Elena", "Frank", "Grace", "Hugo", "Ivy", "Jon",
         "Kara", "Leo", "Maya", "Nate", "Olga", "Paul", "Quinn", "Rosa", "Sam", "Tara"]
LAST = ["Lopez", "Nguyen", "Smith", "Patel", "Kim", "Garcia", "Brown", "Rossi", "Cruz", "Reyes"]


def month_starts(a: date, b: date):
    d = date(a.year, a.month, 1)
    while d <= b:
        yield d
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def build(path: Path, seed: int = 11, n_customers: int = 9000) -> dict:
    rng = np.random.default_rng(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE locations (location_id INTEGER PRIMARY KEY, location_name TEXT, brand TEXT,
            ownership TEXT, franchisee_id TEXT, opened_on TEXT, closed_on TEXT, updated_at TEXT);
        CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT,
            email TEXT, home_location_id INTEGER, created_at TEXT, updated_at TEXT);
        CREATE TABLE services (service_id INTEGER PRIMARY KEY, service_name TEXT, category TEXT,
            list_price REAL, updated_at TEXT);
        CREATE TABLE memberships (membership_id INTEGER PRIMARY KEY, customer_id INTEGER,
            location_id INTEGER, plan_name TEXT, monthly_fee REAL, start_date TEXT, end_date TEXT,
            updated_at TEXT);
        CREATE TABLE appointments (appointment_id INTEGER PRIMARY KEY, customer_id INTEGER,
            location_id INTEGER, service_id INTEGER, scheduled_at TEXT, status TEXT, updated_at TEXT);
        CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, customer_id INTEGER,
            location_id INTEGER, appointment_id INTEGER, membership_id INTEGER, payment_type TEXT,
            amount TEXT, payment_status TEXT, paid_at TEXT, updated_at TEXT);
        CREATE TABLE leads (lead_id INTEGER PRIMARY KEY, location_id INTEGER, lead_source TEXT,
            created_at TEXT, converted_customer_id INTEGER, updated_at TEXT);
        """
    )

    def ts(d: date, rng=rng) -> str:
        return datetime(d.year, d.month, d.day, int(rng.integers(8, 20)), int(rng.integers(0, 60))).isoformat(sep=" ")

    def money_text(x: float) -> str:
        # 15% of amounts arrive formatted the way a person would type them
        return f"${x:,.2f}" if rng.random() < 0.15 else f"{x:.2f}"

    # --- locations: brand A corporate, brand B franchised --------------------
    locations = []
    for i, city in enumerate(CITIES, start=1):
        corporate = i <= 10
        brand = "Vitality Clinics" if corporate else "Lumen Wellness"
        opened = START - timedelta(days=int(rng.integers(90, 900)))
        if i in (9, 18, 23):  # three openings during the period
            opened = START + timedelta(days=int(rng.integers(60, 400)))
        closed = START + timedelta(days=420) if i == 15 else None
        raw_name = f"{brand.split()[0]} - {city}"
        if rng.random() < 0.3:
            raw_name = "  " + raw_name.lower() + " "
        locations.append((i, raw_name, brand, "corporate" if corporate else "franchise",
                          None if corporate else f"FR-{(i % 6) + 1:02d}",
                          opened.isoformat(), closed.isoformat() if closed else None, ts(opened)))
    cur.executemany("INSERT INTO locations VALUES (?,?,?,?,?,?,?,?)", locations)
    loc_open = {l[0]: date.fromisoformat(l[5]) for l in locations}
    loc_close = {l[0]: (date.fromisoformat(l[6]) if l[6] else END) for l in locations}
    loc_ids = np.array([l[0] for l in locations])

    cur.executemany("INSERT INTO services VALUES (?,?,?,?,?)",
                    [(i, n, c, p, ts(START)) for i, (n, c, p) in enumerate(SERVICES, start=1)])

    # --- customers, plus duplicates and test accounts ----------------------
    customers, appts, pays, members = [], [], [], []
    cid = aid = pid = mid = 0
    window_days = (END - START).days

    def add_customer(first, last, email, loc, created):
        nonlocal cid
        cid += 1
        customers.append((cid, first, last, email, loc, ts(created), ts(created)))
        return cid

    real_ids = []
    for _ in range(n_customers):
        loc = int(rng.choice(loc_ids))
        lo, hi = max(START, loc_open[loc]), loc_close[loc]
        if lo >= hi:
            continue
        created = lo + timedelta(days=int(rng.integers(0, (hi - lo).days)))
        first, last = rng.choice(FIRST), rng.choice(LAST)
        email = f"{first}.{last}{int(rng.integers(1, 9999))}@example.com".lower()
        if rng.random() < 0.04:
            email = None
        c = add_customer(first, last, email, loc, created)
        real_ids.append((c, loc, created, email, first, last))

    # ~3% duplicates: same person re-registered, email typed differently
    dupes = rng.choice(len(real_ids), size=int(0.03 * len(real_ids)), replace=False)
    dup_rows = []
    for k in dupes:
        c, loc, created, email, first, last = real_ids[k]
        if not email:
            continue
        variant = email.upper() if rng.random() < 0.5 else f" {email} "
        later = min(END, created + timedelta(days=int(rng.integers(1, 120))))
        dup_rows.append((add_customer(first, last, variant, loc, later), loc, later))

    test_rows = []
    for t in range(30):
        loc = int(rng.choice(loc_ids))
        d = max(START, loc_open[loc]) + timedelta(days=int(rng.integers(0, 60)))
        test_rows.append((add_customer("Test", f"User{t}", f"test{t}@clinic-test.com", loc, d), loc, d))

    # --- activity per customer --------------------------------------------
    everyone = [(c, loc, created) for c, loc, created, *_ in real_ids] + dup_rows + test_rows
    for c, loc, created in everyone:
        stop = loc_close[loc]
        # membership for ~38% of customers
        m_id, m_start, m_end, fee = None, None, None, None
        if rng.random() < 0.38:
            plan, fee = PLANS[int(rng.choice(3, p=[0.5, 0.35, 0.15]))]
            m_start = created + timedelta(days=int(rng.integers(0, 45)))
            if m_start < stop:
                months = int(rng.geometric(0.07))
                m_end = m_start + timedelta(days=30 * months)
                m_end = None if m_end >= stop else m_end
                mid += 1
                m_id = mid
                members.append((m_id, c, loc, plan, fee, m_start.isoformat(),
                                m_end.isoformat() if m_end else None, ts(m_start)))
                for ms in month_starts(m_start, m_end or stop):
                    charge = max(ms, m_start)
                    if charge >= (m_end or stop) or charge > END:
                        continue
                    pid += 1
                    pays.append((pid, c, loc, None, m_id, "membership", money_text(fee),
                                 "void" if rng.random() < 0.005 else "settled", ts(charge), ts(charge)))
        # appointments
        active_days = max(1, (stop - created).days)
        rate = 1.3 if m_id else 0.25  # visits per 30 days
        n_appts = rng.poisson(rate * active_days / 30)
        for _ in range(n_appts):
            d = created + timedelta(days=int(rng.integers(0, active_days)))
            if d > END:
                continue
            status = str(rng.choice(["completed", "cancelled", "no_show"], p=[0.85, 0.09, 0.06]))
            svc = int(rng.integers(1, len(SERVICES) + 1))
            aid += 1
            appts.append((aid, c, loc, svc, ts(d), str(rng.choice(STATUS_SPELLINGS[status])), ts(d)))
            if status == "completed":
                price = SERVICES[svc - 1][2] * (0.8 if m_id else 1.0)
                pid += 1
                pays.append((pid, c, loc, aid, None, "service", money_text(price),
                             "void" if rng.random() < 0.01 else "settled", ts(d), ts(d)))
                if rng.random() < 0.02:
                    pid += 1
                    later = min(END, d + timedelta(days=int(rng.integers(1, 20))))
                    pays.append((pid, c, loc, aid, None, "refund", money_text(-price),
                                 "settled", ts(later), ts(later)))

    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?)", customers)
    cur.executemany("INSERT INTO memberships VALUES (?,?,?,?,?,?,?,?)", members)
    cur.executemany("INSERT INTO appointments VALUES (?,?,?,?,?,?,?)", appts)
    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?,?)", pays)

    # --- leads, some of which convert --------------------------------------
    leads, lid = [], 0
    converted = {c: (loc, created) for c, loc, created, *_ in real_ids}
    for c, (loc, created) in converted.items():
        if rng.random() < 0.7:
            lid += 1
            channel = str(rng.choice(list(LEAD_SOURCES)))
            lead_day = max(START, created - timedelta(days=int(rng.integers(0, 30))))
            leads.append((lid, loc, str(rng.choice(LEAD_SOURCES[channel])), ts(lead_day), c, ts(lead_day)))
    for _ in range(int(len(converted) * 1.6)):  # leads that never convert
        loc = int(rng.choice(loc_ids))
        lo, hi = max(START, loc_open[loc]), loc_close[loc]
        if lo >= hi:
            continue
        d = lo + timedelta(days=int(rng.integers(0, (hi - lo).days)))
        channel = str(rng.choice(list(LEAD_SOURCES)))
        lid += 1
        leads.append((lid, loc, str(rng.choice(LEAD_SOURCES[channel])), ts(d), None, ts(d)))
    cur.executemany("INSERT INTO leads VALUES (?,?,?,?,?,?)", leads)
    con.commit()

    counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["locations", "customers", "services", "memberships", "appointments", "payments", "leads"]}
    con.close()
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/crm.sqlite")
    ap.add_argument("--customers", type=int, default=9000)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    print(build(Path(a.out), a.seed, a.customers))
