from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.ingestion.manual import (
    clear_ingestion_state,
    correct_account_balance,
    get_ingestion_state,
    ingest_manual_payload,
)
from app.models.domain import (
    BalanceCorrectionRequest,
    IngestionStateResponse,
    ManualIngestionRequest,
    ManualIngestionResponse,
    Program,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/manual", response_model=ManualIngestionResponse)
async def manual_ingestion(payload: ManualIngestionRequest) -> ManualIngestionResponse:
    return ingest_manual_payload(payload)


@router.get("/state/{user_id}", response_model=IngestionStateResponse)
async def ingestion_state(user_id: UUID) -> IngestionStateResponse:
    return get_ingestion_state(user_id)


@router.delete("/state/{user_id}", response_model=IngestionStateResponse)
async def clear_state(user_id: UUID) -> IngestionStateResponse:
    return clear_ingestion_state(user_id)


@router.patch("/state/{user_id}/accounts/{program}", response_model=IngestionStateResponse)
async def correct_balance(
    user_id: UUID,
    program: Program,
    correction: BalanceCorrectionRequest,
) -> IngestionStateResponse:
    return correct_account_balance(user_id, program, correction)
