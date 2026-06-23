"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = .../conversational-ai-assistant
# config.py is at <root>/backend/app/config.py → parents[2] is <root>.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Knowledge base
    knowledge_base_dir: str = str(PROJECT_ROOT / "knowledge_base")

    # Storage
    database_path: str = str(PROJECT_ROOT / "backend" / "data" / "analytics.db")

    # Retrieval
    top_k: int = 4

    # --- Embeddings (Vertex AI / Gemini) ---
    # Retrieval uses vector embeddings when available; otherwise it falls back to
    # the built-in TF-IDF keyword search.
    embeddings_enabled: bool = True
    embedding_model: str = "text-embedding-004"

    # Backend selection for embeddings AND generation:
    #   use_vertex=True  -> Vertex AI (uses ADC / service account + project/location)
    #   use_vertex=False -> Gemini Developer API (uses GEMINI_API_KEY)
    use_vertex: bool = False
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"

    # Where to cache computed KB embeddings (avoids re-embedding on every boot).
    embeddings_cache_path: str = str(
        PROJECT_ROOT / "backend" / "data" / "kb_embeddings.json"
    )

    # --- Dialogflow CX (the User → CX → Webhook path) ---
    # Set these to route the demo through a real CX agent via /cx/detect-intent.
    dialogflow_project: str = ""
    dialogflow_location: str = "global"
    dialogflow_agent_id: str = ""
    dialogflow_language: str = "en"

    # Confidence below this is treated as "low" (suggest human handoff).
    confidence_threshold: float = 0.35

    # Webhook security (optional shared secret header from Dialogflow CX)
    webhook_secret: str = ""

    # CORS
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
