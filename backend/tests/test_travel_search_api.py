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
