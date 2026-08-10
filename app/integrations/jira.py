"""Jira Cloud REST helper (optional — disabled when env is empty)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings


class JiraError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


def jira_enabled() -> bool:
    settings = get_settings()
    return bool(
        settings.jira_base_url
        and settings.jira_email
        and settings.jira_api_token
        and settings.jira_project_key
    )


def _text_node(text: str, *, link: str | None = None, bold: bool = False) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "text", "text": text}
    marks: list[dict[str, Any]] = []
    if bold:
        marks.append({"type": "strong"})
    if link:
        marks.append({"type": "link", "attrs": {"href": link}})
    if marks:
        node["marks"] = marks
    return node


def _paragraph(*parts: dict[str, Any] | str) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for part in parts:
        if isinstance(part, str):
            if part:
                content.append(_text_node(part))
        else:
            content.append(part)
    return {"type": "paragraph", "content": content or [_text_node("")]}


def _heading(text: str, level: int = 2) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [_text_node(text)],
    }


def _bullet_list(items: list[str | list[dict[str, Any] | str]]) -> dict[str, Any]:
    list_items = []
    for item in items:
        if isinstance(item, str):
            para = _paragraph(item)
        else:
            para = _paragraph(*item)
        list_items.append({"type": "listItem", "content": [para]})
    return {"type": "bulletList", "content": list_items}


def description_to_adf(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build Atlassian Document Format from helper blocks."""
    return {"type": "doc", "version": 1, "content": blocks}


def plain_description_to_adf(description: str) -> dict[str, Any]:
    paragraphs = [p.strip() for p in description.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [""]
    return {
        "type": "doc",
        "version": 1,
        "content": [_paragraph(p) for p in paragraphs],
    }


def _auth() -> tuple[str, str]:
    settings = get_settings()
    return settings.jira_email, settings.jira_api_token


def _base() -> str:
    return get_settings().jira_base_url.rstrip("/")


def create_issue(
    *,
    summary: str,
    description: str | list[dict[str, Any]],
    issue_type: str | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    if not jira_enabled():
        raise JiraError(
            "Jira is not configured. Set JIRA_BASE_URL, JIRA_EMAIL, "
            "JIRA_API_TOKEN, JIRA_PROJECT_KEY in .env"
        )

    settings = get_settings()
    base = _base()
    itype = issue_type or settings.jira_issue_type

    if isinstance(description, list):
        adf_description = description_to_adf(description)
    else:
        adf_description = plain_description_to_adf(description)

    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": settings.jira_project_key},
            "summary": summary[:255],
            "description": adf_description,
            "issuetype": {"name": itype},
        }
    }
    if labels:
        payload["fields"]["labels"] = labels

    url = f"{base}/rest/api/3/issue"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            json=payload,
            auth=_auth(),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    if response.status_code >= 400:
        raise JiraError(
            f"Jira API error {response.status_code}: {response.text[:500]}",
            status_code=response.status_code,
        )

    data = response.json()
    key = data.get("key")
    return {
        "key": key,
        "id": data.get("id"),
        "self": data.get("self"),
        "url": f"{base}/browse/{key}" if key else None,
    }


def update_issue(
    issue_key: str,
    *,
    summary: str | None = None,
    description: str | list[dict[str, Any]] | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    if not jira_enabled():
        raise JiraError("Jira is not configured.")

    fields: dict[str, Any] = {}
    if summary is not None:
        fields["summary"] = summary[:255]
    if description is not None:
        if isinstance(description, list):
            fields["description"] = description_to_adf(description)
        else:
            fields["description"] = plain_description_to_adf(description)
    if labels is not None:
        fields["labels"] = labels

    if not fields:
        raise JiraError("Nothing to update")

    base = _base()
    url = f"{base}/rest/api/3/issue/{issue_key}"
    with httpx.Client(timeout=30.0) as client:
        response = client.put(
            url,
            json={"fields": fields},
            auth=_auth(),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    if response.status_code >= 400:
        raise JiraError(
            f"Jira API error {response.status_code}: {response.text[:500]}",
            status_code=response.status_code,
        )

    return {"key": issue_key, "url": f"{base}/browse/{issue_key}"}
