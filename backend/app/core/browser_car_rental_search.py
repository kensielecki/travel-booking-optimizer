from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.core.reservation_agent import plan_reservation
from app.models.domain import (
    CarRentalBrowserSearchRequest,
    ReservationOption,
    ReservationPlan,
    ReservationPlanRequest,
)

_TINYFISH_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"
_SOURCE_URLS = {
    "kayak": "https://www.kayak.com/cars",
    "expedia": "https://www.expedia.com/Cars",
    "national": "https://www.nationalcar.com/en/reserve.html",
    "avis": "https://www.avis.com/en/reservation",
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


def search_car_rentals_with_browser(payload: CarRentalBrowserSearchRequest) -> ReservationPlan:
    base_plan = plan_reservation(ReservationPlanRequest(intent=payload.intent, max_options=payload.max_options))
    if base_plan.required_user_inputs:
        return base_plan

    scraped_options: list[ReservationOption] = []
    warnings = list(base_plan.warnings)

    browserless_token = os.getenv("BROWSERLESS_API_TOKEN")
    if browserless_token:
        for source in _normalize_sources(payload.sources):
            try:
                result = _run_browserless_source(source, payload, browserless_token)
            except RuntimeError as exc:
                warnings.append(str(exc))
                continue
            options, notes = _options_from_browserless_result(source, result, payload)
            scraped_options.extend(options)
            warnings.extend(notes)
    else:
        warnings.append("Browserless search is disabled because BROWSERLESS_API_TOKEN is not configured.")

    if scraped_options:
        return _browser_scrape_plan(base_plan, scraped_options, payload, warnings)

    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        return base_plan.model_copy(
            update={
                "warnings": warnings
                + ["TinyFish browser search is disabled because TINYFISH_API_KEY is not configured."],
            }
        )

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
        return _browser_scrape_plan(base_plan, scraped_options, payload, warnings)

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
        "browserless": {
            "configured": bool(os.getenv("BROWSERLESS_API_TOKEN")),
            "role": "REST browser function for public car-rental search pages",
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


def _browser_scrape_plan(
    base_plan: ReservationPlan,
    scraped_options: list[ReservationOption],
    payload: CarRentalBrowserSearchRequest,
    warnings: list[str],
) -> ReservationPlan:
    scraped_options = sorted(
        scraped_options,
        key=lambda option: (option.total_price_usd, -option.provider_confidence),
    )[: payload.max_options]
    return base_plan.model_copy(
        update={
            "options": scraped_options,
            "recommended_option_id": scraped_options[0].id,
            "warnings": warnings + ["Experimental browser-scraped car results must be re-opened and verified before approval."],
        }
    )


def _run_browserless_source(source: str, payload: CarRentalBrowserSearchRequest, api_token: str) -> dict[str, Any]:
    base_url = os.getenv("BROWSERLESS_BASE_URL", "https://production-sfo.browserless.io")
    timeout_seconds = float(os.getenv("BROWSERLESS_TIMEOUT_SECONDS", "45"))
    endpoint = f"{base_url.rstrip('/')}/function?token={urllib.parse.quote(api_token)}"
    context = _browserless_context(source, payload)
    request_payload = {
        "code": _BROWSERLESS_FUNCTION_CODE,
        "context": context,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"{source} Browserless scrape failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{source} Browserless scrape returned non-JSON response.") from exc
    data = parsed.get("data", parsed)
    if not isinstance(data, dict):
        return {"options": [], "notes": [f"{source} Browserless returned non-object data."]}
    return data


def _browserless_context(source: str, payload: CarRentalBrowserSearchRequest) -> dict[str, Any]:
    intent = payload.intent
    return {
        "source": source,
        "url": _SOURCE_URLS[source],
        "maxOptions": payload.max_options,
        "pickupLocation": intent.pickup_location,
        "dropoffLocation": intent.dropoff_location or intent.pickup_location,
        "pickupDate": intent.pickup_date.isoformat() if intent.pickup_date else None,
        "pickupTime": intent.pickup_time.isoformat() if intent.pickup_time else None,
        "dropoffDate": intent.dropoff_date.isoformat() if intent.dropoff_date else None,
        "dropoffTime": intent.dropoff_time.isoformat() if intent.dropoff_time else None,
        "vehicleClass": intent.vehicle_class,
        "driverAge": intent.driver_age,
        "maxTotalUsd": intent.max_total_usd,
    }


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
        complete = _read_tinyfish_complete_event(request, timeout_seconds=float(os.getenv("TINYFISH_TIMEOUT_SECONDS", "45")))
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


_BROWSERLESS_FUNCTION_CODE = r"""
export default async ({ page, context }) => {
  const notes = [];
  try {
    await page.setViewport({ width: 1440, height: 1100 });
    await page.goto(context.url, { waitUntil: "domcontentloaded", timeout: 25000 });
    await page.waitForTimeout(2500);

    const fillAttempt = await page.evaluate((ctx) => {
      const actions = [];
      const values = [
        ctx.pickupLocation,
        ctx.dropoffLocation,
        ctx.pickupDate,
        ctx.dropoffDate,
        ctx.pickupTime,
        ctx.dropoffTime,
      ].filter(Boolean);
      const inputs = Array.from(document.querySelectorAll("input, [contenteditable='true']"))
        .filter((el) => !el.disabled && el.offsetParent !== null)
        .slice(0, 12);
      inputs.forEach((input, index) => {
        const value = values[index];
        if (!value) return;
        input.focus();
        if ("value" in input) input.value = value;
        else input.textContent = value;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        actions.push({ index, value });
      });
      return actions;
    }, context);
    notes.push(`Browserless attempted ${fillAttempt.length} generic form fills on ${context.source}.`);

    const clicked = await page.evaluate(() => {
      const candidates = Array.from(document.querySelectorAll("button, a, input[type='submit']"));
      const match = candidates.find((el) => /search|find|show|view|continue/i.test(el.innerText || el.value || ""));
      if (match) {
        match.click();
        return true;
      }
      return false;
    });
    if (clicked) {
      await page.waitForTimeout(7000);
    }

    const data = await page.evaluate((ctx) => {
      const text = document.body ? document.body.innerText : "";
      const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
      const priceLines = lines.filter((line) => /\$\s?\d{2,5}/.test(line)).slice(0, 80);
      const options = [];
      for (let i = 0; i < priceLines.length && options.length < ctx.maxOptions; i += 1) {
        const line = priceLines[i];
        const price = line.match(/\$\s?([0-9,]+(?:\.[0-9]{2})?)/);
        if (!price) continue;
        const nearby = lines.slice(Math.max(0, lines.indexOf(line) - 4), Math.min(lines.length, lines.indexOf(line) + 5)).join(" | ");
        options.push({
          merchant: ctx.source,
          label: nearby.slice(0, 220),
          total_price_usd: Number(price[1].replace(/,/g, "")),
          currency: "USD",
          booking_url: location.href,
          vehicle_class: ctx.vehicleClass || null,
          cancellation_summary: "Extracted from browser-rendered public page; verify terms on provider site.",
          pay_later: true,
          free_cancellation: true,
          provider_reference: `${ctx.source}-${i}`,
        });
      }
      return { options, pageTitle: document.title, currentUrl: location.href, priceLineCount: priceLines.length };
    }, context);

    return {
      data: {
        options: data.options,
        notes: [
          ...notes,
          `Browserless page title: ${data.pageTitle}`,
          `Browserless current URL: ${data.currentUrl}`,
          `Browserless found ${data.priceLineCount} visible price-like lines.`,
        ],
      },
      type: "application/json",
    };
  } catch (error) {
    return {
      data: {
        options: [],
        notes: [`Browserless function error: ${error.message}`],
      },
      type: "application/json",
    };
  }
};
"""


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


def _options_from_browserless_result(
    source: str,
    result: dict[str, Any],
    payload: CarRentalBrowserSearchRequest,
) -> tuple[list[ReservationOption], list[str]]:
    return _options_from_browser_result(
        provider_prefix="browserless",
        confidence=0.62,
        truth="browser_scraped_unverified_inventory",
        source=source,
        result=result,
        payload=payload,
    )


def _options_from_browser_result(
    provider_prefix: str,
    confidence: float,
    truth: str,
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
                provider=f"{provider_prefix}_{source}",
                merchant=merchant,
                label=label,
                total_price_usd=total,
                currency=str(item.get("currency") or "USD"),
                booking_url=str(item.get("booking_url") or _SOURCE_URLS[source]),
                provider_reference=str(item.get("provider_reference") or f"{provider_prefix}-{source}"),
                source_environment="unknown",
                provider_confidence=confidence,
                pay_later=bool(item.get("pay_later", True)),
                free_cancellation=bool(item.get("free_cancellation", True)),
                cancellation_summary=item.get("cancellation_summary"),
                details={
                    "inventory_truth": truth,
                    "source_kind": f"{provider_prefix}_browser_scrape",
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
