"""Unit checks that do not need HTTP/Playwright (tool AuthZ guards)."""

from app.agent.tools import execute_tool


def test_create_order_denies_other_user_id():
    record = execute_tool(
        "create_order",
        {"user_id": "999", "item_name": "Mouse", "total": 10},
        authenticated_user_id="123",
        lang="en",
    )
    assert record.denied is True
    assert record.result is None


def test_list_orders_denies_other_user_id():
    record = execute_tool(
        "list_orders",
        {"user_id": "999"},
        authenticated_user_id="123",
        lang="bg",
    )
    assert record.denied is True
    assert record.result is None
    assert "отказ" in (record.error or "").lower() or "denied" in (record.error or "").lower()
