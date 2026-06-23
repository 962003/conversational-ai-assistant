"""Vector retrieval tests using an injected fake embedding client (no network)."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.knowledge_base import KnowledgeBase, _tokenize  # noqa: E402


class FakeEmbedClient:
    """Deterministic bag-of-words 'embeddings' over distinctive (non-stopword)
    tokens. Crude vs. a real model, but enough to verify the vector pipeline and
    that cosine ranking surfaces the chunk a query overlaps with."""
    enabled = True
    model = "fake-embed-001"
    backend = "fake"
    DIM = 1024

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.DIM
        for tok in _tokenize(text):
            idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.DIM
            v[idx] += 1.0
        return v

    def embed(self, texts, task_type="RETRIEVAL_DOCUMENT"):
        return [self._vec(t) for t in texts]

    def embed_one(self, text, task_type="RETRIEVAL_QUERY"):
        return self._vec(text)


def test_vector_search_is_used_and_ranks_correctly():
    kb = KnowledgeBase(embed_client=FakeEmbedClient())
    assert kb.use_vectors is True
    assert kb.retrieval_method == "vector"

    # A line that appears verbatim in refund_policy.md.
    results = kb.search("Refunds are issued to the original payment method")
    assert results, "expected vector results"
    assert results[0]["method"] == "vector"
    assert results[0]["doc"] == "refund_policy.md"


def test_pricing_query_vector():
    kb = KnowledgeBase(embed_client=FakeEmbedClient())
    # Distinctive phrasing from pricing.md.
    results = kb.search("Annual billing saves roughly two months compared to monthly")
    assert results[0]["doc"] == "pricing.md"


def test_falls_back_to_keyword_when_embeddings_disabled():
    class Disabled:
        enabled = False
        model = "none"
        backend = "disabled"

    kb = KnowledgeBase(embed_client=Disabled())
    assert kb.use_vectors is False
    assert kb.retrieval_method == "keyword"
    results = kb.search("refund policy")
    assert results[0]["method"] == "keyword"
    assert results[0]["doc"] == "refund_policy.md"
