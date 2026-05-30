# Agentic Travel Product Discovery

Last updated: 2026-05-18

This file tracks how to discover APIs, B2B services, and AI-agent infrastructure for the loyalty optimizer.

## Discovery Goal

Find providers that can help us move from:

> Search live flight/hotel prices and recommend payment paths.

to:

> Let an AI-assisted product plan, compare, validate, and eventually book travel with deterministic controls.

## Market Map

### 1. Raw Inventory APIs

These provide prices, availability, rates, or offers. They are the base layer.

Current/near-term examples:

- SerpApi Google Flights
- SerpApi Google Hotels
- Duffel
- Kiwi Tequila
- LiteAPI / Nuitée

Best use:

- V0 shopping and comparison.
- Live price signal.
- Deterministic ranking inputs.

Key evaluation questions:

- Is access self-serve?
- Is the API search-only or booking-capable?
- Does it return taxes, fees, fare rules, cancellation terms, baggage, room policies, and deep links?
- Is data production or sandbox?
- Are commercial terms compatible with a consumer loyalty-optimizer product?

### 2. Partner/Sales-Gated Inventory Platforms

These can be strong later, but should not block V0.

Examples:

- Booking.com Demand API
- Expedia Rapid
- Hotelbeds
- Travelport
- Sabre
- Amadeus

Best use:

- Later production inventory expansion.
- Booking-capable hotel/flight flows once the business model and compliance posture are clearer.

Key evaluation questions:

- Do they accept early-stage startups?
- Do they require booking volume, agency credentials, IATA/ARC, or account-manager approval?
- Is there a sandbox before commercial approval?
- Can we show inventory without taking payment?

### 3. AI-Agent Travel Execution Layers

These are newer platforms built around AI agents, MCP tools, normalized schemas, or travel-specific orchestration.

Examples to investigate:

- Boxcribe
- Nowah
- Telivity / OTAIP
- Tripgic
- Avigate
- AMGiNE
- MustSeen

Best use:

- Learning architecture patterns.
- Possible acceleration if they expose useful APIs/MCP tools.
- Later booking orchestration if they can handle supplier integrations, PNR/order flows, settlement, changes, refunds, and policy checks.

Key evaluation questions:

- Do they expose an API, MCP server, SDK, or only a managed service?
- Do they have real inventory access or just orchestration?
- Are they search-only, booking-capable, or post-booking capable?
- Can we keep deterministic math and audit logs?
- Can our app remain the product UX, or do they require white-labeling their UI?
- Do they support consumer travel, corporate travel, or travel agencies only?

## Initial Agent-Oriented Watchlist

| Provider | Positioning | Access signal | Initial fit |
| --- | --- | --- | --- |
| Boxcribe | AI-native travel API / agentic GDS | Request demo | Worth investigating for agent-ready schemas and supplier aggregation. Likely B2B/sales-led. |
| Nowah | Travel API and MCP server for AI agents | Platform/API positioning | Very relevant if MCP/API access is real and accessible. Investigate pricing and sandbox. |
| Telivity / OTAIP | Open-core AI travel agent framework | Open source plus managed service | Strong architecture-learning candidate. Could inform our deterministic agent workflow. |
| Tripgic | Unified API for flights, hotels, cars, activities | Book session for API access | Potential aggregator, but sales/onboarding-led. |
| Avigate | Airline supply API and agents marketplace | Sign up / demo / contact sales | Relevant for airline supply, probably B2B travel-seller oriented. |
| AMGiNE | AI automation for TMCs/corporate travel | Enterprise/TMC-oriented | Useful reference, likely not a V0 integration. |
| MustSeen | Execution layer for AI-powered travel | B2B/developer positioning | Investigate whether it provides useful bookable itinerary APIs. |

## Expanded Provider Assessment

### Best Near-Term Fits

| Provider | Type | Why it matters | Access | Fit | Next action |
| --- | --- | --- | --- | --- | --- |
| SerpApi | Search data API | Already gives live Google Flights and Hotels market signal. | Self-serve | High for V0 search, low for booking | Keep as current live shopping baseline. |
| Duffel | Flight search and booking API | Modern flight API with test mode, live activation path, NDC/order model. | Self-serve test; live approval later | High for flight workflow/prototype | Use sandbox to build offer/order abstractions; do not treat sandbox fares as real market prices. |
| LiteAPI / Nuitée | Hotel rates, booking, management | Explicitly positioned for programmable/agentic hotel booking workflows. | Free sandbox / developer onboarding | High for hotels | Test sandbox key, then add production-readiness checks. |
| Hotelbeds | Hotel, activities, transfers APIs | Broad B2B travel supply with evaluation environment and booking APIs. | Registration gives evaluation keys; certification for more | Medium-high | Investigate after LiteAPI; promising if evaluation access is easy. |
| Kiwi Tequila | Flight search API | Accessible alternative flight source, useful for comparison and coverage. | Key-gated | Medium | Add key if available; validate price quality and terms. |
| FlightAPI.io | Flight price/status/schedule API | Self-serve trial and paid tiers; search/pricing data. | Free trial, paid self-serve | Medium | Evaluate as backup flight-price source, but likely search-only. |
| MakCorps | Hotel price comparison API | Pulls prices from many OTAs, useful as price-intelligence signal. | API key / trial | Medium | Evaluate as hotel price comparator, not booking engine. |

### Agentic / AI-Native Infrastructure

| Provider | Type | Why it matters | Access | Fit | Next action |
| --- | --- | --- | --- | --- | --- |
| Boxcribe | Agentic GDS / AI-native travel API | Claims unified API, AI-optimized schemas, 100+ suppliers, bookable products across multiple categories. | Request demo | High as strategic reference; uncertain as V0 vendor | Request docs/demo only after we know desired integration surface. |
| MustSeen | Execution layer for AI travel platforms | Positions itself as validation/bookability layer for AI-generated itineraries; mentions Amadeus, Duffel, LiteAPI. | Get API access / beta | High concept fit | Investigate if it can validate/convert itineraries without taking over UX. |
| Nowah | Travel API/MCP positioning | Potentially relevant if it exposes MCP tools or agent-callable APIs. | Unknown | Medium-high | Verify docs, sandbox, and whether it is real inventory or orchestration. |
| Telivity / OTAIP | Open-core AI travel agent framework | Useful architecture reference for AI travel agent patterns. | Open source + managed service | Medium | Review code/design for planner/tool architecture, not inventory dependency. |
| Sabre agentic APIs / MCP | Enterprise GDS agent layer | Signals where enterprise travel infrastructure is heading: MCP and agent-ready APIs. | Enterprise | Reference only for now | Track, but do not pursue V0. |
| AMGiNE | AI automation for TMCs | Corporate travel/TMC workflow automation, not consumer inventory source. | Enterprise/TMC | Reference only | Use as product inspiration for post-booking automation. |

### Unified B2B Travel Platforms

| Provider | Type | Why it matters | Access | Fit | Next action |
| --- | --- | --- | --- | --- | --- |
| Tripgic | Unified API for flights, hotels, cars, activities | Claims single normalized API, sandbox credentials, flights/hotels/cars/activities. | Book/get in touch | Medium | Ask about sandbox, startup access, booking support, cancellation support. |
| Tripedge | Travel API + components + white-label | Explicitly mentions loyalty initiatives and points banks; flights + hotels. | Contact/onboarding | Medium-high | Good strategic candidate if they support loyalty-aware white-label/API without owning UX. |
| Traveloris | B2B AI trip planner + booking widget | AI planner and booking widget, strong for tours/activities/destination commerce. | Demo/contact | Low-medium for flights/hotels; high for activities | Consider later for activity/itinerary layer, not core flight/hotel optimizer. |
| Volero | B2B travel booking system/API | Broad travel booking platform across flights/hotels/cars/etc. | Likely sales/onboarding | Medium | Add to later partner list; not V0. |
| Adivaha | Travel APIs and white-label platforms | Broad OTA/travel agency tooling. | Likely sales/onboarding | Medium-low | Reference for white-label patterns, less likely core integration. |

### Data/Support APIs

These do not replace booking inventory, but can enrich ranking and reliability.

| Provider | Type | Use | Access | Fit |
| --- | --- | --- | --- | --- |
| Aviationstack | Flight status/schedules/routes | Delay, schedule, route metadata; not booking prices. | Free tier and paid self-serve | Medium for flight reliability layer. |
| AirLabs | Aviation data | Flight status/schedules/airports/routes. | Self-serve plans | Medium for enrichment. |
| FlightAware AeroAPI | Flight tracking/status | Strong operational flight data. | Paid/developer access | Later enrichment. |
| Google Places / Maps | Hotel/POI geocoding, distance, neighborhood | Needed for "20 minutes from X" hotel ranking. | Self-serve cloud API | High for location intelligence. |
| OpenTripMap | POIs/attractions | Lightweight destination context. | Self-serve | Medium for itinerary enrichment. |

## Shortlist By Product Stage

### V0: Live Search And Recommendation

Use:

- SerpApi Google Flights
- SerpApi Google Hotels
- Duffel test mode
- LiteAPI sandbox

Investigate:

- Hotelbeds evaluation environment
- Kiwi Tequila
- FlightAPI.io
- MakCorps

Avoid for V0:

- Amadeus
- Travelport
- Sabre
- Expedia Rapid
- Booking.com Demand API

### V1: Better Supply And Deep Links

Investigate:

- Hotelbeds
- Tripedge
- Tripgic
- LiteAPI production
- Duffel live activation
- Google Places/Maps

### V2: Booking And Agent Execution

Investigate:

- MustSeen
- Boxcribe
- Nowah
- Telivity/OTAIP
- Sabre agentic APIs, only if enterprise motion becomes realistic

## Top Discovery Questions To Ask Vendors

Use this email/demo script:

1. Do you provide sandbox API credentials before commercial approval?
2. Are results live production-like inventory, sandbox fixtures, or cached data?
3. Are you search-only, booking-capable, or post-booking capable?
4. Can we keep our own frontend UX and recommendation engine?
5. Do you return taxes, fees, cancellation policy, refundability, baggage, fare/room rules, and final payable totals?
6. Do you support deep links if we do not book in-app?
7. What supplier categories are included: flights, hotels, cars, activities, transfers?
8. What commercial model applies: affiliate commission, markup, per-call, revenue share, monthly minimums?
9. Do you require IATA/ARC/agency credentials, existing booking volume, or enterprise contract?
10. Do you support agentic/MCP/tool-call workflows, or only REST APIs?
11. What is the path from sandbox to production?
12. Who owns traveler support, changes, cancellations, chargebacks, and refunds?

## Current Assessment

The most useful near-term stack is:

- SerpApi for real market visibility.
- Duffel for flight booking workflow design.
- LiteAPI/Nuitée for hotel booking workflow design.
- Google Places/Maps for location constraints.

The most strategically interesting agentic platforms are:

- Boxcribe
- MustSeen
- Nowah
- Telivity/OTAIP

But none should replace our deterministic loyalty optimizer until they prove they can provide structured, auditable tool outputs while letting our app own ranking and payment-path logic.

## Product Discovery Method

### Phase 1: Wide Scan

Build a longlist from:

- Search queries:
  - `travel API for AI agents`
  - `MCP server travel booking API`
  - `AI travel agent booking API`
  - `hotel booking API self serve`
  - `flight booking API self serve`
  - `B2B travel API startup sandbox`
  - `NDC API aggregator startup`
  - `travel agent marketplace API`
- Startup databases and app stores:
  - Product Hunt
  - GitHub
  - YC company directory
  - RapidAPI
  - Postman API Network
  - Travel Tech Show exhibitor lists
  - PhocusWire / Skift travel tech coverage
- Developer ecosystems:
  - MCP server directories
  - OpenAPI directories
  - GitHub repos tagged travel, booking, NDC, GDS, MCP

### Phase 2: Access Triage

Tag each provider as:

- `active`: we have a working key.
- `self_serve_candidate`: signup/key appears available.
- `partner_candidate`: likely needs onboarding but may be realistic.
- `enterprise_deferred`: sales-heavy, not V0.
- `reference_only`: useful architecture/product inspiration.

Reject or defer providers that:

- Require opaque scraping as the core path.
- Require cloud-browser login/session replay.
- Require enterprise sales before a sandbox.
- Cannot expose prices/fees/policies in structured form.
- Force us to surrender the primary product UX.

### Phase 3: Proof Of Access

For each promising provider:

1. Create a sandbox key.
2. Run one real query for a known route or hotel market.
3. Confirm response includes enough detail for deterministic ranking.
4. Add a key-gated provider adapter.
5. Add provider status and tests.
6. Only then consider deeper integration.

### Phase 4: Product Fit Scoring

Score each provider 1-5 on:

- Access speed
- Coverage
- Data quality
- Price transparency
- Booking capability
- Loyalty relevance
- Cancellation/refund/change detail
- Developer experience
- Commercial fit
- Agent-readiness

## Recommendation

Keep the V0 product independent and deterministic.

Use agent platforms as accelerators only if they can provide structured tools or supplier access without taking over the core user experience.

Short term priorities:

1. Keep SerpApi + Duffel as the working flight stack.
2. Add LiteAPI/Nuitée if a key is available.
3. Keep Booking.com and Expedia in partner-research mode.
4. Investigate Nowah, Boxcribe, and Telivity/OTAIP as agent-specific references or possible integrations.
5. Improve our own deterministic planner before outsourcing decision logic.

## Sources

- Boxcribe: https://www.boxcribe.com/
- Nowah: https://platform.nowah.xyz/
- Telivity: https://telivity.app/
- Tripgic: https://www.tripgic.com/
- Avigate: https://www.avigate.ai/
- AMGiNE: https://amgine.ai/
- LiteAPI: https://www.liteapi.travel/
- Booking.com Demand API prerequisites: https://developers.booking.com/demand/docs/getting-started/prerequisites
