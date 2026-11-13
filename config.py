"""
FILE PURPOSE: Central Runtime Configuration

This file loads every tunable setting for the Production AI Platform from
environment variables (prefix PLATFORM_) or a local .env file.

Paths are resolved from the project root rather than the current working
directory, so the API, the ingestion job, and the tests all point at the same
data regardless of where they are launched from.

Override any value with an environment variable, for example:

    PLATFORM_TOP_K=6
    PLATFORM_API_KEY=change-me
"""

# Import Path for project-relative file locations.
from pathlib import Path

# Import field_validator and SecretStr; SecretStr keeps the API key out of logs and reprs.
from pydantic import SecretStr, field_validator

# Import the settings base class that reads environment variables.
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the project root from this file's location.
PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Typed runtime settings shared by the API, workflow, RAG, and tests."""

    model_config = SettingsConfigDict(
        env_prefix="PLATFORM_",
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
    )

    # Application version reported by the root endpoint and OpenAPI document.
    app_version: str = "0.2.0"

    # Log level for the application and workflow logs.
    log_level: str = "INFO"

    # Shared API key. When unset, POST /run is open; set it in any shared environment.
    api_key: SecretStr | None = None

    # Directory containing the .txt enterprise documents to index.
    docs_dir: Path = PROJECT_ROOT / "data" / "docs"

    # Directory where ChromaDB persists the vector index.
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma_db"

    # Directory where approved Markdown reports are written.
    output_dir: Path = PROJECT_ROOT / "data" / "outputs"

    # ChromaDB collection name for enterprise knowledge chunks.
    collection_name: str = "enterprise_knowledge"

    # Sentence-transformers model used for both ingestion and retrieval.
    embedding_model: str = "all-MiniLM-L6-v2"

    # Number of texts encoded per embedding call.
    embedding_batch_size: int = 64

    # Maximum words per document chunk.
    chunk_words: int = 500

    # Default number of chunks returned by retrieval.
    top_k: int = 4

    # Maximum Writer -> Reviewer cycles before the workflow stops without saving.
    max_review_attempts: int = 2

    # Maximum accepted length of a question submitted to POST /run.
    question_max_length: int = 2000

    # Load the embedding model during API startup so the first request is not slow.
    warmup_model: bool = True

    @field_validator("api_key", mode="before")
    @classmethod
    def _blank_key_means_unset(cls, value):
        """Treat an empty PLATFORM_API_KEY as unset so copied .env files do not lock out clients."""

        # Map empty or whitespace-only values to None so authentication stays disabled.
        if isinstance(value, str) and not value.strip():
            return None
        return value


# Create the single settings object imported by the rest of the platform.
settings = Settings()
