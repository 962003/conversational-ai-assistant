"""Dialogflow CX client — sends user text to a *real* CX agent.

This is what makes the demo the full Conversational AI path:

    User → Dialogflow CX (detect_intent) → [CX calls our webhook] → answer

CX performs NLU (intent + entities) and, via its fulfillment webhook, calls our
FastAPI `/dialogflow/webhook`, which runs KB retrieval + Gemini grounding. The
grounded answer, sources, and confidence come back inside the CX response.

Configure via env: DIALOGFLOW_PROJECT, DIALOGFLOW_LOCATION, DIALOGFLOW_AGENT_ID.
Auth uses Application Default Credentials (gcloud auth application-default login,
or a service account). If unconfigured, `enabled` is False.
"""
from __future__ import annotations

from .config import get_settings

try:
    from google.cloud import dialogflowcx_v3 as cx
    from google.api_core.client_options import ClientOptions
    _SDK_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    cx = None
    ClientOptions = None
    _SDK_AVAILABLE = False


class CXClient:
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        s = self.settings
        self._configured = bool(
            s.dialogflow_project and s.dialogflow_agent_id and _SDK_AVAILABLE
        )

    @property
    def enabled(self) -> bool:
        return self._configured

    def _get_client(self):
        if self._client is not None:
            return self._client
        # Regional agents need a region-specific endpoint; "global" uses default.
        location = self.settings.dialogflow_location
        client_options = None
        if location and location != "global":
            client_options = ClientOptions(
                api_endpoint=f"{location}-dialogflow.googleapis.com"
            )
        self._client = cx.SessionsClient(client_options=client_options)
        return self._client

    def detect_intent(self, text: str, session_id: str) -> dict:
        if not self.enabled:
            raise RuntimeError("Dialogflow CX is not configured")

        s = self.settings
        client = self._get_client()
        session_path = client.session_path(
            s.dialogflow_project, s.dialogflow_location, s.dialogflow_agent_id, session_id
        )
        query_input = cx.QueryInput(
            text=cx.TextInput(text=text),
            language_code=s.dialogflow_language,
        )
        response = client.detect_intent(
            request=cx.DetectIntentRequest(session=session_path, query_input=query_input)
        )
        qr = response.query_result

        # Concatenate text responses from fulfillment.
        texts: list[str] = []
        for msg in qr.response_messages:
            if msg.text and msg.text.text:
                texts.extend(msg.text.text)

        params = dict(qr.parameters) if qr.parameters else {}
        return {
            "response": " ".join(texts).strip() or "(no response from agent)",
            "intent": qr.intent.display_name if qr.intent else None,
            "intent_confidence": round(float(qr.intent_detection_confidence), 3),
            "confidence": params.get("confidence"),
            "confidence_label": params.get("confidence_label"),
            "kb_hit": params.get("kb_hit"),
            "sentiment": params.get("sentiment"),
            "sources": params.get("sources"),
            "session_id": session_id,
            "via": "dialogflow-cx",
        }


_client: CXClient | None = None


def get_cx_client() -> CXClient:
    global _client
    if _client is None:
        _client = CXClient()
    return _client
