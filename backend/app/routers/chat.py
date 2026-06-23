"""Direct chat endpoint used by the web frontend (bypasses Dialogflow for demos)."""
from fastapi import APIRouter

from ..models import ChatRequest, ChatResponse, FeedbackRequest, TicketRequest
from .. import database, service

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    result = service.handle_turn(req.message, req.session_id)
    return ChatResponse(**result)


@router.post("/ticket")
def create_ticket(req: TicketRequest):
    ticket_id = database.create_ticket(req.session_id, req.name, req.email, req.issue)
    return {
        "ticket_id": ticket_id,
        "status": "open",
        "message": (
            f"Thanks {req.name}! Ticket #{ticket_id} has been created. "
            "A human agent will email you at "
            f"{req.email} shortly."
        ),
    }


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """Thumbs up/down on an answer → drives the CSAT metric."""
    fid = database.log_feedback(req.session_id, req.rating, req.comment)
    return {"feedback_id": fid, "recorded": True}


@router.get("/tickets")
def list_tickets(limit: int = 50):
    """The human-handoff (Bot → Agent) queue."""
    tickets = database.list_tickets(limit)
    return {
        "total": len(tickets),
        "open": sum(1 for t in tickets if t["status"] == "open"),
        "tickets": tickets,
    }
