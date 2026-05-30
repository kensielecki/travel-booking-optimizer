from __future__ import annotations

from typing import List

from app.models.domain import (
    BookingOption,
    BookingType,
    LoyaltyAccount,
    Offer,
    OptimizationRequest,
    Program,
)


def build_ota_booking_options(request: OptimizationRequest) -> List[BookingOption]:
    """Build deterministic OTA-style V0 shopping options from a trip prompt.

    This module is the adapter boundary: today it returns seeded/demo OTA inventory,
    but later it can be backed by travel search providers without changing optimizer math.
    """
    text = request.intent.raw_intent.lower()
    wants_flights = _mentions_any(text, ["flight", "fly", "airfare", "airport", "direct"])
    wants_hotels = _mentions_any(text, ["hotel", "stay", "room", "lodging", "4 star", "fhr"])

    if not wants_flights and not wants_hotels:
        wants_flights = True
        wants_hotels = True

    options: List[BookingOption] = []
    if wants_flights:
        options.extend(_flight_options(request))
    if wants_hotels:
        options.extend(_hotel_options(request))
    if wants_flights and wants_hotels:
        options.extend(_package_options(request))

    return options


def _flight_options(request: OptimizationRequest) -> List[BookingOption]:
    direct_only = "direct" in request.intent.raw_intent.lower() or "nonstop" in request.intent.raw_intent.lower()
    route = request.intent.destination or "NYC"
    options = [
        BookingOption(
            label=f"United {'nonstop ' if direct_only else ''}cash fare to {route}",
            booking_type=BookingType.cash,
            merchant="United",
            cash_price_usd=438,
            simplicity=5,
            notes=[
                "OTA-style flight result generated from the trip intent.",
                "Direct-flight preference applied." if direct_only else "Includes lowest practical cash airfare.",
            ],
        ),
        BookingOption(
            label=f"Amex Travel cash airfare to {route}",
            booking_type=BookingType.cash,
            merchant="American Express Travel",
            cash_price_usd=456,
            simplicity=4,
            notes=["Keeps flight purchase inside Amex Travel for a single itinerary view."],
        ),
    ]

    united = _account(request.accounts, Program.united)
    if united and united.points_balance >= 20000 and _program_allowed(Program.united, request.intent.preferred_programs):
        options.append(
            BookingOption(
                label=f"United MileagePlus saver-style award to {route}",
                booking_type=BookingType.points,
                merchant="United",
                cash_price_usd=438,
                points_program=Program.united,
                points_used=20000,
                taxes_usd=11.20,
                simplicity=3,
                notes=["Uses captured United miles for a direct-flight award scenario."],
            )
        )

    return options


def _hotel_options(request: OptimizationRequest) -> List[BookingOption]:
    hotel_credit = _best_offer(request.offers, "american express travel")
    amex = _account(request.accounts, Program.amex_mr)
    can_use_amex_points = (
        amex is not None
        and _program_allowed(Program.amex_mr, request.intent.preferred_programs)
    )

    hotels = [
        {
            "name": "The Beekman, A Thompson Hotel",
            "stars": "5-star",
            "distance": "0.12 mi",
            "cash": 1507.22,
            "points": 141542,
            "copay": 91.80,
            "credit": "USD$100 food and beverage credit",
        },
        {
            "name": "The Langham, New York, Fifth Avenue",
            "stars": "5-star",
            "distance": "2.82 mi",
            "cash": 1836.10,
            "points": 183610,
            "copay": 0,
            "credit": "USD$100 property credit",
        },
        {
            "name": "Loews Regency New York Hotel",
            "stars": "5-star",
            "distance": "4.06 mi",
            "cash": 1661.12,
            "points": 166112,
            "copay": 0,
            "credit": "USD$100 food and beverage credit",
        },
        {
            "name": "Equinox Hotel New York",
            "stars": "5-star",
            "distance": "2.9 mi",
            "cash": 2416.19,
            "points": 241619,
            "copay": 0,
            "credit": "USD$100 property credit",
        },
    ]

    options: List[BookingOption] = []
    for hotel in hotels:
        offer_value = hotel_credit.value_usd if hotel_credit else 0
        options.append(
            BookingOption(
                label=f"{hotel['name']} via Amex Travel cash",
                booking_type=BookingType.offer_enhanced if offer_value else BookingType.cash,
                merchant="American Express Travel",
                cash_price_usd=hotel["cash"],
                offer_value_usd=min(offer_value, hotel["cash"]),
                simplicity=4,
                notes=[
                    f"{hotel['stars']} hotel, {hotel['distance']} from searched area.",
                    str(hotel["credit"]),
                    "Applies eligible Amex Travel hotel credit." if offer_value else "Prepaid hotel result from Amex Travel.",
                ],
            )
        )

        if can_use_amex_points and amex and amex.points_balance >= hotel["points"]:
            options.append(
                BookingOption(
                    label=f"{hotel['name']} with Amex Membership Rewards",
                    booking_type=BookingType.points,
                    merchant="American Express Travel",
                    cash_price_usd=hotel["cash"],
                    points_program=Program.amex_mr,
                    points_used=hotel["points"],
                    copay_usd=hotel["copay"],
                    simplicity=3,
                    notes=[
                        f"{hotel['stars']} hotel, {hotel['distance']} from searched area.",
                        "Membership Rewards redemption from Amex Travel search result.",
                    ],
                )
            )

    return options


def _package_options(request: OptimizationRequest) -> List[BookingOption]:
    hotel_credit = _best_offer(request.offers, "american express travel")
    offer_value = hotel_credit.value_usd if hotel_credit else 0
    return [
        BookingOption(
            label="United flight + The Beekman cash package",
            booking_type=BookingType.offer_enhanced if offer_value else BookingType.cash,
            merchant="United + American Express Travel",
            cash_price_usd=1945.22,
            offer_value_usd=min(offer_value, 1507.22),
            simplicity=4,
            notes=[
                "Combines direct-style United airfare with the best-value 5-star Amex Travel hotel result.",
                "Hotel portion can use eligible Amex Travel hotel credit." if offer_value else "Package comparison baseline.",
            ],
        )
    ]


def _account(accounts: List[LoyaltyAccount], program: Program) -> LoyaltyAccount | None:
    return next((account for account in accounts if account.program == program), None)


def _best_offer(offers: List[Offer], merchant_fragment: str) -> Offer | None:
    matching = [
        offer
        for offer in offers
        if merchant_fragment.lower() in offer.merchant.lower()
        or merchant_fragment.lower() in offer.description.lower()
    ]
    if not matching:
        return None
    return max(matching, key=lambda offer: offer.value_usd)


def _mentions_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _program_allowed(program: Program, preferred_programs: List[Program]) -> bool:
    return not preferred_programs or program in preferred_programs
