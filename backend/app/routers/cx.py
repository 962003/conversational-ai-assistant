"""Route a user message through a real Dialogflow CX agent.

This is the production conversational path. If CX isn't configured, the endpoint
responds with `cx_enabled: false` so the frontend can fall back to /chat and show
the user a clear hint instead of an error.
"""
from fastapi import APIRouter

from ..cx_client import get_cx_client
from ..models import ChatRequest

router = APIRouter(prefix="/cx", tags=["dialogflow-cx"])


@router.get("/status")
def cx_status():
    client = get_cx_client()
    s = client.settings
    return {
        "cx_enabled": client.enabled,
        "project": s.dialogflow_project or None,
        "location": s.dialogflow_location,
        "agent_id": s.dialogflow_agent_id or None,
        "language": s.dialogflow_language,
    }


@router.post("/detect-intent")
def detect_intent(req: ChatRequest):
    client = get_cx_client()
    if not client.enabled:
        return {
            "cx_enabled": False,
            "message": (
                "Dialogflow CX is not configured. Set DIALOGFLOW_PROJECT, "
                "DIALOGFLOW_LOCATION and DIALOGFLOW_AGENT_ID, then provision the "
                "agent with dialogflow/provision_agent.py. Falling back to /chat."
            ),
        }
    try:
        result = client.detect_intent(req.message, req.session_id)
        return {"cx_enabled": True, **result}
    except Exception as e:  # surfacing the CX/auth error helps debugging
        return {"cx_enabled": True, "error": str(e)}
