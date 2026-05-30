"use client";

import { useMemo, useState } from "react";
import { ArrowRightLeft, BadgeDollarSign, ChevronDown, Coins, Route, WalletCards } from "lucide-react";

import type { Recommendation } from "@/lib/types";
import { dollars, points } from "@/lib/format";

const icons = {
  cash: BadgeDollarSign,
  points: Coins,
  hybrid: WalletCards,
  transfer: ArrowRightLeft,
  offer_enhanced: Route,
};

export function RecommendationCard({
  recommendation,
  displayRank,
}: {
  recommendation: Recommendation;
  displayRank?: number;
}) {
  const Icon = icons[recommendation.option.booking_type];
  const visibleNotes = recommendation.option.notes.filter((note) => !note.toLowerCase().includes("not configured"));
  const isPackage = recommendation.option.source_provider === "trip_package";
  const [expanded, setExpanded] = useState(false);
  const parsedDetails = useMemo(() => parseDetails(visibleNotes), [visibleNotes]);

  return (
    <article className={`rounded-lg border bg-white ${isPackage ? "border-accent" : "border-line"}`}>
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
        className="block w-full p-4 text-left"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent">
            <Icon size={20} aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <p className="text-xs font-semibold uppercase text-signal">
                Rank {displayRank ?? recommendation.rank}
              </p>
              <p className="text-xs text-slate-500">Score {recommendation.score}</p>
              {isPackage ? (
                <p className="rounded-md bg-accent/10 px-2 py-0.5 text-xs font-semibold text-teal-800">
                  Full trip path
                </p>
              ) : null}
            </div>
            <h2 className="mt-1 text-base font-semibold text-ink">{recommendation.option.label}</h2>
            <p className="mt-1 text-sm text-slate-600">{recommendation.option.merchant}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="rounded-md bg-surface px-2 py-1 text-xs text-slate-600">
                {recommendation.option.source_environment} source
              </span>
              <span className="rounded-md bg-cobalt/10 px-2 py-1 text-xs text-blue-800">
                {Math.round(recommendation.option.provider_confidence * 100)}% provider confidence
              </span>
            </div>
          </div>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line bg-white text-slate-600">
            <ChevronDown
              size={17}
              aria-hidden="true"
              className={`transition-transform ${expanded ? "rotate-180" : ""}`}
            />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <Metric label="Out of pocket" value={dollars(recommendation.out_of_pocket_usd)} />
          <Metric
            label="Cents per point"
            value={recommendation.cents_per_point === null ? "Cash" : `${recommendation.cents_per_point.toFixed(2)}¢`}
          />
          <Metric label="Savings" value={dollars(recommendation.effective_savings_usd)} />
          <Metric
            label="Points"
            value={recommendation.option.points_used ? points(recommendation.option.points_used) : "None"}
          />
        </div>
      </button>

      {expanded ? (
        <div className="border-t border-line p-4 pt-3">
          <div className="grid gap-3 md:grid-cols-2">
            <DetailPanel
              title="Booking path"
              rows={[
                ["Provider", recommendation.option.source_provider?.replaceAll("_", " ") ?? "Unknown"],
                ["Environment", recommendation.option.source_environment],
                ["Merchant", recommendation.option.merchant],
                ["Booking type", recommendation.option.booking_type.replaceAll("_", " ")],
                ["Confidence", `${Math.round(recommendation.option.provider_confidence * 100)}%`],
              ]}
            />
            <DetailPanel
              title="Payment math"
              rows={[
                ["Cash price", dollars(recommendation.option.cash_price_usd)],
                ["Taxes", dollars(recommendation.option.taxes_usd)],
                ["Fees", dollars(recommendation.option.fees_usd)],
                ["Copay", dollars(recommendation.option.copay_usd)],
                ["Offer credit", dollars(recommendation.option.offer_value_usd)],
                ["Final out-of-pocket", dollars(recommendation.out_of_pocket_usd)],
              ]}
            />
          </div>

          {parsedDetails.legs.length ? (
            <section className="mt-3 rounded-md border border-line bg-surface/80 p-3">
              <p className="text-xs font-semibold uppercase text-signal">Trip legs</p>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {parsedDetails.legs.map((leg) => (
                  <div key={leg.label} className="rounded-md bg-white px-3 py-2">
                    <p className="text-xs font-semibold text-ink">{leg.type}</p>
                    <p className="mt-1 text-sm leading-5 text-slate-700">{leg.label}</p>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <section className="mt-3 rounded-md border border-line bg-surface/80 p-3">
            <p className="text-xs font-semibold uppercase text-signal">Why this ranked here</p>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              {recommendation.reasons.map((reason) => (
                <p key={reason} className="rounded-md bg-white px-3 py-2 text-sm leading-5 text-slate-700">
                  {reason}
                </p>
              ))}
            </div>
          </section>

          {visibleNotes.length ? (
            <section className="mt-3 rounded-md border border-line bg-surface/80 p-3">
              <p className="text-xs font-semibold uppercase text-signal">Provider notes</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {visibleNotes.map((note) => (
                  <span key={note} className="rounded-md bg-white px-2 py-1 text-xs text-slate-600">
                    {note}
                  </span>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-line px-1 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink">{value}</p>
    </div>
  );
}

function DetailPanel({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return (
    <section className="rounded-md border border-line bg-surface/80 p-3">
      <p className="text-xs font-semibold uppercase text-signal">{title}</p>
      <div className="mt-2 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-start justify-between gap-4 border-t border-line pt-2 first:border-t-0 first:pt-0">
            <p className="text-xs text-slate-500">{label}</p>
            <p className="text-right text-xs font-semibold capitalize text-ink">{value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function parseDetails(notes: string[]) {
  const legs = notes
    .filter((note) => note.toLowerCase().startsWith("flight leg:") || note.toLowerCase().startsWith("hotel leg:"))
    .map((note) => {
      const [type, ...labelParts] = note.replace(/\.$/, "").split(":");
      return {
        type,
        label: labelParts.join(":").trim(),
      };
    });

  return { legs };
}
