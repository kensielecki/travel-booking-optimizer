from __future__ import annotations

import re
from dataclasses import dataclass
from app.core.intent_parser import enrich_search_from_intent
from app.core.live_travel_search import search_flights_across_providers, search_hotels_across_providers
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


def discover_trip_options(request: TripDiscoveryRequest) -> OptimizationResponse:
    constraints = _discovery_constraints(request)
    candidates = _candidate_destinations(constraints, request.max_destinations, request.include_near_misses)

    options: list[BookingOption] = []
    provider_statuses: list[ProviderStatus] = []
    warnings: list[str] = []

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
            "warnings": warnings[:12],
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


def _candidate_destinations(constraints: dict, max_destinations: int, include_near_misses: bool) -> list[CandidateDestination]:
    max_flight = constraints.get("max_flight_minutes")
    max_drive = constraints.get("max_drive_minutes")
    scored: list[tuple[int, CandidateDestination]] = []

    for candidate in BAY_AREA_CANDIDATES:
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
        stars = _float_detail(option, "stars") or hotel_floor
        nightly = option.cash_price_usd
        star_gap = max(0, hotel_floor - stars)
        price_gap = max(0, nightly - max_nightly) if max_nightly else 0
        return (star_gap, price_gap, nightly, -option.provider_confidence)

    usable = [option for option in options if option.cash_price_usd > 0]
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
    hotel_stars = _float_detail(hotel, "stars")
    nightly_rate = hotel.cash_price_usd
    constraint_fit = _constraint_fit(candidate, flight_minutes, hotel_stars, nightly_rate, constraints)
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
