"use client";

import { useState } from "react";

export function ClearCapturedData({ apiUrl, userId }: { apiUrl: string; userId: string }) {
  const [status, setStatus] = useState<"idle" | "clearing" | "done" | "error">("idle");

  async function clearData() {
    setStatus("clearing");
    try {
      const response = await fetch(`${apiUrl}/ingestion/state/${userId}`, { method: "DELETE" });
      if (!response.ok) {
        throw new Error(`Clear failed: ${response.status}`);
      }
      setStatus("done");
      window.location.reload();
    } catch {
      setStatus("error");
    }
  }

  return (
    <button
      className="h-8 rounded-md border border-line bg-white px-2.5 text-xs font-semibold text-slate-700"
      type="button"
      onClick={clearData}
      disabled={status === "clearing"}
    >
      {status === "clearing" ? "Clearing" : status === "error" ? "Retry clear" : "Clear"}
    </button>
  );
}
