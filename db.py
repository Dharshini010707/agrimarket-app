"""
db.py — SQLite data layer for AgriMarket.

Everything the app needs to persist (users, crop listings, buyer offers,
reviews) lives in a single local SQLite file: agrimarket.db, created
automatically the first time the app runs.
"""

import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "agrimarket.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('farmer','buyer')),
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            location TEXT,
            language TEXT DEFAULT 'en',
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            crop_name TEXT NOT NULL,
            quantity TEXT,
            unit TEXT DEFAULT 'quintal',
            expected_price REAL,
            location TEXT,
            photo_path TEXT,
            created_at TEXT,
            FOREIGN KEY(farmer_id) REFERENCES users(id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS buyer_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER NOT NULL,
            crop_name TEXT NOT NULL,
            offered_price REAL,
            unit TEXT DEFAULT 'quintal',
            created_at TEXT,
            FOREIGN KEY(buyer_id) REFERENCES users(id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_user_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT,
            FOREIGN KEY(target_user_id) REFERENCES users(id),
            FOREIGN KEY(reviewer_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def now():
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------- Users ----
def create_user(role, name, phone, location, language="en"):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (role, name, phone, location, language, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (role, name, phone, location, language, now()),
    )
    conn.commit()
    uid = c.lastrowid
    conn.close()
    return uid


def get_user_by_phone(phone):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(user_id, name=None, location=None, language=None):
    user = get_user(user_id)
    if not user:
        return
    name = name if name is not None else user["name"]
    location = location if location is not None else user["location"]
    language = language if language is not None else user["language"]
    conn = get_conn()
    conn.execute(
        "UPDATE users SET name=?, location=?, language=? WHERE id=?",
        (name, location, language, user_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- Crops ----
def add_crop(farmer_id, crop_name, quantity, unit, expected_price, location, photo_path):
    conn = get_conn()
    conn.execute(
        """INSERT INTO crops
           (farmer_id, crop_name, quantity, unit, expected_price, location, photo_path, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (farmer_id, crop_name, quantity, unit, expected_price, location, photo_path, now()),
    )
    conn.commit()
    conn.close()


def get_crops(search=None, location=None):
    conn = get_conn()
    query = """
        SELECT crops.*, users.name AS farmer_name, users.phone AS farmer_phone
        FROM crops JOIN users ON crops.farmer_id = users.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND crops.crop_name LIKE ?"
        params.append(f"%{search}%")
    if location:
        query += " AND crops.location LIKE ?"
        params.append(f"%{location}%")
    query += " ORDER BY crops.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_crops_by_farmer(farmer_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM crops WHERE farmer_id = ? ORDER BY created_at DESC", (farmer_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_distinct_crop_names(limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT crop_name, COUNT(*) AS cnt FROM crops GROUP BY crop_name ORDER BY cnt DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [r["crop_name"] for r in rows]


# --------------------------------------------------------- Buyer offers ----
def add_buyer_offer(buyer_id, crop_name, offered_price, unit="quintal"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO buyer_offers (buyer_id, crop_name, offered_price, unit, created_at) "
        "VALUES (?,?,?,?,?)",
        (buyer_id, crop_name, offered_price, unit, now()),
    )
    conn.commit()
    conn.close()


def get_buyer_offers(buyer_id=None):
    conn = get_conn()
    if buyer_id:
        rows = conn.execute(
            "SELECT * FROM buyer_offers WHERE buyer_id = ? ORDER BY created_at DESC",
            (buyer_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM buyer_offers ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_buyers(search_location=None, search_crop=None):
    conn = get_conn()
    query = "SELECT * FROM users WHERE role = 'buyer'"
    params = []
    if search_location:
        query += " AND location LIKE ?"
        params.append(f"%{search_location}%")
    rows = conn.execute(query, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        b = dict(r)
        offers = get_buyer_offers(b["id"])
        if search_crop:
            offers = [o for o in offers if search_crop.lower() in o["crop_name"].lower()]
            if not offers:
                continue
        b["offers"] = offers
        b["avg_rating"], b["review_count"] = get_avg_rating(b["id"])
        result.append(b)
    return result


# -------------------------------------------------------------- Reviews ----
def add_review(target_user_id, reviewer_id, rating, comment):
    conn = get_conn()
    conn.execute(
        "INSERT INTO reviews (target_user_id, reviewer_id, rating, comment, created_at) "
        "VALUES (?,?,?,?,?)",
        (target_user_id, reviewer_id, rating, comment, now()),
    )
    conn.commit()
    conn.close()


def get_reviews(target_user_id):
    conn = get_conn()
    rows = conn.execute(
        """SELECT reviews.*, users.name AS reviewer_name FROM reviews
           JOIN users ON reviews.reviewer_id = users.id
           WHERE target_user_id = ? ORDER BY reviews.created_at DESC""",
        (target_user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_avg_rating(target_user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT AVG(rating) AS avg_r, COUNT(*) AS cnt FROM reviews WHERE target_user_id = ?",
        (target_user_id,),
    ).fetchone()
    conn.close()
    if row and row["cnt"]:
        return round(row["avg_r"], 1), row["cnt"]
    return None, 0
