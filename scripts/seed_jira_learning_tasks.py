"""
Seed / refresh learning-plan stories in Jira Cloud.

Requires .env:
  JIRA_BASE_URL=https://your-domain.atlassian.net
  JIRA_EMAIL=you@example.com
  JIRA_API_TOKEN=...
  JIRA_PROJECT_KEY=KAN
  JIRA_ISSUE_TYPE=Story

Usage:
  # Update existing KAN-1..KAN-8 (default)
  .venv/bin/python scripts/seed_jira_learning_tasks.py

  # Create brand-new issues instead
  .venv/bin/python scripts/seed_jira_learning_tasks.py --create
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.integrations.jira import (
    _bullet_list,
    _heading,
    _paragraph,
    _text_node,
    create_issue,
    jira_enabled,
    update_issue,
)


def _resources(*items: tuple[str, str]) -> list[dict[str, Any]]:
    """items: (label, url)"""
    blocks: list[dict[str, Any]] = [_heading("Resources", 3)]
    blocks.append(
        _bullet_list(
            [[_text_node(f"{label}: "), _text_node(url, link=url)] for label, url in items]
        )
    )
    return blocks


def _story(
    *,
    summary: str,
    goal: str,
    why: str,
    in_repo: list[str],
    do_this: list[str],
    acceptance: list[str],
    resources: list[tuple[str, str]],
    borrow_ideas: list[str] | None = None,
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [
        _heading("Goal", 3),
        _paragraph(goal),
        _heading("Why it matters for AI QA", 3),
        _paragraph(why),
        _heading("In this repo", 3),
        _bullet_list(in_repo),
        _heading("Do this", 3),
        _bullet_list(do_this),
        _heading("Acceptance criteria", 3),
        _bullet_list(acceptance),
    ]
    if borrow_ideas:
        blocks.append(_heading("Borrow / inspiration", 3))
        blocks.append(_bullet_list(borrow_ideas))
    blocks.extend(_resources(*resources))
    return {"summary": summary, "description": blocks}


TASKS: list[dict[str, Any]] = [
    _story(
        summary="[QA-AI Day 1] Agent basics — map User→LLM→Tool→Response",
        goal=(
            "Understand the agent loop: user → planner/LLM → tool call → "
            "result → final reply. Learn to test tool_calls, not only reply text."
        ),
        why=(
            "The most common AI QA mistake is asserting only the reply string. "
            "The real signal is: did it call the right tool, with the right arguments, "
            "and what did the tool return?"
        ),
        in_repo=[
            "app/agent/tools.py — tool schemas + execute",
            "app/agent/runner.py — orchestration (local/openai)",
            "app/agent/local_planner.py — deterministic decisions without OpenAI",
            "UI: http://127.0.0.1:8002/ — tool-call inspector under each reply",
        ],
        do_this=[
            "Run python run.py and open the chat UI",
            "Send at least 5 prompts: order status, profile, ticket, help, invalid order",
            "For each, record: expected tool, actual tool_calls, reply",
            "Compare AGENT_MODE=local vs openai (if you have a key) — same tool choices?",
        ],
        acceptance=[
            "You have a table: prompt → expected tool(s) → actual tool_calls",
            "You know the difference between reply text and tool_calls[] in /chat JSON",
            "You can explain User→Decision→Tool→Response with an example from this repo",
        ],
        borrow_ideas=[
            "From OpenAI docs: function calling = tools; assert on name + arguments",
            "From LangChain/LangGraph tutorials: agent-loop diagrams (ideas only — don't copy the whole stack)",
        ],
        resources=[
            (
                "OpenAI Function calling",
                "https://platform.openai.com/docs/guides/function-calling",
            ),
            (
                "OpenAI Agents / tools overview",
                "https://platform.openai.com/docs/guides/tools",
            ),
            (
                "FastAPI Tutorial (routing basics)",
                "https://fastapi.tiangolo.com/tutorial/",
            ),
            (
                "Playwright APIRequestContext (how we test /chat)",
                "https://playwright.dev/python/docs/api/class-apirequestcontext",
            ),
        ],
    ),
    _story(
        summary="[QA-AI Day 2] Tools + schema — list_orders",
        goal=(
            "Understand tool JSON schemas and the difference between list_orders "
            "(collection) vs get_order (single resource by id)."
        ),
        why=(
            "Wrong tool = wrong data. The schema is the contract between the LLM and "
            "the backend. QA should validate both the schema and runtime arguments."
        ),
        in_repo=[
            "TOOL_DEFINITIONS in app/agent/tools.py",
            "list_orders / get_order in app/api/mock_store.py + app/db.py",
            "Tests in tests/test_agent_qa.py (search for list_orders)",
            "SQLite: data/qa_ai.db → tables users, orders, tickets",
        ],
        do_this=[
            "Read the list_orders and get_order schemas",
            'Prompt: "Show all my orders" as user 123 → expect list_orders',
            "Prompt with a concrete id → get_order",
            "Write/verify a Playwright assert: tool name + only order ids owned by user 123",
        ],
        acceptance=[
            "Test asserts tool name == list_orders",
            "Result contains no foreign order ids (e.g. 789 for user 123)",
            "You can explain which schema field makes the model pass user_id",
        ],
        borrow_ideas=[
            "JSON Schema docs — required, type, enum (for future tool params)",
            "REST naming: GET /users/{id}/orders ≈ list_orders",
        ],
        resources=[
            (
                "JSON Schema — Understanding JSON Schema",
                "https://json-schema.org/understanding-json-schema/",
            ),
            (
                "OpenAI tool/function parameters",
                "https://platform.openai.com/docs/guides/function-calling#function-calling-with-tools",
            ),
            (
                "SQLite Python docs",
                "https://docs.python.org/3/library/sqlite3.html",
            ),
        ],
    ),
    _story(
        summary="[QA-AI Day 3] AuthZ matrix",
        goal=(
            "Build an allow/deny matrix: foreign order, foreign profile, "
            "forged user_id on list_orders / create_ticket."
        ),
        why=(
            'An LLM may "cooperate" with a malicious prompt. AuthZ must live in the '
            "tool layer (code), not only in the system prompt."
        ),
        in_repo=[
            "Guards in app/agent/tools.py (authenticated user vs arguments)",
            "Seed data: user 123 (orders 456, 321) vs user 999 (order 789)",
            "Deny tests in tests/test_agent_qa.py",
        ],
        do_this=[
            "Make a table: actor user_id × resource × expected (allow/deny)",
            "Cases: 123 asks for order 789; 999 asks for 123's profile; ticket for a foreign order",
            "Check: denied/error in tool_calls + reply without foreign email/tracking/total",
            "Add a missing test if you find a gap",
        ],
        acceptance=[
            "For every deny: tool error/denied and no leaked foreign fields in the reply",
            "Snapshot/DB does not contain a ticket created for a foreign order",
            "AuthZ matrix documented (README or a comment next to the test)",
        ],
        borrow_ideas=[
            "OWASP Broken Access Control — apply to tool arguments, not only HTTP routes",
            "Classic IDOR tests → here IDOR via chat prompt + tool args",
        ],
        resources=[
            (
                "OWASP API Security — BOLA/IDOR",
                "https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",
            ),
            (
                "OWASP Top 10 for LLM Apps",
                "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            ),
            (
                "PortSwigger — Access control",
                "https://portswigger.net/web-security/access-control",
            ),
        ],
    ),
    _story(
        summary="[QA-AI Day 4] Failure modes",
        goal=(
            "Expand fault injection: tool_500, fake_tool_response, missing ids. "
            "Ensure the agent does not hallucinate success."
        ),
        why=(
            'Models love to "fill in" missing data. AI QA = negative + chaos testing '
            "at the tool layer."
        ),
        in_repo=[
            "fault parameter on /chat and the UI dropdown",
            "Error handling in runner.py (no shipped/delivered on 500)",
            "Existing tool_500 / fake payload tests",
        ],
        do_this=[
            "Run the same order prompt with fault=tool_500 and without — compare replies",
            "With fake_tool_response, check whether UI/tests catch invented data",
            "Missing / invalid order id — clarification vs 404, no hallucinations",
            "Add 1 new negative test if coverage is missing",
        ],
        acceptance=[
            "On tool_500: no shipped/delivered/successful ticket in the reply",
            "On missing order: no invented tracking/carrier",
            "Tests pass in AGENT_MODE=local without an OpenAI key",
        ],
        borrow_ideas=[
            "Chaos engineering ideas → fault flags instead of a real chaos mesh",
            "Contract testing: tool result schema vs what the agent quotes in the reply",
        ],
        resources=[
            (
                "OWASP LLM — Improper Output Handling / Hallucinations themes",
                "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            ),
            (
                "Playwright assertions",
                "https://playwright.dev/python/docs/test-assertions",
            ),
            (
                "pytest docs",
                "https://docs.pytest.org/en/stable/",
            ),
        ],
    ),
    _story(
        summary="[QA-AI Day 5] Prompt hardening",
        goal=(
            "Add jailbreak / prompt-leak cases in BG and EN. "
            "System prompt and internal instructions must not leak."
        ),
        why=(
            "Prompt injection is a top LLM risk. For agent apps: injection → tool abuse. "
            "You need both refusal behavior and AuthZ in code."
        ),
        in_repo=[
            "SYSTEM / i18n strings in app/agent/i18n.py",
            "Existing prompt-injection tests in test_agent_qa.py",
            "local_planner heuristics for jailbreak-ish phrases",
        ],
        do_this=[
            'Collect 5+ attacks: "ignore previous", "reveal system prompt", admin roleplay, base64 tricks',
            "Run them in BG and EN",
            "Check: reply refuses; system prompt text never appears; tools are not abused",
            "Document which attacks only pass because of local planner vs openai",
        ],
        acceptance=[
            "No case returns the system prompt / a tool-schema dump",
            "Tests cover at least one BG + one EN leak attempt",
            'Short "known gaps" list if openai mode is weaker',
        ],
        borrow_ideas=[
            "Gandalf / prompt-injection playgrounds — phrasing ideas",
            "OWASP LLM01 Prompt Injection — attack categories",
        ],
        resources=[
            (
                "OWASP LLM01: Prompt Injection",
                "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            ),
            (
                "OpenAI — Safety best practices",
                "https://platform.openai.com/docs/guides/safety-checks",
            ),
            (
                "Learn Prompting — Prompt Hacking",
                "https://learnprompting.org/docs/prompt_hacking/introduction",
            ),
            (
                "NIST AI RMF (overview)",
                "https://www.nist.gov/itl/ai-risk-management-framework",
            ),
        ],
    ),
    _story(
        summary="[QA-AI Day 6] Multi-step flows",
        goal=(
            "Test sequences: get_order → create_ticket; profile + order combo. "
            "Assert exact tool order."
        ),
        why=(
            "Real agent bugs live in orchestration: skipped steps, wrong order, "
            "ticket without checking order ownership."
        ),
        in_repo=[
            "local_planner.py — wants_ticket + order lookup",
            "create_ticket flow tests",
            "DB table tickets (persistent tickets after create_ticket)",
        ],
        do_this=[
            "Damaged order 456 → expect get_order then create_ticket",
            "Missing order → NO successful create_ticket (or create_ticket with error)",
            "Check data/qa_ai.db → tickets after a successful flow",
            "Add a test for exact tool order (names == [...])",
        ],
        acceptance=[
            "Happy path: tool order is get_order, create_ticket",
            "Missing order: no successful ticket_id in reply or DB",
            "SQLite ticket has correct user_id / order_id / issue",
        ],
        borrow_ideas=[
            "State machine / BDD Given-When-Then for multi-step agent flows",
            "Snapshot testing of the tool_calls list (names + key args)",
        ],
        resources=[
            (
                "Playwright Python — API testing",
                "https://playwright.dev/python/docs/api-testing",
            ),
            (
                "FastAPI dependency / error handling",
                "https://fastapi.tiangolo.com/tutorial/handling-errors/",
            ),
            (
                "Atlassian Jira REST API (when ticket → Jira)",
                "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/",
            ),
        ],
    ),
    _story(
        summary="[QA-AI Day 7] Portfolio automation",
        goal=(
            "Grow the Playwright suite, polish the README test matrix, "
            "record a short portfolio demo."
        ),
        why=(
            "AI QA skill is proven by a reproducible suite + clear assertions "
            "(tools, authz, faults) — not only a chatbot demo."
        ),
        in_repo=[
            "tests/test_agent_qa.py + tests/conftest.py",
            "README.md — test matrix / scenarios",
            "UI scenario chips in app/static/app.js",
        ],
        do_this=[
            "Group tests: happy / authz / fault / injection / multi-step",
            "Ensure pytest is green with AGENT_MODE=local",
            "Update README with a prompt → expected tools matrix",
            "Optional: 60–90s screen recording of the UI + a failing fault case",
        ],
        acceptance=[
            "pytest green without OPENAI_API_KEY",
            "README has a clear test matrix",
            "You have 1 portfolio artifact (recording or markdown report)",
        ],
        borrow_ideas=[
            "GitHub Actions pytest workflow (idea for a CI badge)",
            "Allure / pytest-html for reports of tool traces",
        ],
        resources=[
            (
                "pytest good practices",
                "https://docs.pytest.org/en/stable/explanation/goodpractices.html",
            ),
            (
                "GitHub Actions — Python",
                "https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python",
            ),
            (
                "Playwright trace viewer",
                "https://playwright.dev/python/docs/trace-viewer",
            ),
        ],
    ),
    _story(
        summary="[QA-AI] DB + Jira agent path",
        goal=(
            "Verify end-to-end: users/orders/tickets in SQLite; "
            "create_ticket can also create a Jira issue when JIRA_* is set."
        ),
        why=(
            "Integrations are where AI agents touch real systems. "
            "QA should check both local persistence and the external side effect."
        ),
        in_repo=[
            "app/db.py — users, orders, tickets",
            "app/integrations/jira.py — create_issue / update_issue",
            "create_ticket in tools.py — optional jira key in result",
            "scripts/seed_jira_learning_tasks.py — this learning plan",
        ],
        do_this=[
            "Create a ticket via chat → see the row in data/qa_ai.db table tickets",
            "With valid JIRA_* in .env: damaged-order flow → local ticket + jira.key",
            "Without Jira env: local ticket still works; jira_error or missing jira field is OK",
            "Reset mock data → tickets table cleared; users/orders reseeded",
        ],
        acceptance=[
            "tickets table is populated by create_ticket",
            "When Jira is configured: result contains jira.key + url",
            "You know how to rotate the API token (never commit it to git)",
        ],
        borrow_ideas=[
            "Contract test: mock Jira HTTP with respx/httpx mock instead of real calls in CI",
            'Keep a separate "learning board" project from production Jira',
        ],
        resources=[
            (
                "Jira Cloud REST API — Create issue",
                "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-post",
            ),
            (
                "Atlassian API tokens",
                "https://id.atlassian.com/manage-profile/security/api-tokens",
            ),
            (
                "ADF (Atlassian Document Format)",
                "https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/",
            ),
            (
                "SQLite Viewer / DB Browser",
                "https://sqlitebrowser.org/",
            ),
        ],
    ),
]


EXTRA_TASKS: list[dict[str, Any]] = [
    _story(
        summary="[QA-AI] Eval harness for nondeterministic OpenAI mode",
        goal=(
            "Build a small evaluation harness so AGENT_MODE=openai can be tested without "
            "brittle exact-string/tool-order asserts that flake every run."
        ),
        why=(
            "Local mode is deterministic (great for CI). OpenAI mode is nondeterministic: "
            "the model may phrase replies differently or occasionally pick a different tool. "
            "An eval harness scores behavior over N runs (pass rate, tool allowed-set, "
            "no-leak checks) instead of a single brittle equality."
        ),
        in_repo=[
            "AGENT_MODE=local vs openai in .env / app/config.py",
            "Playwright API suite in api/tests (currently assumes local)",
            "app/agent/runner.py — run_openai_agent path",
        ],
        do_this=[
            "Pick 5–8 golden prompts (order status, list orders, foreign order deny, ticket, injection)",
            "For each prompt define soft expectations: required tools OR allowed tool set; forbidden reply tokens; must/deny flags",
            "Run each prompt N times (e.g. 5) in openai mode; record pass/fail per criterion",
            "Report pass-rate (e.g. ≥4/5) instead of asserting 100% exact tool order",
            "Keep local mode suite as hard regression; mark openai evals as optional/nightly",
        ],
        acceptance=[
            "Documented eval rubric (criteria per prompt)",
            "Script or npm/pytest command that runs N openai trials and prints a score table",
            "At least one prompt proves flaky exact assert would fail but soft rubric still passes",
            "CI stays green on local mode without OpenAI key",
        ],
        borrow_ideas=[
            "OpenAI Evals / promptfoo / DeepEval patterns — score dimensions, not only pass/fail",
            "Separate 'contract tests' (local) from 'behavioral evals' (openai)",
        ],
        resources=[
            (
                "OpenAI Evals overview",
                "https://github.com/openai/evals",
            ),
            (
                "promptfoo — LLM eval framework",
                "https://www.promptfoo.dev/docs/intro/",
            ),
            (
                "Hugging Face — LLM Evaluation Guide",
                "https://huggingface.co/docs/evaluate/index",
            ),
        ],
    ),
    _story(
        summary="[QA-AI] OWASP LLM security deep-dive",
        goal=(
            "Map OWASP Top 10 for LLM Applications onto this playground and add concrete "
            "test cases / mitigations for the highest-risk items."
        ),
        why=(
            "AI QA without security context misses the expensive bugs: prompt injection → "
            "tool abuse, data leakage, over-permissioned tools, insecure output handling. "
            "Employers hiring AI QA expect OWASP LLM vocabulary + demos."
        ),
        in_repo=[
            "Existing injection tests (api/tests + local_planner refuse path)",
            "AuthZ guards in app/agent/tools.py",
            "Fault injection fake_tool_response",
            "System prompt rules in app/agent/i18n.py",
        ],
        do_this=[
            "Read OWASP LLM Top 10 and make a table: risk → how it appears in qa-ai → current coverage → gap",
            "Focus first on: LLM01 Prompt Injection, LLM02 Insecure Output Handling, LLM06 Sensitive Info Disclosure, LLM08 Excessive Agency",
            "Add ≥3 new attack cases (BG+EN) that try tool abuse or data leak",
            "Document mitigations already in code (AuthZ in tools, not only prompt) vs still missing",
            "Optional: short threat model one-pager for the support agent",
        ],
        acceptance=[
            "OWASP LLM mapping doc (markdown in repo or Jira comment)",
            "New automated tests for at least 3 security scenarios",
            "Clear statement: which controls are in code vs prompt-only",
            "No secrets from .env appear in replies or tool fake payloads trusted as truth",
        ],
        borrow_ideas=[
            "Treat tool arguments like an API: validate/authorize every call",
            "Never trust model output for security decisions — enforce in execute_tool",
        ],
        resources=[
            (
                "OWASP Top 10 for Large Language Model Applications",
                "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            ),
            (
                "OWASP LLM01: Prompt Injection",
                "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
            ),
            (
                "Learn Prompting — Prompt Hacking",
                "https://learnprompting.org/docs/prompt_hacking/introduction",
            ),
            (
                "NIST AI Risk Management Framework",
                "https://www.nist.gov/itl/ai-risk-management-framework",
            ),
        ],
    ),
    _story(
        summary="[QA-AI] Case study / portfolio writeup",
        goal=(
            "Write a short public case study that turns this repo into interview-ready "
            "portfolio proof: problem → approach → bugs found → what you assert."
        ),
        why=(
            "Hiring managers rarely clone repos first. A 1–2 page writeup + demo link "
            "converts 'I know Playwright' into 'I know how to test AI agents'."
        ),
        in_repo=[
            "README.md — expand with test matrix / architecture diagram",
            "api/tests + e2e/tests — cite concrete examples",
            "GitHub repo https://github.com/ilianaMar/qa-ai",
            "Optional: short screen recording of UI tool inspector + failing fault case",
        ],
        do_this=[
            "Draft structure: Context → Architecture (User→Tool→Reply) → What I test → Example bug/finding → Stack → Next steps",
            "Include 1 AuthZ example and 1 hallucination/fault example with before/after asserts",
            "Add a prompt → expected tools matrix to README",
            "Publish as README section and/or LinkedIn/Notion/GitHub Pages post",
            "Optional: 60–90s demo video showing tool_calls inspector",
        ],
        acceptance=[
            "Written case study (≥400 words) linked from README",
            "Contains architecture sketch + 2 concrete test examples with expected tools",
            "States clearly: local mode for CI, openai for eval/demo",
            "No secrets (.env / tokens) in the writeup or screenshots",
        ],
        borrow_ideas=[
            "Title angle: 'How I test an AI support agent beyond reply text'",
            "Show a failing fake_tool_response case — very memorable in interviews",
        ],
        resources=[
            (
                "Writing a technical case study (guidance)",
                "https://developers.google.com/tech-writing",
            ),
            (
                "Playwright trace viewer — good for demo screenshots",
                "https://playwright.dev/docs/trace-viewer",
            ),
            (
                "GitHub profile README / project README tips",
                "https://docs.github.com/en/get-started/writing-on-github",
            ),
        ],
    ),
]


# Existing seeded keys from first run (update in place — no duplicates)
DEFAULT_ISSUE_KEYS = [
    "KAN-1",
    "KAN-2",
    "KAN-3",
    "KAN-4",
    "KAN-5",
    "KAN-6",
    "KAN-7",
    "KAN-8",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or refresh QA-AI learning stories in Jira")
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create brand-new issues for ALL TASKS (duplicates if already seeded)",
    )
    parser.add_argument(
        "--create-extra",
        action="store_true",
        help="Create only EXTRA_TASKS (eval harness, OWASP LLM, portfolio writeup)",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not jira_enabled():
        print("Jira is not configured.")
        print("Add to .env:")
        print("  JIRA_BASE_URL=https://your-domain.atlassian.net")
        print("  JIRA_EMAIL=you@example.com")
        print("  JIRA_API_TOKEN=...")
        print("  JIRA_PROJECT_KEY=KAN")
        raise SystemExit(1)

    labels = ["qa-ai", "learning-plan"]

    if args.create_extra:
        print(f"Creating {len(EXTRA_TASKS)} extra issues in project {settings.jira_project_key} ...")
        for task in EXTRA_TASKS:
            issue = create_issue(
                summary=task["summary"],
                description=task["description"],
                labels=labels,
            )
            print(f"  ✓ {issue['key']}  {issue.get('url')}")
    elif args.create:
        print(f"Creating {len(TASKS)} issues in project {settings.jira_project_key} ...")
        for task in TASKS:
            issue = create_issue(
                summary=task["summary"],
                description=task["description"],
                labels=labels,
            )
            print(f"  ✓ {issue['key']}  {issue.get('url')}")
    else:
        if len(TASKS) != len(DEFAULT_ISSUE_KEYS):
            raise SystemExit("TASKS count must match DEFAULT_ISSUE_KEYS")
        print(f"Updating {len(TASKS)} existing issues ...")
        for key, task in zip(DEFAULT_ISSUE_KEYS, TASKS, strict=True):
            issue = update_issue(
                key,
                summary=task["summary"],
                description=task["description"],
                labels=labels,
            )
            print(f"  ✓ {issue['key']}  {issue.get('url')}")
    print("Done.")


if __name__ == "__main__":
    main()
