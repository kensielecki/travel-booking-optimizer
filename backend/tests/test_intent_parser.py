from __future__ import annotations

from datetime import time
from uuid import UUID

from app.core.intent_parser import enrich_search_from_intent
from app.models.domain import TravelSearchRequest

USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_intent_parser_extracts_common_travel_constraints() -> None:
    search = enrich_search_from_intent(
        TravelSearchRequest(
            user_id=USER_ID,
            raw_intent=(
                "Weekend trip to San Diego around $1,800. Direct flight only, "
                "arrive before midday, 4 star hotel or higher within 20 minutes."
            ),
            origin="SFO",
            destination="San Diego",
        )
    )

    assert search.direct_only is True
    assert search.latest_arrival_time == time(hour=12)
    assert search.hotel_min_stars == 4
    assert search.hotel_max_travel_minutes == 20
    assert search.budget_usd == 1800


def test_intent_parser_does_not_override_explicit_fields() -> None:
    search = enrich_search_from_intent(
        TravelSearchRequest(
            user_id=USER_ID,
            raw_intent="Direct flight, arrive before noon, 5 star hotel under $900.",
            origin="SFO",
            destination="San Diego",
            direct_only=False,
            latest_arrival_time=time(hour=14),
            hotel_min_stars=3,
            budget_usd=1200,
        )
    )

    assert search.direct_only is True
    assert search.latest_arrival_time == time(hour=14)
    assert search.hotel_min_stars == 3
    assert search.budget_usd == 1200
