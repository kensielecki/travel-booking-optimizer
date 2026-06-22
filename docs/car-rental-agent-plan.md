# Car Rental Reservation Agent Plan

Last updated: 2026-06-22

## Current Status

The first car-rental agent layer is implemented as a safe backend skeleton. It can:

- Create a car-rental reservation plan.
- Generate mock pay-later/free-cancellation car options.
- Apply guardrails before queueing.
- Queue a selected option for review.
- Record explicit approval.
- Execute a dry run.
- Persist queue, approval, and dry-run audit state locally.

It cannot yet submit a real provider booking. That is intentional.

## Borrowed Pattern From `2603_events-aggregator`

The events RSVP project has a useful agent pattern:

1. Discover candidates.
2. Rank/score them.
3. Apply guardrails.
4. Add eligible items to a queue.
5. Wait for review.
6. Execute only after approval.
7. Stop on unknown/risky fields.
8. Log the result.
9. Notify the user.
10. Prevent duplicates.

For travel, we are reusing the queue, approval, guardrail, dry-run, duplicate-prevention, and audit concepts.

We are not copying the credentialed TinyFish browser-login flow as the default execution path. Car rentals can create financial obligations, no-show penalties, insurance choices, cancellation constraints, and payment risk. The default path should be provider/API-first, with browser agents only as a supervised fallback.

## New Backend API

Reservation planning:

```http
POST /reservations/plan
```

Queue selected option:

```http
POST /reservations/queue
```

Approve queued item:

```http
POST /reservations/{user_id}/queue/{queue_item_id}/approve
```

Dry-run execution:

```http
POST /reservations/{user_id}/queue/{queue_item_id}/execute-dry-run
```

Read state:

```http
GET /reservations/{user_id}/state
```

## Current Guardrails

Required before queueing:

- Pickup location.
- Dropoff location.
- Pickup date.
- Pickup time.
- Dropoff date.
- Dropoff time.
- Driver age.

Preferred/required for generated options:

- Pay later.
- Free cancellation.
- No payment required now.
- Maximum charge cap when supplied.

Execution:

- Real provider submission is disabled.
- Dry-run execution only.
- Missing approval is reported in dry-run output and would block real execution.
- Options requiring payment now would block real execution.
- Options exceeding approved max charge would block real execution.

## Local Credential Policy

The user is comfortable with local credential storage for now, but the first implementation does not store or require car-rental credentials.

When credentials are added later:

- Store them locally only.
- Prefer provider tokens over usernames/passwords.
- Keep them server-side.
- Never expose them to the frontend.
- Never send them to a browser agent unless a specific provider flow requires it and the user approves.
- Replace local credential storage with a proper secret manager before production.

## Next Build Steps

1. Add frontend UI for car-rental reservation planning.
2. Add a real provider discovery layer for car rentals.
3. Research accessible car-rental APIs:
   - CarTrawler.
   - Rentalcars/Booking.com partner paths.
   - Expedia Rapid cars, if access is available.
   - Direct rental-provider affiliate/API paths.
4. Add provider readiness metadata for car rentals.
5. Add real execution only after:
   - final review screen exists,
   - explicit approval is persisted,
   - duplicate prevention is enforced,
   - cancellation/no-show policy is captured,
   - max charge cap is checked,
   - provider response is audited.

## Product Rule

The user can ask the product to book a car, but the system should first create a booking plan and require approval before any real reservation is submitted.
