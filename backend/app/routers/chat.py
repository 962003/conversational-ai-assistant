"""Direct chat endpoint used by the web frontend (bypasses Dialogflow for demos)."""
from fastapi import APIRouter

from ..models import ChatRequest, ChatResponse, TicketRequest
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
