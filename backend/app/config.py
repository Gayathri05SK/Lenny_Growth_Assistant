from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite:///./local.db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    default_llm_provider: str = Field(
        default="groq",
        validation_alias=AliasChoices("DEFAULT_LLM_PROVIDER", "default_llm_provider"),
    )

    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key"),
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        validation_alias=AliasChoices("ANTHROPIC_MODEL", "anthropic_model"),
    )

    groq_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GROQ_API_KEY", "groq_api_key"),
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias=AliasChoices("GROQ_MODEL", "groq_model"),
    )

    ollama_host: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_HOST", "ollama_host"),
    )
    ollama_model: str = Field(
        default="qwen2:0.5b",
        validation_alias=AliasChoices("OLLAMA_MODEL", "ollama_model"),
    )

    # Qdrant: leave qdrant_url empty to use a local on-disk Qdrant (no server needed).
    # Set qdrant_url (+ qdrant_api_key) to point at Qdrant Cloud or a docker instance instead.
    qdrant_url: str = Field(
        default="",
        validation_alias=AliasChoices("QDRANT_URL", "qdrant_url"),
    )
    qdrant_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("QDRANT_API_KEY", "qdrant_api_key"),
    )
    qdrant_local_path: str = Field(
        default="./qdrant_data",
        validation_alias=AliasChoices("QDRANT_LOCAL_PATH", "qdrant_local_path"),
    )
    qdrant_collection: str = Field(
        default="lennys_transcripts",
        validation_alias=AliasChoices("QDRANT_COLLECTION", "qdrant_collection"),
    )


settings = Settings()
