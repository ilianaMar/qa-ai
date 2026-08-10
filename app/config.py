from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    agent_mode: str = "local"  # local | openai
    openai_model: str = "gpt-4o-mini"
    host: str = "127.0.0.1"
    port: int = 8002

    # SQLite file (relative to project root unless absolute)
    database_path: str = "data/qa_ai.db"

    # Jira Cloud (optional)
    jira_base_url: str = ""  # e.g. https://your-domain.atlassian.net
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""  # e.g. QA
    jira_issue_type: str = "Task"

    @property
    def use_openai(self) -> bool:
        return self.agent_mode == "openai" and bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
