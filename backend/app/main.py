"""FastAPI application entry point for the Enterprise Customer Support AI backend."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .cx_client import get_cx_client
from .database import init_db
from .embeddings import get_embedding_client
from .gemini_client import get_gemini
from .knowledge_base import get_kb
from .routers import analytics, chat, cx, knowledge, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_kb()        # warm the knowledge base
    yield


app = FastAPI(
    title="Enterprise Customer Support AI",
    description=(
        "Dialogflow CX + Gemini + Webhook + Knowledge Base + Analytics. "
        "A mini Google Contact Center AI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(webhook.router)
app.include_router(cx.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {
        "service": "Enterprise Customer Support AI",
        "status": "ok",
        "docs": "/docs",
        "endpoints": [
            "POST /chat",
            "POST /cx/detect-intent",
            "GET /cx/status",
            "POST /dialogflow/webhook",
            "POST /knowledge/search",
            "GET /analytics",
            "POST /ticket",
        ],
    }


@app.get("/health")
def health():
    kb = get_kb()
    embed = get_embedding_client()
    return {
        "status": "healthy",
        "gemini_enabled": get_gemini().enabled,
        "kb_sections": len(kb.chunks),
        "model": settings.gemini_model,
        "retrieval_method": kb.retrieval_method,
        "embeddings_backend": embed.backend,
        "embedding_model": settings.embedding_model if embed.enabled else None,
        "dialogflow_cx_enabled": get_cx_client().enabled,
    }
