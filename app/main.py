"""FastAPI entrypoint: mock APIs + /chat agent endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent.runner import run_agent
from app.agent.tools import ToolCallRecord
from app.api.routes import router as api_router
from app.config import get_settings
from app.logging_setup import get_logger, setup_logging

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="AI QA Playground",
    description="Small support agent with mock tools — built for AI behavior testing.",
    version="0.1.0",
)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def _startup() -> None:
    setup_logging()
    from app.db import ensure_seeded

    ensure_seeded()
    get_logger().info("app started")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = get_logger()
    if request.url.path.startswith(("/static", "/docs", "/openapi", "/redoc")):
        return await call_next(request)
    response = await call_next(request)
    logger.info("%s %s → %s", request.method, request.url.path, response.status_code)
    return response


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = Field(default="123", min_length=1)
    fault: Literal["none", "tool_500", "fake_tool_response"] = "none"
    language: Literal["bg", "en"] = "en"


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallRecord]
    agent_mode: str
    user_id: str
    language: Literal["bg", "en"]


@app.get("/")
def ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "ok": True,
        "agent_mode": "openai" if settings.use_openai else "local",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    settings = get_settings()
    logger = get_logger()
    logger.info(
        "chat request user_id=%s fault=%s lang=%s message=%s",
        body.user_id,
        body.fault,
        body.language,
        body.message[:200],
    )
    reply, tool_calls = run_agent(
        body.message,
        authenticated_user_id=body.user_id,
        fault=body.fault,
        lang=body.language,
    )
    for tool in tool_calls:
        logger.info(
            "tool name=%s denied=%s error=%s args=%s result=%s",
            tool.name,
            tool.denied,
            tool.error,
            json.dumps(tool.arguments, ensure_ascii=False)[:300],
            json.dumps(tool.result, ensure_ascii=False, default=str)[:500]
            if tool.result is not None
            else "null",
        )
    logger.info("chat reply=%s", reply[:300])
    return ChatResponse(
        reply=reply,
        tool_calls=tool_calls,
        agent_mode="openai" if settings.use_openai else "local",
        user_id=body.user_id,
        language=body.language,
    )
