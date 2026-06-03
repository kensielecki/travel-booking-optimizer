# Manual Vacation Rental Compare

## Decision

Airbnb should be treated as a manual verification source, not a production automated inventory provider.

The product can generate an Airbnb search link from destination, dates, and budget. The user opens the link, reviews Airbnb directly, and can later use the browser extension to capture visible listing details for comparison.

## Why

Airbnb does not expose a normal public traveler-search API for this use case. Logged-in browser automation creates reliability, account-safety, privacy, and terms-of-service risks.

## Current V1 Behavior

- The frontend shows a `Manual vacation-rental compare` panel.
- If a destination can be inferred from the destination field or prompt, the panel generates an Airbnb search URL.
- The flow does not log in, scrape, bypass CAPTCHA, or book.

## Future Capture Shape

When the extension supports this source, capture only visible, user-reviewed fields:

```json
{
  "source": "manual_airbnb_capture",
  "listing_name": "Example apartment",
  "listing_url": "https://www.airbnb.com/rooms/example",
  "destination": "Seattle",
  "check_in": "2026-07-24",
  "check_out": "2026-07-26",
  "nightly_rate_usd": 325,
  "total_price_usd": 890,
  "cleaning_fee_usd": 100,
  "service_fee_usd": 80,
  "rating": 4.92,
  "review_count": 184,
  "cancellation_summary": "Visible cancellation text"
}
```

These captured candidates can become manual `BookingOption` rows and be ranked against hotel/provider inventory.
