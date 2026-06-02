# V1 Live Data Plan

Last updated: 2026-06-01

## Goal

Move from a demoable optimizer to a live travel-search product with clear provider truth:

- Production live market signals for flights and hotels.
- Sandbox sources clearly marked as sandbox.
- Mock fallback only when no live or sandbox source returns usable results.
- Readiness shown in the UI so the team knows which provider unlock comes next.

## Current Provider Roles

| Provider | Category | Current role | Environment rule |
| --- | --- | --- | --- |
| SerpApi Google Flights | Flight | Production market-price baseline | Production when `SERPAPI_API_KEY` is set |
| SerpApi Google Hotels | Hotel | Production hotel market-price baseline | Production when `SERPAPI_API_KEY` is set |
| Duffel | Flight | Flight offers and future booking/order path | Sandbox for `duffel_test_*`, production for `duffel_live_*` |
| LiteAPI/Nuitee | Hotel | Hotel rates and future booking path | Sandbox by default, production when `LITEAPI_ENV=production` |
| Kiwi Tequila | Flight | Optional second flight-search source | Production when `KIWI_TEQUILA_API_KEY` is set |
| Google Maps | Location | Hotel distance and travel-time scoring | Production when `GOOGLE_MAPS_API_KEY` is set |
| Amadeus | Flight/hotel | Deferred fallback candidate | Keep deferred for now |

## V1 Build Order

1. Provider readiness
   - Add `/travel-search/provider-readiness`.
   - Show configured providers and sandbox/production state in the frontend.
   - Keep credentials server-side only.

2. Location intelligence
   - Add a target-location field to trip intent/search.
   - Use Google Maps/Places for hotel proximity and travel time.
   - Score hotels against constraints like “within 20 minutes of SoHo.”

3. Production hotel path
   - Continue with SerpApi Google Hotels for market pricing.
   - Switch LiteAPI/Nuitee from sandbox to production when access is approved.
   - Keep Hotelbeds as the next hotel provider to evaluate if LiteAPI production access is delayed.

4. Production flight path
   - Keep SerpApi Google Flights as flight discovery baseline.
   - Use Duffel sandbox for offer-shape testing.
   - Move to Duffel live only when booking/payment/support workflow is intentionally in scope.

5. Award availability
   - Add real airline/hotel award search separately from cash travel search.
   - Keep award math deterministic.
   - Treat portal-specific redemptions like Amex Travel and Chase Travel as separate integrations, not screenshots.

## Acceptance Criteria

- The UI shows whether each provider is production, sandbox, or missing.
- Optimization results label the source environment on every recommendation.
- Production and sandbox prices are not treated as equally reliable in ranking.
- Mock options appear only as fallback.
- No credentials or captured user secrets are exposed to the browser.

## Payment-Agent Note

Crossmint and Lobster Cash are reserved for the later supervised payment layer, not V1 inventory search. Use them as candidate infrastructure for scoped virtual cards, agent payment permissions, and checkout execution after the app has final booking-review screens, explicit user approval, and payment audit records.

See `docs/payment-agent-infrastructure.md`.
