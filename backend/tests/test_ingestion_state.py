from __future__ import annotations

from uuid import UUID

from app.ingestion.manual import (
    clear_ingestion_state,
    correct_account_balance,
    get_ingestion_state,
    ingest_manual_payload,
)
from app.models.domain import (
    BalanceCorrectionRequest,
    IngestionSource,
    LoyaltyAccount,
    ManualIngestionRequest,
    Offer,
    Program,
)

USER_ID = UUID("22222222-2222-4222-8222-222222222222")


def test_browser_extension_payload_is_stored_in_demo_state() -> None:
    clear_ingestion_state(USER_ID)
    payload = ManualIngestionRequest(
        user_id=USER_ID,
        source=IngestionSource.browser_extension,
        accounts=[
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.amex_mr,
                display_name="Amex Membership Rewards",
                points_balance=110000,
            )
        ],
        offers=[
            Offer(
                user_id=USER_ID,
                program=Program.amex_mr,
                merchant="Hilton",
                description="Spend $500 or more, get $100 back.",
                value_usd=100,
                min_spend_usd=500,
            )
        ],
    )

    response = ingest_manual_payload(payload)
    state = get_ingestion_state(USER_ID)

    assert response.run.status == "success"
    assert state.last_run is not None
    assert state.last_run.source == IngestionSource.browser_extension
    assert state.accounts[0].points_balance == 110000
    assert state.offers[0].merchant == "Hilton"


def test_clear_ingestion_state_removes_demo_capture() -> None:
    clear_ingestion_state(USER_ID)

    state = get_ingestion_state(USER_ID)

    assert state.accounts == []
    assert state.offers == []
    assert state.last_run is None


def test_balance_correction_updates_existing_account() -> None:
    clear_ingestion_state(USER_ID)
    payload = ManualIngestionRequest(
        user_id=USER_ID,
        source=IngestionSource.browser_extension,
        accounts=[
            LoyaltyAccount(
                user_id=USER_ID,
                program=Program.chase_ur,
                display_name="Chase Ultimate Rewards",
                points_balance=7947,
            )
        ],
    )

    ingest_manual_payload(payload)
    state = correct_account_balance(
        USER_ID,
        Program.chase_ur,
        BalanceCorrectionRequest(points_balance=24000),
    )

    assert state.accounts[0].points_balance == 24000
    assert state.last_run is not None
    assert state.last_run.metadata["manual_balance_correction"] is True
    clear_ingestion_state(USER_ID)


def test_ingestion_normalizes_and_filters_noisy_unknown_offers() -> None:
    clear_ingestion_state(USER_ID)
    payload = ManualIngestionRequest(
        user_id=USER_ID,
        source=IngestionSource.browser_extension,
        offers=[
            Offer(
                user_id=USER_ID,
                program=Program.amex_mr,
                merchant="Unknown merchant",
                description="Random non-travel line get $25 back",
                value_usd=25,
                min_spend_usd=0,
            ),
            Offer(
                user_id=USER_ID,
                program=Program.amex_mr,
                merchant="Unknown merchant",
                description="American Express Travel hotel credit get $300 back",
                value_usd=300,
                min_spend_usd=0,
            ),
            Offer(
                user_id=USER_ID,
                program=Program.amex_mr,
                merchant="Unknown merchant",
                description="American Express Travel hotel credit get $300 back",
                value_usd=300,
                min_spend_usd=0,
            ),
        ],
    )

    ingest_manual_payload(payload)
    state = get_ingestion_state(USER_ID)

    assert len(state.offers) == 1
    assert state.offers[0].merchant == "American Express Travel"
    clear_ingestion_state(USER_ID)
