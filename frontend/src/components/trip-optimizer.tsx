"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Loader2,
  Search,
  SlidersHorizontal,
} from "lucide-react";

import { AccountBalanceEditor } from "@/components/account-balance-editor";
import { BrandMark } from "@/components/brand/brand-mark";
import { ClearCapturedData } from "@/components/clear-captured-data";
import { RecommendationCard } from "@/components/recommendation-card";
import { dollars } from "@/lib/format";
import type {
  IngestionState,
  OptimizationResponse,
  Program,
  ProviderReadiness,
  RankingMode,
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
  const comparisonOptions = rankedOptions.slice(0, 10);
  const discoverySummary = response ? getDiscoverySummary(response) : null;

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
      const discoveryMode = shouldUseDiscoveryMode(intent, destination);
      const apiResponse = await fetch(`${apiUrl}/travel-search/${discoveryMode ? "discover" : "optimize"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search: {
            user_id: userId,
            raw_intent: constraints.length ? `${intent.trim()} Constraints: ${constraints.join("; ")}.` : intent.trim(),
            origin: origin.trim() || undefined,
            destination: discoveryMode ? "Open destination discovery" : destination.trim() || undefined,
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
          ...(discoveryMode
            ? {
                max_destinations: 10,
                include_near_misses: true,
              }
            : {}),
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
      <section className="mx-auto max-w-[1320px] overflow-hidden rounded-2xl border border-line bg-white/78 shadow-[0_24px_70px_rgba(27,39,60,0.12)]">
        <header className="flex min-h-20 flex-wrap items-center justify-between gap-4 border-b border-line bg-white/95 px-5 py-4 backdrop-blur md:px-7">
          <div className="flex items-center gap-3">
            <BrandMark />
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

        <section className="bg-gradient-to-r from-[#f6f9fc] to-[#eef6f5] p-4 md:p-6">
          <form className="rounded-2xl border border-line bg-white p-4 shadow-sm md:p-5" onSubmit={optimize}>
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Trip intent</p>
                <h1 className="mt-2 max-w-2xl text-3xl font-semibold leading-tight tracking-[-0.02em] text-ink">
                  Describe the trip. Refine it like a normal travel search.
                </h1>
                <label className="mt-4 block">
                  <span className="text-xs font-bold uppercase text-slate-500">Prompt</span>
                  <textarea
                    className="mt-1 min-h-28 w-full resize-none rounded-xl border border-line bg-surface/50 p-3 text-base leading-6 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                    value={intent}
                    onChange={(event) => setIntent(event.target.value)}
                  />
                </label>
                <div className="mt-3 flex flex-wrap gap-2">
                  {SAMPLE_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => setIntent(prompt)}
                      className="rounded-md border border-line bg-white px-3 py-2 text-left text-xs font-semibold leading-4 text-slate-600 transition hover:border-cobalt/40 hover:text-ink"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>

              <SearchContextPanel
                connectedSourceCount={connectedSourceCount}
                capturedCount={capturedCount}
                capturedAccounts={capturedAccounts}
                capturedOffers={capturedOffers}
                ingestionState={ingestionState}
                providerStatuses={providerStatuses}
                apiUrl={apiUrl}
                userId={userId}
              />
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_1fr_1fr_auto]">
              <SearchField label="From" value={origin} onChange={setOrigin} />
              <SearchField label="To / destination" value={destination} onChange={setDestination} />
              <DateField label="Depart" value={departureDate} onChange={setDepartureDate} />
              <DateField label="Return" value={returnDate} onChange={setReturnDate} />
              <SearchField label="Budget" value={budget} onChange={setBudget} />
              <button
                type="submit"
                disabled={isOptimizing}
                className="inline-flex min-h-14 items-center justify-center gap-2 rounded-xl bg-night px-6 text-sm font-bold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isOptimizing ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                Search
              </button>
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_210px]">
              <SearchField label="Hotel details" value={hotelPreference} onChange={setHotelPreference} />
              <label className="block rounded-xl border border-line bg-surface/60 px-3 py-2">
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
              <label className="flex min-h-14 items-center justify-between rounded-xl border border-line bg-surface/60 px-3 py-2">
                <span>
                  <span className="block text-xs font-bold uppercase text-slate-500">Direct flights</span>
                  <strong className="text-base">{directOnly ? "Only direct" : "Allow stops"}</strong>
                </span>
                <input
                  type="checkbox"
                  checked={directOnly}
                  onChange={(event) => setDirectOnly(event.target.checked)}
                  className="h-4 w-4 accent-teal-600"
                />
              </label>
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <SearchField label="Arrival / travel-time preference" value={arrivalWindow} onChange={setArrivalWindow} />
              <ProgramSelector selectedPrograms={selectedPrograms} onToggle={toggleProgram} />
            </div>
          </form>

          <section className="mt-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Suggested itineraries</p>
                <h2 className="mt-1 text-2xl font-semibold tracking-[-0.02em] text-ink">
                  {response
                    ? "Best booking paths"
                    : connectedSourceCount
                      ? "Ready for a live itinerary search"
                      : "Connect the API to build a live itinerary"}
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  Expand an option to inspect flight, hotel, provider detail, and payment math.
                </p>
              </div>
              <p className="text-sm text-slate-500">
                {comparisonOptions.length
                  ? `${comparisonOptions.length} itinerary ${comparisonOptions.length === 1 ? "option" : "options"}`
                  : connectedSourceCount
                    ? `${connectedSourceCount} production sources ready`
                    : "Waiting for provider results"}
              </p>
            </div>

            {error ? <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</p> : null}

            {discoverySummary ? <DiscoverySummaryPanel summary={discoverySummary} /> : null}

            <div className="mt-4 space-y-3">
              {comparisonOptions.length ? (
                comparisonOptions.map((recommendation, index) => (
                  <RecommendationCard
                    key={`${recommendation.rank}-${recommendation.option.label}`}
                    recommendation={recommendation}
                    displayRank={index + 1}
                  />
                ))
              ) : (
                <ConnectedEmptyState connectedSourceCount={connectedSourceCount} providerReadiness={providerReadiness} />
              )}
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

function shouldUseDiscoveryMode(intent: string, destination: string) {
  const text = intent.toLowerCase();
  const destinationText = destination.trim().toLowerCase();
  if (!destinationText || destinationText.includes("open") || destinationText.includes("any")) {
    return true;
  }

  const discoverySignals = [
    "anywhere",
    "any destination",
    "somewhere",
    "find me",
    "where should",
    "under 3 hours",
    "under three hours",
    "fly more than",
    "drive more than",
    "flight time",
    "drive time",
  ];
  const hasDiscoverySignal = discoverySignals.some((signal) => text.includes(signal));
  const hasSpecificDestination = /\b(nyc|new york|san diego|los angeles|las vegas|seattle|portland|phoenix|palm springs)\b/.test(text);
  return hasDiscoverySignal && !hasSpecificDestination;
}

function getDiscoverySummary(response: OptimizationResponse) {
  const discoveryOptions = response.recommendations
    .map((recommendation) => recommendation.option)
    .filter((option) => option.source_provider === "trip_discovery");
  const searchedWarning = response.warnings.find((warning) => warning.startsWith("Discovery mode:"));
  const constraintWarning = response.warnings.find((warning) => warning.startsWith("Discovery constraints:"));

  if (!discoveryOptions.length && !searchedWarning) {
    return null;
  }

  const destinations = Array.from(
    new Set(
      discoveryOptions
        .map((option) => option.details?.destination)
        .filter((destination): destination is string => typeof destination === "string" && Boolean(destination.trim())),
    ),
  );
  const searched = searchedWarning?.replace("Discovery mode: searched Bay Area candidates:", "").replace(/\.$/, "").trim();

  return {
    searched,
    constraints: constraintWarning?.replace("Discovery constraints:", "").replace(/\.$/, "").trim(),
    matchedDestinations: destinations,
    skipped: response.warnings.filter((warning) => warning.startsWith("Skipped ")).slice(0, 4),
  };
}

function DiscoverySummaryPanel({
  summary,
}: {
  summary: {
    searched?: string;
    constraints?: string;
    matchedDestinations: string[];
    skipped: string[];
  };
}) {
  return (
    <section className="mt-3 rounded-2xl border border-cobalt/20 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Discovery mode</p>
          <h3 className="mt-1 text-base font-semibold text-ink">Multi-destination search from the Bay Area</h3>
        </div>
        <StatusPill tone="blue">query plan</StatusPill>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {summary.searched ? (
          <div className="rounded-xl border border-line bg-surface/70 p-3">
            <p className="text-xs font-bold uppercase text-slate-500">Searched</p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{summary.searched}</p>
          </div>
        ) : null}
        {summary.constraints ? (
          <div className="rounded-xl border border-line bg-surface/70 p-3">
            <p className="text-xs font-bold uppercase text-slate-500">Constraints</p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{summary.constraints}</p>
          </div>
        ) : null}
      </div>
      {summary.matchedDestinations.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {summary.matchedDestinations.map((destination) => (
            <span key={destination} className="rounded-md bg-accent/10 px-2.5 py-1 text-xs font-semibold text-teal-800">
              {destination}
            </span>
          ))}
        </div>
      ) : null}
      {summary.skipped.length ? (
        <div className="mt-3 space-y-1">
          {summary.skipped.map((warning) => (
            <p key={warning} className="text-xs leading-5 text-slate-500">
              {warning}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function SearchContextPanel({
  connectedSourceCount,
  capturedCount,
  capturedAccounts,
  capturedOffers,
  ingestionState,
  providerStatuses,
  apiUrl,
  userId,
}: {
  connectedSourceCount: number;
  capturedCount: number;
  capturedAccounts: IngestionState["accounts"];
  capturedOffers: IngestionState["offers"];
  ingestionState: IngestionState | null;
  providerStatuses: OptimizationResponse["provider_statuses"];
  apiUrl: string;
  userId: string;
}) {
  return (
    <aside className="rounded-xl border border-line bg-surface/60 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-extrabold uppercase tracking-wide text-signal">Search context</p>
        <StatusPill tone={connectedSourceCount ? "green" : "blue"}>
          {connectedSourceCount ? `${connectedSourceCount} sources` : "beta"}
        </StatusPill>
      </div>

      <div className="mt-3 grid gap-2">
        <div className="rounded-md bg-white p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase text-slate-500">Captured loyalty</p>
              <p className="mt-1 text-sm font-semibold text-ink">
                {capturedCount ? `${capturedCount} account/offer inputs` : "No capture yet"}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {ingestionState?.last_run ? `Last ${ingestionState.last_run.status}` : "Use the extension to add balances and offers."}
              </p>
            </div>
            {capturedCount > 0 ? <ClearCapturedData apiUrl={apiUrl} userId={userId} /> : null}
          </div>
        </div>

        {capturedAccounts.slice(0, 3).map((account) => (
          <div key={account.id} className="rounded-md bg-white p-3">
            <p className="text-xs font-bold uppercase text-slate-500">{account.display_name}</p>
            <AccountBalanceEditor account={account} apiUrl={apiUrl} userId={userId} />
          </div>
        ))}

        {capturedOffers.slice(0, 2).map((offer) => (
          <div key={offer.id} className="rounded-md bg-white p-3">
            <p className="text-sm font-semibold text-ink">{offer.merchant}</p>
            <p className="mt-1 text-xs text-slate-600">
              {dollars(offer.value_usd)} value on {dollars(offer.min_spend_usd)} spend
            </p>
          </div>
        ))}

        {providerStatuses.length ? (
          <div className="rounded-md bg-white p-3">
            <p className="text-xs font-bold uppercase text-slate-500">Provider health</p>
            <div className="mt-2 space-y-1">
              {providerStatuses.slice(0, 3).map((status) => (
                <div key={`${status.category}-${status.provider}`} className="flex items-center justify-between gap-2 text-xs">
                  <span className="truncate text-slate-600">{status.provider.replaceAll("_", " ")}</span>
                  <strong className={status.status === "live" ? "text-teal-700" : "text-amber-700"}>{status.status}</strong>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}

function ProgramSelector({
  selectedPrograms,
  onToggle,
}: {
  selectedPrograms: Program[];
  onToggle: (program: Program) => void;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface/60 px-3 py-2">
      <span className="text-xs font-bold uppercase text-slate-500">Programs</span>
      <div className="mt-2 flex flex-wrap gap-2">
        {PROGRAM_OPTIONS.map((program) => {
          const selected = selectedPrograms.includes(program.value);
          return (
            <button
              key={program.value}
              type="button"
              onClick={() => onToggle(program.value)}
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
