"""HTTP routes that mirror the mock support APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.mock_store import ApiError, create_ticket, get_order, get_user, store


router = APIRouter()


class TicketCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    issue: str = Field(..., min_length=1)
    order_id: str | None = None


@router.get("/users/{user_id}")
def read_user(user_id: str):
    try:
        return get_user(user_id)
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/orders/{order_id}")
def read_order(order_id: str):
    try:
        return get_order(order_id)
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
