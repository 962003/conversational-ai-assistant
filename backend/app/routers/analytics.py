"""Analytics dashboard endpoint."""
from fastapi import APIRouter

from ..analytics import get_analytics

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def analytics():
    return get_analytics()
