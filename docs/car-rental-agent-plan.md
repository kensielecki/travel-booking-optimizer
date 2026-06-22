# Car Rental Reservation Agent Plan

Last updated: 2026-06-22

## Current Status

The first car-rental agent layer is implemented as a safe backend skeleton. It can:

- Create a car-rental reservation plan.
- Generate pay-later/free-cancellation car-rental provider check options.
- Apply guardrails before queueing.
- Queue a selected option for review.
- Record explicit approval.
- Execute a dry run.
- Persist queue, approval, and dry-run audit state locally.

It cannot yet submit a real provider booking. It also does not yet confirm live car inventory from a connected car API. That is intentional.

An experimental browser-search endpoint now exists for faster inventory discovery:

```http
POST /reservations/car-rentals/browser-search
```

This can use TinyFish when `TINYFISH_API_KEY` is configured. Browser-scraped results are labeled as unverified and must be reopened before approval. This endpoint must not log in, reserve, enter payment, or click final booking buttons.

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

Browser search readiness:

```http
GET /reservations/car-rentals/browser-readiness
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
- Booking/check URL supplied for manual verification.

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
2. Add frontend UI for experimental browser-scraped car-rental discovery.
3. Add provider readiness metadata for car rentals.
4. Connect the first real car inventory API once access is available.
5. Add real execution only after:
   - final review screen exists,
   - explicit approval is persisted,
   - duplicate prevention is enforced,
   - cancellation/no-show policy is captured,
   - max charge cap is checked,
   - provider response is audited.

## Product Rule

The user can ask the product to book a car, but the system should first create a booking plan and require approval before any real reservation is submitted.

## Car Rental Source Strategy

The product now separates provider checks from confirmed inventory:

| Source | Current use | Access notes | Product label |
| --- | --- | --- | --- |
| National | Direct handoff/check link | Direct public inventory API not confirmed; likely partner/commercial route. | Direct brand check |
| Avis | Direct handoff/check link | Direct public inventory API not confirmed; likely partner/commercial route. | Direct brand check |
| Enterprise | Direct handoff/check link | Direct public inventory API not confirmed; likely partner/commercial route. | Direct brand check |
| Hertz | Direct handoff/check link | Direct public inventory API not confirmed; likely partner/commercial route. | Direct brand check |
| Budget | Direct handoff/check link | Same Avis Budget family; public inventory API not confirmed. | Direct brand check |
| Alamo | Direct handoff/check link | Enterprise Mobility family; public inventory API not confirmed. | Direct brand check |
| Sixt | Direct handoff/check link | Public booking site available; API access requires partner validation. | Direct brand check |
| Expedia | Aggregator handoff/check link now; possible API path later. | Expedia Group Rapid includes a Cars API for search/details/booking flows, but access requires partner setup. | Aggregator check |
| Kayak | Aggregator handoff/check link now. | Useful metasearch UI; public booking API access is not confirmed. | Aggregator check |
| Booking.com Cars | Aggregator handoff/check link now; possible API path later. | Demand API exposes cars search/details; car orders are currently beta/permissioned. | API candidate |
| TinyFish | Browser automation. | Requires `TINYFISH_API_KEY`; implemented as experimental browser search. | Browser scrape, unverified |
| Browserbase | Browser automation candidate. | Requires `BROWSERBASE_API_KEY`; not implemented yet. | Browser scrape candidate |

For V0/V1, these checks are useful for quickly opening the right provider pages, but the returned prices are estimated placeholders and must be verified before queueing or approving a reservation. Once a real car inventory API is connected, options from that provider should be labeled `production` and should include provider references, cancellation/no-show terms, taxes, fees, and final total.
