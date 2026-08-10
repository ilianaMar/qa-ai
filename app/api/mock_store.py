"""In-memory mock backend for users, orders, and tickets."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class MockStore:
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    tickets: dict[str, dict[str, Any]] = field(default_factory=dict)

    def reset(self) -> None:
        self.users = {
            "123": {
                "user_id": "123",
                "name": "Ana Petrova",
                "email": "ana@example.com",
                "phone": "+359888000123",
            },
            "999": {
                "user_id": "999",
                "name": "Other User",
                "email": "other@example.com",
                "phone": "+359888000999",
            },
        }
        self.orders = {
            "456": {
                "order_id": "456",
                "user_id": "123",
                "status": "shipped",
                "carrier": "Speedy",
                "tracking": "SPY123456",
                "items": [{"sku": "KB-01", "name": "Mechanical Keyboard", "qty": 1}],
                "total": 189.90,
            },
            "789": {
                "order_id": "789",
                "user_id": "999",
                "status": "delivered",
                "carrier": "Econt",
                "tracking": "ECO987654",
                "items": [{"sku": "MS-02", "name": "Wireless Mouse", "qty": 2}],
                "total": 79.50,
            },
        }
        self.tickets = {}

    def snapshot(self) -> dict[str, Any]:
        return {
            "users": deepcopy(self.users),
            "orders": deepcopy(self.orders),
            "tickets": deepcopy(self.tickets),
        }


store = MockStore()
store.reset()


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def get_user(user_id: str) -> dict[str, Any]:
    user = store.users.get(user_id)
    if not user:
        raise ApiError(404, f"User '{user_id}' not found")
    return deepcopy(user)


def get_order(order_id: str) -> dict[str, Any]:
    order = store.orders.get(order_id)
    if not order:
        raise ApiError(404, f"Order '{order_id}' not found")
    return deepcopy(order)


def create_ticket(user_id: str, issue: str, order_id: str | None = None) -> dict[str, Any]:
    if user_id not in store.users:
        raise ApiError(404, f"User '{user_id}' not found")
    if not issue or not issue.strip():
        raise ApiError(400, "Issue description is required")
    if order_id:
        order = store.orders.get(order_id)
        if not order:
            raise ApiError(404, f"Order '{order_id}' not found")
        if order["user_id"] != user_id:
            raise ApiError(403, "Order belongs to another user")

    ticket_id = f"T-{uuid4().hex[:8]}"
    ticket = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "issue": issue.strip(),
        "status": "open",
    }
    if order_id:
        ticket["order_id"] = order_id
    store.tickets[ticket_id] = ticket
    return deepcopy(ticket)
