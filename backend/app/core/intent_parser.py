from __future__ import annotations

import re
from datetime import time

from app.models.domain import TravelSearchRequest


def enrich_search_from_intent(search: TravelSearchRequest) -> TravelSearchRequest:
    text = _normalize(search.raw_intent)
    updates: dict[str, object] = {}

    if not search.direct_only and _mentions_any(text, ["direct flight", "nonstop", "non-stop", "no layover"]):
        updates["direct_only"] = True

    if search.latest_arrival_time is None:
        latest_arrival = _parse_latest_arrival_time(text)
        if latest_arrival:
            updates["latest_arrival_time"] = latest_arrival

    if search.hotel_min_stars is None:
        hotel_stars = _parse_hotel_min_stars(text)
        if hotel_stars:
            updates["hotel_min_stars"] = hotel_stars

    if search.hotel_max_travel_minutes is None:
        travel_minutes = _parse_max_travel_minutes(text)
        if travel_minutes:
            updates["hotel_max_travel_minutes"] = travel_minutes

    parsed_budget = _parse_budget(text)
    if parsed_budget and search.budget_usd == 2000:
        updates["budget_usd"] = parsed_budget

    if not updates:
        return search
    return search.model_copy(update=updates)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _mentions_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _parse_latest_arrival_time(text: str) -> time | None:
    if _mentions_any(text, ["before midday", "by midday", "before noon", "by noon"]):
        return time(hour=12)

    match = re.search(r"(?:arrive|arrival|land|landing)[^.;,]*(?:before|by)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return time(hour=hour, minute=minute)
    return None


def _parse_hotel_min_stars(text: str) -> int | None:
    match = re.search(r"([1-5])\s*[- ]?\s*star(?:s)?(?:\s+or\s+higher|\+)?", text)
    return int(match.group(1)) if match else None


def _parse_max_travel_minutes(text: str) -> int | None:
    match = re.search(r"(?:within|no further than|under|less than)\s+(\d{1,3})\s*(?:min|mins|minute|minutes)", text)
    return int(match.group(1)) if match else None


def _parse_budget(text: str) -> float | None:
    match = re.search(r"(?:budget|under|around|~|about|approx(?:imately)?)\s*\$?\s*([\d,]+(?:\.\d+)?)", text)
    if not match:
        match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))
