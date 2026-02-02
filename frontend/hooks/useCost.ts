// hooks/useCost.ts
"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { readCache, writeCache } from "@/lib/cache";
import type { CostRes } from "@/types/dashboard";

const COST_TTL = 60_000; // 60s

export function useCost(plantId: string, year: number, month1to12: number) {
  const [data, setData] = useState<CostRes | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      const cacheKey = `cost:${plantId}:${year}:${month1to12}`;
      const cached = readCache<CostRes>(cacheKey);
      if (cached && alive) {
        setData(cached);
        setLoading(false);
      }

      try {
        if (alive) {
          setLoading((prev) => prev && !cached);
          setError(null);
        }

        // ✅ TODO: ปรับ endpoint ให้ตรงของคุณ
        // ตัวอย่าง: /api/cost_summary?year=2026&month=2
        const res = await fetchJson<CostRes>(
          `/api/cost_summary?year=${year}&month=${month1to12}`,
          { plantId, timeoutMs: 10_000 }
        );

        writeCache(cacheKey, res, COST_TTL);
        if (!alive) return;
        setData(res);
        setLoading(false);
      } catch (e) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : "cost error");
        setLoading(false);
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, [plantId, year, month1to12]);

  return { data, loading, error };
}
