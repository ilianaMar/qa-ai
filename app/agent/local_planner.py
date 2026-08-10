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


def _wants_jira(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "jira",
            "джира",
            "create jira",
            "създай в jira",
            "отвори в jira",
            "jira ticket",
            "jira issue",
        )
    )


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


def _wants_list_orders(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "list orders",
            "my orders",
            "all orders",
            "show orders",
            "orders list",
            "моите поръчки",
            "поръчките ми",
            "всички поръчки",
            "списък с поръчки",
            "какви поръчки",
            "покажи поръчките",
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


def _wants_create_order(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "create order",
            "create an order",
            "place order",
            "place an order",
            "new order",
            "създай поръчка",
            "създай ордер",
            "нова поръчка",
            "направи поръчка",
        )
    )


def _wants_create_user(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "create user",
            "create a user",
            "register user",
            "new user",
            "създай потребител",
            "създай юзър",
            "създай user",
            "нов потребител",
            "регистрирай",
        )
    )


def _extract_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    match = re.search(r"(\+?\d[\d\s-]{7,}\d)", text)
    if not match:
        return None
    return re.sub(r"[\s-]", "", match.group(1))


def _extract_total(text: str) -> float | None:
    match = re.search(
        r"(?:total|amount|цена|за)\s*[:=]?\s*(\d+(?:[.,]\d+)?)",
        text,
        re.IGNORECASE,
    )
    if match:
        return float(match.group(1).replace(",", "."))
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:лв|bgn|eur|\$)?\b", text, re.IGNORECASE)
    if match and _wants_create_order(text):
        return float(match.group(1).replace(",", "."))
    return None


def _extract_item_name(text: str) -> str | None:
    patterns = [
        r"(?:item|product|продукт|артикул)\s*[:=]?\s*[\"']?([^\"'\n,;]+)[\"']?",
        r"(?:for|за)\s+(?:a\s+|an\s+)?([A-Za-zА-Яа-я0-9][\w\s-]{1,40})",
        r"(?:поръчка|order)\s+(?:за|for)\s+([A-Za-zА-Яа-я0-9][\w\s-]{1,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip(" .")
            # Avoid capturing trailing price phrases
            name = re.split(r"\b(?:total|amount|цена|за\s+\d)\b", name, maxsplit=1)[0].strip()
            if name and name.lower() not in {"order", "поръчка", "user", "ticket"}:
                return name
    return None


def _extract_user_name(text: str) -> str | None:
    patterns = [
        r"(?:name|име)\s*[:=]\s*([A-Za-zА-Яа-я][\w\s.-]{1,40})",
        r"(?:user|потребител|юзър)\s+([A-Za-zА-Яа-я][\w.-]{1,40})",
        r"(?:create user|създай потребител|създай юзър)\s+([A-Za-zА-Яа-я][\w\s.-]{1,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip(" .,")
            # Stop before email/phone keywords
            name = re.split(r"\b(?:email|mail|phone|телефон|with|с)\b", name, maxsplit=1)[0].strip()
            if name:
                return name
    return None


def _extract_custom_user_id(text: str) -> str | None:
    match = re.search(r"(?:user[_ ]?id|id)\s*[:=]?\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _extract_custom_order_id_for_create(text: str) -> str | None:
    match = re.search(
        r"(?:order[_ ]?id|с\s+id|with\s+id)\s*[:=]?\s*(\d{3,})",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


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


def plan(
    message: str,
    authenticated_user_id: str,
    lang: str = "en",
) -> list[PlannedAction]:
    from app.agent.i18n import Lang, t

    language: Lang = "bg" if lang == "bg" else "en"
    text = message.strip()
    if not text:
        return [PlannedAction(kind="clarify", message=t(language, "empty_help"))]

    if _is_prompt_injection(text):
        return [
            PlannedAction(
                kind="refuse",
                message=t(language, "refuse_prompt"),
            )
        ]

    actions: list[PlannedAction] = []
    order_id = _extract_order_id(text)
    wants_ticket = _wants_ticket(text)
    wants_jira = _wants_jira(text)
    wants_create_order = _wants_create_order(text)
    wants_create_user = _wants_create_user(text)
    wants_user = _wants_user(text) and not wants_create_user
    wants_list = _wants_list_orders(text)
    wants_order = _wants_order(text) and not wants_list and not wants_create_order
    other_user = _mentions_other_user(text)

    if wants_create_user:
        name = _extract_user_name(text)
        email = _extract_email(text)
        phone = _extract_phone(text)
        if not name or not email or not phone:
            return [
                PlannedAction(
                    kind="clarify",
                    message=t(language, "need_user_fields"),
                )
            ]
        args: dict = {"name": name, "email": email, "phone": phone}
        custom_id = _extract_custom_user_id(text)
        if custom_id and custom_id.lower() not in {"email", "phone", "name"}:
            # Avoid treating bare words; only keep id-like tokens
            if re.fullmatch(r"[A-Za-z0-9_-]+", custom_id):
                args["user_id"] = custom_id
        actions.append(PlannedAction(kind="tool", tool_name="create_user", arguments=args))
        return actions

    if wants_create_order:
        item_name = _extract_item_name(text) or "Custom item"
        total = _extract_total(text)
        args = {
            "user_id": authenticated_user_id,
            "item_name": item_name,
            "total": total if total is not None else 0.0,
            "status": "pending",
        }
        custom_oid = _extract_custom_order_id_for_create(text)
        if custom_oid:
            args["order_id"] = custom_oid
        actions.append(PlannedAction(kind="tool", tool_name="create_order", arguments=args))
        return actions

    if other_user and (wants_order or wants_list or "789" in text):
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
                    message=t(language, "only_own_orders"),
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
            issue = (
                t(language, "damaged_order", order_id=order_id)
                if order_id
                else t(language, "damaged_order_plain")
            )
        elif order_id:
            issue = t(language, "support_order", order_id=order_id)
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

    if wants_jira:
        if order_id:
            actions.append(
                PlannedAction(
                    kind="tool",
                    tool_name="get_order",
                    arguments={"order_id": order_id},
                )
            )
        summary = (
            f"QA-AI follow-up for order {order_id}"
            if order_id
            else "QA-AI follow-up from support agent"
        )
        description = text
        jira_args: dict = {"summary": summary, "description": description}
        if order_id:
            jira_args["order_id"] = order_id
        actions.append(
            PlannedAction(
                kind="tool",
                tool_name="create_jira_issue",
                arguments=jira_args,
            )
        )
        return actions

    if wants_list:
        actions.append(
            PlannedAction(
                kind="tool",
                tool_name="list_orders",
                arguments={"user_id": authenticated_user_id},
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
                    message=t(language, "which_order"),
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
                    message=t(language, "which_order"),
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
            message=t(language, "how_help"),
        )
    ]
