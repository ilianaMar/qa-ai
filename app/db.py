"""SQLite persistence for users, orders, and tickets."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.config import get_settings

SEED_USERS = [
    {
        "user_id": "123",
        "name": "Ana Petrova",
        "email": "ana@example.com",
        "phone": "+359888000123",
    },
    {
        "user_id": "999",
        "name": "Other User",
        "email": "other@example.com",
        "phone": "+359888000999",
    },
]

SEED_ORDERS = [
    {
        "order_id": "456",
        "user_id": "123",
        "status": "shipped",
        "carrier": "Speedy",
        "tracking": "SPY123456",
        "items": [{"sku": "KB-01", "name": "Mechanical Keyboard", "qty": 1}],
        "total": 189.90,
    },
    {
        "order_id": "321",
        "user_id": "123",
        "status": "pending",
        "carrier": None,
        "tracking": None,
        "items": [{"sku": "HD-03", "name": "USB Headset", "qty": 1}],
        "total": 59.00,
    },
    {
        "order_id": "789",
        "user_id": "999",
        "status": "delivered",
        "carrier": "Econt",
        "tracking": "ECO987654",
        "items": [{"sku": "MS-02", "name": "Wireless Mouse", "qty": 2}],
        "total": 79.50,
    },
]


def db_path() -> Path:
    settings = get_settings()
    path = Path(settings.database_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                carrier TEXT,
                tracking TEXT,
                items_json TEXT NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                status TEXT NOT NULL,
                order_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );
            """
        )
        conn.commit()


def reset_db() -> None:
    """Wipe tickets; wipe and reseed users + orders."""
    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM tickets")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM users")
        for user in SEED_USERS:
            conn.execute(
                "INSERT INTO users (user_id, name, email, phone) VALUES (?, ?, ?, ?)",
                (user["user_id"], user["name"], user["email"], user["phone"]),
            )
        for order in SEED_ORDERS:
            conn.execute(
                """
                INSERT INTO orders
                (order_id, user_id, status, carrier, tracking, items_json, total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order["order_id"],
                    order["user_id"],
                    order["status"],
                    order["carrier"],
                    order["tracking"],
                    json.dumps(order["items"]),
                    order["total"],
                ),
            )
        conn.commit()


def ensure_seeded() -> None:
    init_db()
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if count == 0:
        reset_db()


def _user_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
    }


def _order_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "order_id": row["order_id"],
        "user_id": row["user_id"],
        "status": row["status"],
        "carrier": row["carrier"],
        "tracking": row["tracking"],
        "items": json.loads(row["items_json"]),
        "total": row["total"],
    }


def _ticket_from_row(row: sqlite3.Row) -> dict[str, Any]:
    ticket = {
        "ticket_id": row["ticket_id"],
        "user_id": row["user_id"],
        "issue": row["issue"],
        "status": row["status"],
    }
    if row["order_id"]:
        ticket["order_id"] = row["order_id"]
    return ticket


def fetch_user(user_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return _user_from_row(row) if row else None


def fetch_order(order_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    return _order_from_row(row) if row else None


def fetch_orders_for_user(user_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY order_id",
            (user_id,),
        ).fetchall()
    return [_order_from_row(row) for row in rows]


def insert_user(
    user_id: str,
    name: str,
    email: str,
    phone: str,
) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            "INSERT INTO users (user_id, name, email, phone) VALUES (?, ?, ?, ?)",
            (user_id, name, email, phone),
        )
        conn.commit()
    return {"user_id": user_id, "name": name, "email": email, "phone": phone}


def insert_order(
    order_id: str,
    user_id: str,
    *,
    status: str = "pending",
    carrier: str | None = None,
    tracking: str | None = None,
    items: list[dict[str, Any]] | None = None,
    total: float = 0.0,
) -> dict[str, Any]:
    items = items or [{"sku": "NEW-01", "name": "Custom item", "qty": 1}]
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO orders
            (order_id, user_id, status, carrier, tracking, items_json, total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (order_id, user_id, status, carrier, tracking, json.dumps(items), total),
        )
        conn.commit()
    return {
        "order_id": order_id,
        "user_id": user_id,
        "status": status,
        "carrier": carrier,
        "tracking": tracking,
        "items": items,
        "total": total,
    }


def insert_ticket(
    ticket_id: str,
    user_id: str,
    issue: str,
    status: str = "open",
    order_id: str | None = None,
) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tickets (ticket_id, user_id, issue, status, order_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ticket_id, user_id, issue, status, order_id),
        )
        conn.commit()
    ticket = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "issue": issue,
        "status": status,
    }
    if order_id:
        ticket["order_id"] = order_id
    return ticket


def snapshot_db() -> dict[str, Any]:
    with connect() as conn:
        users = {
            r["user_id"]: _user_from_row(r) for r in conn.execute("SELECT * FROM users").fetchall()
        }
        orders = {
            r["order_id"]: _order_from_row(r)
            for r in conn.execute("SELECT * FROM orders").fetchall()
        }
        tickets = {
            r["ticket_id"]: _ticket_from_row(r)
            for r in conn.execute("SELECT * FROM tickets").fetchall()
        }
    return {"users": users, "orders": orders, "tickets": tickets}


ensure_seeded()
