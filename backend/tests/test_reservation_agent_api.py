from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_car_rental_plan_requires_core_booking_details() -> None:
    response = client.post(
        "/reservations/plan",
        json={
            "intent": {
                "user_id": "22222222-2222-4222-8222-222222222222",
                "category": "car_rental",
                "raw_intent": "Reserve a midsize car for my trip.",
                "pickup_location": "SFO",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "planned"
    assert payload["risk_level"] == "high"
    assert payload["options"] == []
    assert "Pickup date" in payload["required_user_inputs"]
    assert "Driver age" in payload["required_user_inputs"]


def test_car_rental_queue_approval_and_dry_run_flow() -> None:
    user_id = "33333333-3333-4333-8333-333333333333"
    plan_response = client.post(
        "/reservations/plan",
        json={
            "intent": {
                "user_id": user_id,
                "category": "car_rental",
                "raw_intent": "Reserve a pay later midsize car at SFO.",
                "pickup_location": "SFO",
                "dropoff_location": "SFO",
                "pickup_date": "2026-07-24",
                "pickup_time": "10:00",
                "dropoff_date": "2026-07-26",
                "dropoff_time": "16:00",
                "vehicle_class": "midsize",
                "max_total_usd": 300,
                "driver_age": 35,
                "constraints": ["pay later", "free cancellation"],
            },
            "max_options": 3,
        },
    )

    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert plan["risk_level"] == "low"
    assert plan["recommended_option_id"]
    assert len(plan["options"]) >= 1
    assert all(option["pay_later"] for option in plan["options"])
    assert all(option["free_cancellation"] for option in plan["options"])

    queue_response = client.post(
        "/reservations/queue",
        json={
            "plan": plan,
            "selected_option_id": plan["recommended_option_id"],
            "review_window_hours": 0,
            "max_charge_usd": 300,
        },
    )

    assert queue_response.status_code == 200
    queue_item = queue_response.json()
    assert queue_item["status"] == "pending_review"
    assert queue_item["approval_required"] is True

    approval_response = client.post(
        f"/reservations/{user_id}/queue/{queue_item['id']}/approve",
        json={
            "approved_option_id": queue_item["selected_option_id"],
            "max_charge_usd": 300,
            "approval_scope": "dry-run car rental reservation only",
        },
    )

    assert approval_response.status_code == 200
    approval = approval_response.json()
    assert approval["queue_item_id"] == queue_item["id"]

    run_response = client.post(f"/reservations/{user_id}/queue/{queue_item['id']}/execute-dry-run")

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["dry_run"] is True
    assert run["status"] == "dry_run_completed"
    assert "No reservation was submitted" in run["result_message"]

    state_response = client.get(f"/reservations/{user_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert len(state["queue"]) == 1
    assert len(state["approvals"]) == 1
    assert len(state["agent_runs"]) == 1
