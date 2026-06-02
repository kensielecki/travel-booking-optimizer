"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Loader2,
  Plane,
  Play,
  Search,
  SlidersHorizontal,
  WalletCards,
} from "lucide-react";

import { AccountBalanceEditor } from "@/components/account-balance-editor";
import { ClearCapturedData } from "@/components/clear-captured-data";
import { RecommendationCard } from "@/components/recommendation-card";
import { dollars, points } from "@/lib/format";
import type {
  IngestionState,
  OptimizationResponse,
  Program,
  ProviderReadiness,
  RankingMode,
  Recommendation,
} from "@/lib/types";

const PROGRAM_OPTIONS: Array<{ label: string; value: Program }> = [
  { label: "United", value: "united" },
  { label: "Hilton", value: "hilton" },
  { label: "Amex MR", value: "amex_mr" },
  { label: "Chase UR", value: "chase_ur" },
];

const RANKING_OPTIONS: Array<{ label: string; value: RankingMode }> = [
  { label: "Balanced", value: "balanced" },
  { label: "Lowest cash", value: "lowest_out_of_pocket" },
  { label: "Best CPP", value: "highest_cpp" },
  { label: "Total value", value: "total_value" },
  { label: "Simplest", value: "simplest" },
];

const SAMPLE_PROMPTS = [
  "Weekend trip to NYC using United + Hilton with a $2,000 budget. Direct flights only. 4 star hotel or higher.",
  "Two-night New York trip from SFO. Arrive before midday, keep hotels near Midtown, compare cash and points.",
  "Long weekend in San Diego using Amex offers. Direct flight preferred and hotel under $1,200.",
];

interface TripOptimizerProps {
  apiUrl: string;
  userId: string;
  initialDemo?: OptimizationResponse | null;
  initialIngestionState?: IngestionState | null;
}

export function TripOptimizer({
  apiUrl,
  userId,
  initialDemo = null,
  initialIngestionState = null,
}: TripOptimizerProps) {
  const [intent, setIntent] = useState(
    initialDemo?.intent.raw_intent ??
      "Weekend trip to NYC using United + Hilton with a ~$2,000 equivalent budget.",
  );
  const [budget, setBudget] = useState(String(initialDemo?.intent.budget_usd ?? 2000));
  const [destination, setDestination] = useState(initialDemo?.intent.destination ?? "NYC");
  const [origin, setOrigin] = useState("SFO");
  const [departureDate, setDepartureDate] = useState("2026-07-24");
  const [returnDate, setReturnDate] = useState("2026-07-26");
  const [rankingMode, setRankingMode] = useState<RankingMode>("balanced");
  const [selectedPrograms, setSelectedPrograms] = useState<Program[]>(["united", "hilton", "amex_mr"]);
  const [directOnly, setDirectOnly] = useState(true);
  const [arrivalWindow, setArrivalWindow] = useState("Arrive before midday");
  const [hotelPreference, setHotelPreference] = useState("4 star or higher, within 20 minutes");
  const [response, setResponse] = useState<OptimizationResponse | null>(initialDemo);
  const [providerReadiness, setProviderReadiness] = useState<ProviderReadiness[]>([]);
  const [ingestionState, setIngestionState] = useState<IngestionState | null>(initialIngestionState);
  const [error, setError] = useState<string | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const isLocalApi = apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");

  const capturedAccounts = ingestionState?.accounts ?? [];
  const capturedOffers = ingestionState?.offers ?? [];
  const capturedCount = capturedAccounts.length + capturedOffers.length;

  const providerStatuses = response?.provider_statuses ?? [];
  const configuredProviderReadiness = providerReadiness.filter((provider) => provider.configured);
  const liveProductionCount = providerStatuses.filter(
    (status) => status.status === "live" && status.environment === "production",
  ).length;
  const readyProductionCount = configuredProviderReadiness.filter(
    (provider) => provider.environment === "production",
  ).length;
  const connectedSourceCount = liveProductionCount || readyProductionCount;

  const groupedRecommendations = useMemo(() => {
    const recommendations = response?.recommendations ?? [];
    const fullTripPaths = recommendations.filter(
      (recommendation) => recommendation.option.source_provider === "trip_package",
    );
    const standalone = recommendations.filter(
      (recommendation) => recommendation.option.source_provider !== "trip_package",
    );
    return { fullTripPaths, standalone };
  }, [response?.recommendations]);

  const rankedOptions = groupedRecommendations.fullTripPaths.length
    ? groupedRecommendations.fullTripPaths
    : groupedRecommendations.standalone;
  const selectedOption = rankedOptions[0] ?? null;
  const comparisonOptions = rankedOptions.slice(0, 3);

  const normalizedBudget = useMemo(() => {
    const parsed = Number(budget.replace(/[$,]/g, ""));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 2000;
  }, [budget]);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      try {
        const [readinessResponse, demoResponse, ingestionResponse] = await Promise.all([
          fetch(`${apiUrl}/travel-search/provider-readiness`),
          initialDemo ? Promise.resolve(null) : fetch(`${apiUrl}/demo/nyc-weekend`),
          initialIngestionState ? Promise.resolve(null) : fetch(`${apiUrl}/ingestion/state/${userId}`),
        ]);

        if (cancelled) {
          return;
        }

        if (readinessResponse.ok) {
          setProviderReadiness((await readinessResponse.json()) as ProviderReadiness[]);
        }

        if (demoResponse?.ok) {
          const demo = (await demoResponse.json()) as OptimizationResponse;
          setResponse(demo);
          setIntent(demo.intent.raw_intent);
          setBudget(String(demo.intent.budget_usd));
          setDestination(demo.intent.destination ?? "NYC");
        }

        if (ingestionResponse?.ok) {
          setIngestionState((await ingestionResponse.json()) as IngestionState);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(
            isLocalApi
              ? "Hosted beta shell is live. Connect the FastAPI backend for live searches."
              : caught instanceof Error
                ? caught.message
                : "Could not reach travel API",
          );
        }
      }
    }

    loadInitialData();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, initialDemo, initialIngestionState, isLocalApi, userId]);

  async function optimize(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsOptimizing(true);
    setError(null);

    const constraints = [
      directOnly ? "direct flight only" : null,
      arrivalWindow.trim() || null,
      hotelPreference.trim() || null,
    ].filter(Boolean);

    try {
      const apiResponse = await fetch(`${apiUrl}/travel-search/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search: {
            user_id: userId,
            raw_intent: constraints.length ? `${intent.trim()} Constraints: ${constraints.join("; ")}.` : intent.trim(),
            origin: origin.trim() || undefined,
            destination: destination.trim() || undefined,
            departure_date: departureDate || undefined,
            return_date: returnDate || undefined,
            check_in_date: departureDate || undefined,
            check_out_date: returnDate || undefined,
            direct_only: directOnly,
            budget_usd: normalizedBudget,
            preferred_programs: selectedPrograms,
            ranking_mode: rankingMode,
          },
          accounts: capturedAccounts,
          offers: capturedOffers,
          transfer_bonuses: [
            {
              from_program: "amex_mr",
              to_program: "united",
              bonus_pct: 20,
              valid_through: "2026-06-15",
            },
          ],
        }),
      });

      if (!apiResponse.ok) {
        throw new Error(`Optimizer returned ${apiResponse.status}`);
      }

      setResponse(await apiResponse.json());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not run optimizer");
    } finally {
      setIsOptimizing(false);
    }
  }

  function toggleProgram(program: Program) {
    setSelectedPrograms((current) =>
      current.includes(program) ? current.filter((item) => item !== program) : [...current, program],
    );
  }

  return (
    <main className="min-h-screen px-4 py-5 text-ink sm:px-6">
      <section className="mx-auto min-h-[calc(100vh-2.5rem)] max-w-[1540px] overflow-hidden rounded-2xl border border-line bg-white/70 shadow-[0_24px_70px_rgba(27,39,60,0.12)]">
        <header className="flex min-h-20 flex-wrap items-center justify-between gap-4 border-b border-line bg-white/90 px-5 py-4 backdrop-blur md:px-7">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-night text-white">
              <Plane size={21} aria-hidden="true" />
            </div>
            <div>
              <p className="text-base font-semibold leading-tight text-ink">Travel Booking Optimizer</p>
              <p className="text-sm text-slate-500">Search, compare, decide</p>
            </div>
          </div>

          <nav className="flex rounded-xl border border-line bg-surface p-1 text-sm font-semibold text-slate-500">
            <span className="rounded-lg bg-white px-3 py-2 text-ink shadow-sm">Flights + Hotels</span>
            <span className="px-3 py-2">Offers</span>
            <span className="px-3 py-2">Points</span>
          </nav>

          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={connectedSourceCount ? "green" : "blue"}>
              {connectedSourceCount ? `${connectedSourceCount} connected sources` : "Beta shell"}
            </StatusPill>
            <StatusPill tone="blue">
              <SlidersHorizontal size={14} aria-hidden="true" />
              {RANKING_OPTIONS.find((option) => option.value === rankingMode)?.label ?? "Balanced"}
            </StatusPill>
          </div>
        </header>

        <section className="grid min-h-[760px] lg:grid-cols-[300px_minmax(0,1fr)_330px]">
          <aside className="border-b border-line bg-white/55 p-5 lg:border-b-0 lg:border-r">
            <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Preferences</p>
            <h1 className="mt-3 text-2xl font-semibold leading-tight tracking-[-0.02em] text-ink">
              Direct, early, premium enough.
            </h1>

            <form className="mt-4 space-y-3" onSubmit={optimize}>
              <label className="block">
                <span className="text-xs font-bold uppercase text-slate-500">Trip prompt</span>
                <textarea
                  className="mt-1 min-h-32 w-full resize-none rounded-xl border border-line bg-white p-3 text-sm leading-5 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  value={intent}
                  onChange={(event) => setIntent(event.target.value)}
                />
              </label>

              <PreferenceField label="Direct only">
                <label className="flex items-center justify-between gap-3">
                  <strong>{directOnly ? "Yes" : "No"}</strong>
                  <input
                    type="checkbox"
                    checked={directOnly}
                    onChange={(event) => setDirectOnly(event.target.checked)}
                    className="h-4 w-4 accent-teal-600"
                  />
                </label>
              </PreferenceField>

              <PreferenceField label="Arrive by">
                <input
                  className="w-full bg-transparent text-base font-semibold outline-none"
                  value={arrivalWindow}
                  onChange={(event) => setArrivalWindow(event.target.value)}
                  aria-label="Arrival preference"
                />
              </PreferenceField>

              <PreferenceField label="Hotel floor">
                <input
                  className="w-full bg-transparent text-sm font-semibold outline-none"
                  value={hotelPreference}
                  onChange={(event) => setHotelPreference(event.target.value)}
                  aria-label="Hotel preference"
                />
              </PreferenceField>

              <label className="block rounded-xl border border-line bg-white p-3">
                <span className="text-xs font-bold uppercase text-slate-500">Ranking</span>
                <select
                  className="mt-1 w-full bg-transparent text-base font-semibold outline-none"
                  value={rankingMode}
                  onChange={(event) => setRankingMode(event.target.value as RankingMode)}
                >
                  {RANKING_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="rounded-xl border border-line bg-white p-3">
                <span className="text-xs font-bold uppercase text-slate-500">Programs</span>
                <div className="mt-2 flex flex-wrap gap-2">
                  {PROGRAM_OPTIONS.map((program) => {
                    const selected = selectedPrograms.includes(program.value);
                    return (
                      <button
                        key={program.value}
                        type="button"
                        onClick={() => toggleProgram(program.value)}
                        className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${
                          selected
                            ? "border-accent bg-accent/10 text-teal-800"
                            : "border-line bg-white text-slate-700"
                        }`}
                      >
                        {program.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <button
                type="submit"
                disabled={isOptimizing}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-night px-4 text-sm font-bold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isOptimizing ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
                Build itinerary
              </button>
            </form>
          </aside>

          <section className="bg-gradient-to-r from-[#f6f9fc] to-[#eef6f5] p-5">
            <form
              className="grid gap-3 rounded-2xl border border-line bg-white p-3 shadow-sm md:grid-cols-[1fr_1fr_1fr_auto]"
              onSubmit={optimize}
            >
              <SearchField label="Origin" value={origin} onChange={setOrigin} />
              <SearchField label="Destination" value={destination} onChange={setDestination} />
              <div className="grid grid-cols-2 gap-2">
                <DateField label="Depart" value={departureDate} onChange={setDepartureDate} />
                <DateField label="Return" value={returnDate} onChange={setReturnDate} />
              </div>
              <button
                type="submit"
                disabled={isOptimizing}
                className="inline-flex min-h-14 items-center justify-center gap-2 rounded-xl bg-night px-5 text-sm font-bold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isOptimizing ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                Search
              </button>
            </form>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Itinerary options</p>
                <h2 className="mt-1 text-xl font-semibold text-ink">
                  {response
                    ? "Ranked booking paths"
                    : connectedSourceCount
                      ? "API connected. Ready to build a live itinerary."
                      : "Connect the API to build a live itinerary"}
                </h2>
              </div>
              <p className="text-sm text-slate-500">
                {comparisonOptions.length
                  ? `${comparisonOptions.length} best ${comparisonOptions.length === 1 ? "option" : "options"}`
                  : connectedSourceCount
                    ? `${connectedSourceCount} production sources ready`
                    : "Waiting for provider results"}
              </p>
            </div>

            {error ? <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</p> : null}

            <div className="mt-4 space-y-3">
              {comparisonOptions.length ? (
                comparisonOptions.map((recommendation, index) => (
                  <ItineraryOption
                    key={`${recommendation.rank}-${recommendation.option.label}`}
                    recommendation={recommendation}
                    rank={index + 1}
                    origin={origin}
                    destination={destination}
                  />
                ))
              ) : (
                <ConnectedEmptyState connectedSourceCount={connectedSourceCount} providerReadiness={providerReadiness} />
              )}
            </div>

            {response ? (
              <section className="mt-5 space-y-3">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Deep details</p>
                    <p className="mt-1 text-sm text-slate-600">Expand any option to inspect booking math, provider notes, and ranking reasons.</p>
                  </div>
                  <p className="text-xs text-slate-500">{response.recommendations.length} total recommendations</p>
                </div>
                {response.recommendations.slice(0, 5).map((recommendation, index) => (
                  <RecommendationCard
                    key={`${recommendation.rank}-${recommendation.option.label}-detail`}
                    recommendation={recommendation}
                    displayRank={index + 1}
                  />
                ))}
              </section>
            ) : null}
          </section>

          <aside className="border-t border-line bg-white/80 p-5 lg:border-l lg:border-t-0">
            <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Booking path</p>
            <h2 className="mt-3 text-2xl font-semibold leading-tight tracking-[-0.02em] text-ink">
              Recommended payment stack
            </h2>

            <BookingPath recommendation={selectedOption} />

            <section className="mt-4 rounded-2xl border border-line bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Captured data</p>
                {capturedCount > 0 ? <ClearCapturedData apiUrl={apiUrl} userId={userId} /> : null}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {ingestionState?.last_run ? `Last ${ingestionState.last_run.status}` : "No capture yet"}
              </p>

              {capturedCount > 0 ? (
                <div className="mt-3 space-y-3">
                  {capturedAccounts.map((account) => (
                    <div key={account.id} className="border-t border-line pt-3">
                      <p className="text-sm font-semibold text-ink">{account.display_name}</p>
                      <AccountBalanceEditor account={account} apiUrl={apiUrl} userId={userId} />
                    </div>
                  ))}

                  {capturedOffers.slice(0, 4).map((offer) => (
                    <div key={offer.id} className="border-t border-line pt-3">
                      <p className="text-sm font-semibold text-ink">{offer.merchant}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {dollars(offer.value_usd)} value on {dollars(offer.min_spend_usd)} spend
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm leading-5 text-slate-600">
                  Capture a visible rewards page with the Chrome extension to include balances and offers.
                </p>
              )}
            </section>

            {providerStatuses.length ? (
              <section className="mt-4 rounded-2xl border border-line bg-white p-4">
                <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Provider health</p>
                <div className="mt-2 space-y-2">
                  {providerStatuses.slice(0, 6).map((status) => (
                    <div key={`${status.category}-${status.provider}`} className="flex items-center justify-between border-t border-line pt-2 first:border-t-0 first:pt-0">
                      <span className="text-sm text-slate-600">{status.provider.replaceAll("_", " ")}</span>
                      <strong className={status.status === "live" ? "text-sm text-teal-700" : "text-sm text-amber-700"}>
                        {status.status}
                      </strong>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </aside>
        </section>
      </section>
    </main>
  );
}

function PreferenceField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-white p-3">
      <span className="text-xs font-bold uppercase text-slate-500">{label}</span>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function SearchField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block rounded-xl border border-line bg-surface/60 px-3 py-2">
      <span className="text-xs font-bold uppercase text-slate-500">{label}</span>
      <input
        className="mt-1 w-full bg-transparent text-base font-semibold outline-none"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function DateField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block rounded-xl border border-line bg-surface/60 px-3 py-2">
      <span className="text-xs font-bold uppercase text-slate-500">{label}</span>
      <input
        className="mt-1 w-full bg-transparent text-sm font-semibold outline-none"
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function StatusPill({ children, tone }: { children: React.ReactNode; tone: "green" | "blue" | "orange" }) {
  const tones = {
    green: "border-accent/30 bg-accent/10 text-teal-800",
    blue: "border-cobalt/20 bg-cobalt/10 text-blue-800",
    orange: "border-signal/25 bg-signal/10 text-orange-800",
  };

  return (
    <span className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 text-xs font-bold ${tones[tone]}`}>
      {children}
    </span>
  );
}

function ItineraryOption({
  recommendation,
  rank,
  origin,
  destination,
}: {
  recommendation: Recommendation;
  rank: number;
  origin: string;
  destination: string;
}) {
  const option = recommendation.option;
  const route = deriveRoute(option.label, origin, destination);
  const confidence = Math.round(option.provider_confidence * 100);
  const tagTone = rank === 1 ? "green" : option.booking_type === "points" || option.booking_type === "transfer" ? "orange" : "blue";

  return (
    <article className={`rounded-2xl border bg-white p-4 ${rank === 1 ? "border-cobalt/40 shadow-[0_0_0_3px_rgba(37,99,235,0.08)]" : "border-line"}`}>
      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_150px]">
        <div className="min-w-0">
          <StatusPill tone={tagTone}>{rank === 1 ? "best path" : option.booking_type.replaceAll("_", " ")}</StatusPill>
          <div className="mt-3 flex items-center gap-3">
            <span className="text-3xl font-extrabold tracking-[-0.03em] text-ink">{route.from}</span>
            <div className="h-0.5 min-w-16 flex-1 bg-gradient-to-r from-cobalt to-accent" />
            <span className="text-3xl font-extrabold tracking-[-0.03em] text-ink">{route.to}</span>
          </div>
          <h3 className="mt-3 text-lg font-semibold leading-tight text-ink">{option.label}</h3>
          <p className="mt-1 text-sm leading-5 text-slate-600">{option.merchant}</p>
          <p className="mt-2 text-xs text-slate-500">
            {option.source_environment} source · {confidence}% provider confidence · score {recommendation.score}
          </p>
          <div className="mt-3 grid h-2 overflow-hidden rounded-full bg-slate-100 md:w-4/5" style={{ gridTemplateColumns: "70% 30%" }}>
            <span className="bg-accent" />
            <span className="bg-cobalt" />
          </div>
        </div>
        <div className="border-t border-line pt-3 md:border-l md:border-t-0 md:pl-4 md:pt-0">
          <p className="text-xs font-bold uppercase text-slate-500">Effective cost</p>
          <p className="mt-1 text-xl font-extrabold text-ink">{dollars(recommendation.out_of_pocket_usd)}</p>
          <p className="text-sm text-slate-500">Save {dollars(recommendation.effective_savings_usd)}</p>
          <p className="mt-3 text-xs font-semibold text-slate-600">
            {recommendation.cents_per_point === null ? "Cash path" : `${recommendation.cents_per_point.toFixed(2)} cents per point`}
          </p>
        </div>
      </div>
    </article>
  );
}

function BookingPath({ recommendation }: { recommendation: Recommendation | null }) {
  if (!recommendation) {
    return (
      <div className="mt-4 rounded-2xl border border-line bg-white p-4">
        <StatusPill tone="blue">ready to search</StatusPill>
        <p className="mt-4 text-sm leading-5 text-slate-600">
          Run a search to generate the selected booking path, payment stack, and savings.
        </p>
      </div>
    );
  }

  const option = recommendation.option;
  const rows = [
    ["Provider", option.source_provider?.replaceAll("_", " ") ?? "Unknown"],
    ["Merchant", option.merchant],
    ["Booking type", option.booking_type.replaceAll("_", " ")],
    ["Points", option.points_used ? points(option.points_used) : "Save for later"],
  ];

  return (
    <div className="mt-4 rounded-2xl border border-line bg-white p-4">
      <StatusPill tone="green">ready to review</StatusPill>
      <div className="my-4 border-y border-line py-4">
        <p className="text-sm text-slate-500">Pay now</p>
        <p className="mt-1 text-4xl font-extrabold tracking-[-0.04em] text-ink">{dollars(recommendation.out_of_pocket_usd)}</p>
        <p className="text-sm text-slate-500">{dollars(recommendation.effective_savings_usd)} savings included</p>
      </div>
      <div className="space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between border-t border-line pt-2 first:border-t-0 first:pt-0">
            <span className="text-sm text-slate-600">{label}</span>
            <strong className="max-w-36 text-right text-sm capitalize text-ink">{value}</strong>
          </div>
        ))}
      </div>
      <button className="mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-night px-4 text-sm font-bold text-white">
        <WalletCards size={16} aria-hidden="true" />
        Open details
      </button>
    </div>
  );
}

function ConnectedEmptyState({
  connectedSourceCount,
  providerReadiness,
}: {
  connectedSourceCount: number;
  providerReadiness: ProviderReadiness[];
}) {
  if (!connectedSourceCount) {
    return (
      <div className="rounded-2xl border border-line bg-white p-8 text-sm text-slate-600">
        The hosted frontend is live. Deploy the FastAPI backend and set <code>NEXT_PUBLIC_API_URL</code> to enable live searches.
      </div>
    );
  }

  const configured = providerReadiness.filter((provider) => provider.configured).slice(0, 5);

  return (
    <div className="rounded-2xl border border-accent/30 bg-white p-5 shadow-sm">
      <StatusPill tone="green">{connectedSourceCount} production sources ready</StatusPill>
      <p className="mt-3 text-sm leading-5 text-slate-600">
        The Render API is connected. Press <strong>Search</strong> or <strong>Build itinerary</strong> to pull live flight and hotel results.
      </p>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {configured.map((provider) => (
          <div key={`${provider.category}-${provider.provider}`} className="rounded-xl border border-line bg-surface/70 p-3">
            <p className="text-sm font-semibold text-ink">{provider.provider.replaceAll("_", " ")}</p>
            <p className="mt-1 text-xs font-semibold uppercase text-teal-700">{provider.environment}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function deriveRoute(label: string, origin: string, destination: string) {
  const lower = label.toLowerCase();
  const from = normalizeAirportCode(origin, "SFO");

  if (lower.includes("san diego") || lower.includes("san ")) {
    return { from, to: "SAN" };
  }
  if (lower.includes("nyc") || lower.includes("new york")) {
    return { from, to: "NYC" };
  }
  return { from, to: normalizeAirportCode(destination, "TRIP") };
}

function normalizeAirportCode(value: string, fallback: string) {
  const trimmed = value.trim().toUpperCase();
  if (!trimmed) {
    return fallback;
  }

  const aliases: Record<string, string> = {
    "NEW YORK": "NYC",
    NYC: "NYC",
    "SAN DIEGO": "SAN",
    SAN: "SAN",
    "LOS ANGELES": "LAX",
    "SAN FRANCISCO": "SFO",
  };

  return aliases[trimmed] ?? trimmed.slice(0, 3);
}
