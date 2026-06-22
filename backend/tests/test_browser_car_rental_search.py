from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.browser_car_rental_search import _options_from_browserless_result, _options_from_tinyfish_result
from app.main import app
from app.models.domain import CarRentalBrowserSearchRequest, ReservationIntent

client = TestClient(app)


def _complete_intent() -> dict:
    return {
        "user_id": str(uuid4()),
        "category": "car_rental",
        "raw_intent": "Find a midsize car at SFO.",
        "pickup_location": "SFO",
        "dropoff_location": "SFO",
        "pickup_date": "2026-07-24",
        "pickup_time": "10:00",
        "dropoff_date": "2026-07-26",
        "dropoff_time": "16:00",
        "vehicle_class": "midsize",
        "driver_age": 35,
    }


def test_browser_readiness_endpoint_reports_shape() -> None:
    response = client.get("/reservations/car-rentals/browser-readiness")

    assert response.status_code == 200
    payload = response.json()
    assert "tinyfish" in payload
    assert "browserless" in payload
    assert "browserbase" in payload
    assert "kayak" in payload["tinyfish"]["sources"]
    assert "kayak" in payload["browserless"]["sources"]


def test_browser_search_without_tinyfish_key_falls_back(monkeypatch) -> None:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)

    response = client.post(
        "/reservations/car-rentals/browser-search",
        json={"intent": _complete_intent(), "sources": ["kayak"], "max_options": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["options"]
    assert any("TINYFISH_API_KEY is not configured" in warning for warning in payload["warnings"])


def test_tinyfish_result_is_normalized_to_reservation_options() -> None:
    intent = ReservationIntent.model_validate(_complete_intent())
    payload = CarRentalBrowserSearchRequest(intent=intent, sources=["kayak"], max_options=2)

    options, notes = _options_from_tinyfish_result(
        "kayak",
        {
            "options": [
                {
                    "merchant": "Avis",
                    "label": "Avis midsize",
                    "total_price_usd": "$241.22",
                    "currency": "USD",
                    "booking_url": "https://www.kayak.com/cars/example",
                    "vehicle_class": "midsize",
                    "cancellation_summary": "Free cancellation shown.",
                    "pay_later": True,
                    "free_cancellation": True,
                    "provider_reference": "abc",
                }
            ],
            "notes": ["sample scrape"],
        },
        payload,
    )

    assert notes == ["sample scrape"]
    assert len(options) == 1
    assert options[0].provider == "tinyfish_kayak"
    assert options[0].merchant == "Avis"
    assert options[0].total_price_usd == 241.22
    assert options[0].details["inventory_truth"] == "browser_scraped_unverified_inventory"


def test_browserless_result_is_normalized_to_reservation_options() -> None:
    intent = ReservationIntent.model_validate(_complete_intent())
    payload = CarRentalBrowserSearchRequest(intent=intent, sources=["kayak"], max_options=2)

    options, notes = _options_from_browserless_result(
        "kayak",
        {
            "options": [
                {
                    "merchant": "kayak",
                    "label": "Budget midsize | $219 total",
                    "total_price_usd": 219,
                    "currency": "USD",
                    "booking_url": "https://www.kayak.com/cars/example",
                    "vehicle_class": "midsize",
                    "cancellation_summary": "Verify on provider site.",
                    "pay_later": True,
                    "free_cancellation": True,
                    "provider_reference": "browserless-1",
                }
            ],
            "notes": ["browserless sample"],
        },
        payload,
    )

    assert notes == ["browserless sample"]
    assert len(options) == 1
    assert options[0].provider == "browserless_kayak"
    assert options[0].total_price_usd == 219
    assert options[0].provider_confidence == 0.62
    assert options[0].details["source_kind"] == "browserless_browser_scrape"
