"""Deterministic local planner — reliable for CI / Playwright without an API key."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


ORDER_RE = re.compile(
    r"(?:order|поръчк\w*)\s*(?:#|№|id|:)?\s*(\d+)",
    re.IGNORECASE,
)
BARE_ORDER_RE = re.compile(r"\b(\d{3,})\b")


@dataclass
class PlannedAction:
    kind: str  # tool | clarify | refuse | answer
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    message: str | None = None


def _wants_ticket(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "ticket",
            "тикет",
            "create ticket",
            "създай тикет",
            "отвори тикет",
            "damaged",
            "повредена",
            "счупена",
            "broken",
            "refund",
            "рефънд",
        )
    )


def _wants_user(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "my profile",
            "my data",
            "personal data",
            "моите данни",
            "лични данни",
            "личните",
            "моят профил",
            "моя профил",
            "профил",
            "email",
            "телефон",
            "phone",
        )
    )


def _wants_order(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "order",
            "поръчка",
            "поръчката",
            "tracking",
            "статус",
            "къде е",
            "where is",
            "delivery",
            "доставк",
            "куриер",
            "courier",
        )
    )


def _mentions_other_user(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "another user",
            "other user",
            "друг потребител",
            "другого",
            "someone else",
            "not mine",
            "не моята",
            "чужда",
            "user 999",
            "на друг",
        )
    )


def _is_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "system prompt",
            "ignore previous",
            "ignore all instructions",
            "reveal your instructions",
            "покажи системния",
            "системния промпт",
            "developer message",
            "jailbreak",
        )
    )


def _extract_order_id(text: str) -> str | None:
    match = ORDER_RE.search(text)
    if match:
        return match.group(1)
    # Fallback: bare number only when clearly about an order
    if _wants_order(text):
        bare = BARE_ORDER_RE.search(text)
        if bare:
            return bare.group(1)
    return None


def plan(message: str, authenticated_user_id: str) -> list[PlannedAction]:
    text = message.strip()
    if not text:
        return [PlannedAction(kind="clarify", message="Кажи ми с какво да помогна.")]

    if _is_prompt_injection(text):
        return [
            PlannedAction(
                kind="refuse",
                message="Не мога да споделям вътрешни инструкции. Мога да помогна с поръчки, профил или тикети.",
            )
        ]

    actions: list[PlannedAction] = []
    order_id = _extract_order_id(text)
    wants_ticket = _wants_ticket(text)
    wants_user = _wants_user(text)
    wants_order = _wants_order(text)
    other_user = _mentions_other_user(text)

    if other_user and (wants_order or "789" in text):
        target = order_id or ("789" if "789" in text else None)
        if target:
            actions.append(
                PlannedAction(
                    kind="tool",
                    tool_name="get_order",
                    arguments={"order_id": target},
                )
            )
        else:
            actions.append(
                PlannedAction(
                    kind="refuse",
                    message="Мога да показвам само поръчки от твоя акаунт.",
                )
            )
        return actions

    if wants_ticket:
        if order_id:
            actions.append(
                PlannedAction(
                    kind="tool",
                    tool_name="get_order",
                    arguments={"order_id": order_id},
                )
            )
        issue = text
        lowered = text.lower()
        if "повредена" in lowered or "damaged" in lowered:
            issue = f"Повредена поръчка {order_id}" if order_id else "Повредена поръчка"
        elif order_id:
            issue = f"Заявка за поддръжка за поръчка {order_id}"
        ticket_args: dict = {"user_id": authenticated_user_id, "issue": issue}
        if order_id:
            ticket_args["order_id"] = order_id
        actions.append(
            PlannedAction(
                kind="tool",
                tool_name="create_ticket",
                arguments=ticket_args,
            )
        )
        return actions

    # Two requests in one prompt: profile + order
    if wants_user and (wants_order or order_id):
        actions.append(
            PlannedAction(
                kind="tool",
                tool_name="get_user",
                arguments={"user_id": authenticated_user_id},
            )
        )
        if not order_id:
            actions.append(
                PlannedAction(
                    kind="clarify",
                    message="Кой е номерът на поръчката?",
                )
            )
            return actions
        actions.append(
            PlannedAction(
                kind="tool",
                tool_name="get_order",
                arguments={"order_id": order_id},
            )
        )
        return actions

    if wants_user:
        actions.append(
            PlannedAction(
                kind="tool",
                tool_name="get_user",
                arguments={"user_id": authenticated_user_id},
            )
        )
        return actions

    if wants_order or order_id:
        if not order_id:
            return [
                PlannedAction(
                    kind="clarify",
                    message="Кой е номерът на поръчката?",
                )
            ]
        actions.append(
            PlannedAction(
                kind="tool",
                tool_name="get_order",
                arguments={"order_id": order_id},
            )
        )
        return actions

    return [
        PlannedAction(
            kind="clarify",
            message="Мога да проверя статус на поръчка, профил или да създам тикет. С какво да помогна?",
        )
    ]
