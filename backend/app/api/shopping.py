from __future__ import annotations

from fastapi import APIRouter

from app.core.optimizer import optimize_trip
from app.core.ota_shopping import build_ota_booking_options
from app.models.domain import OptimizationRequest, OptimizationResponse

router = APIRouter(prefix="/shopping", tags=["shopping"])


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_shopping_intent(request: OptimizationRequest) -> OptimizationResponse:
    shopping_options = build_ota_booking_options(request)
    return optimize_trip(request.model_copy(update={"booking_options": shopping_options}))
