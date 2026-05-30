"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Loader2, Plane, Play, SlidersHorizontal } from "lucide-react";

import { AccountBalanceEditor } from "@/components/account-balance-editor";
import { ClearCapturedData } from "@/components/clear-captured-data";
import { RecommendationCard } from "@/components/recommendation-card";
import { dollars } from "@/lib/format";
import type { IngestionState, OptimizationResponse, Program, ProviderReadiness, RankingMode } from "@/lib/types";

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
  const [ingestionState, setIngestionState] = useState<IngestionState | null>(initialIngestionState);
  const [providerReadiness, setProviderReadiness] = useState<ProviderReadiness[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const isLocalApi = apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");

  const capturedCount = (ingestionState?.accounts.length ?? 0) + (ingestionState?.offers.length ?? 0);
  const capturedAccounts = ingestionState?.accounts ?? [];
  const capturedOffers = ingestionState?.offers ?? [];
  const groupedProviderStatuses = useMemo(() => {
    const statuses = response?.provider_statuses ?? [];
    return {
      flight: statuses.filter((status) => status.category === "flight"),
      hotel: statuses.filter((status) => status.category === "hotel"),
    };
  }, [response?.provider_statuses]);
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
  const recommendedItinerary =
    groupedRecommendations.fullTripPaths[0] ?? groupedRecommendations.standalone[0] ?? null;
  const liveProductionProviders = useMemo(
    () =>
      providerReadiness.filter(
        (provider) => provider.configured && provider.environment === "production",
      ),
    [providerReadiness],
  );

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
          setProviderReadiness([]);
          setError(
            isLocalApi
              ? "Live backend is not connected to this hosted beta yet."
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
  }, [apiUrl, initialDemo, initialIngestionState, userId]);

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
    <main className="min-h-screen">
      <section className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-night text-white">
              <Plane size={18} aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-ink">Travel Booking Optimizer</p>
              <p className="text-xs text-slate-500">Live travel payment intelligence</p>
            </div>
          </div>
          <div className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm text-slate-700">
            <SlidersHorizontal size={16} className="text-cobalt" aria-hidden="true" />
            {RANKING_OPTIONS.find((option) => option.value === rankingMode)?.label ?? "Balanced"}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[390px_1fr]">
        <aside className="rounded-lg border border-line bg-white p-4">
          <p className="text-xs font-semibold uppercase text-signal">Trip intent</p>
          <h1 className="mt-2 text-2xl font-semibold leading-tight text-ink">
            Ask for the trip. Get the best live itinerary path.
          </h1>

          <form className="mt-5 space-y-4" onSubmit={optimize}>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Prompt</span>
              <textarea
                className="mt-1 min-h-28 w-full resize-none rounded-md border border-line bg-white p-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                value={intent}
                onChange={(event) => setIntent(event.target.value)}
              />
            </label>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase text-signal">Try a prompt</p>
              {SAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setIntent(prompt)}
                  className="block w-full rounded-md border border-line bg-surface px-3 py-2 text-left text-xs leading-5 text-slate-600 transition hover:border-cobalt hover:bg-white hover:text-ink"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Budget</span>
                <input
                  className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  value={budget}
                  onChange={(event) => setBudget(event.target.value)}
                  inputMode="decimal"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Destination</span>
                <input
                  className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  value={destination}
                  onChange={(event) => setDestination(event.target.value)}
                />
              </label>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">From</span>
                <input
                  className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  value={origin}
                  onChange={(event) => setOrigin(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Depart</span>
                <input
                  className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  type="date"
                  value={departureDate}
                  onChange={(event) => setDepartureDate(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Return</span>
                <input
                  className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                  type="date"
                  value={returnDate}
                  onChange={(event) => setReturnDate(event.target.value)}
                />
              </label>
            </div>

            <label className="block">
              <span className="text-sm font-medium text-slate-700">Rank by</span>
              <select
                className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
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

            <div>
              <span className="text-sm font-medium text-slate-700">Programs</span>
              <div className="mt-2 flex flex-wrap gap-2">
                {PROGRAM_OPTIONS.map((program) => {
                  const selected = selectedPrograms.includes(program.value);
                  return (
                    <button
                      key={program.value}
                      type="button"
                      onClick={() => toggleProgram(program.value)}
                      className={`rounded-md border px-2.5 py-1 text-xs font-medium ${
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

            <div className="grid gap-3">
              <label className="flex items-center justify-between gap-3 rounded-md border border-line bg-white px-3 py-2">
                <span className="text-sm font-medium text-slate-700">Direct flight only</span>
                <input
                  type="checkbox"
                  checked={directOnly}
                  onChange={(event) => setDirectOnly(event.target.checked)}
                  className="h-4 w-4 accent-teal-600"
                />
              </label>
              <input
                className="h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                value={arrivalWindow}
                onChange={(event) => setArrivalWindow(event.target.value)}
                aria-label="Arrival preference"
              />
              <input
                className="h-10 w-full rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
                value={hotelPreference}
                onChange={(event) => setHotelPreference(event.target.value)}
                aria-label="Hotel preference"
              />
            </div>

            <button
              type="submit"
              disabled={isOptimizing}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-night px-4 text-sm font-semibold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isOptimizing ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
              Build itinerary
            </button>
          </form>

          <section className="mt-5 border-t border-line pt-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase text-signal">Captured data</p>
              <div className="flex items-center gap-2">
                <p className="text-xs text-slate-500">
                  {ingestionState?.last_run ? `Last ${ingestionState.last_run.status}` : "No capture yet"}
                </p>
                {capturedCount > 0 ? <ClearCapturedData apiUrl={apiUrl} userId={userId} /> : null}
              </div>
            </div>

            {capturedCount > 0 ? (
              <div className="mt-3 space-y-3">
                {typeof ingestionState?.last_run?.metadata?.extraction_confidence === "number" ? (
                  <div className="border-t border-line pt-3">
                    <p className="text-sm font-semibold text-ink">
                      {Math.round(ingestionState.last_run.metadata.extraction_confidence * 100)}% extraction confidence
                    </p>
                    {ingestionState.last_run.metadata.page_url_host ? (
                      <p className="mt-1 text-sm text-slate-600">{ingestionState.last_run.metadata.page_url_host}</p>
                    ) : null}
                    {ingestionState.last_run.metadata.warnings?.length ? (
                      <p className="mt-1 text-sm text-slate-600">
                        {ingestionState.last_run.metadata.warnings.join(" ")}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {capturedAccounts.map((account) => (
                  <div key={account.id} className="border-t border-line pt-3">
                    <p className="text-sm font-semibold text-ink">{account.display_name}</p>
                    <AccountBalanceEditor account={account} apiUrl={apiUrl} userId={userId} />
                  </div>
                ))}

                {capturedOffers.map((offer) => (
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
                Use the Chrome extension to capture a visible rewards page, then refresh this app.
              </p>
            )}
          </section>
        </aside>

        <section className="space-y-4">
          <div className="rounded-lg border border-line bg-white p-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase text-signal">Live itinerary</p>
                <h2 className="mt-1 text-xl font-semibold text-ink">
                  {response ? "Best booking paths from live providers" : "Connect the API to build a live itinerary"}
                </h2>
              </div>
              <p className="text-sm text-slate-500">
                {liveProductionProviders.length
                  ? `${liveProductionProviders.length} production sources connected`
                  : "Waiting for live provider status"}
              </p>
            </div>
            {error ? <p className="mt-3 text-sm font-medium text-red-700">{error}</p> : null}
            {recommendedItinerary ? <ItinerarySummary recommendation={recommendedItinerary} /> : null}
            {response?.provider_statuses?.length ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <ProviderStatusGroup label="Flights" statuses={groupedProviderStatuses.flight} />
                <ProviderStatusGroup label="Hotels" statuses={groupedProviderStatuses.hotel} />
              </div>
            ) : null}
            {providerReadiness.length ? <ProviderReadinessPanel providers={providerReadiness} /> : null}
          </div>

          {response ? (
            <>
              {groupedRecommendations.fullTripPaths.length ? (
                <RecommendationSection
                  title="Itinerary paths"
                  description="Flight and hotel combinations with credits, live provider confidence, and prompt constraints applied."
                  recommendations={groupedRecommendations.fullTripPaths}
                />
              ) : null}

              <RecommendationSection
                title="Standalone options"
                description="Individual fares, hotels, award comparisons, and payment paths that can still be useful."
                recommendations={groupedRecommendations.standalone}
              />
            </>
          ) : (
            <div className="rounded-lg border border-line bg-white p-8 text-sm text-slate-600">
              The hosted frontend is live. Deploy the FastAPI backend and set <code>NEXT_PUBLIC_API_URL</code> to enable live searches.
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function RecommendationSection({
  title,
  description,
  recommendations,
}: {
  title: string;
  description: string;
  recommendations: OptimizationResponse["recommendations"];
}) {
  if (!recommendations.length) {
    return null;
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h3 className="text-sm font-semibold uppercase text-signal">{title}</h3>
          <p className="mt-1 text-sm text-slate-600">{description}</p>
        </div>
        <p className="text-xs text-slate-500">{recommendations.length} options</p>
      </div>
      {recommendations.map((recommendation, index) => (
        <RecommendationCard
          key={`${recommendation.rank}-${recommendation.option.label}`}
          recommendation={recommendation}
          displayRank={index + 1}
        />
      ))}
    </section>
  );
}

function ItinerarySummary({ recommendation }: { recommendation: OptimizationResponse["recommendations"][number] }) {
  const isFullTrip = recommendation.option.source_provider === "trip_package";

  return (
    <div className="mt-4 rounded-md border border-accent/40 bg-gradient-to-br from-accent/10 via-white to-cobalt/10 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <CheckCircle2 size={17} className="text-accent" aria-hidden="true" />
            <p className="text-xs font-semibold uppercase text-teal-800">
              {isFullTrip ? "Recommended itinerary" : "Best current option"}
            </p>
          </div>
          <h3 className="mt-2 text-lg font-semibold leading-snug text-ink">{recommendation.option.label}</h3>
          <p className="mt-1 text-sm text-slate-700">
            {recommendation.option.source_environment} source · {Math.round(recommendation.option.provider_confidence * 100)}% provider confidence
          </p>
        </div>
        <div className="grid min-w-48 grid-cols-2 gap-2 text-right">
          <SummaryMetric label="Pay now" value={dollars(recommendation.out_of_pocket_usd)} />
          <SummaryMetric label="Savings" value={dollars(recommendation.effective_savings_usd)} />
        </div>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-3">
        {recommendation.reasons.slice(0, 3).map((reason) => (
          <p key={reason} className="rounded-md bg-white px-3 py-2 text-sm leading-5 text-slate-700">
            {reason}
          </p>
        ))}
      </div>
    </div>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-base font-semibold text-ink">{value}</p>
    </div>
  );
}

function ProviderStatusGroup({
  label,
  statuses,
}: {
  label: string;
  statuses: OptimizationResponse["provider_statuses"];
}) {
  const liveCount = statuses.filter((status) => status.status === "live").length;

  return (
    <div className="rounded-md border border-line bg-surface/80 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase text-signal">{label}</p>
        <p className="text-xs text-slate-500">
          {liveCount ? `${liveCount} live` : "Fallback ready"}
        </p>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {statuses.map((status) => (
          <div
            key={`${status.category}-${status.provider}`}
            className="rounded-md border border-line bg-white px-2.5 py-1 text-xs text-slate-700"
            title={status.warnings.join(" ")}
          >
            {status.provider.replaceAll("_", " ")}
            {" · "}
            <span className={status.status === "live" ? "text-teal-700" : "text-amber-700"}>
              {status.status}
            </span>
            {" · "}
            {status.environment}
            {" · "}
            {status.result_count}
          </div>
        ))}
      </div>
    </div>
  );
}

function ProviderReadinessPanel({ providers }: { providers: ProviderReadiness[] }) {
  const configured = providers.filter((provider) => provider.configured).length;

  return (
    <div className="mt-4 rounded-md border border-line bg-surface/80 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase text-signal">V1 data readiness</p>
        <p className="text-xs text-slate-500">
          {configured}/{providers.length} configured
        </p>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {providers.map((provider) => (
          <div key={`${provider.category}-${provider.provider}`} className="rounded-md border border-line bg-white p-2.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-semibold text-ink">{provider.provider.replaceAll("_", " ")}</p>
              <span
                className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
                  provider.configured ? "bg-accent/10 text-teal-800" : "bg-orange-50 text-signal"
                }`}
              >
                {provider.configured ? provider.environment : "needed"}
              </span>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">{provider.v1_role}</p>
            <p className="mt-1 text-xs leading-5 text-slate-500">{provider.next_step}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
