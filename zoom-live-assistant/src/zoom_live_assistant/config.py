from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    system_prompt: str = Field(
        default=(
            "You are an expert sales engineer assistant in a live customer call. "
            "Provide concise, accurate suggestions the host can say out loud. "
            "If uncertain, clearly state assumptions and offer a safe clarifying question."
        ),
        alias="ASSISTANT_SYSTEM_PROMPT",
    )
    max_context_messages: int = Field(default=30, alias="MAX_CONTEXT_MESSAGES")
    min_question_length: int = Field(default=12, alias="MIN_QUESTION_LENGTH")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8080, alias="API_PORT")
    zoom_webhook_secret: str = Field(default="", alias="ZOOM_WEBHOOK_SECRET")
    verify_zoom_signatures: bool = Field(default=True, alias="VERIFY_ZOOM_SIGNATURES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
