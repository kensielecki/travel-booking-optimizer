from __future__ import annotations

import os
import re
from dataclasses import dataclass
from app.core.intent_parser import enrich_search_from_intent
from app.core.live_travel_search import get_provider_readiness, search_flights_across_providers, search_hotels_across_providers
from app.core.optimizer import optimize_trip
from app.models.domain import (
    BookingOption,
    BookingType,
    OptimizationRequest,
    OptimizationResponse,
    ProviderStatus,
    TripDiscoveryRequest,
    TripIntent,
    TravelSearchRequest,
)


@dataclass(frozen=True)
class CandidateDestination:
    city: str
    airport: str
    region: str
    flight_minutes: int | None
    drive_minutes: int | None
    hotel_query: str


@dataclass(frozen=True)
class DiscoveryPlan:
    scope: str
    candidate_pool_count: int
    matched_candidate_count: int
    selected_candidates: list[CandidateDestination]
    skipped_candidate_count: int
    provider_call_budget: int
    estimated_provider_calls: int
    providers_per_candidate: int


BAY_AREA_CANDIDATES = [
    CandidateDestination("San Diego", "SAN", "Southern California", 95, None, "San Diego California"),
    CandidateDestination("Los Angeles", "LAX", "Southern California", 85, None, "Los Angeles California"),
    CandidateDestination("Palm Springs", "PSP", "Southern California", 95, None, "Palm Springs California"),
    CandidateDestination("Las Vegas", "LAS", "Nevada", 95, None, "Las Vegas Nevada"),
    CandidateDestination("Phoenix", "PHX", "Arizona", 120, None, "Phoenix Arizona"),
    CandidateDestination("Santa Barbara", "SBA", "Central Coast", 80, 310, "Santa Barbara California"),
    CandidateDestination("Seattle", "SEA", "Pacific Northwest", 130, None, "Seattle Washington"),
    CandidateDestination("Portland", "PDX", "Pacific Northwest", 105, None, "Portland Oregon"),
    CandidateDestination("Monterey / Carmel", "MRY", "Central Coast", None, 125, "Carmel California"),
    CandidateDestination("Napa", "STS", "Wine Country", None, 65, "Napa California"),
    CandidateDestination("Lake Tahoe", "RNO", "Tahoe", 70, 230, "Lake Tahoe California"),
]

US_CANDIDATES = [
    *BAY_AREA_CANDIDATES,
    CandidateDestination("Denver", "DEN", "Mountain West", 150, None, "Denver Colorado"),
    CandidateDestination("Salt Lake City", "SLC", "Mountain West", 115, None, "Salt Lake City Utah"),
    CandidateDestination("Scottsdale", "PHX", "Arizona", 120, None, "Scottsdale Arizona"),
    CandidateDestination("Santa Fe", "SAF", "Southwest", 150, None, "Santa Fe New Mexico"),
    CandidateDestination("Austin", "AUS", "Texas", 210, None, "Austin Texas"),
    CandidateDestination("Dallas", "DFW", "Texas", 210, None, "Dallas Texas"),
    CandidateDestination("Chicago", "ORD", "Midwest", 250, None, "Chicago Illinois"),
    CandidateDestination("Nashville", "BNA", "Southeast", 250, None, "Nashville Tennessee"),
    CandidateDestination("New Orleans", "MSY", "Southeast", 255, None, "New Orleans Louisiana"),
    CandidateDestination("Charleston", "CHS", "Southeast", 320, None, "Charleston South Carolina"),
    CandidateDestination("Miami", "MIA", "Florida", 335, None, "Miami Florida"),
    CandidateDestination("New York", "JFK", "Northeast", 330, None, "New York New York"),
    CandidateDestination("Boston", "BOS", "Northeast", 340, None, "Boston Massachusetts"),
    CandidateDestination("Washington DC", "DCA", "Northeast", 320, None, "Washington DC"),
    CandidateDestination("Honolulu", "HNL", "Hawaii", 330, None, "Honolulu Hawaii"),
    CandidateDestination("Kauai", "LIH", "Hawaii", 340, None, "Kauai Hawaii"),
]

EUROPE_CANDIDATES = [
    CandidateDestination("London", "LHR", "United Kingdom", 620, None, "London England"),
    CandidateDestination("Paris", "CDG", "France", 650, None, "Paris France"),
    CandidateDestination("Amsterdam", "AMS", "Netherlands", 640, None, "Amsterdam Netherlands"),
    CandidateDestination("Dublin", "DUB", "Ireland", 610, None, "Dublin Ireland"),
    CandidateDestination("Edinburgh", "EDI", "United Kingdom", 640, None, "Edinburgh Scotland"),
    CandidateDestination("Rome", "FCO", "Italy", 720, None, "Rome Italy"),
    CandidateDestination("Florence", "FLR", "Italy", 735, None, "Florence Italy"),
    CandidateDestination("Milan", "MXP", "Italy", 700, None, "Milan Italy"),
    CandidateDestination("Venice", "VCE", "Italy", 725, None, "Venice Italy"),
    CandidateDestination("Barcelona", "BCN", "Spain", 700, None, "Barcelona Spain"),
    CandidateDestination("Madrid", "MAD", "Spain", 680, None, "Madrid Spain"),
    CandidateDestination("Mallorca", "PMI", "Spain", 725, None, "Mallorca Spain"),
    CandidateDestination("Lisbon", "LIS", "Portugal", 660, None, "Lisbon Portugal"),
    CandidateDestination("Porto", "OPO", "Portugal", 665, None, "Porto Portugal"),
    CandidateDestination("Zurich", "ZRH", "Switzerland", 690, None, "Zurich Switzerland"),
    CandidateDestination("Geneva", "GVA", "Switzerland", 695, None, "Geneva Switzerland"),
    CandidateDestination("Copenhagen", "CPH", "Denmark", 665, None, "Copenhagen Denmark"),
    CandidateDestination("Stockholm", "ARN", "Sweden", 690, None, "Stockholm Sweden"),
    CandidateDestination("Oslo", "OSL", "Norway", 690, None, "Oslo Norway"),
    CandidateDestination("Reykjavik", "KEF", "Iceland", 500, None, "Reykjavik Iceland"),
    CandidateDestination("Berlin", "BER", "Germany", 685, None, "Berlin Germany"),
    CandidateDestination("Munich", "MUC", "Germany", 700, None, "Munich Germany"),
    CandidateDestination("Vienna", "VIE", "Austria", 720, None, "Vienna Austria"),
    CandidateDestination("Prague", "PRG", "Czech Republic", 715, None, "Prague Czech Republic"),
    CandidateDestination("Budapest", "BUD", "Hungary", 735, None, "Budapest Hungary"),
    CandidateDestination("Athens", "ATH", "Greece", 810, None, "Athens Greece"),
    CandidateDestination("Santorini", "JTR", "Greece", 850, None, "Santorini Greece"),
    CandidateDestination("Mykonos", "JMK", "Greece", 850, None, "Mykonos Greece"),
    CandidateDestination("Dubrovnik", "DBV", "Croatia", 780, None, "Dubrovnik Croatia"),
    CandidateDestination("Split", "SPU", "Croatia", 780, None, "Split Croatia"),
    CandidateDestination("Nice", "NCE", "France", 705, None, "Nice France"),
    CandidateDestination("Monaco", "NCE", "French Riviera", 705, None, "Monaco"),
    CandidateDestination("Brussels", "BRU", "Belgium", 660, None, "Brussels Belgium"),
    CandidateDestination("Bruges", "BRU", "Belgium", 660, None, "Bruges Belgium"),
]

SOUTHEAST_ASIA_CANDIDATES = [
    CandidateDestination("Singapore", "SIN", "Southeast Asia", 1030, None, "Singapore"),
    CandidateDestination("Bangkok", "BKK", "Thailand", 1020, None, "Bangkok Thailand"),
    CandidateDestination("Chiang Mai", "CNX", "Thailand", 1060, None, "Chiang Mai Thailand"),
    CandidateDestination("Phuket", "HKT", "Thailand", 1080, None, "Phuket Thailand"),
    CandidateDestination("Koh Samui", "USM", "Thailand", 1110, None, "Koh Samui Thailand"),
    CandidateDestination("Bali", "DPS", "Indonesia", 1120, None, "Bali Indonesia"),
    CandidateDestination("Lombok", "LOP", "Indonesia", 1140, None, "Lombok Indonesia"),
    CandidateDestination("Jakarta", "CGK", "Indonesia", 1040, None, "Jakarta Indonesia"),
    CandidateDestination("Yogyakarta", "YIA", "Indonesia", 1090, None, "Yogyakarta Indonesia"),
    CandidateDestination("Kuala Lumpur", "KUL", "Malaysia", 1050, None, "Kuala Lumpur Malaysia"),
    CandidateDestination("Penang", "PEN", "Malaysia", 1080, None, "Penang Malaysia"),
    CandidateDestination("Ho Chi Minh City", "SGN", "Vietnam", 1000, None, "Ho Chi Minh City Vietnam"),
    CandidateDestination("Hanoi", "HAN", "Vietnam", 980, None, "Hanoi Vietnam"),
    CandidateDestination("Da Nang / Hoi An", "DAD", "Vietnam", 1030, None, "Hoi An Vietnam"),
    CandidateDestination("Nha Trang", "CXR", "Vietnam", 1040, None, "Nha Trang Vietnam"),
    CandidateDestination("Manila", "MNL", "Philippines", 840, None, "Manila Philippines"),
    CandidateDestination("Cebu", "CEB", "Philippines", 930, None, "Cebu Philippines"),
    CandidateDestination("Siem Reap", "SAI", "Cambodia", 1040, None, "Siem Reap Cambodia"),
    CandidateDestination("Luang Prabang", "LPQ", "Laos", 1040, None, "Luang Prabang Laos"),
]

EAST_ASIA_CANDIDATES = [
    CandidateDestination("Tokyo", "HND", "Japan", 660, None, "Tokyo Japan"),
    CandidateDestination("Kyoto", "KIX", "Japan", 700, None, "Kyoto Japan"),
    CandidateDestination("Osaka", "KIX", "Japan", 700, None, "Osaka Japan"),
    CandidateDestination("Fukuoka", "FUK", "Japan", 735, None, "Fukuoka Japan"),
    CandidateDestination("Okinawa", "OKA", "Japan", 775, None, "Okinawa Japan"),
    CandidateDestination("Seoul", "ICN", "South Korea", 720, None, "Seoul South Korea"),
    CandidateDestination("Taipei", "TPE", "Taiwan", 800, None, "Taipei Taiwan"),
    CandidateDestination("Hong Kong", "HKG", "Hong Kong", 845, None, "Hong Kong"),
    CandidateDestination("Shanghai", "PVG", "China", 790, None, "Shanghai China"),
    CandidateDestination("Beijing", "PEK", "China", 810, None, "Beijing China"),
]

LATIN_AMERICA_CANDIDATES = [
    CandidateDestination("Mexico City", "MEX", "Mexico", 250, None, "Mexico City Mexico"),
    CandidateDestination("Los Cabos", "SJD", "Mexico", 190, None, "Los Cabos Mexico"),
    CandidateDestination("Puerto Vallarta", "PVR", "Mexico", 220, None, "Puerto Vallarta Mexico"),
    CandidateDestination("Cancun", "CUN", "Mexico", 310, None, "Cancun Mexico"),
    CandidateDestination("Belize", "BZE", "Central America", 330, None, "Belize"),
    CandidateDestination("Guatemala City / Antigua", "GUA", "Central America", 330, None, "Antigua Guatemala"),
    CandidateDestination("Costa Rica", "SJO", "Central America", 360, None, "Costa Rica"),
    CandidateDestination("Panama City", "PTY", "Central America", 415, None, "Panama City Panama"),
    CandidateDestination("Cartagena", "CTG", "Colombia", 450, None, "Cartagena Colombia"),
    CandidateDestination("Medellin", "MDE", "Colombia", 455, None, "Medellin Colombia"),
    CandidateDestination("Bogota", "BOG", "Colombia", 460, None, "Bogota Colombia"),
    CandidateDestination("Quito", "UIO", "Ecuador", 470, None, "Quito Ecuador"),
    CandidateDestination("Galapagos", "GPS", "Ecuador", 560, None, "Galapagos Ecuador"),
    CandidateDestination("Lima", "LIM", "Peru", 500, None, "Lima Peru"),
    CandidateDestination("Cusco", "CUZ", "Peru", 560, None, "Cusco Peru"),
    CandidateDestination("Santiago", "SCL", "Chile", 700, None, "Santiago Chile"),
    CandidateDestination("Buenos Aires", "EZE", "Argentina", 760, None, "Buenos Aires Argentina"),
    CandidateDestination("Montevideo", "MVD", "Uruguay", 800, None, "Montevideo Uruguay"),
    CandidateDestination("Rio de Janeiro", "GIG", "Brazil", 820, None, "Rio de Janeiro Brazil"),
    CandidateDestination("Sao Paulo", "GRU", "Brazil", 800, None, "Sao Paulo Brazil"),
]

ASIA_CANDIDATES = [*SOUTHEAST_ASIA_CANDIDATES, *EAST_ASIA_CANDIDATES]


def discover_trip_options(request: TripDiscoveryRequest) -> OptimizationResponse:
    constraints = _discovery_constraints(request)
    scope = _discovery_scope(request.search.raw_intent)
    plan = _discovery_plan(request, constraints, scope)
    candidates = plan.selected_candidates
    searched = ", ".join(candidate.city for candidate in candidates) if candidates else "none"

    options: list[BookingOption] = []
    provider_statuses: list[ProviderStatus] = []
    warnings: list[str] = [
        f"Discovery mode: searched {_scope_label(scope)} candidates: {searched}.",
        _plan_summary(plan),
        _constraint_summary(constraints),
    ]
    if not candidates:
        warnings.append(f"No {_scope_label(scope)} destination candidates matched the requested travel-time constraints.")
    elif plan.skipped_candidate_count:
        warnings.append(
            f"Discovery budget: held back {plan.skipped_candidate_count} matching candidates to stay within the live-search budget."
        )

    for candidate in candidates:
        flight_search = _candidate_search(request.search, candidate, constraints, destination=candidate.airport)
        hotel_search = _candidate_search(request.search, candidate, constraints, destination=candidate.hotel_query)
        flight_response = search_flights_across_providers(flight_search)
        hotel_response = search_hotels_across_providers(hotel_search)
        provider_statuses.extend(flight_response.provider_statuses)
        provider_statuses.extend(hotel_response.provider_statuses)
        warnings.extend(flight_response.warnings)
        warnings.extend(hotel_response.warnings)

        flight = _best_flight_option(
            _filter_mock_options_for_discovery(flight_response.booking_options, flight_response.provider_statuses),
            constraints,
        )
        hotel = _best_hotel_option(
            _filter_mock_options_for_discovery(hotel_response.booking_options, hotel_response.provider_statuses),
            constraints,
        )
        if not flight or not hotel:
            missing = "flight and hotel" if not flight and not hotel else "flight" if not flight else "hotel"
            warnings.append(f"Skipped {candidate.city}: no usable live {missing} option matched the discovery constraints.")
            continue

        option = _build_discovery_package(candidate, flight, hotel, constraints)
        if option:
            options.append(option)

    options.sort(key=_discovery_sort_key)

    optimization = optimize_trip(
        OptimizationRequest(
            intent=TripIntent(
                user_id=request.search.user_id,
                raw_intent=request.search.raw_intent,
                origin=request.search.origin or "Alameda / Bay Area",
                destination="Open destination discovery",
                budget_usd=request.search.budget_usd,
                preferred_programs=request.search.preferred_programs,
                ranking_mode=request.search.ranking_mode,
            ),
            accounts=request.accounts,
            offers=request.offers,
            transfer_bonuses=request.transfer_bonuses,
            booking_options=options[:10],
        )
    )
    return optimization.model_copy(
        update={
            "provider_statuses": _dedupe_provider_statuses(provider_statuses),
            "warnings": warnings[:16],
        }
    )


def _discovery_constraints(request: TripDiscoveryRequest) -> dict:
    text = request.search.raw_intent.lower()
    return {
        "max_flight_minutes": request.max_flight_minutes or _parse_time_limit_minutes(text, "fly", "flight"),
        "max_drive_minutes": request.max_drive_minutes or _parse_time_limit_minutes(text, "drive", "driving"),
        "max_nightly_rate_usd": request.max_nightly_rate_usd or _parse_nightly_rate(text),
        "hotel_min_stars": request.search.hotel_min_stars or _parse_star_floor(text) or 5,
        "include_near_misses": request.include_near_misses,
    }


def _constraint_summary(constraints: dict) -> str:
    parts = [f"hotel floor {constraints.get('hotel_min_stars', 5)} star"]
    if constraints.get("max_nightly_rate_usd"):
        parts.append(f"nightly rate under ${constraints['max_nightly_rate_usd']:,.0f}")
    if constraints.get("max_flight_minutes"):
        parts.append(f"flight time under {constraints['max_flight_minutes']} min")
    if constraints.get("max_drive_minutes"):
        parts.append(f"drive time under {constraints['max_drive_minutes']} min")
    if constraints.get("include_near_misses"):
        parts.append("near misses allowed")
    return f"Discovery constraints: {', '.join(parts)}."


def _discovery_scope(text: str) -> str:
    normalized = text.lower()
    if any(token in normalized for token in ["south east asia", "southeast asia", "sea asia", "thailand", "vietnam", "singapore", "bali"]):
        return "southeast_asia"
    if any(token in normalized for token in ["east asia", "japan", "tokyo", "kyoto", "osaka", "korea", "seoul", "taiwan", "taipei", "hong kong", "china"]):
        return "east_asia"
    if "asia" in normalized:
        return "asia"
    if any(
        token in normalized
        for token in [
            "central america",
            "south america",
            "latin america",
            "mexico",
            "costa rica",
            "panama",
            "belize",
            "guatemala",
            "colombia",
            "peru",
            "ecuador",
            "chile",
            "argentina",
            "uruguay",
            "brazil",
        ]
    ):
        return "latin_america"
    if any(token in normalized for token in ["europe", "european", "france", "italy", "spain", "london", "paris"]):
        return "europe"
    if any(token in normalized for token in ["across the us", "across us", "united states", "usa", "u.s.", "america", "domestic"]):
        return "united_states"
    if any(token in normalized for token in ["anywhere", "global", "international"]):
        return "global"
    return "bay_area"


def _scope_label(scope: str) -> str:
    return {
        "bay_area": "Bay Area",
        "united_states": "United States",
        "europe": "Europe",
        "southeast_asia": "Southeast Asia",
        "east_asia": "East Asia",
        "asia": "Asia",
        "latin_america": "Central & South America",
        "global": "global",
    }.get(scope, "Bay Area")


def _candidate_pool(scope: str) -> list[CandidateDestination]:
    if scope == "united_states":
        return US_CANDIDATES
    if scope == "europe":
        return EUROPE_CANDIDATES
    if scope == "southeast_asia":
        return SOUTHEAST_ASIA_CANDIDATES
    if scope == "east_asia":
        return EAST_ASIA_CANDIDATES
    if scope == "asia":
        return ASIA_CANDIDATES
    if scope == "latin_america":
        return LATIN_AMERICA_CANDIDATES
    if scope == "global":
        return [*US_CANDIDATES, *EUROPE_CANDIDATES, *ASIA_CANDIDATES, *LATIN_AMERICA_CANDIDATES]
    return BAY_AREA_CANDIDATES


def _discovery_plan(request: TripDiscoveryRequest, constraints: dict, scope: str) -> DiscoveryPlan:
    pool = _candidate_pool(scope)
    matched = _candidate_destinations(
        constraints,
        max_destinations=len(pool),
        include_near_misses=request.include_near_misses,
        scope=scope,
    )
    providers_per_candidate = _configured_provider_call_count()
    provider_call_budget = _provider_call_budget(request.max_provider_calls)
    budget_limited_candidates = max(1, provider_call_budget // providers_per_candidate)
    selected_count = min(request.max_destinations, budget_limited_candidates, len(matched))
    selected = matched[:selected_count]

    return DiscoveryPlan(
        scope=scope,
        candidate_pool_count=len(pool),
        matched_candidate_count=len(matched),
        selected_candidates=selected,
        skipped_candidate_count=max(0, len(matched) - len(selected)),
        provider_call_budget=provider_call_budget,
        estimated_provider_calls=len(selected) * providers_per_candidate,
        providers_per_candidate=providers_per_candidate,
    )


def _provider_call_budget(request_budget: int) -> int:
    raw_budget = os.getenv("DISCOVERY_PROVIDER_CALL_BUDGET")
    if raw_budget:
        try:
            return max(2, min(80, int(raw_budget)))
        except ValueError:
            return request_budget
    return request_budget


def _configured_provider_call_count() -> int:
    readiness = get_provider_readiness()
    flight_calls = sum(1 for provider in readiness if provider.category == "flight" and provider.configured)
    hotel_calls = sum(1 for provider in readiness if provider.category == "hotel" and provider.configured)
    return max(2, flight_calls + hotel_calls)


def _plan_summary(plan: DiscoveryPlan) -> str:
    return (
        "Discovery plan: "
        f"scope {_scope_label(plan.scope)}, "
        f"candidate pool {plan.candidate_pool_count}, "
        f"matched {plan.matched_candidate_count}, "
        f"selected {len(plan.selected_candidates)}, "
        f"provider call budget {plan.provider_call_budget}, "
        f"estimated provider calls {plan.estimated_provider_calls}."
    )


def _candidate_destinations(
    constraints: dict,
    max_destinations: int,
    include_near_misses: bool,
    scope: str = "bay_area",
) -> list[CandidateDestination]:
    max_flight = constraints.get("max_flight_minutes")
    max_drive = constraints.get("max_drive_minutes")
    scored: list[tuple[int, CandidateDestination]] = []

    for candidate in _candidate_pool(scope):
        flight_fit = candidate.flight_minutes is not None and (max_flight is None or candidate.flight_minutes <= max_flight)
        drive_fit = candidate.drive_minutes is not None and (max_drive is None or candidate.drive_minutes <= max_drive)
        near_flight = candidate.flight_minutes is not None and max_flight is not None and candidate.flight_minutes <= max_flight + 45
        near_drive = candidate.drive_minutes is not None and max_drive is not None and candidate.drive_minutes <= max_drive + 45

        if max_drive is None and candidate.flight_minutes is None:
            continue

        if flight_fit or (max_drive is not None and drive_fit):
            score = 0
        elif include_near_misses and (near_flight or (max_drive is not None and near_drive)):
            score = 1
        else:
            continue

        travel_minutes = min(
            [value for value in [candidate.flight_minutes, candidate.drive_minutes] if value is not None],
            default=9999,
        )
        scored.append((score * 10000 + travel_minutes, candidate))

    scored.sort(key=lambda item: item[0])
    return [candidate for _, candidate in scored[:max_destinations]]


def _candidate_search(
    search: TravelSearchRequest,
    candidate: CandidateDestination,
    constraints: dict,
    destination: str,
) -> TravelSearchRequest:
    enriched = enrich_search_from_intent(search)
    return enriched.model_copy(
        update={
            "destination": destination,
            "raw_intent": f"{search.raw_intent} Destination candidate: {candidate.city}.",
            "origin": search.origin or "SFO",
            "hotel_min_stars": constraints["hotel_min_stars"],
            "max_results": min(search.max_results, 5),
        }
    )


def _best_flight_option(options: list[BookingOption], constraints: dict) -> BookingOption | None:
    if not options:
        return None

    def score(option: BookingOption) -> tuple:
        minutes = _option_duration_minutes(option)
        max_flight = constraints.get("max_flight_minutes")
        violation = 0 if minutes is None or max_flight is None or minutes <= max_flight else minutes - max_flight
        return (violation, option.cash_price_usd, -option.provider_confidence)

    best = sorted(options, key=score)[0]
    minutes = _option_duration_minutes(best)
    max_flight = constraints.get("max_flight_minutes")
    if minutes and max_flight and minutes > max_flight + 45:
        return None
    return best


def _filter_mock_options_for_discovery(
    options: list[BookingOption],
    statuses: list[ProviderStatus],
) -> list[BookingOption]:
    non_mock = [option for option in options if option.source_environment != "mock"]
    if non_mock:
        return non_mock

    non_mock_provider_was_attempted = any(status.status in {"live", "failed"} for status in statuses)
    if non_mock_provider_was_attempted:
        return []
    return options


def _best_hotel_option(options: list[BookingOption], constraints: dict) -> BookingOption | None:
    hotel_floor = constraints.get("hotel_min_stars") or 5
    max_nightly = constraints.get("max_nightly_rate_usd")

    def score(option: BookingOption) -> tuple:
        quality = _hotel_quality(option, hotel_floor)
        nightly = option.cash_price_usd
        star_gap = max(0, hotel_floor - quality)
        price_gap = max(0, nightly - max_nightly) if max_nightly else 0
        return (star_gap, price_gap, nightly, -option.provider_confidence)

    usable = [
        option
        for option in options
        if option.cash_price_usd > 0 and _hotel_is_usable(option, constraints)
    ]
    return sorted(usable, key=score)[0] if usable else None


def _build_discovery_package(
    candidate: CandidateDestination,
    flight: BookingOption,
    hotel: BookingOption,
    constraints: dict,
) -> BookingOption:
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
    flight_minutes = _option_duration_minutes(flight) or candidate.flight_minutes
    hotel_stars = _hotel_quality(hotel, constraints.get("hotel_min_stars") or 5)
    hotel_class_signal = hotel_stars if hotel_stars > 0 else None
    hotel_rating = _float_detail(hotel, "guest_rating")
    nightly_rate = hotel.cash_price_usd
    constraint_fit = _constraint_fit(candidate, flight_minutes, hotel_stars, nightly_rate, constraints)
    constraint_checks = _constraint_checks(candidate, flight_minutes, hotel_class_signal, hotel_rating, nightly_rate, constraints)
    travel_label = (
        f"{flight_minutes} min flight"
        if flight_minutes
        else f"{candidate.drive_minutes} min drive"
        if candidate.drive_minutes
        else "reachable from Bay Area"
    )

    return BookingOption(
        label=f"{candidate.city}: {flight.merchant} flight + {hotel.label}",
        booking_type=BookingType.cash,
        merchant=f"{flight.merchant} + {hotel.merchant}",
        cash_price_usd=round(flight.cash_price_usd + hotel.cash_price_usd, 2),
        taxes_usd=round(flight.taxes_usd + hotel.taxes_usd, 2),
        fees_usd=round(flight.fees_usd + hotel.fees_usd, 2),
        copay_usd=round(flight.copay_usd + hotel.copay_usd, 2),
        simplicity=max(1, round((flight.simplicity + hotel.simplicity) / 2)),
        source_provider="trip_discovery",
        source_environment=source_environment,
        provider_confidence=round(min(flight.provider_confidence, hotel.provider_confidence), 2),
        details={
            "kind": "trip_package",
            "destination": candidate.city,
            "region": candidate.region,
            "constraint_fit": constraint_fit,
            "constraint_checks": constraint_checks,
            "travel_minutes": flight_minutes or candidate.drive_minutes,
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
            "Discovery result generated from Bay Area candidate search.",
            f"Destination: {candidate.city} ({candidate.region}).",
            f"Travel time: {travel_label}.",
            f"Constraint fit: {constraint_fit}.",
            f"Flight leg: {flight.label}.",
            f"Hotel leg: {hotel.label}.",
        ],
    )


def _constraint_fit(
    candidate: CandidateDestination,
    flight_minutes: int | None,
    hotel_stars: float | None,
    nightly_rate: float,
    constraints: dict,
) -> str:
    violations = 0
    near_misses = 0
    max_flight = constraints.get("max_flight_minutes")
    max_drive = constraints.get("max_drive_minutes")
    max_nightly = constraints.get("max_nightly_rate_usd")
    hotel_floor = constraints.get("hotel_min_stars") or 5

    if max_flight and flight_minutes and flight_minutes > max_flight:
        near_misses += 1 if flight_minutes <= max_flight + 45 else 0
        violations += 0 if flight_minutes <= max_flight + 45 else 1
    if max_drive and candidate.drive_minutes and candidate.drive_minutes > max_drive:
        near_misses += 1 if candidate.drive_minutes <= max_drive + 45 else 0
        violations += 0 if candidate.drive_minutes <= max_drive + 45 else 1
    if max_nightly and nightly_rate > max_nightly:
        near_misses += 1 if nightly_rate <= max_nightly * 1.15 else 0
        violations += 0 if nightly_rate <= max_nightly * 1.15 else 1
    if hotel_stars and hotel_stars < hotel_floor:
        near_misses += 1 if hotel_stars >= hotel_floor - 0.5 else 0
        violations += 0 if hotel_stars >= hotel_floor - 0.5 else 1

    if violations:
        return "weak"
    if near_misses:
        return "near_miss"
    return "exact"


def _constraint_checks(
    candidate: CandidateDestination,
    flight_minutes: int | None,
    hotel_stars: float | None,
    hotel_rating: float | None,
    nightly_rate: float,
    constraints: dict,
) -> list[dict]:
    max_flight = constraints.get("max_flight_minutes")
    max_drive = constraints.get("max_drive_minutes")
    max_nightly = constraints.get("max_nightly_rate_usd")
    hotel_floor = constraints.get("hotel_min_stars") or 5
    checks: list[dict] = []

    if max_flight:
        if flight_minutes is None:
            checks.append(_constraint_check("Flight time", "unknown", f"Requested under {max_flight} min; provider did not supply duration."))
        elif flight_minutes <= max_flight:
            checks.append(_constraint_check("Flight time", "pass", f"{flight_minutes} min, within requested {max_flight} min."))
        elif flight_minutes <= max_flight + 45:
            checks.append(_constraint_check("Flight time", "near_miss", f"{flight_minutes} min, above requested {max_flight} min."))
        else:
            checks.append(_constraint_check("Flight time", "fail", f"{flight_minutes} min, above requested {max_flight} min."))

    if max_drive and candidate.drive_minutes:
        if candidate.drive_minutes <= max_drive:
            checks.append(_constraint_check("Drive time", "pass", f"{candidate.drive_minutes} min, within requested {max_drive} min."))
        elif candidate.drive_minutes <= max_drive + 45:
            checks.append(_constraint_check("Drive time", "near_miss", f"{candidate.drive_minutes} min, above requested {max_drive} min."))
        else:
            checks.append(_constraint_check("Drive time", "fail", f"{candidate.drive_minutes} min, above requested {max_drive} min."))

    if hotel_stars is None:
        checks.append(_constraint_check("Hotel class", "unknown", f"Requested {hotel_floor} star; provider did not supply class."))
    elif hotel_stars >= hotel_floor:
        checks.append(_constraint_check("Hotel class", "pass", f"{hotel_stars:g} star equivalent, meets requested {hotel_floor} star."))
    elif hotel_stars >= hotel_floor - 0.5:
        checks.append(_constraint_check("Hotel class", "near_miss", f"{hotel_stars:g} star equivalent, near requested {hotel_floor} star."))
    else:
        checks.append(_constraint_check("Hotel class", "fail", f"{hotel_stars:g} star equivalent, below requested {hotel_floor} star."))

    if max_nightly:
        if nightly_rate <= max_nightly:
            checks.append(_constraint_check("Nightly price", "pass", f"${nightly_rate:,.0f}, within requested ${max_nightly:,.0f}."))
        elif nightly_rate <= max_nightly * 1.15:
            checks.append(_constraint_check("Nightly price", "near_miss", f"${nightly_rate:,.0f}, above requested ${max_nightly:,.0f}."))
        else:
            checks.append(_constraint_check("Nightly price", "fail", f"${nightly_rate:,.0f}, above requested ${max_nightly:,.0f}."))

    if hotel_rating is not None:
        if hotel_rating >= 4.7:
            checks.append(_constraint_check("Guest rating", "pass", f"{hotel_rating:g}, highly rated."))
        elif hotel_rating >= 4.4:
            checks.append(_constraint_check("Guest rating", "near_miss", f"{hotel_rating:g}, solid but not top tier."))
        else:
            checks.append(_constraint_check("Guest rating", "fail", f"{hotel_rating:g}, below high-rating threshold."))

    return checks


def _constraint_check(label: str, status: str, detail: str) -> dict:
    return {"label": label, "status": status, "detail": detail}


def _hotel_is_usable(option: BookingOption, constraints: dict) -> bool:
    if option.source_environment == "mock":
        return True

    hotel_floor = constraints.get("hotel_min_stars") or 5
    quality = _hotel_quality(option, hotel_floor)
    if quality >= hotel_floor:
        return True
    if constraints.get("include_near_misses") and quality >= hotel_floor - 0.5:
        return True
    return False


def _hotel_quality(option: BookingOption, hotel_floor: int) -> float:
    stars = _float_detail(option, "stars")
    rating = _float_detail(option, "guest_rating")
    provider = option.source_provider or ""

    if provider == "serpapi_google_hotels" and hotel_floor >= 5:
        if stars and stars >= 5 and rating and rating >= 4.5:
            return 5.0
        if rating and rating >= 4.7:
            return 4.5
        if stars and stars >= 5:
            return 4.0
        return rating or 0

    if stars:
        return stars
    if rating and rating >= 4.7:
        return 4.5
    if rating and rating >= 4.4:
        return 4.0
    return rating or 0


def _discovery_sort_key(option: BookingOption) -> tuple:
    fit = str(option.details.get("constraint_fit", "weak"))
    fit_rank = {"exact": 0, "near_miss": 1, "weak": 2}.get(fit, 2)
    travel_minutes = option.details.get("travel_minutes")
    return (
        fit_rank,
        int(travel_minutes) if isinstance(travel_minutes, int) else 9999,
        -option.provider_confidence,
        option.cash_price_usd,
    )


def _parse_time_limit_minutes(text: str, *keywords: str) -> int | None:
    for keyword in keywords:
        pattern = rf"(?:{keyword}\w*[^.,;]{{0,40}}(?:under|less than|no more than|not more than|do not want[^.,;]*more than|don't want[^.,;]*more than|more than|within|maximum|max)?\s*)(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|minute|minutes|min|mins)"
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            return int(value * 60) if unit.startswith(("hour", "hr")) else int(value)
    return None


def _parse_nightly_rate(text: str) -> float | None:
    match = re.search(r"(?:under|less than|below|max|maximum|not more than)\s*\$?([\d,]+)(?:\s*(?:a|per)\s*night|/night| nightly)?", text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _parse_star_floor(text: str) -> int | None:
    match = re.search(r"(\d)\s*(?:star|stars)", text)
    if not match:
        return None
    return max(1, min(5, int(match.group(1))))


def _option_duration_minutes(option: BookingOption) -> int | None:
    duration = option.details.get("duration")
    if isinstance(duration, str):
        return _duration_text_to_minutes(duration)
    for note in option.notes:
        if "duration" in note.lower():
            parsed = _duration_text_to_minutes(note)
            if parsed:
                return parsed
    return None


def _duration_text_to_minutes(text: str) -> int | None:
    hours = re.search(r"(\d+)\s*h", text)
    minutes = re.search(r"(\d+)\s*m", text)
    if hours or minutes:
        return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)
    iso = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?", text)
    if iso:
        return int(iso.group(1) or 0) * 60 + int(iso.group(2) or 0)
    return None


def _float_detail(option: BookingOption, key: str) -> float | None:
    value = option.details.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _dedupe_provider_statuses(statuses: list[ProviderStatus]) -> list[ProviderStatus]:
    by_key: dict[tuple[str, str, str], ProviderStatus] = {}
    for status in statuses:
        key = (status.provider, status.category, status.environment)
        existing = by_key.get(key)
        if not existing:
            by_key[key] = status
            continue
        by_key[key] = existing.model_copy(
            update={
                "result_count": existing.result_count + status.result_count,
                "latency_ms": existing.latency_ms + status.latency_ms,
                "warnings": [*existing.warnings, *status.warnings][:5],
            }
        )
    return list(by_key.values())
