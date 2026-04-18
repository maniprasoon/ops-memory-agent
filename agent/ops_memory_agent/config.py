from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env.example", ".env.example", "../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")
    groq_api_key: SecretStr = Field(alias="GROQ_API_KEY")
    groq_model: str = Field(default="qwen/qwen3-32b", alias="GROQ_MODEL")


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
