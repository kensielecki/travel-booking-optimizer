# Travel Booking Optimizer Brand Guidelines

## Brand Direction

Travel Booking Optimizer should feel like a premium travel operations desk: fast, calm, precise, and a little sharper than a normal booking site. The product is not a travel blog or a points tracker. It is a decision cockpit for choosing the best way to book a trip.

Reference feel:

- Linear: crisp workspace structure, restrained chrome, high clarity.
- Ramp: money-aware confidence, compact financial detail, strong hierarchy.
- Modern airline checkout: routes, fares, confidence, policy and payment details.
- Quiet luxury travel: enough polish to feel premium without resort-style decoration.

## Logo Concept

The mark combines three ideas:

- Route intelligence: a curved route line from origin to opportunity.
- Travel inventory: a minimal wing/plane geometry.
- Payment optimization: a single teal value node that signals the chosen path.

Use the square mark as the app icon, favicon, nav logo, extension icon base, and small product badge. Avoid adding tiny text inside the mark.

Primary asset:

- `frontend/public/brand/travel-booking-optimizer-mark.svg`

React component:

- `frontend/src/components/brand/brand-mark.tsx`

## Color System

Primary neutrals:

- Night Ink: `#111317` for logo base, primary text, main commands.
- Soft Surface: `#F5F7FA` for app backgrounds and panels.
- Line: `#D8DDE6` for dividers and quiet borders.
- White: `#FFFFFF` for dense content surfaces.

Functional accents:

- Clear Teal: `#00A88F` for recommended paths, success, captured value, selected states.
- Cobalt: `#2563EB` for provider confidence, live data, route visualization, secondary actions.
- Signal Coral: `#FF6B35` for section labels, warnings, priority notes, key callouts.
- Premium Gold: `#C9A44C` for rare “best value” or payment optimization details.

Usage rule: keep the UI mostly neutral. Use teal and cobalt for functional meaning, coral for emphasis, and gold only as a scarce premium accent.

## Typography

Use a modern system sans stack until a dedicated brand font is worth adding. The current app can remain on the browser/system stack with tight hierarchy:

- Product title: 15-18px, semibold.
- App panel headings: 20-28px, semibold, compact line height.
- Dense facts: 12-15px, high contrast, generous spacing.
- Technical badges: 11-12px, uppercase sparingly.

Avoid oversized marketing typography inside the app. This should feel like a working product surface.

## UI Aesthetic

The interface should look like a booking intelligence workspace:

- Compact itinerary cards with expandable details.
- Strong route and price hierarchy.
- Small technical badges for live/sandbox/provider confidence.
- Neutral panels with a few sharp accent moments.
- No busy background photography in the core app view.
- No decorative gradient blobs or single-color theme domination.

## Voice

The product should sound decisive and practical:

- “Best current option”
- “Provider confidence”
- “Constraint fit”
- “Pay now”
- “Savings included”
- “Open booking source”

Avoid vague travel marketing language unless it directly helps explain an itinerary.
