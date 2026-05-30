from __future__ import annotations

from operator import attrgetter
from typing import List, Optional

from app.models.domain import (
    BookingOption,
    BookingType,
    LoyaltyAccount,
    Offer,
    OptimizationRequest,
    OptimizationResponse,
    Program,
    RankingMode,
    Recommendation,
    TransferBonus,
)


def calculate_cents_per_point(option: BookingOption) -> Optional[float]:
    """Return deterministic cents-per-point; no model output is involved."""
    if option.points_used <= 0:
        return None

    value_usd = (
        option.cash_price_usd
        - option.taxes_usd
        - option.fees_usd
        - option.copay_usd
        + option.offer_value_usd
    )
    return round((value_usd / option.points_used) * 100, 3)


def calculate_out_of_pocket(option: BookingOption) -> float:
    if option.booking_type in {BookingType.cash, BookingType.offer_enhanced}:
        return round(option.cash_price_usd - option.offer_value_usd, 2)
    return round(option.taxes_usd + option.fees_usd + option.copay_usd - option.offer_value_usd, 2)


def calculate_effective_savings(option: BookingOption) -> float:
    return round(max(0, option.cash_price_usd - calculate_out_of_pocket(option)), 2)


def optimize_trip(request: OptimizationRequest) -> OptimizationResponse:
    options = request.booking_options or generate_demo_booking_options(
        budget_usd=request.intent.budget_usd,
        preferred_programs=request.intent.preferred_programs,
        accounts=request.accounts,
        offers=request.offers,
        transfer_bonuses=request.transfer_bonuses,
    )
    recommendations = [_score_option(option, request.intent.ranking_mode) for option in options]
    recommendations.sort(key=attrgetter("score"), reverse=True)

    ranked = [
        recommendation.model_copy(update={"rank": index + 1})
        for index, recommendation in enumerate(recommendations)
    ]
    return OptimizationResponse(
        intent=request.intent,
        recommendations=ranked,
        generated_booking_options=options,
    )


def generate_demo_booking_options(
    budget_usd: float,
    preferred_programs: List[Program],
    accounts: List[LoyaltyAccount],
    offers: List[Offer],
    transfer_bonuses: List[TransferBonus],
) -> List[BookingOption]:
    """Create realistic V0 options when no live pricing integration is connected."""
    account_by_program = {account.program: account for account in accounts}
    best_hotel_offer = _best_offer(offers, "hilton")
    best_transfer = _best_transfer_bonus(transfer_bonuses, Program.amex_mr, Program.united)

    cash_price = round(budget_usd * 0.92, 2)
    options = [
        BookingOption(
            label="Cash fare + hotel direct",
            booking_type=BookingType.cash,
            merchant="United + Hilton",
            cash_price_usd=cash_price,
            offer_value_usd=best_hotel_offer.value_usd if best_hotel_offer else 0,
            simplicity=5,
            notes=["Preserves points and keeps cancellation rules simple."],
        )
    ]

    united = account_by_program.get(Program.united)
    if united and united.points_balance >= 65000 and _program_allowed(Program.united, preferred_programs):
        options.append(
            BookingOption(
                label="United award flight + cash hotel",
                booking_type=BookingType.hybrid,
                merchant="United + Hilton",
                cash_price_usd=cash_price,
                points_program=Program.united,
                points_used=65000,
                taxes_usd=11.20,
                copay_usd=round(cash_price * 0.38, 2),
                offer_value_usd=best_hotel_offer.value_usd if best_hotel_offer else 0,
                simplicity=4,
                notes=["Uses existing United miles and applies eligible hotel offer."],
            )
        )

    hilton = account_by_program.get(Program.hilton)
    if hilton and hilton.points_balance >= 120000 and _program_allowed(Program.hilton, preferred_programs):
        options.append(
            BookingOption(
                label="Cash flight + Hilton points stay",
                booking_type=BookingType.hybrid,
                merchant="United + Hilton",
                cash_price_usd=cash_price,
                points_program=Program.hilton,
                points_used=120000,
                taxes_usd=0,
                copay_usd=round(cash_price * 0.46, 2),
                simplicity=4,
                notes=["Saves cash on lodging while keeping the flight simple."],
            )
        )

    amex = account_by_program.get(Program.amex_mr)
    if (
        amex
        and best_transfer
        and amex.points_balance >= 50000
        and _program_allowed(Program.amex_mr, preferred_programs)
        and _program_allowed(Program.united, preferred_programs)
    ):
        required_points = round(60000 / (1 + best_transfer.bonus_pct / 100))
        options.append(
            BookingOption(
                label="Transfer Amex to United route",
                booking_type=BookingType.transfer,
                merchant="Amex MR transfer partner",
                cash_price_usd=cash_price,
                points_program=Program.united,
                transfer_from_program=Program.amex_mr,
                transfer_bonus_pct=best_transfer.bonus_pct,
                points_used=required_points,
                taxes_usd=11.20,
                copay_usd=round(cash_price * 0.32, 2),
                simplicity=2,
                notes=[f"Includes a {best_transfer.bonus_pct:.0f}% transfer bonus."],
            )
        )

    if best_hotel_offer:
        options.append(
            BookingOption(
                label="Offer-enhanced cash booking",
                booking_type=BookingType.offer_enhanced,
                merchant=best_hotel_offer.merchant,
                cash_price_usd=cash_price,
                offer_value_usd=best_hotel_offer.value_usd,
                simplicity=5,
                notes=["Uses an active card offer without introducing award availability risk."],
            )
        )

    return options


def _score_option(option: BookingOption, ranking_mode: RankingMode) -> Recommendation:
    cpp = calculate_cents_per_point(option)
    out_of_pocket = calculate_out_of_pocket(option)
    effective_savings = calculate_effective_savings(option)
    total_value = round(effective_savings + option.offer_value_usd, 2)
    preference_adjustment, preference_reasons = _preference_adjustment(option)
    reasons = _build_reasons(option, cpp, out_of_pocket, effective_savings, preference_reasons)

    normalized_cpp = min(cpp or 0, 5) * 20
    normalized_cash = max(0, 100 - out_of_pocket / max(option.cash_price_usd, 1) * 100)
    normalized_value = min(total_value / max(option.cash_price_usd, 1) * 100, 100)
    normalized_simple = option.simplicity * 20
    normalized_confidence = option.provider_confidence * 100

    if ranking_mode == RankingMode.lowest_out_of_pocket:
        score = normalized_cash * 0.70 + normalized_simple * 0.20 + normalized_cpp * 0.10
    elif ranking_mode == RankingMode.highest_cpp:
        score = normalized_cpp * 0.70 + normalized_cash * 0.20 + normalized_simple * 0.10
    elif ranking_mode == RankingMode.total_value:
        score = normalized_value * 0.65 + normalized_cpp * 0.20 + normalized_simple * 0.15
    elif ranking_mode == RankingMode.simplest:
        score = normalized_simple * 0.70 + normalized_cash * 0.20 + normalized_value * 0.10
    else:
        score = (
            normalized_cash * 0.30
            + normalized_cpp * 0.25
            + normalized_value * 0.20
            + normalized_simple * 0.15
            + normalized_confidence * 0.10
        )

    score = max(0, min(100, score + preference_adjustment))

    return Recommendation(
        option=option,
        rank=0,
        cents_per_point=cpp,
        out_of_pocket_usd=max(0, out_of_pocket),
        cash_avoided_usd=max(0, option.cash_price_usd - option.taxes_usd - option.fees_usd - option.copay_usd),
        effective_savings_usd=effective_savings,
        total_economic_value_usd=total_value,
        score=round(score, 2),
        reasons=reasons,
    )


def _build_reasons(
    option: BookingOption,
    cpp: Optional[float],
    out_of_pocket: float,
    effective_savings: float,
    preference_reasons: List[str],
) -> List[str]:
    reasons = [f"Estimated out-of-pocket cost is ${max(0, out_of_pocket):,.2f}."]
    if cpp is not None:
        reasons.append(f"Deterministic redemption value is {cpp:.2f} cents per point.")
    if option.offer_value_usd:
        reasons.append(f"Includes ${option.offer_value_usd:,.2f} in active offer value.")
    if option.transfer_bonus_pct:
        reasons.append(f"Transfer bonus reduces required source points by {option.transfer_bonus_pct:.0f}%.")
    if option.source_environment == "sandbox":
        reasons.append("Provider result is sandbox data, so treat the price as workflow validation rather than market truth.")
    elif option.source_environment == "mock":
        reasons.append("Provider result is mock data for fallback testing.")
    reasons.extend(preference_reasons)
    reasons.append(f"Effective savings versus cash baseline: ${effective_savings:,.2f}.")
    return reasons


def _preference_adjustment(option: BookingOption) -> tuple[float, List[str]]:
    joined_notes = " ".join(option.notes).lower()
    adjustment = 0.0
    reasons: List[str] = []

    if "matches arrival preference" in joined_notes:
        adjustment += 8
        reasons.append("Matches the requested arrival window.")
    if "arrives after preferred" in joined_notes:
        adjustment -= 12
        reasons.append("Arrives after the requested arrival window.")
    if "0 stops" in joined_notes or "nonstop" in option.label.lower():
        adjustment += 3
        reasons.append("Keeps the flight nonstop.")
    if "1 stop" in joined_notes:
        adjustment -= 2
    if "2 stops" in joined_notes or "3 stops" in joined_notes:
        adjustment -= 6

    return adjustment, reasons


def _best_offer(offers: List[Offer], merchant_fragment: str) -> Optional[Offer]:
    matching = [offer for offer in offers if merchant_fragment.lower() in offer.merchant.lower()]
    if not matching:
        return None
    return max(matching, key=lambda offer: offer.value_usd)


def _program_allowed(program: Program, preferred_programs: List[Program]) -> bool:
    return not preferred_programs or program in preferred_programs


def _best_transfer_bonus(
    bonuses: List[TransferBonus],
    from_program: Program,
    to_program: Program,
) -> Optional[TransferBonus]:
    matching = [
        bonus
        for bonus in bonuses
        if bonus.from_program == from_program and bonus.to_program == to_program
    ]
    if not matching:
        return None
    return max(matching, key=lambda bonus: bonus.bonus_pct)
