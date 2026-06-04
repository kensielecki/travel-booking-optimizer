from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_search_optimize_combines_provider_results_and_offer_credit(monkeypatch) -> None:
    monkeypatch.delenv("DUFFEL_API_TOKEN", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_ENV", raising=False)
    monkeypatch.delenv("LITEAPI_PRODUCTION_API_KEY", raising=False)
    monkeypatch.delenv("KIWI_TEQUILA_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    response = client.post(
        "/travel-search/optimize",
        json={
            "search": {
                "user_id": "11111111-1111-4111-8111-111111111111",
                "raw_intent": "Direct flight and 4 star hotel in San Diego",
                "origin": "SFO",
                "destination": "San Diego",
                "departure_date": "2026-07-24",
                "return_date": "2026-07-26",
                "check_in_date": "2026-07-24",
                "check_out_date": "2026-07-26",
                "direct_only": True,
                "hotel_min_stars": 4,
                "budget_usd": 2000,
            },
            "accounts": [
                {
                    "user_id": "11111111-1111-4111-8111-111111111111",
                    "program": "united",
                    "display_name": "United MileagePlus",
                    "points_balance": 20826,
                }
            ],
            "offers": [
                {
                    "user_id": "11111111-1111-4111-8111-111111111111",
                    "program": "amex_mr",
                    "merchant": "American Express Travel",
                    "description": "Platinum Hotel Credit",
                    "value_usd": 300,
                    "min_spend_usd": 0,
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_statuses"]
    assert {status["provider"] for status in payload["provider_statuses"]} == {
        "serpapi_google_flights",
        "kiwi_tequila_flights",
        "duffel",
        "amadeus_flight_offers",
        "mock_flights",
        "serpapi_google_hotels",
        "liteapi_hotels",
        "amadeus_hotel_search",
        "mock_hotels",
    }
    labels = [recommendation["option"]["label"] for recommendation in payload["recommendations"]]
    assert any(label.startswith("Trip package:") for label in labels)
    assert any("United nonstop cash fare" in label for label in labels)
    assert any("United MileagePlus award alternative" in label for label in labels)
    assert any("The Beekman" in label for label in labels)
    assert any(
        recommendation["option"]["offer_value_usd"] == 300
        for recommendation in payload["recommendations"]
        if "The Beekman" in recommendation["option"]["label"]
    )
    assert any(
        recommendation["option"]["source_provider"] == "trip_package"
        and recommendation["option"]["offer_value_usd"] == 300
        for recommendation in payload["recommendations"]
    )


def test_provider_readiness_endpoint_does_not_run_searches(monkeypatch) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "serpapi")
    monkeypatch.setenv("DUFFEL_API_TOKEN", "duffel_live_example")
    monkeypatch.setenv("LITEAPI_API_KEY", "liteapi")
    monkeypatch.setenv("LITEAPI_ENV", "production")

    response = client.get("/travel-search/provider-readiness")

    assert response.status_code == 200
    payload = response.json()
    providers = {provider["provider"]: provider for provider in payload}
    assert providers["serpapi_google_hotels"]["environment"] == "production"
    assert providers["duffel"]["environment"] == "production"
    assert providers["liteapi_hotels"]["environment"] == "production"
    assert providers["google_maps"]["category"] == "location"


def test_discover_endpoint_builds_open_destination_packages(monkeypatch) -> None:
    monkeypatch.delenv("DUFFEL_API_TOKEN", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_ENV", raising=False)
    monkeypatch.delenv("LITEAPI_PRODUCTION_API_KEY", raising=False)
    monkeypatch.delenv("KIWI_TEQUILA_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    response = client.post(
        "/travel-search/discover",
        json={
            "search": {
                "user_id": "11111111-1111-4111-8111-111111111111",
                "raw_intent": "Find me a 5 star hotel under $500 a night and I do not want to fly more than 3 hours.",
                "origin": "SFO",
                "destination": "Open destination",
                "departure_date": "2026-07-24",
                "return_date": "2026-07-26",
                "check_in_date": "2026-07-24",
                "check_out_date": "2026-07-26",
                "budget_usd": 2000,
            },
            "max_destinations": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    first_option = payload["recommendations"][0]["option"]
    assert first_option["source_provider"] == "trip_discovery"
    assert first_option["details"]["kind"] == "trip_package"
    assert first_option["details"]["destination"]
    assert first_option["details"]["constraint_fit"] in {"exact", "near_miss", "weak"}
    constraint_checks = first_option["details"]["constraint_checks"]
    assert {check["label"] for check in constraint_checks} >= {"Flight time", "Hotel class", "Nightly price"}
    assert all(check["status"] in {"pass", "near_miss", "fail", "unknown"} for check in constraint_checks)


def test_discover_filters_weak_google_hotel_five_star_claim(monkeypatch) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "")
    monkeypatch.delenv("DUFFEL_API_TOKEN", raising=False)
    monkeypatch.delenv("LITEAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_ENV", raising=False)
    monkeypatch.delenv("LITEAPI_PRODUCTION_API_KEY", raising=False)
    monkeypatch.delenv("KIWI_TEQUILA_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    from app.core.trip_discovery import _hotel_is_usable
    from app.models.domain import BookingOption

    weak_google_hotel = BookingOption(
        label="Blue Heron Cottages via Google Hotels",
        booking_type="cash",
        merchant="Google Hotels",
        cash_price_usd=788,
        source_provider="serpapi_google_hotels",
        source_environment="production",
        details={"kind": "hotel", "stars": 5, "guest_rating": 4.1},
    )

    assert not _hotel_is_usable(
        weak_google_hotel,
        {"hotel_min_stars": 5, "include_near_misses": True},
    )


def test_discovery_scope_expands_to_global_region_catalogs() -> None:
    from app.core.trip_discovery import _candidate_destinations, _discovery_scope

    assert _discovery_scope("Find 5 star hotels across the US") == "united_states"
    assert _discovery_scope("Find luxury hotels across Europe") == "europe"
    assert _discovery_scope("Find beach hotels in Southeast Asia") == "southeast_asia"
    assert _discovery_scope("Find hotels in East Asia") == "east_asia"
    assert _discovery_scope("Find hotels in Japan or Korea") == "east_asia"
    assert _discovery_scope("Find boutique hotels in Central America") == "latin_america"
    assert _discovery_scope("Find luxury hotels in South America") == "latin_america"
    assert _discovery_scope("Find hotels in Asia") == "asia"

    constraints = {"include_near_misses": True, "hotel_min_stars": 5}
    us_candidates = _candidate_destinations(constraints, 40, True, "united_states")
    europe_candidates = _candidate_destinations(constraints, 20, True, "europe")
    southeast_asia_candidates = _candidate_destinations(constraints, 20, True, "southeast_asia")
    east_asia_candidates = _candidate_destinations(constraints, 20, True, "east_asia")
    latin_america_candidates = _candidate_destinations(constraints, 40, True, "latin_america")
    asia_candidates = _candidate_destinations(constraints, 40, True, "asia")

    assert "New York" in {candidate.city for candidate in us_candidates}
    europe_cities = {candidate.city for candidate in europe_candidates}
    assert "Paris" in europe_cities
    assert "Reykjavik" in europe_cities
    assert "Berlin" in europe_cities
    assert "Bangkok" in {candidate.city for candidate in southeast_asia_candidates}
    assert "Tokyo" in {candidate.city for candidate in east_asia_candidates}
    assert "Seoul" in {candidate.city for candidate in east_asia_candidates}
    assert "Mexico City" in {candidate.city for candidate in latin_america_candidates}
    assert "Costa Rica" in {candidate.city for candidate in latin_america_candidates}
    asia_cities = {candidate.city for candidate in asia_candidates}
    assert "Bangkok" in asia_cities
    assert "Tokyo" in asia_cities


def test_discovery_travel_time_constraint_filters_wider_catalog() -> None:
    from app.core.trip_discovery import _candidate_destinations

    candidates = _candidate_destinations(
        {"max_flight_minutes": 120, "hotel_min_stars": 5, "include_near_misses": True},
        20,
        True,
        "united_states",
    )
    cities = {candidate.city for candidate in candidates}

    assert "Phoenix" in cities
    assert "New York" not in cities


def test_discovery_plan_caps_selected_candidates_by_provider_budget(monkeypatch) -> None:
    from app.core.trip_discovery import _discovery_constraints, _discovery_plan
    from app.models.domain import TravelSearchRequest, TripDiscoveryRequest

    monkeypatch.delenv("DUFFEL_API_TOKEN", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_ENV", raising=False)
    monkeypatch.delenv("LITEAPI_PRODUCTION_API_KEY", raising=False)
    monkeypatch.delenv("KIWI_TEQUILA_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("DISCOVERY_PROVIDER_CALL_BUDGET", "4")

    request = TripDiscoveryRequest(
        search=TravelSearchRequest(
            user_id="11111111-1111-4111-8111-111111111111",
            raw_intent="Find 5 star hotels across the US",
            origin="SFO",
            destination="Open destination",
        ),
        max_destinations=10,
    )

    plan = _discovery_plan(request, _discovery_constraints(request), "united_states")

    assert plan.provider_call_budget == 4
    assert plan.providers_per_candidate == 2
    assert len(plan.selected_candidates) == 2
    assert plan.estimated_provider_calls == 4
    assert plan.skipped_candidate_count > 0
