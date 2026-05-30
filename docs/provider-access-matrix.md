# Travel Provider Access Matrix

Last updated: 2026-05-19

This file tracks which travel inventory providers are practical for V0 versus gated behind sales, account managers, certification, or enterprise contracts.

## V0-Friendly Or Currently Usable

| Provider | Category | Access model | V0 status | Notes |
| --- | --- | --- | --- | --- |
| SerpApi Google Flights | Flights | Self-serve key, free tier and paid plans | Active | Good broad market signal. Search-only; not booking-capable. |
| SerpApi Google Hotels | Hotels | Self-serve key, free tier and paid plans | Active | Good V0 hotel-shopping source. Search-only; not booking-capable. |
| Duffel | Flights | Self-serve test token; live activation later | Active in test mode | Good flight booking-capable candidate. Current token returns sandbox inventory. |
| Kiwi Tequila | Flights | Self-serve key expected | Adapter ready | Useful as a second accessible flight source once a key is added. |
| LiteAPI / Nuitée | Hotels | Developer-oriented onboarding and sandbox key | Active in sandbox | Strong next hotel API candidate. Backend supports `LITEAPI_API_KEY`; treat current key as sandbox until `LITEAPI_ENV=production` and production access are explicitly enabled. |
| Hotelbeds APItude | Hotels, activities, transfers | Free API key/evaluation environment, certification later | Candidate | Strong hotel-supply candidate; docs mention evaluation keys and test environment. |
| FlightAPI.io | Flights | Self-serve trial/paid API | Candidate | Possible backup flight-price source; verify data coverage and booking limitations. |
| MakCorps | Hotels | Self-serve/trial hotel price comparison API | Candidate | Useful hotel price intelligence; likely not booking-capable. |
| Aviationstack / AirLabs | Aviation data | Self-serve free/paid tiers | Enrichment only | Useful for schedule/status/reliability, not shopping/booking. |
| Google Places / Maps | Location data | Self-serve cloud API | Readiness scaffolded | Important for "within 20 minutes of X" hotel ranking. Backend readiness tracks `GOOGLE_MAPS_API_KEY`; scoring is not wired yet. |

## Partner Or Sales-Gated

| Provider | Category | Access model | V0 status | Notes |
| --- | --- | --- | --- | --- |
| Booking.com Demand API | Hotels, cars, attractions, some connected trip inventory | Managed Affiliate Partner + Partner Centre access from Booking.com account manager | Research only | Not a simple self-serve API. Good to pursue if user can get affiliate/API access. |
| Expedia Rapid API | Hotels | Apply/become partner; credentials after approval; consultant/account-manager model | Research only | Strong production hotel source, but not a quick V0 dependency. |
| Amadeus | Flights/hotels | Enterprise-sales gated for the useful scope in this project | Deferred | Do not ask user to chase Amadeus for V0. Keep code path parked. |
| Travelport / Sabre | Flights/hotels/GDS | Enterprise/GDS commercial relationship | Later | Relevant only when the product moves toward agency/GDS-grade inventory. |
| Tripgic / Tripedge / Volero | Unified B2B travel APIs | Sales/onboarding-led | Research only | Potentially useful later for broader supply or white-label booking capabilities. |
| Boxcribe / MustSeen / Nowah | Agentic travel infrastructure | Demo/API access unclear or sales-led | Strategic watchlist | Interesting for AI-agent execution and validation, but not a V0 dependency. |

## Current Recommendation

Short term:

1. Keep SerpApi as the live market-price signal for flights and hotels.
2. Use Duffel test mode to build flight booking-capable workflows safely.
3. Evaluate LiteAPI/Nuitée next for hotel availability/rates because it looks more developer-friendly than Booking.com or Expedia.
4. Evaluate Hotelbeds APItude as a second hotel-supply path because it advertises evaluation keys.
5. Keep Booking.com and Expedia in the research lane until partner access is clear.

Do not build V0 around any provider that requires account-manager approval before we can test a real query.

## Sources

- SerpApi pricing: https://serpapi.com/pricing
- Duffel test mode: https://duffel.com/docs/api/overview/test-mode/duffel-airways
- Duffel dashboard tokens: https://duffel.com/docs/guides/getting-started-with-the-dashboard
- Booking.com Demand API prerequisites: https://developers.booking.com/demand/docs/getting-started/prerequisites
- Booking.com Demand API overview: https://developers.booking.com/demand/docs/open-api/demand-api
- Expedia Rapid getting started: https://developers.expediagroup.com/docs/products/rapid/setup/getting-started?locale=en_US
- Expedia Rapid partner signup: https://partner.expediagroup.com/en-gb/join-us/rapid-api
- LiteAPI hotel rates: https://docs.liteapi.travel/reference/post_hotels-rates
- LiteAPI pricing and usage: https://docs.liteapi.travel/reference/api-pricing-usage-costs
- Hotelbeds getting started: https://developer.hotelbeds.com/documentation/getting-started/
- Hotelbeds developer portal: https://developer.hotelbeds.com/
- Boxcribe: https://www.boxcribe.com/
- MustSeen: https://www.must-seen.com/
- Tripedge: https://tripedge.com/
