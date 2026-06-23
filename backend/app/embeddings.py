"""Vertex AI / Gemini text embeddings.

Wraps the google-genai SDK, which can target either backend with the same code:
  * Vertex AI            -> Client(vertexai=True, project=..., location=...)  (ADC auth)
  * Gemini Developer API -> Client(api_key=GEMINI_API_KEY)

Used by the knowledge base for vector retrieval. If no credentials are configured
(or the SDK is unavailable), `enabled` is False and the knowledge base transparently
falls back to TF-IDF keyword search.
"""
from __future__ import annotations

from .config import get_settings

try:
    from google import genai
    from google.genai import types
    _SDK_AVAILABLE = True
except Exception:  # pragma: no cover - SDK optional at import time
    genai = None
    types = None
    _SDK_AVAILABLE = False

# Task types tell the model how an input will be used, which improves retrieval
# quality (asymmetric document vs. query embeddings).
TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
TASK_QUERY = "RETRIEVAL_QUERY"

_MAX_BATCH = 100


class EmbeddingClient:
    def __init__(self):
        self.settings = get_settings()
        self.model = self.settings.embedding_model
        self._client = None

        if not (_SDK_AVAILABLE and self.settings.embeddings_enabled):
            return

        try:
            if self.settings.use_vertex and self.settings.google_cloud_project:
                self._client = genai.Client(
                    vertexai=True,
                    project=self.settings.google_cloud_project,
                    location=self.settings.google_cloud_location,
                )
            elif self.settings.gemini_api_key:
                self._client = genai.Client(api_key=self.settings.gemini_api_key)
        except Exception:
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def backend(self) -> str:
        if not self.enabled:
            return "disabled"
        return "vertex-ai" if self.settings.use_vertex else "gemini-api"

    def embed(self, texts: list[str], task_type: str = TASK_DOCUMENT) -> list[list[float]]:
        """Embed a list of texts, batching to respect API limits."""
        if not self.enabled:
            raise RuntimeError("Embedding client is not enabled")

        vectors: list[list[float]] = []
        for start in range(0, len(texts), _MAX_BATCH):
            batch = texts[start:start + _MAX_BATCH]
            resp = self._client.models.embed_content(
                model=self.model,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            for emb in resp.embeddings:
                vectors.append(list(emb.values))
        return vectors

    def embed_one(self, text: str, task_type: str = TASK_QUERY) -> list[float]:
        return self.embed([text], task_type=task_type)[0]


_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    global _client
    if _client is None:
        _client = EmbeddingClient()
    return _client
