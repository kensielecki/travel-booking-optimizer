# V0 Acceptance Checklist

Last updated: 2026-05-19

V0 is a demoable travel and loyalty optimizer. It is not a production booking engine.

## V0 User Story

A user can enter a trip intent such as:

> Direct weekend flight and 4 star hotel in San Diego around $2,000. Arrive before midday.

The app should return ranked payment/trip paths using live travel search, captured loyalty data, card offers, and deterministic math.

## In Scope

- Live flight price signal through SerpApi Google Flights.
- Live hotel market signal through SerpApi Google Hotels.
- Duffel sandbox flight offers for booking-workflow validation.
- LiteAPI/Nuitée sandbox hotel rates for booking-workflow validation.
- Local browser-extension ingestion for visible loyalty balances and offers.
- Manual balance correction for parser ambiguity.
- Deterministic cents-per-point and effective-savings calculations.
- Full trip path generation from flight + hotel combinations.
- Provider status, environment, and confidence labels.
- Offer-enhanced hotel/payment-path recommendations.
- Basic prompt parsing for direct/nonstop, arrival window, hotel star floor, travel-time preference, and budget.
- Local JSON persistence for demo state.

## Out Of Scope

- Real booking completion.
- Payment collection.
- Production Duffel ticketing.
- Production LiteAPI hotel booking.
- Amex Travel or Chase Travel portal automation.
- Cookie/session replay.
- Cloud-browser authenticated scraping.
- Enterprise-only providers such as Amadeus, Travelport, Sabre.
- Full Supabase/auth deployment.

## Acceptance Criteria

- Backend starts locally at `http://127.0.0.1:8000`.
- Frontend starts locally at `http://localhost:3000`.
- `/health` returns `{"status":"ok"}`.
- `/travel-search/flights` returns live SerpApi results and Duffel sandbox status when keys are present.
- `/travel-search/hotels` returns live SerpApi hotel results and LiteAPI sandbox status when keys are present.
- `/travel-search/optimize` returns both:
  - Full trip paths.
  - Standalone options.
- Recommendations expose:
  - Out-of-pocket cost.
  - Cents-per-point when points are used.
  - Effective savings.
  - Provider confidence.
  - Source environment.
- Captured noisy offers are normalized/deduped enough that obvious duplicate `Unknown merchant` rows do not dominate the UI.
- Backend tests pass.
- Frontend build passes.

## Current Provider Truth

| Provider | Environment | V0 role |
| --- | --- | --- |
| SerpApi Google Flights | Production search signal | Real market flight prices. |
| SerpApi Google Hotels | Production search signal | Real market hotel prices. |
| Duffel | Sandbox | Flight booking workflow validation. |
| LiteAPI/Nuitée | Sandbox | Hotel booking workflow validation. |
| Kiwi Tequila | Disabled until key | Backup flight source. |
| Amadeus | Deferred | Enterprise/sales-gated; not V0. |
| Booking.com Demand API | Research only | Partner/account-manager access. |
| Expedia Rapid | Research only | Partner/sales access. |

## What Would Make V0 Feel Finished

1. Confirm the default UI intent produces useful full-trip paths.
2. Confirm captured balances/offers are clean enough for demo use.
3. Add one short “why this wins” explanation block for each top trip path.
4. Add a small provider health/legend panel explaining production vs sandbox.
5. Run one final end-to-end demo path and capture screenshots.

## V1 Candidates

- True hotel location scoring using Google Maps/Places.
- Better full-trip package ranking.
- Offer merchant normalization and expiration handling.
- Supabase/Postgres persistence.
- Auth/multi-user support.
- Deep links or booking handoff flows.
- Production activation for Duffel and LiteAPI if commercially appropriate.
