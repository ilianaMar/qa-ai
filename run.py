"""
AI QA Playground — support agent with mock tools.

Flow:
  User → LLM/planner → Decision → Tool call → Response

Tools:
  GET  /users/{user_id}
  POST /users
  GET  /orders/{order_id}
  POST /orders
  POST /tickets
  POST /chat          (agent entrypoint; returns reply + tool_calls for assertions)
"""

from __future__ import annotations

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
