"""HTTP routes that mirror the mock support APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.mock_store import (
    ApiError,
    create_order,
    create_ticket,
    create_user,
    get_order,
    get_user,
    list_orders,
    store,
)

router = APIRouter()


class TicketCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    issue: str = Field(..., min_length=1)
    order_id: str | None = None


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    user_id: str | None = None


class OrderCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    order_id: str | None = None
    status: str = "pending"
    carrier: str | None = None
    tracking: str | None = None
    items: list[dict[str, Any]] | None = None
    total: float = 0.0


@router.get("/users/{user_id}")
def read_user(user_id: str):
    try:
        return get_user(user_id)
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/users", status_code=201)
def post_user(body: UserCreate):
    try:
        return create_user(
            name=body.name,
            email=body.email,
            phone=body.phone,
            user_id=body.user_id,
        )
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/users/{user_id}/orders")
def read_user_orders(user_id: str):
    try:
        return {"user_id": user_id, "orders": list_orders(user_id)}
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/orders/{order_id}")
def read_order(order_id: str):
    try:
        return get_order(order_id)
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/orders", status_code=201)
def post_order(body: OrderCreate):
    try:
        return create_order(
            body.user_id,
            order_id=body.order_id,
            status=body.status,
            carrier=body.carrier,
            tracking=body.tracking,
            items=body.items,
            total=body.total,
        )
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/tickets", status_code=201)
def post_ticket(body: TicketCreate):
    try:
        return create_ticket(body.user_id, body.issue, order_id=body.order_id)
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/_qa/reset")
def qa_reset():
    """Reset mock data between Playwright scenarios."""
    store.reset()
    return {"ok": True, "snapshot": store.snapshot()}


@router.get("/_qa/snapshot")
def qa_snapshot():
    return store.snapshot()
