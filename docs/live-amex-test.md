# Live Amex Capture Test

Use this only after the mock extension flow works.

## When To Log In

Log into Amex manually in Chrome after these are true:

- Backend is running at `http://127.0.0.1:8000`.
- Frontend is running at `http://127.0.0.1:3000`.
- The Chrome extension is loaded from `extension/`.
- The mock fixture capture succeeds and shows high confidence.

At that point, open Amex yourself in Chrome and authenticate normally. Codex should not see, store, or request your password, 2FA code, cookies, or session tokens.

## Suggested First Live Page

Start with a page that shows low-risk read-only information:

- Membership Rewards balance page.
- Amex Offers page.

Avoid pages that show full card numbers, statements, personal profile data, or sensitive documents.

## Capture Steps

1. Open Chrome.
2. Log into Amex manually.
3. Navigate to a page with Membership Rewards balance or Amex Offers.
4. Click the `Travel Booking Optimizer Capture` extension.
5. Click `Capture tab`.
6. Review the normalized JSON before sending.
7. Confirm:
   - `metadata.detected_program` is `amex_mr`.
   - `metadata.extraction_confidence` is reasonable.
   - `accounts` contains only points balance data.
   - `offers` contains only offer descriptions and estimated values.
   - No raw passwords, cookies, card numbers, or 2FA material appears.
8. Click `Send`.
9. Refresh the frontend.

## What To Do If Extraction Looks Wrong

Do not click `Send`. Take a screenshot of the extension popup with sensitive data cropped or blurred, then adjust the parser before trying again.

## Current Limitation

V0 stores captured data only in backend memory. Restarting the backend clears the captured state. Supabase persistence is the next production step.
