"""FastAPI entrypoint: mock APIs + /chat agent endpoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent.runner import run_agent
from app.agent.tools import ToolCallRecord
from app.api.routes import router as api_router
from app.config import get_settings


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="AI QA Playground",
    description="Small support agent with mock tools — built for AI behavior testing.",
    version="0.1.0",
)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = Field(default="123", min_length=1)
    fault: Literal["none", "tool_500", "fake_tool_response"] = "none"


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallRecord]
    agent_mode: str
    user_id: str


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
    reply, tool_calls = run_agent(
        body.message,
        authenticated_user_id=body.user_id,
        fault=body.fault,
    )
    return ChatResponse(
        reply=reply,
        tool_calls=tool_calls,
        agent_mode="openai" if settings.use_openai else "local",
        user_id=body.user_id,
    )
