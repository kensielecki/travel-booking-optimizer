# Repository Audit And Rebuild Plan

## Repository Audit

The source archive contained a small application surrounded by development artifacts. The clean extraction kept the useful code and docs while excluding `.env`, `.env.local`, `.git`, `node_modules`, `.next`, caches, generated output, and macOS metadata.

Reusable reference material:

- FastAPI app layout with separate API modules.
- Pydantic schema concepts for users, loyalty accounts, balances, ingestion runs, and portfolio responses.
- Supabase/Postgres schema direction and health tracking concepts.
- Transfer bonus watcher idea and editable YAML promotion data.
- Mock/demo scripts and product context around loyalty program valuation.
- Next.js/Tailwind app scaffold as a baseline frontend technology choice.

Technical debt to leave behind:

- TinyFish-centered ingestion assumptions.
- Cookie/session replay and Playwright cookie normalization.
- Server-side browser login automation.
- AI-driven valuation for core financial calculations.
- Portfolio-first UX that underplays the travel shopping decision.
- Cron/plist local-machine assumptions.
- Prompt files as the source of truth for redemption math.
- Environment-specific secrets and generated dependency output.

## Proposed Architecture

Backend:

- FastAPI service with modular routers.
- Supabase/Postgres for durable storage.
- Optional Redis for cached travel pricing and promotion lookups.
- Deterministic optimization engine for cents-per-point, out-of-pocket, savings, and ranking.
- AI explanation service as an optional layer after deterministic recommendation generation.

Frontend:

- Travel shopping workflow as the first screen.
- Trip intent form with budget, programs, and preference controls.
- Ranked recommendation UI with cash, points, hybrid, transfer, and offer-enhanced options.
- Portfolio as a supporting view, not the product center.

Ingestion:

- Browser extension source for authenticated pages the user is already viewing.
- Local helper/agent source for user-controlled local extraction.
- Manual import fallback for V0 demos and early beta users.
- Normalized ingestion payloads, ingestion run records, and raw snapshots for debugging.

## Migration Plan

1. Preserve legacy repo only as reference material.
2. Create a clean source tree with docs, backend, frontend, and database schema.
3. Rebuild domain models around trip intent, booking options, redemption options, transfer bonuses, offers, and recommendations.
4. Implement deterministic optimization before any AI layer.
5. Add fake/manual ingestion and seeded demo data for V0.
6. Reintroduce Supabase persistence behind repository interfaces.
7. Add extension ingestion contracts after the V0 demo flow works.

## Rebuild Execution Plan

Phase 1:

- Clean repo structure.
- Deterministic optimization engine.
- Mock/manual ingestion.
- Trip intent API.
- Recommendation engine.
- Travel-first frontend skeleton.
- Focused unit tests for trust-critical math.

Phase 2:

- Browser extension ingestion.
- Real offer ingestion.
- Travel pricing integrations.
- Transfer bonus automation.

Phase 3:

- Local helper/background sync.
- Production deployment.
- Advanced explanation and edge-case intelligence.
