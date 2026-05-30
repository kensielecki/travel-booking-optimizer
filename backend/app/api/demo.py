from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter

from app.core.optimizer import optimize_trip
from app.ingestion.manual import get_ingestion_state
from app.models.domain import (
    LoyaltyAccount,
    Offer,
    OptimizationRequest,
    OptimizationResponse,
    Program,
    RankingMode,
    TransferBonus,
    TripIntent,
)

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_USER_ID = UUID("11111111-1111-4111-8111-111111111111")


@router.get("/nyc-weekend", response_model=OptimizationResponse)
async def nyc_weekend_demo() -> OptimizationResponse:
    state = get_ingestion_state(DEMO_USER_ID)
    accounts = state.accounts or _seed_accounts()
    offers = state.offers or _seed_offers()

    request = OptimizationRequest(
        intent=TripIntent(
            user_id=DEMO_USER_ID,
            raw_intent="Weekend trip to NYC using United + Hilton with a ~$2,000 equivalent budget.",
            destination="NYC",
            budget_usd=2000,
            preferred_programs=[Program.united, Program.hilton],
            ranking_mode=RankingMode.balanced,
        ),
        accounts=accounts,
        offers=offers,
        transfer_bonuses=[
            TransferBonus(
                from_program=Program.amex_mr,
                to_program=Program.united,
                bonus_pct=20,
                valid_through=date(2026, 6, 15),
            )
        ],
    )
    return optimize_trip(request)


def _seed_accounts() -> list[LoyaltyAccount]:
    return [
        LoyaltyAccount(
            user_id=DEMO_USER_ID,
            program=Program.united,
            display_name="United MileagePlus",
            points_balance=82000,
        ),
        LoyaltyAccount(
            user_id=DEMO_USER_ID,
            program=Program.hilton,
            display_name="Hilton Honors",
            points_balance=180000,
        ),
        LoyaltyAccount(
            user_id=DEMO_USER_ID,
            program=Program.amex_mr,
            display_name="Amex Membership Rewards",
            points_balance=110000,
        ),
    ]


def _seed_offers() -> list[Offer]:
    return [
        Offer(
            user_id=DEMO_USER_ID,
            program=Program.amex_mr,
            merchant="Hilton",
            description="Spend $500 or more, get $100 back.",
            value_usd=100,
            min_spend_usd=500,
            expires_on=date(2026, 6, 30),
        )
    ]
