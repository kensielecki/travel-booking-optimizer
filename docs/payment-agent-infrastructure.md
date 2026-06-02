# Payment Agent Infrastructure

Last updated: 2026-06-01

## Decision

Use Crossmint and Lobster Cash as the preferred future infrastructure direction for agent-assisted payments once the product moves beyond recommendation into supervised booking execution.

This is not part of V0 live search. It should be treated as a later payment and checkout layer that sits after deterministic search, ranking, and explicit user approval.

## Intended Role

Crossmint and Lobster Cash are candidates for:

- Scoped payment authorization for agents.
- Virtual card or wallet-based payment execution.
- User-controlled spending limits.
- Safer checkout experiments than exposing a primary personal card.
- Audit trails for agent-initiated payment attempts.

They should not replace:

- Travel inventory search.
- Deterministic ranking.
- Loyalty valuation math.
- Final user approval before a transaction.

## Target Flow

1. Search inventory through travel providers.
   - Flights: SerpApi, Duffel, and other future sources.
   - Hotels: SerpApi, LiteAPI/Nuitee, and other future sources.

2. Rank booking paths deterministically.
   - Cash cost.
   - Points cost.
   - Fees, taxes, copays.
   - Offer value.
   - Provider confidence.
   - Preference fit.

3. Present a final booking review screen.
   - Selected flight/hotel.
   - Exact supplier/provider.
   - Total expected charge.
   - Cancellation/refund notes where available.
   - Card or virtual-card funding source.
   - Explicit user confirmation.

4. Create scoped payment permission.
   - Merchant or provider scope where possible.
   - Maximum amount.
   - Expiration window.
   - One-time use preference.

5. Execute booking through the selected provider path.
   - Direct API booking where available.
   - Assisted browser checkout only where allowed and reliable.
   - Never store raw card details in the app.

6. Store audit metadata.
   - Provider.
   - Amount.
   - Permission ID or payment session ID.
   - Booking/order reference when returned.
   - No raw card PAN/CVV storage.

## Product Guardrails

- No autonomous booking without final user approval.
- No payment execution in V0.
- No storage of raw payment credentials.
- No browser-session replay for payment.
- No hidden retries that could duplicate a charge.
- Every attempted payment must have a visible status and audit record.
- Support cancellation/refund paths before broad beta booking.

## Implementation Timing

V0:

- Search and recommend only.
- Keep booking/payment out of scope.
- Add payment-agent architecture notes only.

V1:

- Add durable searches, saved preferences, and better provider results.
- Add final booking-review UI, still without charging.

V1.5:

- Prototype payment permission objects in the backend.
- Add a disabled/sandbox payment provider abstraction.
- Evaluate Crossmint and Lobster API flows in test mode if available.

V2:

- Add supervised booking/payment experiments with strict caps.
- Prefer low-risk hotel bookings or refundable paths first.
- Require explicit confirmation for every transaction.

## Open Questions

- Which Crossmint agent payment flow fits best for travel provider checkout?
- Can Lobster virtual cards be scoped by merchant, amount, and expiration for our use case?
- Are prepaid/virtual cards accepted by Duffel, LiteAPI/Nuitee, hotel suppliers, and airline direct checkout paths?
- What liability and support obligations do we assume if the app initiates booking?
- What refund/cancellation metadata is available before payment?
- How do we prevent duplicate booking attempts if a provider times out?

