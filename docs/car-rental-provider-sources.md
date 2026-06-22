# Car Rental Provider Sources

Last updated: 2026-06-22

## Current Product Position

The car-rental reservation agent currently returns provider check options, not confirmed live inventory. Each option has a booking/check URL and is marked as handoff inventory until we connect a real car API.

This is deliberate because rental cars can create financial obligations through deposits, no-show terms, insurance choices, cancellation windows, and payment/card authorizations.

## Browser Automation Experiment

On 2026-06-22, a controlled TinyFish scrape was tested against Kayak Cars with SFO midsize-car criteria. The request reached TinyFish but timed out before returning a completed structured result, so the backend correctly fell back to provider handoff checks.

Implication: TinyFish is useful to keep as a fast experimental lane, but the next reliability step is either provider-specific prompts/scripts or Browserbase/Stagehand-style controlled browser sessions. Browser results must remain labeled `browser_scraped_unverified_inventory` until the user reopens the provider page and confirms the rate, terms, and final total.

## Provider Matrix

| Provider | Type | Current product use | API/inventory path | Notes |
| --- | --- | --- | --- | --- |
| Booking.com Cars | Aggregator/API candidate | Handoff link now | Demand API Cars | Strongest near-term API candidate. Stable search/look/redirect is supported; end-to-end API booking is beta and permissioned. |
| Expedia Cars | Aggregator/API candidate | Handoff link now | Expedia Group Rapid Cars, if partner access is approved | Useful for broad OTA inventory if available. Treat as partner-gated until credentials and docs access are confirmed. |
| Kayak Cars | Metasearch | Handoff link now | Public car booking API not confirmed | Useful comparison surface, but booking terms depend on the onward provider. |
| National | Direct brand | Handoff link now | Partner/commercial access, if available | Good fit for loyalty-aware checks through Emerald Club, but direct public API access is not confirmed. |
| Avis | Direct brand | Handoff link now | Partner/commercial access, if available | Direct check should verify rate type, taxes, cancellation, and preferred profile benefits. |
| Enterprise | Direct brand | Handoff link now | Partner/commercial access, if available | Useful direct baseline, especially for local and airport pickup. |
| Hertz | Direct brand | Handoff link now | Partner/commercial access, if available | Useful direct baseline and loyalty profile path. |
| Budget | Direct brand | Handoff link now | Avis Budget commercial path, if available | Often useful as lower-cost direct option. |
| Alamo | Direct brand | Handoff link now | Enterprise Mobility commercial path, if available | Often useful for leisure trips. |
| Sixt | Direct brand | Handoff link now | Partner/commercial access, if available | Useful for premium/luxury inventory. |
| CarTrawler | B2B mobility platform | Not implemented | Enterprise/partner path | Potentially strong car-rental infrastructure provider, but not self-serve in the same way as LiteAPI/Duffel. |
| TinyFish | Browser automation | Experimental browser search | `TINYFISH_API_KEY` | Fastest path to scrape public rental results, but outputs must be marked unverified and re-opened before approval. |
| Browserless | Managed browser automation | Experimental browser search | `BROWSERLESS_API_TOKEN` | Implemented as a REST browser function. Better fit than TinyFish for provider-specific scripts because we control the extraction code. |
| Browserbase | Cloud browser automation | Candidate, not implemented | `BROWSERBASE_API_KEY` | Stronger longer-term browser-agent infrastructure with sessions, observability, and Stagehand-style automation. |

## Recommendation

1. Use Booking.com Cars as the first real car inventory integration if partner access is practical.
2. Keep Expedia Rapid Cars as second priority if the user can get partner access.
3. Keep National, Avis, Enterprise, Hertz, Budget, Alamo, Sixt, Expedia, and Kayak as handoff/direct-check options so the agent can still help the user compare quickly.
4. Use Browserless first for browser-scraped public result discovery because it gives us code-level control of the browser function. Keep TinyFish as a secondary experimental lane, then Browserbase if we need more controlled sessions, observability, or Stagehand workflows.
5. Add an inventory-truth label to every result:
   - `live_api_inventory`
   - `redirect_api_inventory`
   - `browser_scraped_unverified_inventory`
   - `direct_brand_handoff`
   - `aggregator_handoff`
   - `estimated_placeholder`
6. Never allow a booking agent to submit a car reservation until the option includes cancellation/no-show terms, final total, provider reference, and explicit user approval.

## Next Implementation Hooks

- Add a `car_rental_providers` readiness endpoint.
- Add frontend support for `/reservations/car-rentals/browser-search`.
- Add a live provider adapter interface:
  - `search(intent) -> list[ReservationOption]`
  - `details(option_ref) -> ReservationOption`
  - `terms(option_ref) -> ProviderTerms`
  - `reserve(approved_option, approval) -> ReservationRecord`
- Add `BookingCarsProvider` once credentials are available.
- Add a frontend car-rental search panel with pickup location, dropoff location, dates/times, driver age, vehicle class, max total, and source filters.
