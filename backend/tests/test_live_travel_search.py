from __future__ import annotations

from uuid import UUID

from app.core.live_travel_search import get_provider_readiness, search_live_flights, search_live_hotels
from app.models.domain import TravelSearchRequest

USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_flight_search_returns_mock_results_without_duffel_key(monkeypatch) -> None:
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("KIWI_TEQUILA_API_KEY", raising=False)
    monkeypatch.delenv("DUFFEL_API_TOKEN", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    response = search_live_flights(
        TravelSearchRequest(
            user_id=USER_ID,
            raw_intent="Direct flight to San Diego",
            origin="SFO",
            destination="SAN",
            direct_only=True,
        )
    )

    assert response.live is False
    assert response.provider == "aggregated_flights"
    provider_status = {status.provider: status for status in response.provider_statuses}
    assert provider_status["serpapi_google_flights"].status == "disabled"
    assert provider_status["kiwi_tequila_flights"].status == "disabled"
    assert provider_status["duffel"].status == "disabled"
    assert provider_status["amadeus_flight_offers"].status == "disabled"
    assert provider_status["mock_flights"].status == "fallback"
    assert any(option.merchant == "United" for option in response.booking_options)
    assert response.warnings


def test_hotel_search_returns_mock_results_without_serpapi_key(monkeypatch) -> None:
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_API_KEY", raising=False)
    monkeypatch.delenv("LITEAPI_ENV", raising=False)
    monkeypatch.delenv("LITEAPI_PRODUCTION_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    response = search_live_hotels(
        TravelSearchRequest(
            user_id=USER_ID,
            raw_intent="4 star hotel in New York",
            destination="New York",
            hotel_min_stars=4,
        )
    )

    assert response.live is False
    assert response.provider == "aggregated_hotels"
    provider_status = {status.provider: status for status in response.provider_statuses}
    assert provider_status["serpapi_google_hotels"].status == "disabled"
    assert provider_status["liteapi_hotels"].status == "disabled"
    assert provider_status["amadeus_hotel_search"].status == "disabled"
    assert provider_status["mock_hotels"].status == "fallback"
    assert "The Beekman" in response.booking_options[0].label
    assert response.warnings


def test_provider_readiness_classifies_configured_environments(monkeypatch) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "serpapi")
    monkeypatch.setenv("DUFFEL_API_TOKEN", "duffel_test_example")
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_liteapi")
    monkeypatch.setenv("LITEAPI_ENV", "sandbox")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("KIWI_TEQUILA_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    readiness = {provider.provider: provider for provider in get_provider_readiness()}

    assert readiness["serpapi_google_flights"].configured is True
    assert readiness["serpapi_google_flights"].environment == "production"
    assert readiness["duffel"].environment == "sandbox"
    assert readiness["liteapi_hotels"].environment == "sandbox"
    assert readiness["google_maps"].configured is False
    assert readiness["kiwi_tequila_flights"].configured is False


def test_provider_readiness_prefers_legacy_liteapi_env_key(monkeypatch) -> None:
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_liteapi")
    monkeypatch.setenv("LITEAPI_ENV", "prod_liteapi")
    monkeypatch.delenv("LITEAPI_PRODUCTION_API_KEY", raising=False)

    readiness = {provider.provider: provider for provider in get_provider_readiness()}

    assert readiness["liteapi_hotels"].configured is True
    assert readiness["liteapi_hotels"].environment == "production"
