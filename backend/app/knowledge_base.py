"""Knowledge base loading and retrieval.

The KB is a folder of Markdown files. Each file is split into sections by heading
so retrieval returns focused passages. Two retrieval backends:

  * **vector** (default when embeddings are configured) — Vertex AI / Gemini
    embeddings + cosine similarity. Document and query embeddings use asymmetric
    task types for better recall.
  * **keyword** (fallback) — dependency-free TF-IDF, so the app still works with
    no credentials.

Chunk embeddings are cached to disk keyed by a content+model signature, so we only
call the embedding API when the KB or model actually changes.
"""
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import get_settings
from .embeddings import TASK_DOCUMENT, TASK_QUERY, EmbeddingClient, get_embedding_client

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "do", "i", "my", "you", "your", "how", "what", "can", "with", "at", "it",
    "this", "that", "be", "as", "by", "we", "us", "our", "me",
}


@dataclass
class Chunk:
    doc: str          # source file name (e.g. refund_policy.md)
    title: str        # heading of the section
    text: str         # section body
    tokens: list[str] # cached tokenization (for TF-IDF fallback)

    @property
    def embed_input(self) -> str:
        return f"{self.title}\n{self.text}"


def _tokenize(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-z0-9]+", text.lower())
        if t not in _STOPWORDS and len(t) > 1
    ]


class KnowledgeBase:
    def __init__(self, directory: str | None = None, embed_client: EmbeddingClient | None = None):
        settings = get_settings()
        self.directory = Path(directory or settings.knowledge_base_dir)
        self.chunks: list[Chunk] = []
        self._df: dict[str, int] = {}

        # When a client is injected (tests), skip the on-disk cache for isolation.
        self._injected = embed_client is not None
        self._embed_client = embed_client or get_embedding_client()

        self._matrix: np.ndarray | None = None   # (n_chunks, dim), L2-normalized
        self.use_vectors = False
        self.retrieval_method = "keyword"

        self.load()

    # ------------------------------------------------------------------ load
    def load(self) -> None:
        self.chunks = []
        for md in sorted(self.directory.glob("*.md")):
            self._add_document(md.name, md.read_text(encoding="utf-8"))
        self._build_idf()
        self._build_vectors()

    def _add_document(self, name: str, content: str) -> None:
        parts = re.split(r"^(#{1,6}\s+.*)$", content, flags=re.MULTILINE)
        current_title = name.replace(".md", "").replace("_", " ").title()
        buffer: list[str] = []

        def flush():
            body = "\n".join(buffer).strip()
            if body:
                self.chunks.append(
                    Chunk(name, current_title, body, _tokenize(current_title + " " + body))
                )

        for part in parts:
            if re.match(r"^#{1,6}\s+", part or ""):
                flush()
                buffer = []
                current_title = re.sub(r"^#{1,6}\s+", "", part).strip()
            elif part:
                buffer.append(part)
        flush()

    # ----------------------------------------------------------- TF-IDF (fb)
    def _build_idf(self) -> None:
        self._df = {}
        for chunk in self.chunks:
            for term in set(chunk.tokens):
                self._df[term] = self._df.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        n = len(self.chunks) or 1
        return math.log((1 + n) / (1 + self._df.get(term, 0))) + 1

    # ----------------------------------------------------------- vector path
    def _signature(self) -> str:
        h = hashlib.sha256()
        h.update(self._embed_client.model.encode())
        for chunk in self.chunks:
            h.update(chunk.embed_input.encode("utf-8"))
        return h.hexdigest()

    def _load_cache(self, signature: str) -> np.ndarray | None:
        if self._injected:
            return None
        path = Path(get_settings().embeddings_cache_path)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if data.get("signature") != signature:
                return None
            return np.array(data["vectors"], dtype=np.float32)
        except Exception:
            return None

    def _save_cache(self, signature: str, matrix: np.ndarray) -> None:
        if self._injected:
            return
        path = Path(get_settings().embeddings_cache_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps({
                "model": self._embed_client.model,
                "signature": signature,
                "vectors": matrix.tolist(),
            }))
        except Exception:
            pass

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def _build_vectors(self) -> None:
        self._matrix = None
        self.use_vectors = False
        self.retrieval_method = "keyword"

        if not self.chunks or not self._embed_client.enabled:
            return

        signature = self._signature()
        matrix = self._load_cache(signature)
        try:
            if matrix is None:
                vectors = self._embed_client.embed(
                    [c.embed_input for c in self.chunks], task_type=TASK_DOCUMENT
                )
                matrix = np.array(vectors, dtype=np.float32)
                self._save_cache(signature, matrix)
            self._matrix = self._normalize(matrix)
            self.use_vectors = True
            self.retrieval_method = "vector"
        except Exception:
            # Any failure (auth, quota, network) -> stay on TF-IDF.
            self._matrix = None
            self.use_vectors = False
            self.retrieval_method = "keyword"

    # --------------------------------------------------------------- search
    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        top_k = top_k or get_settings().top_k
        if self.use_vectors:
            results = self._vector_search(query, top_k)
            if results is not None:
                return results
        return self._keyword_search(query, top_k)

    def _vector_search(self, query: str, top_k: int) -> list[dict] | None:
        try:
            q = np.array(
                self._embed_client.embed_one(query, task_type=TASK_QUERY),
                dtype=np.float32,
            )
            norm = np.linalg.norm(q) or 1.0
            q = q / norm
            sims = self._matrix @ q  # cosine similarity (both normalized)
            order = np.argsort(-sims)[:top_k]
            return [
                {
                    "doc": self.chunks[i].doc,
                    "title": self.chunks[i].title,
                    "text": self.chunks[i].text,
                    "score": round(float(sims[i]), 4),
                    "method": "vector",
                }
                for i in order
                if sims[i] > 0
            ]
        except Exception:
            return None  # signal fallback for this query

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scored: list[tuple[float, Chunk]] = []
        for chunk in self.chunks:
            tf: dict[str, int] = {}
            for t in chunk.tokens:
                tf[t] = tf.get(t, 0) + 1
            score = sum(tf.get(t, 0) * self._idf(t) for t in q_tokens)
            if score > 0:
                score /= math.sqrt(len(chunk.tokens) or 1)
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "doc": c.doc,
                "title": c.title,
                "text": c.text,
                "score": round(s, 4),
                "method": "keyword",
            }
            for s, c in scored[:top_k]
        ]


# Singleton used across the app
_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
