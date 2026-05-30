CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.loyalty_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    program TEXT NOT NULL,
    display_name TEXT NOT NULL,
    points_balance BIGINT NOT NULL DEFAULT 0 CHECK (points_balance >= 0),
    source TEXT NOT NULL DEFAULT 'manual_import',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, program)
);

CREATE TABLE IF NOT EXISTS public.offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    program TEXT,
    merchant TEXT NOT NULL,
    description TEXT NOT NULL,
    value_usd NUMERIC(10,2) NOT NULL CHECK (value_usd >= 0),
    min_spend_usd NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (min_spend_usd >= 0),
    expires_on DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.transfer_bonuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_program TEXT NOT NULL,
    to_program TEXT NOT NULL,
    bonus_pct NUMERIC(5,2) NOT NULL CHECK (bonus_pct >= 0),
    valid_through DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.trip_intents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    raw_intent TEXT NOT NULL,
    origin TEXT,
    destination TEXT,
    budget_usd NUMERIC(10,2) NOT NULL CHECK (budget_usd > 0),
    preferred_programs TEXT[] NOT NULL DEFAULT '{}',
    ranking_mode TEXT NOT NULL DEFAULT 'balanced',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.booking_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_intent_id UUID NOT NULL REFERENCES public.trip_intents(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    booking_type TEXT NOT NULL,
    merchant TEXT NOT NULL,
    cash_price_usd NUMERIC(10,2) NOT NULL CHECK (cash_price_usd >= 0),
    taxes_usd NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (taxes_usd >= 0),
    fees_usd NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (fees_usd >= 0),
    copay_usd NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (copay_usd >= 0),
    points_program TEXT,
    points_used BIGINT NOT NULL DEFAULT 0 CHECK (points_used >= 0),
    transfer_from_program TEXT,
    transfer_bonus_pct NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (transfer_bonus_pct >= 0),
    offer_value_usd NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (offer_value_usd >= 0),
    simplicity INT NOT NULL DEFAULT 3 CHECK (simplicity BETWEEN 1 AND 5),
    notes JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_intent_id UUID NOT NULL REFERENCES public.trip_intents(id) ON DELETE CASCADE,
    booking_option_id UUID NOT NULL REFERENCES public.booking_options(id) ON DELETE CASCADE,
    rank INT NOT NULL CHECK (rank > 0),
    cents_per_point NUMERIC(8,4),
    out_of_pocket_usd NUMERIC(10,2) NOT NULL,
    cash_avoided_usd NUMERIC(10,2) NOT NULL,
    effective_savings_usd NUMERIC(10,2) NOT NULL,
    total_economic_value_usd NUMERIC(10,2) NOT NULL,
    score NUMERIC(8,3) NOT NULL,
    reasons JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    account_count INT NOT NULL DEFAULT 0,
    offer_count INT NOT NULL DEFAULT 0,
    raw_snapshot JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_loyalty_accounts_user_id ON public.loyalty_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_offers_user_id ON public.offers(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_intents_user_id ON public.trip_intents(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_trip_intent_id ON public.recommendations(trip_intent_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_user_id ON public.ingestion_runs(user_id);
