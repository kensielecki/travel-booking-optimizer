from __future__ import annotations

from fastapi import APIRouter

from app.core.intent_parser import enrich_search_from_intent
from app.core.live_travel_search import (
    get_provider_readiness,
    search_live_flights,
    search_live_hotels,
    search_live_trip,
)
from app.core.optimizer import optimize_trip
from app.core.trip_discovery import discover_trip_options
from app.models.domain import (
    BookingOption,
    BookingType,
    OptimizationRequest,
    OptimizationResponse,
    Program,
    ProviderReadiness,
    TripDiscoveryRequest,
    TravelOptimizationRequest,
    TravelSearchRequest,
    TravelSearchResponse,
    TripIntent,
)

router = APIRouter(prefix="/travel-search", tags=["travel search"])


@router.post("/flights", response_model=TravelSearchResponse)
async def flight_search(search: TravelSearchRequest) -> TravelSearchResponse:
    return search_live_flights(enrich_search_from_intent(search))


@router.post("/hotels", response_model=TravelSearchResponse)
async def hotel_search(search: TravelSearchRequest) -> TravelSearchResponse:
    return search_live_hotels(enrich_search_from_intent(search))


@router.post("/parse-intent", response_model=TravelSearchRequest)
async def parse_intent(search: TravelSearchRequest) -> TravelSearchRequest:
    return enrich_search_from_intent(search)


@router.get("/provider-readiness", response_model=list[ProviderReadiness])
async def provider_readiness() -> list[ProviderReadiness]:
    return get_provider_readiness()


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_live_search(request: TravelOptimizationRequest) -> OptimizationResponse:
    enriched_search = enrich_search_from_intent(request.search)
    search_response = search_live_trip(enriched_search)
    options = search_response.booking_options
    options = _apply_offer_value(options, request)
    options = _add_loyalty_award_comparisons(options, request)
    options = [*_build_trip_package_options(options, max_packages=6), *options]

    optimization = OptimizationRequest(
        intent=TripIntent(
            user_id=request.search.user_id,
            raw_intent=enriched_search.raw_intent,
            origin=enriched_search.origin,
            destination=enriched_search.destination,
            budget_usd=enriched_search.budget_usd,
            preferred_programs=enriched_search.preferred_programs,
            ranking_mode=enriched_search.ranking_mode,
        ),
        accounts=request.accounts,
        offers=request.offers,
        transfer_bonuses=request.transfer_bonuses,
        booking_options=options,
    )
    optimized = optimize_trip(optimization)
    return optimized.model_copy(
        update={
            "provider_statuses": search_response.provider_statuses,
            "warnings": search_response.warnings,
        }
    )


@router.post("/discover", response_model=OptimizationResponse)
async def discover_live_trip(request: TripDiscoveryRequest) -> OptimizationResponse:
    return discover_trip_options(request)


def _apply_offer_value(options: list[BookingOption], request: TravelOptimizationRequest) -> list[BookingOption]:
    travel_credit = next(
        (
            offer
            for offer in request.offers
            if "american express travel" in offer.merchant.lower()
            or "american express travel" in offer.description.lower()
            or "amex travel" in offer.description.lower()
        ),
        None,
    )
    if not travel_credit:
        return options

    enhanced = []
    for option in options:
        is_hotelish = _is_hotel_option(option)
        if is_hotelish:
            enhanced.append(
                option.model_copy(
                    update={
                        "booking_type": BookingType.offer_enhanced,
                        "offer_value_usd": min(travel_credit.value_usd, option.cash_price_usd),
                        "notes": [*option.notes, "Applies eligible Amex Travel hotel credit."],
                    }
                )
            )
        else:
            enhanced.append(option)
    return enhanced


def _build_trip_package_options(options: list[BookingOption], max_packages: int = 6) -> list[BookingOption]:
    flights = [
        option
        for option in options
        if _is_flight_option(option) and option.booking_type == BookingType.cash
    ][:3]
    hotels = [
        option
        for option in options
        if _is_hotel_option(option) and option.cash_price_usd > 0
    ][:3]
    if not flights or not hotels:
        return []

    packages: list[BookingOption] = []
    for flight in flights:
        for hotel in hotels:
            booking_type = BookingType.offer_enhanced if hotel.offer_value_usd else BookingType.cash
            environments = {flight.source_environment, hotel.source_environment}
            source_environment = (
                "mock"
                if "mock" in environments
                else "sandbox"
                if "sandbox" in environments
                else "production"
                if environments == {"production"}
                else "unknown"
            )
            provider_confidence = round(min(flight.provider_confidence, hotel.provider_confidence), 2)
            package = BookingOption(
                label=f"Trip package: {flight.merchant} flight + {hotel.label}",
                booking_type=booking_type,
                merchant=f"{flight.merchant} + {hotel.merchant}",
                cash_price_usd=round(flight.cash_price_usd + hotel.cash_price_usd, 2),
                taxes_usd=round(flight.taxes_usd + hotel.taxes_usd, 2),
                fees_usd=round(flight.fees_usd + hotel.fees_usd, 2),
                copay_usd=round(flight.copay_usd + hotel.copay_usd, 2),
                offer_value_usd=hotel.offer_value_usd,
                simplicity=max(1, round((flight.simplicity + hotel.simplicity) / 2)),
                source_provider="trip_package",
                source_environment=source_environment,
                provider_confidence=provider_confidence,
                details={
                    "kind": "trip_package",
                    "flight": {
                        "label": flight.label,
                        "provider": flight.source_provider,
                        "merchant": flight.merchant,
                        "cash_price_usd": flight.cash_price_usd,
                        "booking_url": flight.booking_url,
                        "provider_reference": flight.provider_reference,
                        "details": flight.details,
                    },
                    "hotel": {
                        "label": hotel.label,
                        "provider": hotel.source_provider,
                        "merchant": hotel.merchant,
                        "cash_price_usd": hotel.cash_price_usd,
                        "booking_url": hotel.booking_url,
                        "provider_reference": hotel.provider_reference,
                        "details": hotel.details,
                    },
                },
                notes=[
                    "Combined trip path generated from live provider results.",
                    f"Flight leg: {flight.label}.",
                    f"Hotel leg: {hotel.label}.",
                    *[
                        note
                        for note in [*flight.notes, *hotel.notes]
                        if "arrival preference" in note.lower()
                        or "refundable" in note.lower()
                        or "sandbox" in note.lower()
                        or "offer" in note.lower()
                    ][:5],
                ],
            )
            packages.append(package)

    packages.sort(
        key=lambda option: (
            option.source_environment == "sandbox",
            option.cash_price_usd - option.offer_value_usd,
            -option.provider_confidence,
        )
    )
    return packages[:max_packages]


def _is_flight_option(option: BookingOption) -> bool:
    text = f"{option.label} {option.merchant} {option.source_provider or ''}".lower()
    return any(token in text for token in ["flight", "airways", "airlines", "serpapi_google_flights", "duffel", "kiwi"])


def _is_hotel_option(option: BookingOption) -> bool:
    text = f"{option.label} {option.merchant} {option.source_provider or ''}".lower()
    return any(
        token in text
        for token in [
            "hotel",
            "inn",
            "resort",
            "lodge",
            "google hotels",
            "liteapi",
            "amadeus hotels",
            "beekman",
            "langham",
            "loews",
            "equinox",
        ]
    )


def _add_loyalty_award_comparisons(
    options: list[BookingOption],
    request: TravelOptimizationRequest,
) -> list[BookingOption]:
    united = next((account for account in request.accounts if account.program == Program.united), None)
    if not united or united.points_balance < 20000:
        return options

    enhanced = list(options)
    for option in options:
        if "united" not in option.merchant.lower() or option.points_used:
            continue
        enhanced.append(
            BookingOption(
                label=f"United MileagePlus award alternative to {request.search.destination}",
                booking_type=BookingType.points,
                merchant="United",
                cash_price_usd=option.cash_price_usd,
                taxes_usd=11.20,
                points_program=Program.united,
                points_used=20000,
                simplicity=3,
                notes=[
                    "Award comparison derived from captured United balance and live cash fare context.",
                    "Real award availability still needs United-specific confirmation.",
                ],
            )
        )
    return enhanced
