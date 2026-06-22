from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from app.core.reservation_agent import plan_reservation
from app.models.domain import (
    CarRentalBrowserSearchRequest,
    ReservationOption,
    ReservationPlan,
    ReservationPlanRequest,
)

_TINYFISH_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"
_TINYFISH_TIMEOUT_SECONDS = float(os.getenv("TINYFISH_TIMEOUT_SECONDS", "45"))
_SOURCE_URLS = {
    "kayak": "https://www.kayak.com/cars",
    "expedia": "https://www.expedia.com/Cars",
    "national": "https://www.nationalcar.com/en/reserve.html",
    "avis": "https://www.avis.com/en/reservation",
}


def search_car_rentals_with_browser(payload: CarRentalBrowserSearchRequest) -> ReservationPlan:
    base_plan = plan_reservation(ReservationPlanRequest(intent=payload.intent, max_options=payload.max_options))
    if base_plan.required_user_inputs:
        return base_plan

    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        base_plan.warnings.append("TinyFish browser search is disabled because TINYFISH_API_KEY is not configured.")
        return base_plan

    scraped_options: list[ReservationOption] = []
    warnings = list(base_plan.warnings)
    for source in _normalize_sources(payload.sources):
        try:
            result = _run_tinyfish_source(source, payload, api_key)
        except RuntimeError as exc:
            warnings.append(str(exc))
            continue
        options, notes = _options_from_tinyfish_result(source, result, payload)
        scraped_options.extend(options)
        warnings.extend(notes)

    if scraped_options:
        scraped_options = sorted(scraped_options, key=lambda option: (option.total_price_usd, -option.provider_confidence))[
            : payload.max_options
        ]
        return base_plan.model_copy(
            update={
                "options": scraped_options,
                "recommended_option_id": scraped_options[0].id,
                "warnings": warnings
                + ["Experimental browser-scraped car results must be re-opened and verified before approval."],
            }
        )

    return base_plan.model_copy(
        update={
            "warnings": warnings
            + ["Browser scrape returned no structured car inventory; falling back to provider handoff checks."],
        }
    )


def browser_car_rental_readiness() -> dict[str, Any]:
    return {
        "tinyfish": {
            "configured": bool(os.getenv("TINYFISH_API_KEY")),
            "role": "browser scrape for public car-rental search pages",
            "sources": sorted(_SOURCE_URLS),
        },
        "browserbase": {
            "configured": bool(os.getenv("BROWSERBASE_API_KEY")),
            "role": "cloud browser sessions / Stagehand candidate",
            "sources": sorted(_SOURCE_URLS),
        },
    }


def _normalize_sources(sources: list[str]) -> list[str]:
    normalized = []
    for source in sources:
        key = source.strip().lower()
        if key in _SOURCE_URLS and key not in normalized:
            normalized.append(key)
    return normalized or ["kayak"]


def _run_tinyfish_source(source: str, payload: CarRentalBrowserSearchRequest, api_key: str) -> dict[str, Any]:
    intent = payload.intent
    url = _SOURCE_URLS[source]
    goal = (
        "Search public car rental inventory using these criteria and extract results as JSON only. "
        "Do not log in, do not reserve, do not enter payment, and do not click final booking buttons. "
        f"Pickup location: {intent.pickup_location}. "
        f"Dropoff location: {intent.dropoff_location or intent.pickup_location}. "
        f"Pickup: {intent.pickup_date} at {intent.pickup_time}. "
        f"Dropoff: {intent.dropoff_date} at {intent.dropoff_time}. "
        f"Vehicle class: {intent.vehicle_class or 'any'}. "
        f"Driver age: {intent.driver_age}. "
        f"Maximum total: {intent.max_total_usd or 'not supplied'}. "
        f"Extract up to {payload.max_options} options as: "
        '{"options":[{"merchant":str,"label":str,"total_price_usd":number,'
        '"currency":str,"booking_url":str,"vehicle_class":str,"cancellation_summary":str,'
        '"pay_later":bool,"free_cancellation":bool,"provider_reference":str}],'
        '"notes":[str]}. If prices are not visible, return {"options":[],"notes":[reason]}.'
    )
    request_payload: dict[str, Any] = {"url": url, "goal": goal}
    if payload.browser_profile == "stealth":
        request_payload["browser_profile"] = "stealth"

    request = urllib.request.Request(
        _TINYFISH_URL,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        complete = _read_tinyfish_complete_event(request, timeout_seconds=_TINYFISH_TIMEOUT_SECONDS)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"{source} browser scrape failed: {exc}") from exc

    if complete is None:
        raise RuntimeError(f"{source} browser scrape timed out before returning a completed TinyFish event.")
    result = complete.get("resultJson") or complete.get("result") or {}
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return {"options": [], "notes": [result[:500]]}
    if not isinstance(result, dict):
        return {"options": [], "notes": [f"{source} returned non-object result."]}
    return result


def _read_tinyfish_complete_event(request: urllib.request.Request, timeout_seconds: float) -> dict[str, Any] | None:
    deadline = time.monotonic() + timeout_seconds
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        while time.monotonic() < deadline:
            raw_line = response.readline()
            if not raw_line:
                break
            event = _tinyfish_event_from_line(raw_line.decode("utf-8", errors="replace"))
            if event and (event.get("type") == "COMPLETE" or event.get("status") == "COMPLETED"):
                return event
    return None


def _tinyfish_event_from_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line.startswith("data:"):
        return None
    try:
        return json.loads(line[5:].strip())
    except json.JSONDecodeError:
        return None


def _tinyfish_complete_event(body: str) -> dict[str, Any] | None:
    completed = None
    for line in body.splitlines():
        event = _tinyfish_event_from_line(line)
        if event and (event.get("type") == "COMPLETE" or event.get("status") == "COMPLETED"):
            completed = event
    return completed


def _options_from_tinyfish_result(
    source: str,
    result: dict[str, Any],
    payload: CarRentalBrowserSearchRequest,
) -> tuple[list[ReservationOption], list[str]]:
    intent = payload.intent
    options: list[ReservationOption] = []
    notes = [str(note) for note in result.get("notes", []) if note]
    for item in result.get("options", [])[: payload.max_options]:
        if not isinstance(item, dict):
            continue
        total = _float_or_none(item.get("total_price_usd"))
        if total is None:
            continue
        if intent.max_total_usd and total > intent.max_total_usd:
            continue
        merchant = str(item.get("merchant") or source.title())
        label = str(item.get("label") or f"{merchant} car rental")
        options.append(
            ReservationOption(
                provider=f"tinyfish_{source}",
                merchant=merchant,
                label=label,
                total_price_usd=total,
                currency=str(item.get("currency") or "USD"),
                booking_url=str(item.get("booking_url") or _SOURCE_URLS[source]),
                provider_reference=str(item.get("provider_reference") or f"tinyfish-{source}"),
                source_environment="unknown",
                provider_confidence=0.58,
                pay_later=bool(item.get("pay_later", True)),
                free_cancellation=bool(item.get("free_cancellation", True)),
                cancellation_summary=item.get("cancellation_summary"),
                details={
                    "inventory_truth": "browser_scraped_unverified_inventory",
                    "source_kind": "tinyfish_browser_scrape",
                    "source": source,
                    "pickup_location": intent.pickup_location,
                    "dropoff_location": intent.dropoff_location or intent.pickup_location,
                    "pickup_date": intent.pickup_date.isoformat() if intent.pickup_date else None,
                    "pickup_time": intent.pickup_time.isoformat() if intent.pickup_time else None,
                    "dropoff_date": intent.dropoff_date.isoformat() if intent.dropoff_date else None,
                    "dropoff_time": intent.dropoff_time.isoformat() if intent.dropoff_time else None,
                    "vehicle_class": item.get("vehicle_class") or intent.vehicle_class,
                },
            )
        )
    return options, notes


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None
