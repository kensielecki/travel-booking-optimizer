# Travel Booking Optimizer

Travel + loyalty optimization platform rebuilt from the legacy loyalty portfolio prototype.

Planned beta URL: `https://kensielecki.github.io/travel-booking-optimizer/`

The product is centered on trip intent:

> "Weekend trip to NYC using United + Hilton with a ~$2,000 equivalent budget."

The system compares cash bookings, points redemptions, transfer partner routes, and active offers, then recommends the best booking and payment path.

## Phase 1 Scope

- FastAPI backend with deterministic optimization logic
- Mock/manual ingestion interfaces
- Trip intent optimization API
- Supabase/Postgres schema draft for the target model
- Modern travel-shopping frontend skeleton

## Run Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

## Load Chrome Extension

The V0 browser extension lives in `extension/`. It captures visible rewards-page data from the user's own local browser session and sends normalized account/offer payloads to the backend.

Setup instructions are in [docs/browser-extension.md](docs/browser-extension.md).

## Test Extension Parser

```bash
node extension/tests/parser.test.js
```

## Design Principles

- Deterministic math owns valuation, savings, and ranking.
- AI may explain recommendations, summarize edge cases, and help users understand tradeoffs.
- Ingestion is extension-first and local-session-friendly.
- No passwords, 2FA seeds, remote session replay, server-side browser auth, or brittle Playwright-only flows.
