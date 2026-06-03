"use client";

import { useMemo, useState } from "react";
import { ArrowRightLeft, BadgeDollarSign, ChevronDown, Coins, ExternalLink, Route, WalletCards } from "lucide-react";

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
                ["Provider ref", recommendation.option.provider_reference ?? "Not supplied"],
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

          <ProviderDetailSection option={recommendation.option} />

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

function ProviderDetailSection({ option }: { option: Recommendation["option"] }) {
  const details = option.details ?? {};
  const kind = stringValue(details.kind);
  const packageFlight = recordValue(details.flight);
  const packageHotel = recordValue(details.hotel);

  return (
    <section className="mt-3 rounded-md border border-line bg-surface/80 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase text-signal">Provider details</p>
        {option.booking_url ? <BookingLink href={option.booking_url} /> : null}
      </div>

      {kind === "trip_package" ? (
        <>
          <DetailRows
            rows={compactRows([
              ["Destination", stringValue(details.destination)],
              ["Region", stringValue(details.region)],
              ["Constraint fit", stringValue(details.constraint_fit)?.replaceAll("_", " ")],
              ["Travel time", numberValue(details.travel_minutes) === null ? undefined : `${numberValue(details.travel_minutes)} min`],
            ])}
          />
          <div className="mt-2 grid gap-3 md:grid-cols-2">
            {packageFlight ? <LegDetailCard title="Flight" leg={packageFlight} /> : null}
            {packageHotel ? <LegDetailCard title="Hotel" leg={packageHotel} /> : null}
          </div>
        </>
      ) : (
        <StandaloneDetailCard details={details} bookingUrl={option.booking_url ?? null} />
      )}
    </section>
  );
}

function LegDetailCard({ title, leg }: { title: string; leg: Record<string, unknown> }) {
  const nestedDetails = recordValue(leg.details) ?? {};
  const bookingUrl = stringValue(leg.booking_url);
  const rows = compactRows([
    ["Provider", stringValue(leg.provider)?.replaceAll("_", " ")],
    ["Merchant", stringValue(leg.merchant)],
    ["Price", numberValue(leg.cash_price_usd) === null ? undefined : dollars(numberValue(leg.cash_price_usd) ?? 0)],
    ["Reference", stringValue(leg.provider_reference)],
    ["Room", stringValue(nestedDetails.room)],
    ["Stars", valueText(nestedDetails.stars)],
    ["Rating", valueText(nestedDetails.guest_rating)],
    ["Duration", stringValue(nestedDetails.duration)],
  ]);

  return (
    <div className="rounded-md bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-ink">{title}</p>
          <p className="mt-1 text-sm leading-5 text-slate-700">{stringValue(leg.label) ?? "Selected option"}</p>
        </div>
        {bookingUrl ? <BookingLink href={bookingUrl} short /> : null}
      </div>
      <DetailRows rows={rows} />
      <NestedDetailFacts details={nestedDetails} />
    </div>
  );
}

function StandaloneDetailCard({
  details,
  bookingUrl,
}: {
  details: Record<string, unknown>;
  bookingUrl: string | null;
}) {
  const rows = compactRows([
    ["Kind", stringValue(details.kind)],
    ["Stops", valueText(details.stops)],
    ["Duration", stringValue(details.duration)],
    ["Room", stringValue(details.room)],
    ["Stars", valueText(details.stars)],
    ["Guest rating", valueText(details.guest_rating)],
    ["Refundable", booleanText(details.refundable)],
    ["Address", stringValue(details.address)],
  ]);

  return (
    <div className="mt-2 rounded-md bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm leading-5 text-slate-700">
          {bookingUrl ? "Open the source link to verify current availability, price, and final checkout rules." : "Provider did not supply an open verification link for this result yet."}
        </p>
        {bookingUrl ? <BookingLink href={bookingUrl} short /> : null}
      </div>
      <DetailRows rows={rows} />
      <NestedDetailFacts details={details} />
    </div>
  );
}

function NestedDetailFacts({ details }: { details: Record<string, unknown> }) {
  const segments = arrayValue(details.segments);
  const slices = arrayValue(details.slices);
  const amenities = arrayValue(details.amenities);

  if (!segments.length && !slices.length && !amenities.length) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2">
      {slices.map((slice, index) => {
        const sliceRecord = recordValue(slice);
        if (!sliceRecord) return null;
        return (
          <div key={`slice-${index}`} className="rounded-md border border-line bg-surface/70 p-2">
            <p className="text-xs font-semibold text-ink">
              {stringValue(sliceRecord.origin) ?? "Origin"} to {stringValue(sliceRecord.destination) ?? "Destination"}
            </p>
            {stringValue(sliceRecord.duration) ? <p className="mt-1 text-xs text-slate-600">{stringValue(sliceRecord.duration)}</p> : null}
          </div>
        );
      })}
      {segments.slice(0, 4).map((segment, index) => {
        const segmentRecord = recordValue(segment);
        if (!segmentRecord) return null;
        return (
          <div key={`segment-${index}`} className="rounded-md border border-line bg-surface/70 p-2">
            <p className="text-xs font-semibold text-ink">
              {stringValue(segmentRecord.airline) ?? "Flight"} {stringValue(segmentRecord.flight_number) ?? ""}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {stringValue(segmentRecord.departure_airport) ?? stringValue(segmentRecord.origin) ?? "Origin"} to{" "}
              {stringValue(segmentRecord.arrival_airport) ?? stringValue(segmentRecord.destination) ?? "Destination"}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {stringValue(segmentRecord.departure_time) ?? stringValue(segmentRecord.local_departure) ?? stringValue(segmentRecord.departing_at) ?? ""}
              {stringValue(segmentRecord.arrival_time) || stringValue(segmentRecord.local_arrival) || stringValue(segmentRecord.arriving_at)
                ? ` -> ${stringValue(segmentRecord.arrival_time) ?? stringValue(segmentRecord.local_arrival) ?? stringValue(segmentRecord.arriving_at)}`
                : ""}
            </p>
          </div>
        );
      })}
      {amenities.length ? (
        <div className="flex flex-wrap gap-2">
          {amenities.slice(0, 8).map((amenity) => (
            <span key={String(amenity)} className="rounded-md bg-surface px-2 py-1 text-xs text-slate-600">
              {String(amenity)}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function DetailRows({ rows }: { rows: Array<[string, string]> }) {
  if (!rows.length) {
    return null;
  }

  return (
    <div className="mt-3 grid gap-2 md:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="rounded-md bg-surface px-2 py-1.5">
          <p className="text-[11px] uppercase text-slate-500">{label}</p>
          <p className="mt-0.5 text-xs font-semibold text-ink">{value}</p>
        </div>
      ))}
    </div>
  );
}

function BookingLink({ href, short = false }: { href: string; short?: boolean }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-cobalt/20 bg-cobalt/10 px-2.5 text-xs font-semibold text-blue-800"
    >
      {short ? "Open" : "Open provider"}
      <ExternalLink size={13} aria-hidden="true" />
    </a>
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

function compactRows(rows: Array<[string, string | undefined]>): Array<[string, string]> {
  return rows.filter((row): row is [string, string] => Boolean(row[1]));
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function arrayValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function booleanText(value: unknown): string | undefined {
  return typeof value === "boolean" ? (value ? "Yes" : "No") : undefined;
}

function valueText(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return undefined;
}
