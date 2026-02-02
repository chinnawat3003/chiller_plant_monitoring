// hooks/useSuggestion.ts
"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import type { SuggestionRes } from "@/types/dashboard";

export function useSuggestion(plantId: string) {
  const [data, setData] = useState<SuggestionRes | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      // ✅ TODO: ปรับ endpoint ให้ตรงของคุณ
      const res = await fetchJson<SuggestionRes>("/api/suggestion", {
        plantId,
        timeoutMs: 12_000,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "suggestion error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plantId]);

  return { data, loading, error, reload };
}
