from __future__ import annotations

from fastapi import APIRouter

from app.core.optimizer import optimize_trip
from app.models.domain import OptimizationRequest, OptimizationResponse

router = APIRouter(prefix="/trip-intents", tags=["trip intents"])


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_intent(request: OptimizationRequest) -> OptimizationResponse:
    return optimize_trip(request)
