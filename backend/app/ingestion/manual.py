from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

from app.models.domain import (
    BalanceCorrectionRequest,
    IngestionSource,
    IngestionStateResponse,
    IngestionRun,
    IngestionStatus,
    LoyaltyAccount,
    ManualIngestionRequest,
    ManualIngestionResponse,
    Offer,
    Program,
)

_accounts_by_user: dict[str, dict[Program, LoyaltyAccount]] = {}
_offers_by_user: dict[str, dict[str, Offer]] = {}
_last_run_by_user: dict[str, IngestionRun] = {}
_STATE_PATH = Path(
    os.getenv(
        "LOYALTY_INGESTION_STATE_PATH",
        Path(__file__).resolve().parents[2] / ".local" / "ingestion-state.json",
    )
)


def ingest_manual_payload(payload: ManualIngestionRequest) -> ManualIngestionResponse:
    """Validate normalized V0 ingestion payloads without storing secrets or sessions."""
    status = IngestionStatus.success
    if not payload.accounts and not payload.offers:
        status = IngestionStatus.sanity_failed

    run = IngestionRun(
        user_id=payload.user_id,
        source=payload.source,
        status=status,
        account_count=len(payload.accounts),
        offer_count=len(payload.offers),
        metadata=payload.metadata,
    )

    if status == IngestionStatus.success:
        _store_payload(payload, run)

    return ManualIngestionResponse(
        run=run,
        accounts=payload.accounts,
        offers=payload.offers,
    )


def get_ingestion_state(user_id: UUID) -> IngestionStateResponse:
    """Return local V0 ingestion state until Supabase persistence lands."""
    user_key = str(user_id)
    return IngestionStateResponse(
        user_id=user_id,
        accounts=list(_accounts_by_user.get(user_key, {}).values()),
        offers=_visible_offers(list(_offers_by_user.get(user_key, {}).values())),
        last_run=_last_run_by_user.get(user_key),
    )


def clear_ingestion_state(user_id: UUID) -> IngestionStateResponse:
    """Clear local demo data for a user so live captures do not mix with test data."""
    user_key = str(user_id)
    _accounts_by_user.pop(user_key, None)
    _offers_by_user.pop(user_key, None)
    _last_run_by_user.pop(user_key, None)
    _persist_state()
    return get_ingestion_state(user_id)


def correct_account_balance(
    user_id: UUID,
    program: Program,
    correction: BalanceCorrectionRequest,
) -> IngestionStateResponse:
    """Apply a user-confirmed balance correction after parser ambiguity."""
    user_key = str(user_id)
    accounts = _accounts_by_user.setdefault(user_key, {})
    existing = accounts.get(program)
    display_name = correction.display_name or (existing.display_name if existing else _default_display_name(program))

    account_data = {
        "user_id": user_id,
        "program": program,
        "display_name": display_name,
        "points_balance": correction.points_balance,
    }
    if existing:
        account_data["id"] = existing.id

    accounts[program] = LoyaltyAccount(**account_data)
    _last_run_by_user[user_key] = IngestionRun(
        user_id=user_id,
        source=IngestionSource.manual_import,
        status=IngestionStatus.success,
        account_count=1,
        offer_count=0,
        metadata={
            "manual_balance_correction": True,
            "program": program.value,
        },
    )
    _persist_state()
    return get_ingestion_state(user_id)


def _store_payload(payload: ManualIngestionRequest, run: IngestionRun) -> None:
    user_key = str(payload.user_id)
    accounts = _accounts_by_user.setdefault(user_key, {})
    offers = _offers_by_user.setdefault(user_key, {})

    for account in payload.accounts:
        accounts[account.program] = account

    for offer in _normalized_offers(payload.offers):
        key = f"{offer.program}:{offer.merchant.lower()}:{offer.description.lower()}:{offer.value_usd}:{offer.min_spend_usd}"
        offers[key] = offer

    _last_run_by_user[user_key] = run
    _persist_state()


def _load_state() -> None:
    if not _STATE_PATH.exists():
        return

    try:
        payload = json.loads(_STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return

    for user_key, accounts in payload.get("accounts_by_user", {}).items():
        _accounts_by_user[user_key] = {
            Program(account["program"]): LoyaltyAccount.model_validate(account)
            for account in accounts
        }

    for user_key, offers in payload.get("offers_by_user", {}).items():
        _offers_by_user[user_key] = {
            f"{offer.get('program')}:{offer['merchant']}:{offer['description']}": Offer.model_validate(offer)
            for offer in offers
        }

    for user_key, run in payload.get("last_run_by_user", {}).items():
        _last_run_by_user[user_key] = IngestionRun.model_validate(run)


def _persist_state() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "accounts_by_user": {
            user_key: [account.model_dump(mode="json") for account in accounts.values()]
            for user_key, accounts in _accounts_by_user.items()
        },
        "offers_by_user": {
            user_key: [offer.model_dump(mode="json") for offer in offers.values()]
            for user_key, offers in _offers_by_user.items()
        },
        "last_run_by_user": {
            user_key: run.model_dump(mode="json")
            for user_key, run in _last_run_by_user.items()
        },
    }
    _STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def _default_display_name(program: Program) -> str:
    return {
        Program.amex_mr: "Amex Membership Rewards",
        Program.chase_ur: "Chase Ultimate Rewards",
        Program.united: "United MileagePlus",
        Program.delta: "Delta SkyMiles",
        Program.marriott: "Marriott Bonvoy",
        Program.hilton: "Hilton Honors",
    }[program]


def _normalized_offers(raw_offers: list[Offer]) -> list[Offer]:
    normalized: list[Offer] = []
    seen: set[tuple[str, str, float, float]] = set()

    for offer in raw_offers:
        merchant = _merchant_from_offer(offer)
        if merchant == "Unknown merchant" and not _is_high_value_travel_offer(offer):
            continue
        cleaned = offer.model_copy(update={"merchant": merchant})
        key = (
            cleaned.merchant.lower(),
            _normalized_description(cleaned.description),
            cleaned.value_usd,
            cleaned.min_spend_usd,
        )
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)

    return normalized


def _visible_offers(offers: list[Offer]) -> list[Offer]:
    return sorted(
        _normalized_offers(offers),
        key=lambda offer: (offer.merchant == "Unknown merchant", -offer.value_usd, offer.merchant),
    )


def _merchant_from_offer(offer: Offer) -> str:
    if offer.merchant and offer.merchant != "Unknown merchant":
        return offer.merchant

    text = offer.description.lower()
    merchant_keywords = {
        "American Express Travel": ["american express travel", "amex travel"],
        "Trafalgar": ["trafalgar"],
        "Caesars Rewards Select Destinations": ["caesars"],
        "Hilton": ["hilton"],
        "United": ["united"],
        "Delta": ["delta"],
        "Marriott": ["marriott"],
        "Hyatt": ["hyatt"],
        "British Airways": ["british airways"],
        "Air France": ["air france"],
        "Avianca": ["avianca"],
    }
    for merchant, keywords in merchant_keywords.items():
        if any(keyword in text for keyword in keywords):
            return merchant
    return "Unknown merchant"


def _is_high_value_travel_offer(offer: Offer) -> bool:
    text = offer.description.lower()
    travel_terms = ["travel", "hotel", "airfare", "flight", "resort", "hilton", "united", "delta", "marriott", "hyatt"]
    return offer.value_usd >= 50 and any(term in text for term in travel_terms)


def _normalized_description(description: str) -> str:
    return " ".join(description.lower().split())[:160]


_load_state()
