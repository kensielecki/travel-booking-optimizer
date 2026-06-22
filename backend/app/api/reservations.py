from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.browser_car_rental_search import (
    browser_car_rental_readiness,
    search_car_rentals_with_browser,
)
from app.core.reservation_agent import (
    approve_reservation,
    execute_reservation_dry_run,
    get_reservation_state,
    plan_reservation,
    queue_reservation,
)
from app.models.domain import (
    AgentRun,
    CarRentalBrowserSearchRequest,
    ReservationApprovalRequest,
    ReservationPlan,
    ReservationPlanRequest,
    ReservationQueueItem,
    ReservationQueueRequest,
    ReservationStateResponse,
    UserApproval,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("/plan", response_model=ReservationPlan)
async def create_reservation_plan(payload: ReservationPlanRequest) -> ReservationPlan:
    return plan_reservation(payload)


@router.get("/car-rentals/browser-readiness")
async def read_car_rental_browser_readiness() -> dict:
    return browser_car_rental_readiness()


@router.post("/car-rentals/browser-search", response_model=ReservationPlan)
async def create_car_rental_browser_search(payload: CarRentalBrowserSearchRequest) -> ReservationPlan:
    return search_car_rentals_with_browser(payload)


@router.post("/queue", response_model=ReservationQueueItem)
async def create_reservation_queue_item(payload: ReservationQueueRequest) -> ReservationQueueItem:
    try:
        return queue_reservation(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{user_id}/queue/{queue_item_id}/approve", response_model=UserApproval)
async def approve_reservation_queue_item(
    user_id: UUID,
    queue_item_id: UUID,
    payload: ReservationApprovalRequest,
) -> UserApproval:
    try:
        return approve_reservation(user_id, queue_item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/queue/{queue_item_id}/execute-dry-run", response_model=AgentRun)
async def execute_reservation_queue_item_dry_run(user_id: UUID, queue_item_id: UUID) -> AgentRun:
    try:
        return execute_reservation_dry_run(user_id, queue_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{user_id}/state", response_model=ReservationStateResponse)
async def read_reservation_state(user_id: UUID) -> ReservationStateResponse:
    return get_reservation_state(user_id)
