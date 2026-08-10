"""Data access: SQLite users, orders, and tickets."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.db import (
    fetch_order,
    fetch_orders_for_user,
    fetch_user,
    insert_order,
    insert_ticket,
    insert_user,
    reset_db,
    snapshot_db,
)


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class _Store:
    def reset(self) -> None:
        reset_db()

    def snapshot(self) -> dict[str, Any]:
        return snapshot_db()


store = _Store()


def get_user(user_id: str) -> dict[str, Any]:
    user = fetch_user(user_id)
    if not user:
        raise ApiError(404, f"User '{user_id}' not found")
    return user


def get_order(order_id: str) -> dict[str, Any]:
    order = fetch_order(order_id)
    if not order:
        raise ApiError(404, f"Order '{order_id}' not found")
    return order


def list_orders(user_id: str) -> list[dict[str, Any]]:
    if not fetch_user(user_id):
        raise ApiError(404, f"User '{user_id}' not found")
    return fetch_orders_for_user(user_id)


def create_user(
    *,
    name: str,
    email: str,
    phone: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    if not name or not name.strip():
        raise ApiError(400, "name is required")
    if not email or not email.strip():
        raise ApiError(400, "email is required")
    if not phone or not phone.strip():
        raise ApiError(400, "phone is required")

    uid = (user_id or "").strip() or f"U-{uuid4().hex[:6]}"
    if fetch_user(uid):
        raise ApiError(409, f"User '{uid}' already exists")

    return insert_user(uid, name.strip(), email.strip(), phone.strip())


def create_order(
    user_id: str,
    *,
    order_id: str | None = None,
    status: str = "pending",
    carrier: str | None = None,
    tracking: str | None = None,
    items: list[dict[str, Any]] | None = None,
    total: float = 0.0,
) -> dict[str, Any]:
    if not fetch_user(user_id):
        raise ApiError(404, f"User '{user_id}' not found")

    oid = (order_id or "").strip()
    if not oid:
        oid = str(1000 + (uuid4().int % 9000))

    if fetch_order(oid):
        raise ApiError(409, f"Order '{oid}' already exists")

    if total < 0:
        raise ApiError(400, "total must be >= 0")

    return insert_order(
        oid,
        user_id,
        status=status or "pending",
        carrier=carrier,
        tracking=tracking,
        items=items,
        total=float(total),
    )


def create_ticket(user_id: str, issue: str, order_id: str | None = None) -> dict[str, Any]:
    if not fetch_user(user_id):
        raise ApiError(404, f"User '{user_id}' not found")
    if not issue or not issue.strip():
        raise ApiError(400, "Issue description is required")
    if order_id:
        order = fetch_order(order_id)
        if not order:
            raise ApiError(404, f"Order '{order_id}' not found")
        if order["user_id"] != user_id:
            raise ApiError(403, "Order belongs to another user")

    ticket_id = f"T-{uuid4().hex[:8]}"
    return insert_ticket(
        ticket_id=ticket_id,
        user_id=user_id,
        issue=issue.strip(),
        status="open",
        order_id=order_id or None,
    )
