"""Knowledge base search + management endpoints."""
from fastapi import APIRouter

from ..knowledge_base import get_kb
from ..models import KnowledgeSearchRequest

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/search")
def search(req: KnowledgeSearchRequest):
    kb = get_kb()
    results = kb.search(req.query, req.top_k)
    return {"query": req.query, "method": kb.retrieval_method, "results": results}


@router.get("/documents")
def list_documents():
    kb = get_kb()
    docs: dict[str, int] = {}
    for chunk in kb.chunks:
        docs[chunk.doc] = docs.get(chunk.doc, 0) + 1
    return {
        "documents": [{"name": k, "sections": v} for k, v in sorted(docs.items())],
        "total_sections": len(kb.chunks),
    }


@router.post("/reload")
def reload_kb():
    kb = get_kb()
    kb.load()
    return {"status": "reloaded", "sections": len(kb.chunks)}
