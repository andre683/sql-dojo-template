#!/usr/bin/env python3
"""
Builds wine.duckdb from scratch. Run from the repo root:
    python seed/seed_wine_world.py
"""
import os, random, duckdb
from datetime import date, datetime, timedelta
from pathlib import Path
from itertools import groupby

RNG = random.Random(42)
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "wine.duckdb"

# ── helpers ────────────────────────────────────────────────────────────────

def rdate(lo: date, hi: date) -> date:
    return lo + timedelta(days=RNG.randint(0, max(0, (hi - lo).days)))

def rdatetime(lo: datetime, hi: datetime) -> datetime:
    delta = max(0, int((hi - lo).total_seconds()))
    return lo + timedelta(seconds=RNG.randint(0, delta))

def wrand(population, weights):
    return RNG.choices(population, weights=weights, k=1)[0]

# ── schema ─────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE regions (
    region_id        INTEGER PRIMARY KEY,
    name             VARCHAR NOT NULL,
    country          VARCHAR NOT NULL,
    parent_region_id INTEGER
);

CREATE TABLE producers (
    producer_id   INTEGER PRIMARY KEY,
    name          VARCHAR NOT NULL,
    region_id     INTEGER NOT NULL,
    country       VARCHAR NOT NULL,
    founding_year INTEGER
);

CREATE TABLE products (
    product_id    INTEGER PRIMARY KEY,
    name          VARCHAR NOT NULL,
    varietal      VARCHAR NOT NULL,
    vintage_year  INTEGER NOT NULL,
    producer_id   INTEGER NOT NULL,
    region_id     INTEGER NOT NULL,
    price_cents   INTEGER NOT NULL,
    cost_cents    INTEGER NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    tags          VARCHAR[]
);

CREATE TABLE customers (
    customer_id             INTEGER PRIMARY KEY,
    email                   VARCHAR NOT NULL UNIQUE,
    first_name              VARCHAR NOT NULL,
    last_name               VARCHAR NOT NULL,
    signup_date             DATE NOT NULL,
    acquisition_channel     VARCHAR NOT NULL,
    referred_by_customer_id INTEGER,
    state                   VARCHAR,
    country                 VARCHAR NOT NULL DEFAULT 'USA'
);

CREATE TABLE orders (
    order_id       INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL,
    created_at     TIMESTAMP NOT NULL,
    shipped_at     TIMESTAMP,
    status         VARCHAR NOT NULL,
    discount_cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE order_items (
    order_item_id    INTEGER PRIMARY KEY,
    order_id         INTEGER NOT NULL,
    product_id       INTEGER NOT NULL,
    quantity         INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);

CREATE TABLE subscriptions (
    subscription_id      INTEGER PRIMARY KEY,
    customer_id          INTEGER NOT NULL,
    plan                 VARCHAR NOT NULL,
    started_at           DATE NOT NULL,
    ended_at             DATE,
    bottles_per_shipment INTEGER NOT NULL
);

CREATE TABLE subscription_events (
    event_id        INTEGER PRIMARY KEY,
    subscription_id INTEGER NOT NULL,
    customer_id     INTEGER NOT NULL,
    event_type      VARCHAR NOT NULL,
    event_at        TIMESTAMP NOT NULL,
    mrr_cents       INTEGER NOT NULL
);

CREATE TABLE web_events (
    event_id    INTEGER PRIMARY KEY,
    visitor_id  VARCHAR NOT NULL,
    customer_id INTEGER,
    event_at    TIMESTAMP NOT NULL,
    event_type  VARCHAR NOT NULL,
    page_path   VARCHAR NOT NULL,
    product_id  INTEGER
);

CREATE TABLE customer_segments_history (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    segment     VARCHAR NOT NULL,
    valid_from  DATE NOT NULL,
    valid_to    DATE,
    is_current  BOOLEAN NOT NULL
);
"""

# ── static reference data ──────────────────────────────────────────────────

REGIONS = [
    (1,  "California",        "USA",       None),
    (2,  "France",            "France",    None),
    (3,  "Spain",             "Spain",     None),
    (4,  "Italy",             "Italy",     None),
    (5,  "Australia",         "Australia", None),
    (6,  "Argentina",         "Argentina", None),
    (7,  "Napa Valley",       "USA",       1),
    (8,  "Sonoma",            "USA",       1),
    (9,  "Paso Robles",       "USA",       1),
    (10, "Bordeaux",          "France",    2),
    (11, "Burgundy",          "France",    2),
    (12, "Rioja",             "Spain",     3),
    (13, "Tuscany",           "Italy",     4),
    (14, "Barossa Valley",    "Australia", 5),
    (15, "Mendoza",           "Argentina", 6),
]

PRODUCERS_DATA = [
    (1,  "Hollow Oak Estate",       7,  "USA",       1979),
    (2,  "Cobalt Hill Cellars",     7,  "USA",       1972),
    (3,  "Chateau Belvaux",         10, "France",    1755),
    (4,  "Domaine des Trois Lunes", 11, "France",    1869),
    (5,  "Bodegas Cerro Nublado",   12, "Spain",     1864),
    (6,  "Tenuta Vallombra",        13, "Italy",     1944),
    (7,  "Kookaburra Flats",        14, "Australia", 1844),
    (8,  "Bodega Viento Andino",    15, "Argentina", 1902),
    (9,  "Fogline Vineyards",       8,  "USA",       1962),
    (10, "Redtail Bench Winery",    7,  "USA",       1976),
    (11, "Chateau Lescaret",        10, "France",    1842),
    (12, "Maison Dufresnay",        11, "France",    1859),
    (13, "Vinedos Las Grullas",     12, "Spain",     1879),
    (14, "Fattoria Ciliegio",       13, "Italy",     1898),
    (15, "Ironbark Creek",          14, "Australia", 1868),
    (16, "Finca Los Condores",      15, "Argentina", 1998),
    (17, "Lantern Rock Winery",     7,  "USA",       1986),
    (18, "Driftwood Coast Cellars", 8,  "USA",       1991),
    (19, "Marrow and Vine",         8,  "USA",       1996),
    (20, "Coyote Grade Vineyards",  9,  "USA",       1981),
]

REGION_VARIETALS = {
    7:  ["Cabernet Sauvignon", "Merlot", "Chardonnay"],
    8:  ["Pinot Noir", "Chardonnay", "Zinfandel"],
    9:  ["Syrah", "Zinfandel", "Cabernet Sauvignon"],
    10: ["Cabernet Sauvignon", "Merlot", "Sauvignon Blanc"],
    11: ["Pinot Noir", "Chardonnay"],
    12: ["Tempranillo", "Grenache"],
    13: ["Sangiovese", "Cabernet Sauvignon"],
    14: ["Syrah", "Grenache", "Cabernet Sauvignon"],
    15: ["Malbec", "Cabernet Sauvignon"],
}

TAGS_POOL = [
    "full-bodied", "tannic", "oaky", "fruity", "earthy",
    "mineral", "spicy", "floral", "crisp", "rich",
    "elegant", "bold", "smooth", "complex", "age-worthy",
    "biodynamic", "organic", "natural", "small-production", "cult",
]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
    "Linda", "William", "Barbara", "David", "Elizabeth", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Christopher", "Lisa", "Daniel", "Nancy", "Matthew", "Betty",
    "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily",
    "Joshua", "Donna", "Kevin", "Michelle", "Brian", "Carol",
    "George", "Amanda", "Edward", "Melissa", "Ronald", "Deborah",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts",
]

DOMAINS   = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
CHANNELS  = ["organic", "paid_search", "referral", "social"]
CH_WGTS   = [0.40, 0.30, 0.15, 0.15]
US_STATES = ["CA", "NY", "TX", "FL", "WA", "OR", "CO", "IL", "MA", "NJ",
             "VA", "GA", "NC", "OH", "PA", "AZ", "MN", "MI", "NV", "CT"]

STATUSES  = ["delivered", "shipped", "pending", "cancelled", "refunded"]
ST_WGTS   = [0.65, 0.10, 0.05, 0.15, 0.05]

SUB_PLANS = ["monthly", "quarterly", "annual"]
SUB_WGTS  = [0.50, 0.30, 0.20]

MRR_TABLE = {
    ("monthly",   2): 4900,  ("monthly",   3): 6900,  ("monthly",   6): 12900,
    ("quarterly", 2): 4500,  ("quarterly", 3): 6300,  ("quarterly", 6): 11900,
    ("annual",    2): 4200,  ("annual",    3): 5900,  ("annual",    6): 10900,
}

PAGE_PATHS = [
    "/", "/wines", "/about", "/blog",
    "/collections/red", "/collections/white", "/collections/rose",
    "/gifts", "/subscriptions",
]

# ── generation functions ───────────────────────────────────────────────────

def gen_products():
    rows = []
    for pid in range(1, 51):
        prod = PRODUCERS_DATA[(pid - 1) % len(PRODUCERS_DATA)]
        producer_id, _, region_id = prod[0], prod[1], prod[2]
        varietal = RNG.choice(REGION_VARIETALS.get(region_id, ["Cabernet Sauvignon"]))
        vintage  = RNG.randint(2018, 2022)
        name     = f"{prod[1]} {varietal} {vintage}"

        if producer_id <= 8:
            price = RNG.randint(8000, 25000)
        elif producer_id <= 16:
            price = RNG.randint(3000, 12000)
        else:
            price = RNG.randint(1500, 6000)

        cost      = int(price * RNG.uniform(0.30, 0.50))
        is_active = pid not in (7, 23)  # two inactive products
        tags      = RNG.sample(TAGS_POOL, RNG.randint(1, 4))

        rows.append((pid, name, varietal, vintage, producer_id, region_id,
                     price, cost, is_active, tags))
    return rows


def gen_customers():
    rows = []
    used_emails = set()
    for cid in range(1, 501):
        first  = RNG.choice(FIRST_NAMES)
        last   = RNG.choice(LAST_NAMES)
        while True:
            email = f"{first.lower()}.{last.lower()}{RNG.randint(1,999)}@{RNG.choice(DOMAINS)}"
            if email not in used_emails:
                used_emails.add(email)
                break

        signup  = rdate(date(2021, 1, 1), date(2024, 6, 30))
        channel = wrand(CHANNELS, CH_WGTS)

        referred_by = None
        if cid > 20 and channel == "referral" and RNG.random() < 0.65:
            referred_by = RNG.randint(1, cid - 1)

        state   = RNG.choice(US_STATES)
        country = "USA" if RNG.random() < 0.90 else RNG.choice(["Canada", "UK", "Australia"])

        rows.append((cid, email, first, last, signup, channel, referred_by, state, country))
    return rows


def gen_orders(customers):
    rows = []
    oid  = 1

    no_orders = set(RNG.sample(range(1, 501), 100))  # 100 customers have no orders (anti_join bait)

    for cid, _, _, _, signup, _, _, _, _ in customers:
        if cid in no_orders:
            continue
        for _ in range(RNG.randint(1, 9)):
            lo = max(signup + timedelta(days=1), date(2021, 6, 1))
            hi = date(2024, 10, 31)
            if lo >= hi:
                continue
            order_dt = rdatetime(
                datetime(lo.year, lo.month, lo.day, 8, 0),
                datetime(hi.year, hi.month, hi.day, 22, 0),
            )
            status = wrand(STATUSES, ST_WGTS)

            shipped_at = None
            if status in ("shipped", "delivered", "refunded"):
                shipped_at = order_dt + timedelta(days=RNG.randint(1, 5),
                                                   hours=RNG.randint(0, 12))

            discount = RNG.choice([0, 0, 0, 0, 500, 1000, 2000])
            rows.append((oid, cid, order_dt, shipped_at, status, discount))
            oid += 1

    return rows


def gen_order_items(orders, products):
    rows    = []
    item_id = 1
    for oid, _, _, _, _, _ in orders:
        n_items   = RNG.randint(1, 4)
        prod_ids  = RNG.sample(range(1, 51), n_items)
        for prod_id in prod_ids:
            base_price = products[prod_id - 1][6]
            price      = round(base_price * RNG.uniform(0.95, 1.05) / 100) * 100
            qty        = RNG.randint(1, 4)
            rows.append((item_id, oid, prod_id, qty, max(100, price)))
            item_id += 1
    return rows


def gen_subscriptions(customers, orders):
    ordering_cids = {o[1] for o in orders}
    eligible      = [c[0] for c in customers if c[0] in ordering_cids]
    sub_cids      = RNG.sample(eligible, min(180, len(eligible)))

    cust_signup = {c[0]: c[4] for c in customers}

    rows = []
    sid  = 1
    for cid in sub_cids:
        signup   = cust_signup[cid]
        lo       = max(signup + timedelta(days=30), date(2021, 7, 1))
        hi       = date(2024, 6, 30)
        if lo >= hi:
            continue
        started  = rdate(lo, hi)
        plan     = wrand(SUB_PLANS, SUB_WGTS)
        bottles  = RNG.choice([2, 3, 6])

        if RNG.random() < 0.60:
            ended = None
        else:
            ended = min(started + timedelta(days=RNG.randint(30, 730)), date(2024, 10, 31))

        rows.append((sid, cid, plan, started, ended, bottles))
        sid += 1
    return rows


def gen_subscription_events(subs):
    rows = []
    eid  = 1

    for sid, cid, plan, started, ended, bottles in subs:
        mrr      = MRR_TABLE.get((plan, bottles), 4900)
        created  = datetime(started.year, started.month, started.day, 10, 0)
        rows.append((eid, sid, cid, "created", created, mrr))
        eid += 1

        if ended:
            # Possibly pause before cancelling
            if RNG.random() < 0.40:
                pause_lo = started + timedelta(days=14)
                pause_hi = ended   - timedelta(days=14)
                if pause_lo < pause_hi:
                    pd   = rdate(pause_lo, pause_hi)
                    rows.append((eid, sid, cid, "paused",
                                 datetime(pd.year, pd.month, pd.day, 10, 0), mrr))
                    eid += 1

                    res_lo = pd    + timedelta(days=7)
                    res_hi = ended - timedelta(days=7)
                    if res_lo < res_hi:
                        rd = rdate(res_lo, res_hi)
                        rows.append((eid, sid, cid, "resumed",
                                     datetime(rd.year, rd.month, rd.day, 10, 0), mrr))
                        eid += 1

            rows.append((eid, sid, cid, "cancelled",
                         datetime(ended.year, ended.month, ended.day, 10, 0), 0))
            eid += 1
        else:
            # Active — maybe paused and resumed
            if RNG.random() < 0.25:
                pause_lo = started    + timedelta(days=30)
                pause_hi = date(2024, 9, 1)
                if pause_lo < pause_hi:
                    pd = rdate(pause_lo, pause_hi)
                    rows.append((eid, sid, cid, "paused",
                                 datetime(pd.year, pd.month, pd.day, 10, 0), mrr))
                    eid += 1

                    if RNG.random() < 0.70:
                        res_lo = pd + timedelta(days=14)
                        res_hi = date(2024, 10, 31)
                        if res_lo < res_hi:
                            rd = rdate(res_lo, res_hi)
                            rows.append((eid, sid, cid, "resumed",
                                         datetime(rd.year, rd.month, rd.day, 10, 0), mrr))
                            eid += 1
    return rows


def gen_web_events(customers):
    rows = []
    eid  = 1

    # 200 identified customers + 200 anonymous visitors
    identified = RNG.sample([c[0] for c in customers], 200)
    visitors   = [(f"vis_{i+1:04d}", identified[i]) for i in range(200)] + \
                 [(f"vis_{i+201:04d}", None)         for i in range(200)]

    for vis_id, cust_id in visitors:
        n_sessions = RNG.randint(2, 12)
        sess_dates = sorted(rdate(date(2022, 1, 1), date(2024, 10, 31))
                            for _ in range(n_sessions))

        for sd in sess_dates:
            ts = datetime(sd.year, sd.month, sd.day,
                          RNG.randint(7, 23), RNG.randint(0, 59))

            # 1–3 page views to open the session
            for _ in range(RNG.randint(1, 3)):
                rows.append((eid, vis_id, cust_id, ts, "page_view",
                             RNG.choice(PAGE_PATHS), None))
                eid += 1
                ts += timedelta(seconds=RNG.randint(15, 120))

            # Funnel: product_view → add_to_cart → checkout_start → purchase
            if RNG.random() < 0.60:
                prod_id = RNG.randint(1, 50)
                rows.append((eid, vis_id, cust_id, ts, "product_view",
                             f"/wines/{prod_id}", prod_id))
                eid += 1
                ts += timedelta(seconds=RNG.randint(30, 240))

                if RNG.random() < 0.45:
                    rows.append((eid, vis_id, cust_id, ts, "add_to_cart",
                                 "/cart", prod_id))
                    eid += 1
                    ts += timedelta(seconds=RNG.randint(30, 300))

                    if RNG.random() < 0.60:
                        rows.append((eid, vis_id, cust_id, ts, "checkout_start",
                                     "/checkout", None))
                        eid += 1
                        ts += timedelta(seconds=RNG.randint(60, 600))

                        if RNG.random() < 0.70:
                            rows.append((eid, vis_id, cust_id, ts, "purchase",
                                         "/checkout/complete", prod_id))
                            eid += 1

    return rows


def gen_customer_segments(con):
    raw = con.execute("""
        WITH monthly AS (
            SELECT
                o.customer_id,
                DATE_TRUNC('month', o.created_at)::DATE AS month,
                SUM(oi.quantity * oi.unit_price_cents)  AS rev
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status NOT IN ('cancelled', 'refunded')
            GROUP BY 1, 2
        ),
        cum AS (
            SELECT customer_id, month,
                   SUM(rev) OVER (PARTITION BY customer_id ORDER BY month) AS cumrev
            FROM monthly
        ),
        seg AS (
            SELECT customer_id, month,
                   CASE
                       WHEN cumrev <  50000  THEN 'bronze'
                       WHEN cumrev < 200000  THEN 'silver'
                       WHEN cumrev < 500000  THEN 'gold'
                       ELSE 'platinum'
                   END AS segment
            FROM cum
        ),
        changes AS (
            SELECT *,
                   LAG(segment) OVER (PARTITION BY customer_id ORDER BY month) AS prev_seg
            FROM seg
        )
        SELECT customer_id, segment, month
        FROM changes
        WHERE prev_seg IS NULL OR segment != prev_seg
        ORDER BY customer_id, month
    """).fetchall()

    history = []
    hid = 1
    for cid, group in groupby(raw, key=lambda r: r[0]):
        records = list(group)
        for i, (_, segment, month) in enumerate(records):
            valid_to   = records[i + 1][2] if i + 1 < len(records) else None
            is_current = valid_to is None
            history.append((hid, cid, segment, month, valid_to, is_current))
            hid += 1
    return history


# ── main ───────────────────────────────────────────────────────────────────

def main():
    db = str(DB_PATH)
    if os.path.exists(db):
        os.remove(db)

    # Write an old storage format so older readers (SQLTools driver bundles
    # DuckDB 0.10.2, the CLI may lag behind pip) can still open the file.
    con = duckdb.connect(db, config={"storage_compatibility_version": "v0.10.2"})
    con.execute(DDL)

    con.executemany("INSERT INTO regions   VALUES (?,?,?,?)",   REGIONS)
    con.executemany("INSERT INTO producers VALUES (?,?,?,?,?)", PRODUCERS_DATA)

    products = gen_products()
    con.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?)", products)

    customers = gen_customers()
    con.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)", customers)

    orders = gen_orders(customers)
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)

    items = gen_order_items(orders, products)
    con.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)

    subs = gen_subscriptions(customers, orders)
    con.executemany("INSERT INTO subscriptions VALUES (?,?,?,?,?,?)", subs)

    sub_events = gen_subscription_events(subs)
    con.executemany("INSERT INTO subscription_events VALUES (?,?,?,?,?,?)", sub_events)

    web = gen_web_events(customers)
    con.executemany("INSERT INTO web_events VALUES (?,?,?,?,?,?,?)", web)

    segments = gen_customer_segments(con)
    con.executemany("INSERT INTO customer_segments_history VALUES (?,?,?,?,?,?)", segments)

    con.close()

    print(f"Built {db}")
    con2 = duckdb.connect(db, read_only=True)
    tables = [
        "regions", "producers", "products", "customers", "orders",
        "order_items", "subscriptions", "subscription_events",
        "web_events", "customer_segments_history",
    ]
    for t in tables:
        n = con2.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<35} {n:>6,} rows")
    con2.close()


if __name__ == "__main__":
    main()
