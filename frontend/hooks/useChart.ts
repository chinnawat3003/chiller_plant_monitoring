// hooks/useChart.ts
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { fetchJson } from "@/lib/api";
import { readCache, writeCache } from "@/lib/cache";
import { chartByKey, type ChartKey } from "@/lib/charts";
import type { ChartRes, LimitsRes } from "@/types/dashboard";

const CHART_TTL = 60_000; // 60s

type ChartState = {
  loading: boolean;
  error: string | null;
  options: any | null; // ag-charts options
};

export function useChart(plantId: string, key: ChartKey) {
  const [state, setState] = useState<ChartState>({
    loading: true,
    error: null,
    options: null,
  });

  const inFlight = useRef(false);

  useEffect(() => {
    let alive = true;

    async function load() {
      if (inFlight.current) return;
      inFlight.current = true;

      const cfg = chartByKey(key);
      const cacheKey = `chart:${plantId}:${key}`;

      // 1) try cache
      const cached = readCache<any>(cacheKey);
      if (cached && alive) {
        setState({ loading: false, error: null, options: cached });
      }

      try {
        if (alive) setState((s) => ({ ...s, loading: s.options === null }));

        const [hist, lim] = await Promise.all([
          fetchJson<ChartRes>(cfg.historyPath, { plantId, timeoutMs: 10_000 }),
          cfg.limitPath
            ? fetchJson<LimitsRes>(cfg.limitPath, { plantId, timeoutMs: 8000 })
            : Promise.resolve<LimitsRes>({ ok: false }),
        ]);

        const points = (hist.points ?? []).map((p) => ({
          time: new Date(p.t),
          value: p.v,
        }));

        const min = lim?.ok ? lim.min : null;
        const max = lim?.ok ? lim.max : null;

        const options = {
          title: { text: `${cfg.title}${cfg.unit ? ` (${cfg.unit})` : ""}` },
          data: points,
          series: [
            {
              type: "line",
              xKey: "time",
              yKey: "value",
              yName: cfg.title,
              marker: { enabled: false },
            },
          ],
          axes: [
            { type: "time", position: "bottom" },
            {
              type: "number",
              position: "left",
              min: typeof min === "number" ? min : undefined,
              max: typeof max === "number" ? max : undefined,
            },
          ],
          legend: { enabled: false },
        };

        writeCache(cacheKey, options, CHART_TTL);
        if (alive) setState({ loading: false, error: null, options });
      } catch (e) {
        if (!alive) return;
        setState((s) => ({
          ...s,
          loading: false,
          error: e instanceof Error ? e.message : "chart error",
        }));
      } finally {
        inFlight.current = false;
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, [plantId, key]);

  return useMemo(() => state, [state]);
}
