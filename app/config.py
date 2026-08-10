from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    agent_mode: str = "local"  # local | openai
    openai_model: str = "gpt-4o-mini"
    host: str = "127.0.0.1"
    port: int = 8002

    @property
    def use_openai(self) -> bool:
        return self.agent_mode == "openai" and bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
