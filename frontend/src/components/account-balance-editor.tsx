"use client";

import { Check, Pencil, X } from "lucide-react";
import { useState } from "react";

import { points } from "@/lib/format";
import type { LoyaltyAccount } from "@/lib/types";

export function AccountBalanceEditor({
  account,
  apiUrl,
  userId,
}: {
  account: LoyaltyAccount;
  apiUrl: string;
  userId: string;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(String(account.points_balance));
  const [status, setStatus] = useState<"idle" | "saving" | "error">("idle");

  async function saveBalance() {
    const normalizedValue = Number(value.replace(/,/g, "").trim());
    if (!Number.isInteger(normalizedValue) || normalizedValue < 0) {
      setStatus("error");
      return;
    }

    setStatus("saving");
    try {
      const response = await fetch(`${apiUrl}/ingestion/state/${userId}/accounts/${account.program}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          points_balance: normalizedValue,
          display_name: account.display_name,
        }),
      });

      if (!response.ok) {
        throw new Error(`Correction failed: ${response.status}`);
      }

      window.location.reload();
    } catch {
      setStatus("error");
    }
  }

  if (!isEditing) {
    return (
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-sm text-slate-600">{points(account.points_balance)} points</p>
        <button
          aria-label={`Correct ${account.display_name} balance`}
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-line bg-white text-slate-600 hover:text-ink"
          type="button"
          onClick={() => setIsEditing(true)}
        >
          <Pencil size={14} aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-2">
        <input
          aria-label={`${account.display_name} corrected points balance`}
          className="h-9 min-w-0 flex-1 rounded-md border border-line bg-surface px-2.5 text-sm outline-none focus:border-accent"
          inputMode="numeric"
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setStatus("idle");
          }}
        />
        <button
          aria-label="Save corrected balance"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ink text-white disabled:opacity-60"
          type="button"
          onClick={saveBalance}
          disabled={status === "saving"}
        >
          <Check size={15} aria-hidden="true" />
        </button>
        <button
          aria-label="Cancel balance correction"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line bg-white text-slate-600"
          type="button"
          onClick={() => {
            setValue(String(account.points_balance));
            setStatus("idle");
            setIsEditing(false);
          }}
        >
          <X size={15} aria-hidden="true" />
        </button>
      </div>
      {status === "error" ? <p className="text-xs font-medium text-red-700">Enter a whole points balance.</p> : null}
    </div>
  );
}
