"""Gemini integration: grounded answer generation, intent detection, sentiment.

Uses the google-genai SDK with Gemini 2.5 Flash. If no API key is configured the
module degrades gracefully to a deterministic fallback so the app still runs in
demos and CI without credentials.
"""
from __future__ import annotations

import json

from .config import get_settings

try:
    from google import genai
    from google.genai import types
    _SDK_AVAILABLE = True
except Exception:  # pragma: no cover - SDK optional at import time
    genai = None
    types = None
    _SDK_AVAILABLE = False


GROUNDED_SYSTEM_PROMPT = """You are the Acme enterprise customer support assistant.
Answer the user's question using ONLY the information in the provided CONTEXT.
Rules:
- Be concise, friendly, and professional.
- If the answer is not contained in the context, reply exactly:
  "I couldn't find information about that in our knowledge base. Would you like me to connect you with a human agent?"
- Never invent prices, policies, dates, or facts.
- When relevant, mention the policy or section your answer is based on."""

INTENT_LABELS = [
    "order_status",
    "refund_policy",
    "pricing",
    "product_information",
    "human_agent",
    "general_question",
]


class GeminiClient:
    def __init__(self):
        self.settings = get_settings()
        self.model = self.settings.gemini_model
        self._client = None
        if not _SDK_AVAILABLE:
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

    # ---- Grounded answer ------------------------------------------------
    def generate_answer(self, question: str, context_chunks: list[dict]) -> str:
        context = "\n\n".join(
            f"[{c['doc']} :: {c['title']}]\n{c['text']}" for c in context_chunks
        )
        if not self.enabled:
            return self._fallback_answer(question, context_chunks)

        prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"
        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=GROUNDED_SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=512,
            ),
        )
        return (resp.text or "").strip()

    # ---- Intent detection (fallback / augmentation to Dialogflow) -------
    def detect_intent(self, text: str) -> str:
        if not self.enabled:
            return self._keyword_intent(text)
        prompt = (
            "Classify the user's support message into exactly one intent.\n"
            f"Intents: {', '.join(INTENT_LABELS)}.\n"
            'Respond with JSON: {"intent": "<one_label>"}.\n\n'
            f"Message: {text}"
        )
        try:
            resp = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(resp.text)
            intent = data.get("intent", "general_question")
            return intent if intent in INTENT_LABELS else "general_question"
        except Exception:
            return self._keyword_intent(text)

    # ---- Sentiment ------------------------------------------------------
    def detect_sentiment(self, text: str) -> str:
        if not self.enabled:
            return self._keyword_sentiment(text)
        prompt = (
            "Classify the sentiment of this customer message as one of: "
            'positive, neutral, negative. Respond JSON {"sentiment": "<label>"}.\n\n'
            f"Message: {text}"
        )
        try:
            resp = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0, response_mime_type="application/json"
                ),
            )
            return json.loads(resp.text).get("sentiment", "neutral")
        except Exception:
            return self._keyword_sentiment(text)

    # ---- Fallbacks (no API key) ----------------------------------------
    @staticmethod
    def _fallback_answer(question: str, chunks: list[dict]) -> str:
        if not chunks:
            return (
                "I couldn't find information about that in our knowledge base. "
                "Would you like me to connect you with a human agent?"
            )
        top = chunks[0]
        return (
            f"Based on our **{top['title']}** documentation:\n\n{top['text']}\n\n"
            "_(Demo fallback response — set GEMINI_API_KEY for AI-generated answers.)_"
        )

    @staticmethod
    def _keyword_intent(text: str) -> str:
        t = text.lower()
        if any(w in t for w in ("agent", "human", "representative", "speak to")):
            return "human_agent"
        if any(w in t for w in ("refund", "return", "money back")):
            return "refund_policy"
        if any(w in t for w in ("price", "pricing", "cost", "plan", "subscription")):
            return "pricing"
        if any(w in t for w in ("order", "track", "shipped", "delivery", "where is")):
            return "order_status"
        if any(w in t for w in ("product", "feature", "sku", "what is acme")):
            return "product_information"
        return "general_question"

    @staticmethod
    def _keyword_sentiment(text: str) -> str:
        t = text.lower()
        neg = ("angry", "terrible", "worst", "broken", "late", "never",
               "disappointed", "frustrated", "useless", "horrible", "complaint")
        pos = ("thanks", "great", "love", "awesome", "perfect", "happy", "good")
        if any(w in t for w in neg):
            return "negative"
        if any(w in t for w in pos):
            return "positive"
        return "neutral"


_client: GeminiClient | None = None


def get_gemini() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
