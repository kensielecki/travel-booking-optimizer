# Travel Booking Optimizer Architecture Handoff

Last updated: 2026-06-02

## Latest Session Notes

- 2026-05-18: Added `backend/.env` support for local provider credentials.
- 2026-05-18: Configured and validated SerpApi Google Hotels live search. `/travel-search/hotels` now returns `provider="serpapi_google_hotels"` and `live=true` when `SERPAPI_API_KEY` is set.
- 2026-05-18: Verified a San Diego hotel query returned live Google Hotels results including Rancho Bernardo Inn, Hotel del Coronado, Paradise Point Resort & Spa, Catamaran Resort Hotel and Spa, and Hyatt Regency Mission Bay Spa and Marina.
- 2026-05-18: Combined `/travel-search/optimize` mixes live provider results, captured United balance, and Amex Travel credit. It only uses mock flight fallback when no live flight provider returns options.
- 2026-05-18: Added provider aggregation/status plumbing. Search responses now include per-provider status, category, latency, result count, and warnings. Amex Travel and Chase Travel are explicitly excluded as live inventory providers for now.
- 2026-05-18: Added Amadeus Flight Offers Search as a second flight provider behind the aggregator. It is disabled until `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` are configured.
- 2026-05-18: Added SerpApi Google Flights as the first live flight provider using the existing `SERPAPI_API_KEY`. Verified `/travel-search/flights` live for SFO to San Diego, returning Frontier, Southwest, and United nonstop options from Google Flights.
- 2026-05-18: Cleaned flight fallback behavior. Duffel and Amadeus now report disabled/failed without injecting mock fares when SerpApi returns live flight options. Deterministic `mock_flights` only appears when no live flight provider returns options.
- 2026-05-18: Added deterministic intent parsing for direct/nonstop, latest arrival time, hotel star floor, hotel travel-time preference, and budget. `/travel-search/parse-intent` exposes the parser, and `/travel-search/flights`, `/travel-search/hotels`, and `/travel-search/optimize` enrich requests before provider calls.
- 2026-05-18: Added Amadeus Hotel Search as a second hotel provider behind the same Amadeus credentials used for flight offers. It is disabled until `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` are configured.
- 2026-05-18: Cleaned hotel fallback behavior. SerpApi Google Hotels and Amadeus Hotels now report disabled/failed without injecting mock hotel rows when another live hotel provider returns options. Deterministic `mock_hotels` only appears when no live hotel provider returns options.
- 2026-05-18: Added Kiwi Tequila as another flight-search provider behind `KIWI_TEQUILA_API_KEY`. It is disabled until a Kiwi/Tequila key is configured.
- 2026-05-18: Product decision: Amadeus is deferred. Treat Amadeus as enterprise-sales gated, not a near-term V0 dependency. Do not ask the user to pursue Amadeus credentials for this stage.
- 2026-05-18: Duffel test API token is configured and accepted. Verified `/travel-search/flights` returns `duffel` provider status `live` with sandbox flight offers alongside SerpApi Google Flights.
- 2026-05-18: Added `docs/provider-access-matrix.md` to separate V0-friendly/self-serve providers from sales-gated providers. Booking.com Demand API and Expedia Rapid are research/partner-access candidates, not immediate V0 blockers.
- 2026-05-18: Improved optimizer preference scoring. Arrival-window matches now get a deterministic boost, late arrivals are penalized, and provider warnings no longer get copied into every recommendation card.
- 2026-05-18: Added LiteAPI/Nuitée as a key-gated hotel provider behind `LITEAPI_API_KEY`. Treat the current LiteAPI key path as sandbox-only until production access is explicitly confirmed.
- 2026-05-18: Added `docs/agentic-travel-discovery.md` to track AI-agent travel platforms, B2B agent services, and a repeatable product-discovery process.
- 2026-05-18: LiteAPI sandbox key is configured and accepted. Tuned the adapter to join `data[]` rate rows to `hotels[]` metadata and extract room name, total price, guest rating, refundability, and sandbox warning.
- 2026-05-18: Added provider confidence metadata to booking options and provider statuses. Recommendations now distinguish production, sandbox, mock, and unknown sources, and balanced scoring includes provider confidence so sandbox/mock prices do not quietly dominate live-market results.
- 2026-05-18: Added generated trip package options. `/travel-search/optimize` now synthesizes full trip paths by combining top flight and hotel options, carrying over offer value, provider confidence, source environment, fees, and key preference notes.
- 2026-05-18: Frontend now separates recommendations into `Full trip paths` and `Standalone options`, with local ranking per section and a visible full-trip-path badge.
- 2026-05-19: Added backend offer normalization/dedupe for captured offers so duplicate/noisy `Unknown merchant` rows do not dominate V0 demo state.
- 2026-05-19: Added `docs/v0-acceptance.md` with V0 scope, acceptance criteria, provider truth, and V1 candidates.
- 2026-05-19: Started V1 live-data hardening. Added provider readiness metadata so the app can show configured providers, sandbox/production state, and the next unlock without running a live search.
- 2026-05-19: Added `GET /travel-search/provider-readiness` and surfaced V1 readiness in the frontend. This makes SerpApi, Duffel, LiteAPI, Kiwi, Amadeus, and Google Maps status explicit.
- 2026-05-29: Verified LiteAPI returns hotel/rate rows for New York, but the configured key still starts with `sand_`, so the backend correctly classifies LiteAPI inventory as sandbox despite `LITEAPI_ENV=production`.
- 2026-05-29: Duffel live token is now configured. `/travel-search/provider-readiness` reports Duffel as `production`, and read-only flight search returns production Duffel offers. No order/booking calls have been made.
- 2026-05-29: LiteAPI production key is now being picked up from the local env configuration. `/travel-search/provider-readiness` reports LiteAPI as `production`, and read-only hotel search returns production LiteAPI hotel rates with `provider_confidence=0.85`.
- 2026-05-29: Added compatibility for the current local LiteAPI env shape where `LITEAPI_API_KEY` contains the sandbox key and `LITEAPI_ENV` contains the production key. Going forward, prefer `LITEAPI_PRODUCTION_API_KEY` for the production key and reserve `LITEAPI_ENV` for labels like `production`/`sandbox`.
- 2026-05-29: Updated the frontend from a generic recommendation list toward a prompt-to-itinerary workflow. The UI now has sample travel prompts, a `Build itinerary` action, a promoted recommended itinerary summary, and clearer production provider readiness.
- 2026-05-29: Added inline expandable itinerary cards. Clicking a recommendation reveals booking path, payment math, parsed trip legs, ranking reasons, and provider notes without creating any booking/order flow.
- 2026-05-29: Refreshed the frontend visual direction toward a slick minimalist workspace: removed the photographic background, added a crisper sticky top bar, widened the work area, tightened cards/forms, and introduced restrained teal/blue/orange accents.
- 2026-05-29: Changed local `.env` loading to override process environment on server restart, so provider key swaps are reflected reliably after restarting FastAPI.
- 2026-06-01: Product decision: keep Crossmint and Lobster Cash as the preferred future infrastructure direction for supervised agent payments and scoped virtual-card execution. They are a payment/checkout layer, not a live travel inventory source, and should only be introduced after explicit booking-review and approval flows exist.
- 2026-06-02: Added a lightweight brand system for Travel Booking Optimizer. The app now uses a custom route/payment intelligence mark instead of the generic plane icon, with brand assets in `frontend/public/brand/` and brand direction documented in `docs/brand-guidelines.md`.
- 2026-06-03: Expanded trip discovery beyond the original Bay Area candidate list. Discovery now detects Bay Area/default, United States, Europe, Southeast Asia, and global/international scopes, then searches a capped curated destination catalog rather than every possible destination.
- 2026-06-03: Added a discovery control layer. Each discovery request now builds a plan with scope, candidate-pool size, matched candidates, selected candidates, provider-call budget, estimated provider calls, and skipped candidate count. `DISCOVERY_PROVIDER_CALL_BUDGET` can cap live discovery breadth from environment config.

## Project Location

`/Users/kensielecki/codex projects/travel-booking-optimizer`

## Product Goal

Build a travel and loyalty optimization platform. The user enters a trip intent such as:

> Weekend trip to NYC using United + Hilton with a ~$2,000 equivalent budget.

The system should compare cash bookings, points redemptions, transfer routes, active card offers, credits, and convenience tradeoffs, then recommend the best booking/payment path.

This is not primarily a points-balance tracker. Balances and offers are inputs to a travel shopping optimizer.

## Current Working Prototype

The local app currently has:

- FastAPI backend.
- Next.js frontend.
- Chrome extension for local-session loyalty/offer capture.
- Local JSON-backed dev persistence.
- Deterministic optimization engine.
- Mock/manual ingestion.
- Live-search provider abstraction for flights and hotels.
- Fallback mock flight/hotel results when live API keys are absent.

Current local URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`

## Current Captured Data

Known local demo user:

`11111111-1111-4111-8111-111111111111`

Captured/corrected balances:

- United MileagePlus: `20,826`
- Chase Ultimate Rewards: `24,224`
- Amex Membership Rewards: `6,363`

Known offers/credits include:

- Amex Travel hotel credit: up to `$300`
- Trafalgar: spend `$1,000`, get `$200`
- Caesars Rewards Select Destinations: spend `$200`, get `$40`
- Some noisy older Amex offer captures with `Unknown merchant`; these should be cleaned/deduped.

## Key Architecture Decisions

1. Deterministic math owns valuation.
   AI may explain/rank edge cases later, but cents-per-point, out-of-pocket, fees, offer value, and savings are deterministic.

2. Extension-first ingestion.
   The browser extension reads visible page text from the user's own session. It does not export cookies, replay sessions, store passwords, store 2FA, or run cloud login automation.

3. APIs for live travel search where possible.
   Current provider boundary supports:
   - Flights: SerpApi Google Flights via `SERPAPI_API_KEY`
   - Flights: Kiwi Tequila via `KIWI_TEQUILA_API_KEY`
   - Flights: Duffel via `DUFFEL_API_TOKEN`
   - Flights: Amadeus Flight Offers via `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` (implemented but deferred; enterprise-sales gated)
   - Hotels: SerpApi Google Hotels via `SERPAPI_API_KEY`
   - Hotels: LiteAPI/Nuitée via `LITEAPI_API_KEY`
   - Hotels: Amadeus Hotel Search via `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` (implemented but deferred; enterprise-sales gated)
   - Location scoring: Google Maps/Places via `GOOGLE_MAPS_API_KEY` (scaffolded, not yet used in ranking)

The readiness endpoint is:

- `GET /travel-search/provider-readiness`

It does not call provider APIs. It only reads local configuration and returns provider role, environment, and next action.

4. Browser/agent automation should be assistive, not the production backbone.
   It can help with user-guided portal workflows, but official APIs are preferred for repeatable search.

5. Booking is not V0.
   V0 should recommend and deep-link/manual-book. In-app booking is a later product because it involves payments, cancellation handling, user profile data, supplier terms, and support workflows.

6. Payment-agent infrastructure is planned for later.
   Crossmint and Lobster Cash are the preferred future candidates for agent-assisted payment permissions, virtual cards, and scoped checkout execution. They should sit after deterministic search/ranking and final user approval, not replace travel inventory providers. See `docs/payment-agent-infrastructure.md`.

## Important Files

Backend:

- `backend/app/main.py`
- `backend/app/models/domain.py`
- `backend/app/core/optimizer.py`
- `backend/app/core/live_travel_search.py`
- `backend/app/core/ota_shopping.py`
- `backend/app/api/travel_search.py`
- `backend/app/api/shopping.py`
- `backend/app/api/ingestion.py`
- `backend/app/ingestion/manual.py`
- `backend/db/schema.sql`

Frontend:

- `frontend/src/app/page.tsx`
- `frontend/src/components/trip-optimizer.tsx`
- `frontend/src/components/recommendation-card.tsx`
- `frontend/src/components/account-balance-editor.tsx`
- `frontend/src/lib/types.ts`

Extension:

- `extension/manifest.json`
- `extension/parser.js`
- `extension/popup.js`
- `extension/popup.html`
- `extension/tests/parser.test.js`

Docs:

- `docs/rebuild-plan.md`
- `docs/browser-extension.md`
- `docs/live-amex-test.md`
- `docs/architecture-handoff.md`
- `docs/provider-access-matrix.md`
- `docs/agentic-travel-discovery.md`
- `docs/v0-acceptance.md`

## Current API Surface

Health:

- `GET /health`

Ingestion:

- `POST /ingestion/manual`
- `GET /ingestion/state/{user_id}`
- `DELETE /ingestion/state/{user_id}`
- `PATCH /ingestion/state/{user_id}/accounts/{program}`

Optimization:

- `POST /trip-intents/optimize`
- `POST /shopping/optimize`

Live search:

- `POST /travel-search/flights`
- `POST /travel-search/hotels`
- `POST /travel-search/parse-intent`
- `POST /travel-search/optimize`

`/travel-search/optimize` is the current best endpoint for V0 live search. It accepts a `TravelOptimizationRequest`, runs flight/hotel providers, applies offers/credits, adds loyalty award comparisons where possible, and ranks results.

Travel search responses now include provider health metadata:

- `provider`
- `category`
- `status`: `live`, `fallback`, `failed`, or `disabled`
- `latency_ms`
- `result_count`
- `warnings`

## Provider Strategy

Current implemented providers:

- SerpApi Google Flights when `SERPAPI_API_KEY` exists. This has been tested live successfully.
- Kiwi Tequila Flights when `KIWI_TEQUILA_API_KEY` exists.
- Duffel for flight search when `DUFFEL_API_TOKEN` exists. A test token is configured and has been verified live against sandbox offers.
- Amadeus Flight Offers Search when `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` exist. This is implemented but deferred because access is enterprise-sales gated for this project stage.
- SerpApi Google Hotels when `SERPAPI_API_KEY` exists. This has been tested live successfully.
- LiteAPI/Nuitée Hotels when `LITEAPI_API_KEY` exists. Treat this as sandbox inventory until production LiteAPI access is explicitly confirmed.
- Amadeus Hotel Search when `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` exist. This is implemented but deferred because access is enterprise-sales gated for this project stage.
- Deterministic `mock_flights` only when no live flight provider returns options.
- Deterministic `mock_hotels` only when no live hotel provider returns options.

Explicitly excluded from V0 live inventory providers:

- Amex Travel portal
- Chase Travel portal
- Logged-in portal scraping
- Screenshots/PDF capture as live pricing sources

These sources may still provide balances, offers, credits, or manual comparison data, but they should not be treated as live inventory providers until a clean official integration path exists.

Recommended next provider review:

- Hotels:
  - SerpApi Google Hotels for fastest V0 live search.
  - LiteAPI/Nuitée as the next likely developer-friendly hotel rates/availability API.
  - Expedia Rapid, Booking.com Demand API, Hotelbeds for fuller production inventory/booking once partner access is clear.
  - Do not prioritize Amadeus in V0 unless enterprise access becomes available later.
- Flights:
  - Duffel for modern search and eventual booking.
  - Kiwi Tequila as an additional accessible search source if a key is available.
  - Travelport if going more enterprise/GDS.
  - Do not prioritize Amadeus in V0 unless enterprise access becomes available later.

## Preference And Ranking Direction

The product should distinguish:

- Hard constraints:
  - Dates
  - Budget ceiling
  - Direct flights only
  - Arrival before a specific time
  - Minimum hotel star rating
  - Maximum distance/time from target location

- Soft preferences:
  - Prefer United
  - Prefer Hilton/Marriott/Hyatt
  - Prefer direct flights
  - Prefer morning arrival
  - Prefer refundable
  - Prefer Amex Travel if a credit applies

The future ranking model should show:

- Best Match
- Best Value
- Worth Considering

Non-preferred options should still appear when they are materially better, for example saving `$300+`, arriving much earlier, or producing a materially higher cents-per-point value.

## Current Known Gaps

1. Full-trip package ranking is early.
   The backend now generates combined flight + hotel trip paths, and the frontend separates full-trip paths from standalone options. Next step is category-aware ranking inside each section.

2. Flight live search is now available through SerpApi Google Flights.
   Duffel and Amadeus remain unconfigured, so they are optional next providers rather than blockers.

3. Prompt parsing is intentionally basic but now active.
   It handles common constraints such as direct/nonstop, arrival before midday/specific time, hotel star floor, hotel travel-time preference, and budget. It does not yet infer destination/date ranges from fully freeform text.

4. Hotel live results are not yet location-intelligent.
   Need distance/time from target location, neighborhoods, and amenity extraction.

5. Flight live results need stronger schedule scoring.
   Need duration, departure/arrival windows, layover counts, layover duration, cabin, fare class, baggage/seat fees.

6. Loyalty award availability is not truly live.
   The backend can add a United award comparison based on captured balance and cash fare context, but real United award availability still needs a provider or user-guided portal confirmation.

7. Offers are noisy.
   Earlier Amex extraction produced duplicate/unknown merchant offers. Need offer dedupe, merchant normalization, eligibility flags, and expiration handling.

8. Persistence is local JSON only.
   Need Supabase/Postgres persistence before beta.

9. No auth/multi-user model yet.
   The app uses a fixed demo user ID.

10. No booking.
   Current scope is recommendation and comparison, not transaction completion.

## Recommended V0 Next Steps

1. Deepen structured prompt parsing.
   Add destination/date extraction, chain preferences, refundable/flexible preferences, and target-address/neighborhood parsing.

2. Improve provider status UX.
   The UI already shows provider statuses; next, group them by flights/hotels and hide disabled-provider noise behind details.

3. Improve hotel ranking.
   Add star rating, distance/time, neighborhood, refundable status, property benefits, and chain preference.

4. Improve flight ranking.
   Add schedule fit, stops, layover duration, departure/arrival times, cabin, and airline preference.

5. Add a second live flight provider.
   Prefer Duffel next because it can support eventual booking flows more cleanly than a search-only provider.

6. Clean offers.
   Deduplicate Amex offer captures and normalize travel-credit offers separately from merchant offers.

7. Add Chase UR transfer logic.
   Especially Chase to United/Hyatt style paths.

## Suggested V1 Direction

- Supabase/Postgres persistence.
- Real user auth.
- Durable trip searches.
- Saved user travel preferences.
- Provider credentials/config management.
- Better browser extension ingestion by program.
- Manual review/correction workflows.
- Deep links to book manually.

## Suggested Later Versions

V2:

- Assisted booking co-pilot.
- Open selected booking path.
- Autofill search parameters where allowed.
- Verify final price changed or not.
- User confirms all purchases manually.

V3:

- In-app booking via provider APIs.
- Traveler profiles.
- Payment handling through scoped payment-agent infrastructure such as Crossmint and Lobster Cash, subject to provider acceptance and compliance review.
- Cancellation/modification flows.
- Support workflow.
- Compliance/security review.

## Review Questions For Another Model Or Architect

1. Is Duffel plus SerpApi a good V0 provider stack, or should hotels start with Expedia/Booking/Hotelbeds despite onboarding friction?
2. Should Amex/Chase Travel portal search remain extension-assisted, or should the product avoid portal-specific search until partner access exists?
3. What is the cleanest preference scoring model for hard constraints vs soft preferences?
4. Should award availability be modeled as estimated until confirmed, or excluded unless confirmed live?
5. What is the right database schema for search results, recommendations, provider responses, and ingestion runs?
6. What should be cached, and for how long, given travel prices change quickly?
7. Where should AI be allowed to influence ranking, if at all, versus only explanation?

## Verification Commands

Backend tests:

```bash
cd "/Users/kensielecki/codex projects/travel-booking-optimizer/backend"
.venv/bin/python -m pytest tests
```

Frontend build:

```bash
cd "/Users/kensielecki/codex projects/travel-booking-optimizer/frontend"
npm run build
```

Extension parser:

```bash
cd "/Users/kensielecki/codex projects/travel-booking-optimizer"
node extension/tests/parser.test.js
```

Run backend:

```bash
cd "/Users/kensielecki/codex projects/travel-booking-optimizer/backend"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run frontend:

```bash
cd "/Users/kensielecki/codex projects/travel-booking-optimizer/frontend"
npm run dev
```
