from __future__ import annotations

from uuid import UUID

from app.core.ota_shopping import build_ota_booking_options
from app.models.domain import (
    LoyaltyAccount,
    Offer,
    OptimizationRequest,
    Program,
    TripIntent,
)

USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_hotel_prompt_generates_amex_travel_hotel_options_with_credit() -> None:
    request = OptimizationRequest(
        intent=TripIntent(
            user_id=USER_ID,
            raw_intent="Find a 4 star or higher hotel in NYC within 20 minutes",
            destination="NYC",
            budget_usd=2000,
            preferred_programs=[Program.amex_mr],
        ),
        accounts=[
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.amex_mr,
                display_name="Amex Membership Rewards",
                points_balance=6363,
            )
        ],
        offers=[
            Offer(
                user_id=USER_ID,
                program=Program.amex_mr,
                merchant="American Express Travel",
                description="Platinum Hotel Credit",
                value_usd=300,
            )
        ],
    )

    options = build_ota_booking_options(request)

    beekman = next(option for option in options if "The Beekman" in option.label and "cash" in option.label)
    assert beekman.cash_price_usd == 1507.22
    assert beekman.offer_value_usd == 300
    assert "Applies eligible Amex Travel hotel credit." in beekman.notes
    assert not any(option.points_program == Program.amex_mr for option in options)


def test_flight_prompt_generates_united_award_when_balance_is_sufficient() -> None:
    request = OptimizationRequest(
        intent=TripIntent(
            user_id=USER_ID,
            raw_intent="Direct flight to NYC",
            destination="NYC",
            budget_usd=1000,
            preferred_programs=[Program.united],
        ),
        accounts=[
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.united,
                display_name="United MileagePlus",
                points_balance=20826,
            )
        ],
    )

    labels = {option.label for option in build_ota_booking_options(request)}

    assert "United nonstop cash fare to NYC" in labels
    assert "United MileagePlus saver-style award to NYC" in labels
