from __future__ import annotations

from uuid import UUID

from app.core.optimizer import calculate_cents_per_point, optimize_trip
from app.models.domain import (
    BookingOption,
    BookingType,
    LoyaltyAccount,
    OptimizationRequest,
    Program,
    RankingMode,
    TripIntent,
)

USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_cents_per_point_formula_includes_taxes_fees_copay_and_offer_value() -> None:
    option = BookingOption(
        label="Award",
        booking_type=BookingType.points,
        merchant="United",
        cash_price_usd=1000,
        taxes_usd=11.2,
        fees_usd=20,
        copay_usd=100,
        offer_value_usd=50,
        points_program=Program.united,
        points_used=50000,
    )

    assert calculate_cents_per_point(option) == 1.838


def test_optimizer_ranks_lowest_out_of_pocket_when_requested() -> None:
    request = OptimizationRequest(
        intent=TripIntent(
            user_id=USER_ID,
            raw_intent="Weekend NYC",
            budget_usd=1000,
            ranking_mode=RankingMode.lowest_out_of_pocket,
        ),
        booking_options=[
            BookingOption(
                label="Cash",
                booking_type=BookingType.cash,
                merchant="United",
                cash_price_usd=900,
                simplicity=5,
            ),
            BookingOption(
                label="Award",
                booking_type=BookingType.points,
                merchant="United",
                cash_price_usd=900,
                taxes_usd=11.2,
                points_program=Program.united,
                points_used=45000,
                simplicity=3,
            ),
        ],
    )

    response = optimize_trip(request)

    assert response.recommendations[0].option.label == "Award"
    assert response.recommendations[0].out_of_pocket_usd == 11.2
    assert response.recommendations[0].cents_per_point == 1.975


def test_offer_enhanced_cash_booking_pays_cash_minus_offer() -> None:
    request = OptimizationRequest(
        intent=TripIntent(
            user_id=USER_ID,
            raw_intent="Hotel booking with card offer",
            budget_usd=1000,
        ),
        booking_options=[
            BookingOption(
                label="Offer cash",
                booking_type=BookingType.offer_enhanced,
                merchant="Hilton",
                cash_price_usd=900,
                offer_value_usd=100,
                simplicity=5,
            )
        ],
    )

    recommendation = optimize_trip(request).recommendations[0]

    assert recommendation.out_of_pocket_usd == 800
    assert recommendation.effective_savings_usd == 100


def test_optimizer_boosts_options_matching_arrival_preference() -> None:
    request = OptimizationRequest(
        intent=TripIntent(
            user_id=USER_ID,
            raw_intent="Direct flight to San Diego, arrive before midday",
            budget_usd=500,
        ),
        booking_options=[
            BookingOption(
                label="Late nonstop",
                booking_type=BookingType.cash,
                merchant="Frontier",
                cash_price_usd=150,
                simplicity=4,
                notes=["0 stops.", "Arrives after preferred 12:00 window."],
            ),
            BookingOption(
                label="Morning nonstop",
                booking_type=BookingType.cash,
                merchant="Southwest",
                cash_price_usd=210,
                simplicity=5,
                notes=["0 stops.", "Matches arrival preference by 12:00."],
            ),
        ],
    )

    response = optimize_trip(request)

    assert response.recommendations[0].option.label == "Morning nonstop"
    assert "Matches the requested arrival window." in response.recommendations[0].reasons


def test_optimizer_generates_demo_options_from_accounts() -> None:
    request = OptimizationRequest(
        intent=TripIntent(user_id=USER_ID, raw_intent="NYC using United and Hilton", budget_usd=2000),
        accounts=[
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.united,
                display_name="United",
                points_balance=90000,
            ),
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.hilton,
                display_name="Hilton",
                points_balance=130000,
            ),
        ],
    )

    response = optimize_trip(request)

    labels = {recommendation.option.label for recommendation in response.recommendations}
    assert "Cash fare + hotel direct" in labels
    assert "United award flight + cash hotel" in labels
    assert "Cash flight + Hilton points stay" in labels


def test_optimizer_respects_preferred_programs_when_generating_options() -> None:
    request = OptimizationRequest(
        intent=TripIntent(
            user_id=USER_ID,
            raw_intent="NYC using United only",
            budget_usd=2000,
            preferred_programs=[Program.united],
        ),
        accounts=[
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.united,
                display_name="United",
                points_balance=90000,
            ),
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.hilton,
                display_name="Hilton",
                points_balance=130000,
            ),
        ],
    )

    labels = {recommendation.option.label for recommendation in optimize_trip(request).recommendations}

    assert "United award flight + cash hotel" in labels
    assert "Cash flight + Hilton points stay" not in labels
