from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.models.domain import (
    AgentRun,
    ReservationApprovalRequest,
    ReservationCategory,
    ReservationIntent,
    ReservationOption,
    ReservationPlan,
    ReservationPlanRequest,
    ReservationQueueItem,
    ReservationQueueRequest,
    ReservationRecord,
    ReservationRiskLevel,
    ReservationStateResponse,
    ReservationStatus,
    UserApproval,
)

_STATE_PATH = Path(
    os.getenv(
        "RESERVATION_AGENT_STATE_PATH",
        Path(__file__).resolve().parents[2] / ".local" / "reservation-agent-state.json",
    )
)

_queue_by_user: dict[str, list[ReservationQueueItem]] = {}
_approvals_by_user: dict[str, list[UserApproval]] = {}
_runs_by_user: dict[str, list[AgentRun]] = {}
_records_by_user: dict[str, list[ReservationRecord]] = {}


def plan_reservation(payload: ReservationPlanRequest) -> ReservationPlan:
    intent = payload.intent
    guardrails = _car_guardrails(intent)
    missing = [item["label"] for item in guardrails if item["status"] == "missing"]
    warnings = [item["detail"] for item in guardrails if item["status"] in {"warning", "blocked"}]
    options = [] if missing else _mock_car_options(intent, payload.max_options)
    filtered_options, option_warnings = _filter_car_options(options, intent)
    warnings.extend(option_warnings)

    risk_level = ReservationRiskLevel.low
    if any(item["status"] == "blocked" for item in guardrails) or missing:
        risk_level = ReservationRiskLevel.high
    elif warnings:
        risk_level = ReservationRiskLevel.medium

    recommended = filtered_options[0].id if filtered_options else None
    return ReservationPlan(
        user_id=intent.user_id,
        intent=intent,
        options=filtered_options,
        recommended_option_id=recommended,
        risk_level=risk_level,
        guardrail_results=guardrails,
        required_user_inputs=missing,
        warnings=warnings,
    )


def queue_reservation(payload: ReservationQueueRequest) -> ReservationQueueItem:
    plan = payload.plan
    user_key = str(plan.user_id)
    selected_id = payload.selected_option_id or plan.recommended_option_id
    if selected_id is None:
        raise ValueError("No reservation option selected.")

    selected = _option_by_id(plan, selected_id)
    if selected is None:
        raise ValueError("Selected reservation option is not part of this plan.")

    duplicate = _duplicate_queue_item(user_key, plan.intent, selected)
    if duplicate:
        return duplicate

    max_charge = payload.max_charge_usd or selected.total_price_usd
    item = ReservationQueueItem(
        user_id=plan.user_id,
        plan=plan.model_copy(update={"status": ReservationStatus.queued}),
        selected_option_id=selected.id,
        book_after=datetime.utcnow() + timedelta(hours=payload.review_window_hours),
        max_charge_usd=max_charge,
    )
    _queue_by_user.setdefault(user_key, []).append(item)
    _persist_state()
    return item


def approve_reservation(user_id: UUID, queue_item_id: UUID, payload: ReservationApprovalRequest) -> UserApproval:
    item = _queue_item(user_id, queue_item_id)
    selected = _option_by_id(item.plan, payload.approved_option_id)
    if selected is None:
        raise ValueError("Approved option is not part of this queued reservation.")

    approval = UserApproval(
        user_id=user_id,
        queue_item_id=queue_item_id,
        approved_option_id=payload.approved_option_id,
        max_charge_usd=payload.max_charge_usd or item.max_charge_usd,
        approval_scope=payload.approval_scope,
        expires_at=payload.expires_at,
    )
    item.status = ReservationStatus.approved
    item.selected_option_id = payload.approved_option_id
    _approvals_by_user.setdefault(str(user_id), []).append(approval)
    _persist_state()
    return approval


def execute_reservation_dry_run(user_id: UUID, queue_item_id: UUID) -> AgentRun:
    item = _queue_item(user_id, queue_item_id)
    selected = _option_by_id(item.plan, item.selected_option_id)
    if selected is None:
        raise ValueError("Selected option no longer exists on the reservation plan.")

    approval = _latest_approval(user_id, queue_item_id)
    steps = [
        "Load queued car-rental reservation.",
        "Verify selected option belongs to the approved plan.",
        "Check pay-later and free-cancellation guardrails.",
        "Check maximum charge cap.",
        "Stop before any provider submission because this endpoint is dry-run only.",
    ]
    warnings = []
    if not approval:
        warnings.append("No approval found; dry-run allowed but real execution would be blocked.")
    if selected.requires_payment_now:
        warnings.append("Selected option requires payment now; real execution would be blocked.")
    if not selected.free_cancellation:
        warnings.append("Selected option is not free-cancellation; real execution would be blocked.")
    if item.max_charge_usd and selected.total_price_usd > item.max_charge_usd:
        warnings.append("Selected option exceeds approved maximum charge; real execution would be blocked.")

    run = AgentRun(
        user_id=user_id,
        queue_item_id=queue_item_id,
        status=ReservationStatus.dry_run_completed,
        steps=steps,
        result_message=(
            f"Dry run complete for {selected.label}. No reservation was submitted. "
            "Real booking execution remains disabled until provider integration and final approval gates are added."
        ),
        provider_response={
            "dry_run": True,
            "selected_provider": selected.provider,
            "selected_merchant": selected.merchant,
            "warnings": warnings,
        },
    )
    item.status = ReservationStatus.dry_run_completed
    _runs_by_user.setdefault(str(user_id), []).append(run)
    _persist_state()
    return run


def get_reservation_state(user_id: UUID) -> ReservationStateResponse:
    user_key = str(user_id)
    return ReservationStateResponse(
        user_id=user_id,
        queue=_queue_by_user.get(user_key, []),
        approvals=_approvals_by_user.get(user_key, []),
        agent_runs=_runs_by_user.get(user_key, []),
        records=_records_by_user.get(user_key, []),
    )


def _car_guardrails(intent: ReservationIntent) -> list[dict]:
    if intent.category != ReservationCategory.car_rental:
        return [_guardrail("Category", "blocked", "This first reservation agent only supports car rentals.")]

    checks = [
        _required_guardrail("Pickup location", intent.pickup_location),
        _required_guardrail("Dropoff location", intent.dropoff_location or intent.pickup_location),
        _required_guardrail("Pickup date", intent.pickup_date),
        _required_guardrail("Pickup time", intent.pickup_time),
        _required_guardrail("Dropoff date", intent.dropoff_date),
        _required_guardrail("Dropoff time", intent.dropoff_time),
        _required_guardrail("Driver age", intent.driver_age),
    ]

    if intent.max_total_usd:
        checks.append(_guardrail("Max charge", "pass", f"Maximum total charge capped at ${intent.max_total_usd:,.0f}."))
    else:
        checks.append(_guardrail("Max charge", "warning", "No maximum total charge supplied; queue will use selected option price as cap."))

    checks.append(_guardrail("Payment safety", "pass", "Planner only returns pay-later/free-cancellation options for now."))
    checks.append(_guardrail("Execution mode", "pass", "Real provider submission is disabled; only dry-run execution is available."))
    return checks


def _mock_car_options(intent: ReservationIntent, max_options: int) -> list[ReservationOption]:
    vehicle = (intent.vehicle_class or "midsize").strip().lower()
    base_price = {
        "economy": 178,
        "compact": 196,
        "midsize": 224,
        "standard": 248,
        "suv": 312,
        "premium": 386,
        "luxury": 510,
    }.get(vehicle, 238)
    providers = [
        ("mock_carrental_paylater", "Hertz", 1.0, "Pay later, free cancellation until 24h before pickup."),
        ("mock_carrental_paylater", "Avis", 1.08, "Pay later, free cancellation until pickup."),
        ("mock_carrental_paylater", "Enterprise", 1.12, "Pay later, free cancellation before pickup."),
        ("mock_carrental_compare", "National", 1.22, "Loyalty-friendly option; pay later; free cancellation."),
    ]
    options = []
    for provider, merchant, multiplier, cancellation in providers[:max_options]:
        total = round(base_price * multiplier, 2)
        options.append(
            ReservationOption(
                provider=provider,
                merchant=merchant,
                label=f"{merchant} {vehicle.title()} car rental",
                total_price_usd=total,
                source_environment="mock",
                provider_confidence=0.45,
                booking_url=_provider_url(merchant),
                provider_reference=f"dry-run-{merchant.lower()}-{int(total)}",
                cancellation_summary=cancellation,
                details={
                    "pickup_location": intent.pickup_location,
                    "dropoff_location": intent.dropoff_location or intent.pickup_location,
                    "pickup_date": intent.pickup_date.isoformat() if intent.pickup_date else None,
                    "pickup_time": intent.pickup_time.isoformat() if intent.pickup_time else None,
                    "dropoff_date": intent.dropoff_date.isoformat() if intent.dropoff_date else None,
                    "dropoff_time": intent.dropoff_time.isoformat() if intent.dropoff_time else None,
                    "vehicle_class": vehicle,
                    "driver_age": intent.driver_age,
                },
            )
        )
    return options


def _filter_car_options(options: list[ReservationOption], intent: ReservationIntent) -> tuple[list[ReservationOption], list[str]]:
    warnings = []
    filtered = [
        option
        for option in options
        if option.pay_later and option.free_cancellation and not option.requires_payment_now
    ]
    if intent.max_total_usd:
        before = len(filtered)
        filtered = [option for option in filtered if option.total_price_usd <= intent.max_total_usd]
        if before and not filtered:
            warnings.append("No generated car-rental options fit the max total charge cap.")
    return sorted(filtered, key=lambda option: (option.total_price_usd, -option.provider_confidence)), warnings


def _required_guardrail(label: str, value: object) -> dict:
    if value is None or value == "":
        return _guardrail(label, "missing", f"{label} is required before a car rental can be queued.")
    return _guardrail(label, "pass", f"{label} supplied.")


def _guardrail(label: str, status: str, detail: str) -> dict:
    return {"label": label, "status": status, "detail": detail}


def _option_by_id(plan: ReservationPlan, option_id: UUID) -> ReservationOption | None:
    return next((option for option in plan.options if option.id == option_id), None)


def _queue_item(user_id: UUID, queue_item_id: UUID) -> ReservationQueueItem:
    item = next((item for item in _queue_by_user.get(str(user_id), []) if item.id == queue_item_id), None)
    if item is None:
        raise ValueError("Reservation queue item not found.")
    return item


def _latest_approval(user_id: UUID, queue_item_id: UUID) -> UserApproval | None:
    approvals = [
        approval
        for approval in _approvals_by_user.get(str(user_id), [])
        if approval.queue_item_id == queue_item_id
    ]
    return approvals[-1] if approvals else None


def _duplicate_queue_item(user_key: str, intent: ReservationIntent, selected: ReservationOption) -> ReservationQueueItem | None:
    for item in _queue_by_user.get(user_key, []):
        existing = item.plan.intent
        if (
            existing.category == intent.category
            and existing.pickup_location == intent.pickup_location
            and existing.pickup_date == intent.pickup_date
            and existing.pickup_time == intent.pickup_time
            and existing.dropoff_date == intent.dropoff_date
            and item.plan.options
            and _option_by_id(item.plan, item.selected_option_id)
            and _option_by_id(item.plan, item.selected_option_id).merchant == selected.merchant
        ):
            return item
    return None


def _provider_url(merchant: str) -> str:
    return {
        "Hertz": "https://www.hertz.com/rentacar/reservation/",
        "Avis": "https://www.avis.com/en/reservation",
        "Enterprise": "https://www.enterprise.com/en/car-rental.html",
        "National": "https://www.nationalcar.com/en/reserve.html",
    }.get(merchant, "https://www.google.com/travel/")


def _load_state() -> None:
    if not _STATE_PATH.exists():
        return
    try:
        payload = json.loads(_STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return

    for user_key, queue in payload.get("queue_by_user", {}).items():
        _queue_by_user[user_key] = [ReservationQueueItem.model_validate(item) for item in queue]
    for user_key, approvals in payload.get("approvals_by_user", {}).items():
        _approvals_by_user[user_key] = [UserApproval.model_validate(item) for item in approvals]
    for user_key, runs in payload.get("runs_by_user", {}).items():
        _runs_by_user[user_key] = [AgentRun.model_validate(item) for item in runs]
    for user_key, records in payload.get("records_by_user", {}).items():
        _records_by_user[user_key] = [ReservationRecord.model_validate(item) for item in records]


def _persist_state() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "queue_by_user": {
            user_key: [item.model_dump(mode="json") for item in queue]
            for user_key, queue in _queue_by_user.items()
        },
        "approvals_by_user": {
            user_key: [item.model_dump(mode="json") for item in approvals]
            for user_key, approvals in _approvals_by_user.items()
        },
        "runs_by_user": {
            user_key: [item.model_dump(mode="json") for item in runs]
            for user_key, runs in _runs_by_user.items()
        },
        "records_by_user": {
            user_key: [item.model_dump(mode="json") for item in records]
            for user_key, records in _records_by_user.items()
        },
    }
    _STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n")


_load_state()
