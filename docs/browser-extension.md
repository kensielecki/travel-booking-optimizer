# Browser Extension Ingestion

The V0 Chrome extension is a local capture companion for the optimizer backend.

## What It Does

- Runs inside the user's own Chrome session.
- Captures visible page text only after the user clicks `Capture tab`.
- Detects known loyalty programs from the current page URL/title/text.
- Attempts basic balance and offer extraction.
- Lets the user review and edit normalized JSON before sending.
- Posts to the local backend endpoint: `POST /ingestion/manual`.

## What It Does Not Do

- It does not store passwords.
- It does not store 2FA seeds.
- It does not export cookies.
- It does not replay sessions.
- It does not run server-side browser automation.
- It does not make redemptions or transactions.

## Local Setup

1. Start the backend:

   ```bash
   cd "/Users/kensielecki/codex projects/travel-booking-optimizer/backend"
   .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. Open Chrome and go to `chrome://extensions`.
3. Enable `Developer mode`.
4. Click `Load unpacked`.
5. Select:

   ```text
   /Users/kensielecki/codex projects/travel-booking-optimizer/extension
   ```

6. Visit a loyalty, bank rewards, airline, or hotel page that is already open in the user's browser session.
7. Click the extension icon.
8. Click `Capture tab`.
9. Review the normalized JSON.
10. If the balance is wrong, enter the correct visible balance in `Correct points balance` and click `Apply correction`.
11. Click `Send`.

The extension blocks sending if the normalized payload contains sensitive-looking patterns such as card/account numbers, email addresses, phone numbers, session/token strings, street addresses, or security-code language.

## Test With A Local Fixture

Before using a real rewards page, open the included mock page in Chrome:

```text
/Users/kensielecki/codex projects/travel-booking-optimizer/fixtures/extension-test-page.html
```

Then run the extension against that page. The expected capture is:

- One `amex_mr` account.
- `110000` Membership Rewards points.
- Two offers: Hilton `$100` back on `$500` spend, and United `$75` back on `$300` spend.

The parser can also be tested from the command line:

```bash
cd "/Users/kensielecki/codex projects/travel-booking-optimizer"
node extension/tests/parser.test.js
```

## Live Amex Test

Do not log into Amex until the mock fixture flow works. The live test checklist is in [live-amex-test.md](live-amex-test.md).

## V0 Contract

The extension sends the same normalized shape as manual ingestion:

```json
{
  "user_id": "11111111-1111-4111-8111-111111111111",
  "source": "browser_extension",
  "accounts": [
    {
      "user_id": "11111111-1111-4111-8111-111111111111",
      "program": "united",
      "display_name": "United MileagePlus",
      "points_balance": 82000
    }
  ],
  "offers": [
    {
      "user_id": "11111111-1111-4111-8111-111111111111",
      "program": "amex_mr",
      "merchant": "Hilton",
      "description": "Spend $500 or more, get $100 back.",
      "value_usd": 100,
      "min_spend_usd": 500
    }
  ]
}
```

## Next Improvements

- Add per-program extractors for Amex MR, Chase UR, United, Hilton, Delta, and Marriott.
- Store local extraction confidence scores.
- Add an extension options page for API URL and user profile selection.
- Add a backend endpoint dedicated to browser extension ingestion once persistence is wired.
- Add per-program confidence thresholds before allowing send.
