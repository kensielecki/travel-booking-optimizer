from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models.domain import (
    AggregatedTravelSearchResponse,
    BookingOption,
    BookingType,
    ProviderReadiness,
    ProviderStatus,
    TravelSearchRequest,
    TravelSearchResponse,
)

AIRPORT_ALIASES = {
    "san francisco": "SFO",
    "sfo": "SFO",
    "new york": "NYC",
    "nyc": "NYC",
    "san diego": "SAN",
    "san": "SAN",
    "los angeles": "LAX",
    "la": "LAX",
    "lax": "LAX",
}


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


_load_local_env()


def search_live_flights(search: TravelSearchRequest) -> TravelSearchResponse:
    return _to_legacy_response(search_flights_across_providers(search), provider="aggregated_flights")


def search_flights_across_providers(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    results = [
        _search_serpapi_google_flights(search),
        _search_kiwi_tequila_flights(search),
        _search_duffel(search),
        _search_amadeus_flights(search),
    ]
    if not any(response.booking_options for response in results):
        results.append(_mock_flight_response(search))
    return _aggregate_results(results)


def search_live_hotels(search: TravelSearchRequest) -> TravelSearchResponse:
    return _to_legacy_response(search_hotels_across_providers(search), provider="aggregated_hotels")


def search_hotels_across_providers(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    results = [_search_serpapi_google_hotels(search), _search_liteapi_hotels(search), _search_amadeus_hotels(search)]
    if not any(response.booking_options for response in results):
        results.append(_mock_hotel_response(search))
    return _aggregate_results(results)


def search_live_trip(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    text = search.raw_intent.lower()
    wants_flights = _mentions_any(text, ["flight", "fly", "airfare", "airport", "direct"])
    wants_hotels = _mentions_any(text, ["hotel", "stay", "room", "lodging", "4 star", "resort"])

    if not wants_flights and not wants_hotels:
        wants_flights = True
        wants_hotels = True

    responses: list[AggregatedTravelSearchResponse] = []
    if wants_flights:
        responses.append(search_flights_across_providers(search))
    if wants_hotels:
        responses.append(search_hotels_across_providers(search))
    return _aggregate_results(responses)


def get_provider_readiness() -> list[ProviderReadiness]:
    serpapi_configured = _env_is_set("SERPAPI_API_KEY")
    duffel_token = os.getenv("DUFFEL_API_TOKEN", "")
    liteapi_key = _liteapi_api_key()
    liteapi_configured = bool(liteapi_key.strip())
    liteapi_environment = _liteapi_environment(liteapi_key)
    kiwi_configured = _env_is_set("KIWI_TEQUILA_API_KEY")
    amadeus_configured = _env_is_set("AMADEUS_CLIENT_ID") and _env_is_set("AMADEUS_CLIENT_SECRET")
    maps_configured = _env_is_set("GOOGLE_MAPS_API_KEY")

    return [
        ProviderReadiness(
            provider="serpapi_google_flights",
            category="flight",
            configured=serpapi_configured,
            environment="production" if serpapi_configured else "unknown",
            v1_role="Production flight market-price signal from Google Flights.",
            next_step=(
                "Use as the baseline flight discovery source."
                if serpapi_configured
                else "Add SERPAPI_API_KEY to enable live Google Flights search."
            ),
        ),
        ProviderReadiness(
            provider="duffel",
            category="flight",
            configured=bool(duffel_token),
            environment=_duffel_environment(duffel_token),
            v1_role="Flight offer and future booking/order path.",
            next_step=(
                "Activate Duffel live access when booking workflow is ready."
                if duffel_token.startswith("duffel_test_")
                else "Use live token for bookable flight offers."
                if duffel_token.startswith("duffel_live_")
                else "Add DUFFEL_API_TOKEN to enable Duffel flight offers."
            ),
        ),
        ProviderReadiness(
            provider="kiwi_tequila_flights",
            category="flight",
            configured=kiwi_configured,
            environment="production" if kiwi_configured else "unknown",
            v1_role="Secondary flight-search breadth and price comparison.",
            next_step=(
                "Use as a second production flight source."
                if kiwi_configured
                else "Add KIWI_TEQUILA_API_KEY if we want another self-serve flight source."
            ),
        ),
        ProviderReadiness(
            provider="serpapi_google_hotels",
            category="hotel",
            configured=serpapi_configured,
            environment="production" if serpapi_configured else "unknown",
            v1_role="Production hotel market-price signal from Google Hotels.",
            next_step=(
                "Use as the baseline hotel discovery source."
                if serpapi_configured
                else "Add SERPAPI_API_KEY to enable live Google Hotels search."
            ),
        ),
        ProviderReadiness(
            provider="liteapi_hotels",
            category="hotel",
            configured=liteapi_configured,
            environment=liteapi_environment if liteapi_configured else "unknown",
            v1_role="Hotel rates and future booking path through LiteAPI/Nuitee.",
            next_step=(
                "Switch to a production LiteAPI key once LiteAPI approves live access."
                if liteapi_configured and liteapi_environment == "sandbox"
                else "Use as a production hotel rate source."
                if liteapi_configured
                else "Add LITEAPI_API_KEY or LITEAPI_PRODUCTION_API_KEY to enable LiteAPI hotel rates."
            ),
        ),
        ProviderReadiness(
            provider="google_maps",
            category="location",
            configured=maps_configured,
            environment="production" if maps_configured else "unknown",
            v1_role="Hotel distance, drive/transit time, and place proximity scoring.",
            next_step=(
                "Add travel-time scoring for hotel constraints."
                if maps_configured
                else "Add GOOGLE_MAPS_API_KEY when we are ready to score hotels by travel time."
            ),
        ),
        ProviderReadiness(
            provider="amadeus",
            category="flight",
            configured=amadeus_configured,
            environment="sandbox" if amadeus_configured else "unknown",
            v1_role="Deferred flight/hotel fallback; not a V1 dependency.",
            next_step="Keep deferred unless enterprise/self-serve access becomes worthwhile.",
        ),
    ]


def _search_duffel(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    token = os.getenv("DUFFEL_API_TOKEN")
    if not token:
        warning = "DUFFEL_API_TOKEN is not configured; Duffel flight search skipped."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="duffel",
                    category="flight",
                    status="disabled",
                    environment="sandbox",
                    confidence=0.45,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )

    try:
        response = _duffel_offer_request(search, token)
        offers = response.get("data", {}).get("offers", [])[: search.max_results]
        options = [_duffel_offer_to_option(offer, search) for offer in offers]
        return AggregatedTravelSearchResponse(
            booking_options=options,
            provider_statuses=[
                ProviderStatus(
                    provider="duffel",
                    category="flight",
                    status="live",
                    environment="sandbox" if token.startswith("duffel_test_") else "production",
                    confidence=0.55 if token.startswith("duffel_test_") else 0.9,
                    latency_ms=_elapsed_ms(started),
                    result_count=len(options),
                )
            ],
        )
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
        warning = f"Duffel flight search failed: {error}."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="duffel",
                    category="flight",
                    status="failed",
                    environment="sandbox" if token.startswith("duffel_test_") else "production",
                    confidence=0.2,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )


def _search_serpapi_google_flights(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        warning = "SERPAPI_API_KEY is not configured; SerpApi Google Flights search skipped."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="serpapi_google_flights",
                    category="flight",
                    status="disabled",
                    environment="production",
                    confidence=0.0,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )

    try:
        response = _serpapi_google_flights(search, api_key)
        flight_results = [
            *response.get("best_flights", []),
            *response.get("other_flights", []),
        ][: search.max_results]
        options = [_serpapi_flight_to_option(flight_result, search) for flight_result in flight_results]
        return AggregatedTravelSearchResponse(
            booking_options=options,
            provider_statuses=[
                ProviderStatus(
                    provider="serpapi_google_flights",
                    category="flight",
                    status="live",
                    environment="production",
                    confidence=0.8,
                    latency_ms=_elapsed_ms(started),
                    result_count=len(options),
                )
            ],
        )
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
        warning = f"SerpApi Google Flights search failed: {error}."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="serpapi_google_flights",
                    category="flight",
                    status="failed",
                    environment="production",
                    confidence=0.2,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )


def _search_kiwi_tequila_flights(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    api_key = os.getenv("KIWI_TEQUILA_API_KEY")
    if not api_key:
        warning = "KIWI_TEQUILA_API_KEY is not configured; Kiwi Tequila flight search skipped."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="kiwi_tequila_flights",
                    category="flight",
                    status="disabled",
                    environment="production",
                    confidence=0.0,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )

    try:
        response = _kiwi_tequila_search(search, api_key)
        flight_results = response.get("data", [])[: search.max_results]
        options = [_kiwi_flight_to_option(flight_result, search) for flight_result in flight_results]
        return AggregatedTravelSearchResponse(
            booking_options=options,
            provider_statuses=[
                ProviderStatus(
                    provider="kiwi_tequila_flights",
                    category="flight",
                    status="live",
                    environment="production",
                    confidence=0.75,
                    latency_ms=_elapsed_ms(started),
                    result_count=len(options),
                )
            ],
        )
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
        warning = f"Kiwi Tequila flight search failed: {error}."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="kiwi_tequila_flights",
                    category="flight",
                    status="failed",
                    environment="production",
                    confidence=0.2,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )


def _search_serpapi_google_hotels(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        warning = "SERPAPI_API_KEY is not configured; SerpApi Google Hotels search skipped."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="serpapi_google_hotels",
                    category="hotel",
                    status="disabled",
                    environment="production",
                    confidence=0.0,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )

    try:
        response = _serpapi_google_hotels(search, api_key)
        properties = response.get("properties", [])[: search.max_results]
        options = [_serpapi_property_to_option(property_result) for property_result in properties]
        return AggregatedTravelSearchResponse(
            booking_options=options,
            provider_statuses=[
                ProviderStatus(
                    provider="serpapi_google_hotels",
                    category="hotel",
                    status="live",
                    environment="production",
                    confidence=0.8,
                    latency_ms=_elapsed_ms(started),
                    result_count=len(options),
                )
            ],
        )
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
        warning = f"SerpApi hotel search failed: {error}."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="serpapi_google_hotels",
                    category="hotel",
                    status="failed",
                    environment="production",
                    confidence=0.2,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )


def _search_amadeus_hotels(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        warning = "AMADEUS_CLIENT_ID/AMADEUS_CLIENT_SECRET are not configured; Amadeus hotel search skipped."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="amadeus_hotel_search",
                    category="hotel",
                    status="disabled",
                    environment="unknown",
                    confidence=0.0,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )

    try:
        access_token = _amadeus_access_token(client_id, client_secret)
        hotel_list = _amadeus_hotels_by_city(search, access_token)
        hotel_ids = [
            hotel.get("hotelId")
            for hotel in hotel_list.get("data", [])
            if isinstance(hotel.get("hotelId"), str)
        ][: max(search.max_results * 3, 5)]
        if not hotel_ids:
            return AggregatedTravelSearchResponse(
                booking_options=[],
                provider_statuses=[
                    ProviderStatus(
                        provider="amadeus_hotel_search",
                        category="hotel",
                        status="live",
                        environment="sandbox",
                        confidence=0.45,
                        latency_ms=_elapsed_ms(started),
                        result_count=0,
                        warnings=["Amadeus hotel list returned no hotel IDs for this destination."],
                    )
                ],
                warnings=["Amadeus hotel list returned no hotel IDs for this destination."],
            )

        offers_response = _amadeus_hotel_offers(search, access_token, hotel_ids)
        hotel_results = offers_response.get("data", [])[: search.max_results]
        options = [_amadeus_hotel_to_option(hotel_result) for hotel_result in hotel_results]
        return AggregatedTravelSearchResponse(
            booking_options=options,
            provider_statuses=[
                ProviderStatus(
                    provider="amadeus_hotel_search",
                    category="hotel",
                    status="live",
                    environment="sandbox",
                    confidence=0.45,
                    latency_ms=_elapsed_ms(started),
                    result_count=len(options),
                )
            ],
        )
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
        warning = f"Amadeus hotel search failed: {error}."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="amadeus_hotel_search",
                    category="hotel",
                    status="failed",
                    environment="unknown",
                    confidence=0.2,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )


def _search_liteapi_hotels(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    api_key = _liteapi_api_key()
    if not api_key:
        warning = "LiteAPI API key is not configured; LiteAPI hotel search skipped."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="liteapi_hotels",
                    category="hotel",
                    status="disabled",
                    environment="sandbox",
                    confidence=0.45,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )

    try:
        response = _liteapi_hotel_rates(search, api_key)
        hotel_results = _liteapi_result_items(response)[: search.max_results]
        hotel_index = _liteapi_hotel_index(response)
        options = [_liteapi_hotel_to_option(hotel_result, hotel_index) for hotel_result in hotel_results]
        environment = _liteapi_environment(api_key)
        warnings = ["LiteAPI response is sandbox inventory."] if environment == "sandbox" else []
        return AggregatedTravelSearchResponse(
            booking_options=options,
            provider_statuses=[
                ProviderStatus(
                    provider="liteapi_hotels",
                    category="hotel",
                    status="live",
                    environment=environment,
                    confidence=0.55 if environment == "sandbox" else 0.85,
                    latency_ms=_elapsed_ms(started),
                    result_count=len(options),
                    warnings=warnings,
                )
            ],
            warnings=warnings,
        )
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
        warning = f"LiteAPI hotel search failed: {error}."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="liteapi_hotels",
                    category="hotel",
                    status="failed",
                    environment="unknown",
                    confidence=0.2,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )


def _duffel_offer_request(search: TravelSearchRequest, token: str) -> dict:
    departure_date = _date_or_default(search.departure_date, days=45)
    origin = _airport_code(search.origin or "SFO")
    destination = _airport_code(search.destination)
    slices = [
        {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date.isoformat(),
        }
    ]
    if search.return_date:
        slices.append(
            {
                "origin": destination,
                "destination": origin,
                "departure_date": search.return_date.isoformat(),
            }
        )

    payload = {
        "data": {
            "slices": slices,
            "passengers": [{"type": "adult"} for _ in range(search.adults)],
            "cabin_class": "economy",
        }
    }
    if search.direct_only:
        payload["data"]["max_connections"] = 0

    request = Request(
        "https://api.duffel.com/air/offer_requests?return_offers=true",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Duffel-Version": "v2",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _search_amadeus_flights(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        warning = "AMADEUS_CLIENT_ID/AMADEUS_CLIENT_SECRET are not configured; Amadeus flight search skipped."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="amadeus_flight_offers",
                    category="flight",
                    status="disabled",
                    environment="unknown",
                    confidence=0.0,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )

    try:
        access_token = _amadeus_access_token(client_id, client_secret)
        response = _amadeus_flight_offers(search, access_token)
        offers = response.get("data", [])[: search.max_results]
        options = [_amadeus_offer_to_option(offer, search, response.get("dictionaries", {})) for offer in offers]
        return AggregatedTravelSearchResponse(
            booking_options=options,
            provider_statuses=[
                ProviderStatus(
                    provider="amadeus_flight_offers",
                    category="flight",
                    status="live",
                    environment="sandbox",
                    confidence=0.45,
                    latency_ms=_elapsed_ms(started),
                    result_count=len(options),
                )
            ],
        )
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
        warning = f"Amadeus flight search failed: {error}."
        return AggregatedTravelSearchResponse(
            booking_options=[],
            provider_statuses=[
                ProviderStatus(
                    provider="amadeus_flight_offers",
                    category="flight",
                    status="failed",
                    environment="unknown",
                    confidence=0.2,
                    latency_ms=_elapsed_ms(started),
                    result_count=0,
                    warnings=[warning],
                )
            ],
            warnings=[warning],
        )


def _amadeus_access_token(client_id: str, client_secret: str) -> str:
    data = urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    request = Request(
        "https://test.api.amadeus.com/v1/security/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise ValueError("Amadeus token response did not include access_token")
    return token


def _amadeus_flight_offers(search: TravelSearchRequest, access_token: str) -> dict:
    params = {
        "originLocationCode": _airport_code(search.origin or "SFO"),
        "destinationLocationCode": _airport_code(search.destination),
        "departureDate": _date_or_default(search.departure_date, days=45).isoformat(),
        "adults": search.adults,
        "currencyCode": "USD",
        "nonStop": str(search.direct_only).lower(),
        "max": min(search.max_results, 20),
    }
    if search.return_date:
        params["returnDate"] = search.return_date.isoformat()

    request = Request(
        f"https://test.api.amadeus.com/v2/shopping/flight-offers?{urlencode(params)}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.amadeus+json",
        },
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _amadeus_hotels_by_city(search: TravelSearchRequest, access_token: str) -> dict:
    params = {
        "cityCode": _airport_code(search.destination),
        "radius": 25,
        "radiusUnit": "KM",
        "hotelSource": "ALL",
    }
    if search.hotel_min_stars:
        params["ratings"] = ",".join(str(rating) for rating in range(search.hotel_min_stars, 6))

    request = Request(
        f"https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city?{urlencode(params)}",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _amadeus_hotel_offers(search: TravelSearchRequest, access_token: str, hotel_ids: list[str]) -> dict:
    params = {
        "hotelIds": ",".join(hotel_ids),
        "adults": search.adults,
        "roomQuantity": search.rooms,
        "checkInDate": _date_or_default(search.check_in_date or search.departure_date, days=45).isoformat(),
        "checkOutDate": _date_or_default(search.check_out_date or search.return_date, days=47).isoformat(),
        "currency": "USD",
        "bestRateOnly": "true",
    }

    request = Request(
        f"https://test.api.amadeus.com/v3/shopping/hotel-offers?{urlencode(params)}",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _serpapi_google_hotels(search: TravelSearchRequest, api_key: str) -> dict:
    params = {
        "engine": "google_hotels",
        "q": search.destination,
        "check_in_date": _date_or_default(search.check_in_date or search.departure_date, days=45).isoformat(),
        "check_out_date": _date_or_default(search.check_out_date or search.return_date, days=47).isoformat(),
        "adults": search.adults,
        "currency": "USD",
        "gl": "us",
        "hl": "en",
        "api_key": api_key,
    }
    if search.hotel_min_stars:
        params["hotel_class"] = search.hotel_min_stars
    if search.budget_usd:
        params["max_price"] = round(search.budget_usd)

    request = Request(f"https://serpapi.com/search?{urlencode(params)}", method="GET")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _google_flights_search_url(search: TravelSearchRequest) -> str:
    query_parts = [
        "Google Flights",
        search.origin or "",
        search.destination,
        search.departure_date.isoformat() if search.departure_date else "",
        search.return_date.isoformat() if search.return_date else "",
    ]
    return f"https://www.google.com/travel/flights?{urlencode({'q': ' '.join(part for part in query_parts if part)})}"


def _google_hotels_search_url(hotel_name: str) -> str:
    return f"https://www.google.com/travel/hotels?{urlencode({'q': hotel_name})}"


def _liteapi_hotel_rates(search: TravelSearchRequest, api_key: str) -> dict:
    payload = {
        "checkin": _date_or_default(search.check_in_date or search.departure_date, days=45).isoformat(),
        "checkout": _date_or_default(search.check_out_date or search.return_date, days=47).isoformat(),
        "currency": "USD",
        "guestNationality": "US",
        "occupancies": [{"adults": search.adults}],
        "iataCode": _airport_code(search.destination),
        "limit": search.max_results,
        "timeout": 8,
        "maxRatesPerHotel": 1,
        "includeHotelData": True,
    }
    if search.hotel_min_stars:
        payload["starRating"] = [float(stars) for stars in range(search.hotel_min_stars, 6)]

    request = Request(
        "https://api.liteapi.travel/v3.0/hotels/rates",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8")
    if not body:
        return {"data": []}
    return json.loads(body)


def _serpapi_google_flights(search: TravelSearchRequest, api_key: str) -> dict:
    params = {
        "engine": "google_flights",
        "departure_id": _airport_code(search.origin or "SFO"),
        "arrival_id": _airport_code(search.destination),
        "outbound_date": _date_or_default(search.departure_date, days=45).isoformat(),
        "type": "1" if search.return_date else "2",
        "adults": search.adults,
        "travel_class": "1",
        "currency": "USD",
        "gl": "us",
        "hl": "en",
        "api_key": api_key,
    }
    if search.return_date:
        params["return_date"] = search.return_date.isoformat()
    if search.direct_only:
        params["stops"] = "1"

    request = Request(f"https://serpapi.com/search?{urlencode(params)}", method="GET")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _kiwi_tequila_search(search: TravelSearchRequest, api_key: str) -> dict:
    departure_date = _date_or_default(search.departure_date, days=45)
    params = {
        "fly_from": _airport_code(search.origin or "SFO"),
        "fly_to": _airport_code(search.destination),
        "date_from": departure_date.strftime("%d/%m/%Y"),
        "date_to": departure_date.strftime("%d/%m/%Y"),
        "adults": search.adults,
        "curr": "USD",
        "limit": search.max_results,
        "sort": "price",
    }
    if search.return_date:
        params["return_from"] = search.return_date.strftime("%d/%m/%Y")
        params["return_to"] = search.return_date.strftime("%d/%m/%Y")
    if search.direct_only:
        params["max_stopovers"] = 0

    request = Request(
        f"https://api.tequila.kiwi.com/v2/search?{urlencode(params)}",
        headers={"apikey": api_key, "Accept": "application/json"},
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _duffel_offer_to_option(offer: dict, search: TravelSearchRequest) -> BookingOption:
    total_amount = float(offer.get("total_amount") or 0)
    currency = offer.get("total_currency", "USD")
    slices = offer.get("slices", [])
    segments = [segment for slice_item in slices for segment in slice_item.get("segments", [])]
    carrier = offer.get("owner", {}).get("name") or (segments[0].get("marketing_carrier", {}).get("name") if segments else "Flight")
    stops = max(0, len(segments) - len(slices))
    notes = [
        f"Live Duffel offer in {currency}.",
        f"{stops} stop{'s' if stops != 1 else ''}.",
    ]
    if slices:
        notes.append(f"Duration: {', '.join(slice_item.get('duration', 'unknown') for slice_item in slices)}.")

    slice_details = [
        {
            "origin": slice_item.get("origin", {}).get("iata_code") or slice_item.get("origin", {}).get("name"),
            "destination": slice_item.get("destination", {}).get("iata_code") or slice_item.get("destination", {}).get("name"),
            "duration": slice_item.get("duration"),
            "segments": [
                {
                    "airline": segment.get("marketing_carrier", {}).get("name"),
                    "flight_number": segment.get("marketing_carrier_flight_number"),
                    "origin": segment.get("origin", {}).get("iata_code") or segment.get("origin", {}).get("name"),
                    "destination": segment.get("destination", {}).get("iata_code") or segment.get("destination", {}).get("name"),
                    "departing_at": segment.get("departing_at"),
                    "arriving_at": segment.get("arriving_at"),
                }
                for segment in slice_item.get("segments", [])
            ],
        }
        for slice_item in slices
    ]

    return BookingOption(
        label=f"{carrier} flight offer to {search.destination}",
        booking_type=BookingType.cash,
        merchant=carrier,
        cash_price_usd=total_amount,
        simplicity=5 if stops == 0 else 3,
        source_provider="duffel",
        source_environment="sandbox" if os.getenv("DUFFEL_API_TOKEN", "").startswith("duffel_test_") else "production",
        provider_confidence=0.55 if os.getenv("DUFFEL_API_TOKEN", "").startswith("duffel_test_") else 0.9,
        provider_reference=offer.get("id"),
        booking_url=_google_flights_search_url(search),
        details={
            "kind": "flight",
            "currency": currency,
            "expires_at": offer.get("expires_at"),
            "slices": slice_details,
        },
        notes=notes,
    )


def _amadeus_offer_to_option(offer: dict, search: TravelSearchRequest, dictionaries: dict) -> BookingOption:
    price = offer.get("price", {})
    itineraries = offer.get("itineraries", [])
    segments = [segment for itinerary in itineraries for segment in itinerary.get("segments", [])]
    validating_airlines = offer.get("validatingAirlineCodes") or []
    carrier_code = validating_airlines[0] if validating_airlines else (
        segments[0].get("carrierCode") if segments else "Flight"
    )
    carrier = dictionaries.get("carriers", {}).get(carrier_code, carrier_code)
    stops = max(0, len(segments) - len(itineraries))
    duration_notes = [
        itinerary.get("duration", "unknown")
        for itinerary in itineraries
        if itinerary.get("duration")
    ]
    notes = [
        "Live Amadeus Flight Offers Search result.",
        f"{stops} stop{'s' if stops != 1 else ''}.",
    ]
    if duration_notes:
        notes.append(f"Duration: {', '.join(duration_notes)}.")

    return BookingOption(
        label=f"{carrier} flight offer to {search.destination}",
        booking_type=BookingType.cash,
        merchant=carrier,
        cash_price_usd=float(price.get("grandTotal") or price.get("total") or 0),
        simplicity=5 if stops == 0 else 3,
        source_provider="amadeus_flight_offers",
        source_environment="sandbox",
        provider_confidence=0.45,
        notes=notes,
    )


def _serpapi_flight_to_option(flight_result: dict, search: TravelSearchRequest) -> BookingOption:
    segments = flight_result.get("flights", [])
    airlines = _unique_nonempty(segment.get("airline") for segment in segments)
    carrier = airlines[0] if airlines else "Google Flights"
    carrier_label = " + ".join(airlines[:2]) if airlines else carrier
    if len(airlines) > 2:
        carrier_label = f"{carrier_label} + {len(airlines) - 2} more"

    stops = max(0, len(segments) - 1)
    duration = _format_minutes(flight_result.get("total_duration"))
    departure = _airport_time_label(segments[0].get("departure_airport")) if segments else None
    arrival = _airport_time_label(segments[-1].get("arrival_airport")) if segments else None

    notes = [
        "Live Google Flights result via SerpApi.",
        f"{stops} stop{'s' if stops != 1 else ''}.",
    ]
    if duration:
        notes.append(f"Total duration: {duration}.")
    if departure and arrival:
        notes.append(f"{departure} to {arrival}.")
    if search.latest_arrival_time:
        arrival_time = _flight_arrival_time(flight_result)
        if arrival_time and arrival_time <= search.latest_arrival_time:
            notes.append(f"Matches arrival preference by {search.latest_arrival_time.strftime('%H:%M')}.")
        elif arrival_time:
            notes.append(f"Arrives after preferred {search.latest_arrival_time.strftime('%H:%M')} window.")

    segment_details = [
        {
            "airline": segment.get("airline"),
            "flight_number": segment.get("flight_number"),
            "airplane": segment.get("airplane"),
            "travel_class": segment.get("travel_class"),
            "departure_airport": segment.get("departure_airport", {}).get("name"),
            "departure_time": segment.get("departure_airport", {}).get("time"),
            "arrival_airport": segment.get("arrival_airport", {}).get("name"),
            "arrival_time": segment.get("arrival_airport", {}).get("time"),
            "duration": _format_minutes(segment.get("duration")),
        }
        for segment in segments
    ]

    return BookingOption(
        label=f"{carrier_label} flight to {search.destination} via Google Flights",
        booking_type=BookingType.cash,
        merchant=carrier,
        cash_price_usd=_extract_price(flight_result.get("price")) or 0,
        simplicity=_flight_simplicity(stops, flight_result, search),
        source_provider="serpapi_google_flights",
        source_environment="production",
        provider_confidence=0.8,
        provider_reference=flight_result.get("booking_token") or flight_result.get("departure_token"),
        booking_url=_google_flights_search_url(search),
        details={
            "kind": "flight",
            "stops": stops,
            "duration": duration,
            "segments": segment_details,
        },
        notes=notes,
    )


def _kiwi_flight_to_option(flight_result: dict, search: TravelSearchRequest) -> BookingOption:
    route = flight_result.get("route", [])
    airlines = _unique_nonempty(flight_result.get("airlines", []))
    carrier = airlines[0] if airlines else "Kiwi"
    stops = max(0, len(route) - 1)
    duration_seconds = flight_result.get("duration", {}).get("total")
    duration = _format_seconds(duration_seconds)
    notes = [
        "Live Kiwi Tequila flight result.",
        f"{stops} stop{'s' if stops != 1 else ''}.",
    ]
    if duration:
        notes.append(f"Total duration: {duration}.")
    if route:
        first = route[0]
        last = route[-1]
        notes.append(f"{first.get('cityFrom', first.get('flyFrom', 'Origin'))} to {last.get('cityTo', last.get('flyTo', 'Destination'))}.")

    return BookingOption(
        label=f"{carrier} flight to {search.destination} via Kiwi",
        booking_type=BookingType.cash,
        merchant=carrier,
        cash_price_usd=float(flight_result.get("price") or 0),
        simplicity=5 if stops == 0 else 3 if stops == 1 else 2,
        source_provider="kiwi_tequila_flights",
        source_environment="production",
        provider_confidence=0.75,
        provider_reference=flight_result.get("id"),
        booking_url=flight_result.get("deep_link"),
        details={
            "kind": "flight",
            "stops": stops,
            "duration": duration,
            "route": [
                {
                    "airline": item.get("airline"),
                    "flight_number": item.get("flight_no"),
                    "origin": item.get("flyFrom"),
                    "destination": item.get("flyTo"),
                    "local_departure": item.get("local_departure"),
                    "local_arrival": item.get("local_arrival"),
                }
                for item in route
            ],
        },
        notes=notes,
    )


def _amadeus_hotel_to_option(hotel_result: dict) -> BookingOption:
    hotel = hotel_result.get("hotel", {})
    offers = hotel_result.get("offers", [])
    offer = offers[0] if offers else {}
    price = offer.get("price", {})
    total = float(price.get("total") or price.get("base") or 0)
    currency = price.get("currency", "USD")
    name = hotel.get("name") or "Amadeus hotel result"
    room = offer.get("room", {})
    room_type = room.get("typeEstimated", {}).get("category")
    notes = [f"Live Amadeus Hotel Search result in {currency}."]
    if room_type:
        notes.append(f"Room category: {room_type}.")
    if offer.get("checkInDate") and offer.get("checkOutDate"):
        notes.append(f"{offer['checkInDate']} to {offer['checkOutDate']}.")

    return BookingOption(
        label=f"{name} via Amadeus Hotels",
        booking_type=BookingType.cash,
        merchant="Amadeus Hotels",
        cash_price_usd=total,
        simplicity=3,
        source_provider="amadeus_hotel_search",
        source_environment="sandbox",
        provider_confidence=0.45,
        notes=notes,
    )


def _liteapi_hotel_to_option(hotel_result: dict, hotel_index: dict[str, dict]) -> BookingOption:
    hotel_id = hotel_result.get("hotelId") or hotel_result.get("id")
    hotel = hotel_index.get(str(hotel_id), {}) if hotel_id else {}
    hotel = hotel or hotel_result.get("hotel") or hotel_result.get("hotelData") or hotel_result
    room_types = hotel_result.get("roomTypes") or hotel_result.get("rooms") or []
    room_type = room_types[0] if room_types and isinstance(room_types[0], dict) else {}
    rates = room_type.get("rates") or hotel_result.get("rates") or []
    rate = rates[0] if rates and isinstance(rates[0], dict) else room_type or hotel_result
    name = hotel.get("name") or hotel_result.get("hotelName") or hotel_result.get("name") or "LiteAPI hotel result"
    price = _liteapi_price(rate) or _liteapi_price(room_type) or _liteapi_price(hotel_result) or 0
    fees = _liteapi_excluded_fees(rate)
    stars = hotel.get("starRating") or hotel.get("stars") or hotel_result.get("starRating")
    rating = hotel.get("rating") or hotel.get("reviewScore") or hotel_result.get("rating")
    room_name = rate.get("name") or room_type.get("name")
    refundable = (rate.get("cancellationPolicies") or {}).get("refundableTag")

    environment = _liteapi_environment(_liteapi_api_key())
    notes = [
        "Sandbox LiteAPI hotel rate result."
        if environment == "sandbox"
        else "Live LiteAPI hotel rate result."
    ]
    if stars:
        notes.append(f"Hotel class: {stars}.")
    if rating:
        notes.append(f"Guest rating: {rating}.")
    if room_name:
        notes.append(f"Room: {room_name}.")
    if refundable:
        notes.append("Refundable rate." if refundable == "RFN" else "Non-refundable rate.")
    if fees:
        notes.append(f"Excludes ${fees:,.2f} in payable-at-property fees.")

    return BookingOption(
        label=f"{name} via LiteAPI",
        booking_type=BookingType.cash,
        merchant="LiteAPI",
        cash_price_usd=float(price),
        fees_usd=fees,
        simplicity=3,
        source_provider="liteapi_hotels",
        source_environment=environment,
        provider_confidence=0.55 if environment == "sandbox" else 0.85,
        provider_reference=str(rate.get("rateId") or rate.get("id") or hotel_id) if (rate.get("rateId") or rate.get("id") or hotel_id) else None,
        booking_url=hotel.get("url") or hotel_result.get("url") or _google_hotels_search_url(name),
        details={
            "kind": "hotel",
            "hotel_id": hotel_id,
            "room": room_name,
            "stars": stars,
            "guest_rating": rating,
            "refundable": refundable == "RFN" if refundable else None,
            "payable_at_property_fees_usd": fees,
            "address": hotel.get("address") or hotel.get("fullAddress"),
        },
        notes=notes,
    )


def _serpapi_property_to_option(property_result: dict) -> BookingOption:
    name = property_result.get("name") or "Hotel result"
    rate = property_result.get("rate_per_night", {})
    total_rate = property_result.get("total_rate", {})
    price = _extract_price(total_rate) or _extract_price(rate) or 0
    stars = property_result.get("extracted_hotel_class") or property_result.get("hotel_class")
    rating = property_result.get("overall_rating")
    notes = ["Live Google Hotels result via SerpApi."]
    if stars:
        notes.append(f"Hotel class: {stars}.")
    if rating:
        notes.append(f"Guest rating: {rating}.")

    return BookingOption(
        label=f"{name} via Google Hotels",
        booking_type=BookingType.cash,
        merchant="Google Hotels",
        cash_price_usd=float(price),
        simplicity=4,
        source_provider="serpapi_google_hotels",
        source_environment="production",
        provider_confidence=0.8,
        provider_reference=property_result.get("property_token") or property_result.get("hotel_id"),
        booking_url=property_result.get("link") or _google_hotels_search_url(name),
        details={
            "kind": "hotel",
            "stars": stars,
            "guest_rating": rating,
            "reviews": property_result.get("reviews"),
            "address": property_result.get("address"),
            "amenities": property_result.get("amenities") or [],
        },
        notes=notes,
    )


def _mock_flight_options(search: TravelSearchRequest) -> list[BookingOption]:
    destination = search.destination
    direct_word = "nonstop " if search.direct_only else ""
    return [
        BookingOption(
            label=f"United {direct_word}cash fare to {destination}",
            booking_type=BookingType.cash,
            merchant="United",
            cash_price_usd=438,
            simplicity=5,
            source_provider="mock_flights",
            source_environment="mock",
            provider_confidence=0.25,
            notes=["Mock flight result. Configure DUFFEL_API_TOKEN for live flight search."],
        ),
        BookingOption(
            label=f"Delta one-stop fare to {destination}",
            booking_type=BookingType.cash,
            merchant="Delta",
            cash_price_usd=372,
            simplicity=3,
            source_provider="mock_flights",
            source_environment="mock",
            provider_confidence=0.25,
            notes=["Mock alternative included because it is materially cheaper."],
        ),
    ]


def _mock_flight_response(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    options = _mock_flight_options(search)
    warning = "No live flight provider returned options; returned deterministic mock flight results."
    return AggregatedTravelSearchResponse(
        booking_options=options,
        provider_statuses=[
            ProviderStatus(
                provider="mock_flights",
                category="flight",
                status="fallback",
                environment="mock",
                confidence=0.25,
                latency_ms=_elapsed_ms(started),
                result_count=len(options),
                warnings=[warning],
            )
        ],
        warnings=[warning],
    )


def _mock_hotel_options(search: TravelSearchRequest) -> list[BookingOption]:
    return [
        BookingOption(
            label="The Beekman, A Thompson Hotel via Google Hotels",
            booking_type=BookingType.cash,
            merchant="Google Hotels",
            cash_price_usd=1507.22,
            simplicity=4,
            source_provider="mock_hotels",
            source_environment="mock",
            provider_confidence=0.25,
            notes=["Mock hotel result. Configure SERPAPI_API_KEY for live hotel search."],
        ),
        BookingOption(
            label="The Langham, New York, Fifth Avenue via Google Hotels",
            booking_type=BookingType.cash,
            merchant="Google Hotels",
            cash_price_usd=1836.10,
            simplicity=4,
            source_provider="mock_hotels",
            source_environment="mock",
            provider_confidence=0.25,
            notes=["Mock hotel result. Configure SERPAPI_API_KEY for live hotel search."],
        ),
    ]


def _mock_hotel_response(search: TravelSearchRequest) -> AggregatedTravelSearchResponse:
    started = time.monotonic()
    options = _mock_hotel_options(search)
    warning = "No live hotel provider returned options; returned deterministic mock hotel results."
    return AggregatedTravelSearchResponse(
        booking_options=options,
        provider_statuses=[
            ProviderStatus(
                provider="mock_hotels",
                category="hotel",
                status="fallback",
                environment="mock",
                confidence=0.25,
                latency_ms=_elapsed_ms(started),
                result_count=len(options),
                warnings=[warning],
            )
        ],
        warnings=[warning],
    )


def _date_or_default(value: date | None, days: int) -> date:
    return value or date.today() + timedelta(days=days)


def _airport_code(value: str) -> str:
    normalized = value.strip().lower()
    return AIRPORT_ALIASES.get(normalized, value.strip().upper()[:3])


def _extract_price(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        extracted = value.get("extracted_lowest") or value.get("extracted_before_taxes_fees") or value.get("extracted_price")
        if isinstance(extracted, (int, float)):
            return float(extracted)
        text = value.get("lowest") or value.get("before_taxes_fees")
    else:
        text = value

    if not isinstance(text, str):
        return None
    digits = "".join(character for character in text if character.isdigit() or character == ".")
    return float(digits) if digits else None


def _liteapi_result_items(response: dict) -> list[dict]:
    data = response.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ["hotels", "results", "rates"]:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    for key in ["hotels", "results", "rates"]:
        value = response.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _liteapi_hotel_index(response: dict) -> dict[str, dict]:
    hotels = response.get("hotels")
    if not isinstance(hotels, list):
        hotels = response.get("data", {}).get("hotels") if isinstance(response.get("data"), dict) else []
    if not isinstance(hotels, list):
        return {}
    return {
        str(hotel.get("id")): hotel
        for hotel in hotels
        if isinstance(hotel, dict) and hotel.get("id")
    }


def _liteapi_price(value: dict) -> float | None:
    retail_rate = value.get("retailRate")
    if isinstance(retail_rate, dict):
        total = retail_rate.get("total")
        if isinstance(total, list) and total and isinstance(total[0], dict):
            extracted = _extract_price(total[0].get("amount"))
            if extracted is not None:
                return extracted
        extracted = _extract_price(retail_rate.get("amount"))
        if extracted is not None:
            return extracted

    for key in ["total", "price", "amount", "netPrice", "retailRate", "commissionableRate"]:
        extracted = _extract_price(value.get(key))
        if extracted is not None:
            return extracted
    pricing = value.get("pricing") or value.get("price")
    if isinstance(pricing, dict):
        for key in ["total", "amount", "value"]:
            extracted = _extract_price(pricing.get(key))
            if extracted is not None:
                return extracted
    return None


def _liteapi_excluded_fees(value: dict) -> float:
    retail_rate = value.get("retailRate")
    if not isinstance(retail_rate, dict):
        return 0
    taxes_and_fees = retail_rate.get("taxesAndFees")
    if not isinstance(taxes_and_fees, list):
        return 0
    return round(
        sum(
            float(fee.get("amount") or 0)
            for fee in taxes_and_fees
            if isinstance(fee, dict) and fee.get("included") is False
        ),
        2,
    )


def _unique_nonempty(values: object) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized or normalized.lower() in seen:
            continue
        unique.append(normalized)
        seen.add(normalized.lower())
    return unique


def _format_minutes(value: object) -> str | None:
    if not isinstance(value, int):
        return None
    hours, minutes = divmod(value, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _format_seconds(value: object) -> str | None:
    if not isinstance(value, int):
        return None
    return _format_minutes(round(value / 60))


def _flight_simplicity(stops: int, flight_result: dict, search: TravelSearchRequest) -> int:
    base = 5 if stops == 0 else 3 if stops == 1 else 2
    if not search.latest_arrival_time:
        return base
    arrival_time = _flight_arrival_time(flight_result)
    if arrival_time and arrival_time > search.latest_arrival_time:
        return max(1, base - 1)
    return base


def _flight_arrival_time(flight_result: dict) -> time | None:
    segments = flight_result.get("flights", [])
    if not segments:
        return None
    arrival = segments[-1].get("arrival_airport", {})
    if not isinstance(arrival, dict):
        return None
    raw_time = arrival.get("time")
    if not isinstance(raw_time, str):
        return None
    for pattern in ("%Y-%m-%d %H:%M", "%I:%M %p"):
        try:
            return datetime.strptime(raw_time, pattern).time()
        except ValueError:
            continue
    return None


def _airport_time_label(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    name = value.get("name")
    time_value = value.get("time")
    if name and time_value:
        return f"{name} at {time_value}"
    if name:
        return str(name)
    return str(time_value) if time_value else None


def _mentions_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _aggregate_results(responses: list[AggregatedTravelSearchResponse]) -> AggregatedTravelSearchResponse:
    options: list[BookingOption] = []
    statuses: list[ProviderStatus] = []
    warnings: list[str] = []

    for response in responses:
        options.extend(response.booking_options)
        statuses.extend(response.provider_statuses)
        warnings.extend(response.warnings)

    return AggregatedTravelSearchResponse(
        booking_options=_dedupe_options(options),
        provider_statuses=statuses,
        warnings=_dedupe_warnings(warnings),
    )


def _dedupe_options(options: list[BookingOption]) -> list[BookingOption]:
    seen: set[str] = set()
    deduped: list[BookingOption] = []

    for option in sorted(options, key=lambda item: item.cash_price_usd):
        key = "|".join(
            [
                option.merchant.lower().strip(),
                option.label.lower().strip(),
                str(round(option.cash_price_usd)),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(option)

    return deduped


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    return list(dict.fromkeys(warnings))


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _env_is_set(name: str) -> bool:
    value = os.getenv(name)
    return bool(value and value.strip())


def _configured_environment(value: str | None, default: str) -> str:
    normalized = (value or default).strip().lower()
    if normalized in {"production", "sandbox", "mock", "unknown"}:
        return normalized
    return default


def _duffel_environment(token: str) -> str:
    if token.startswith("duffel_live_"):
        return "production"
    if token.startswith("duffel_test_"):
        return "sandbox"
    return "unknown" if token else "unknown"


def _liteapi_api_key() -> str:
    production_key = os.getenv("LITEAPI_PRODUCTION_API_KEY", "").strip()
    if production_key:
        return production_key

    legacy_env_value = os.getenv("LITEAPI_ENV", "").strip()
    if legacy_env_value and legacy_env_value.lower() not in {"production", "sandbox", "mock", "unknown"}:
        return legacy_env_value

    return os.getenv("LITEAPI_API_KEY", "").strip()


def _liteapi_environment(api_key: str) -> str:
    configured = _configured_environment(os.getenv("LITEAPI_ENV"), default="production")
    if api_key.startswith("sand_"):
        return "sandbox"
    if api_key:
        return "production"
    return configured


def _to_legacy_response(
    response: AggregatedTravelSearchResponse,
    provider: str,
) -> TravelSearchResponse:
    has_live = any(status.status == "live" for status in response.provider_statuses)
    return TravelSearchResponse(
        provider=provider,
        live=has_live,
        booking_options=response.booking_options,
        warnings=response.warnings,
        provider_statuses=response.provider_statuses,
    )
