// hooks/useSnapshots.ts
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { fetchJson } from "@/lib/api";
import type { OneShotOk, Item } from "@/types/dashboard";

type SnapshotState = {
  loading: boolean;
  error: string | null;
  items: Item[];
};

const POLL_MS = 10_000;

export function useSnapshots(plantId: string) {
  const [state, setState] = useState<SnapshotState>({
    loading: true,
    error: null,
    items: [],
  });

  const inFlight = useRef(false);

  async function loadOnce() {
    if (inFlight.current) return;
    inFlight.current = true;

    try {
      setState((s) => ({ ...s, loading: s.items.length === 0, error: null }));

      // ปรับ endpoint ให้ตรงของคุณ
      const paths = [
        "/api/snapshot_chiller",
        "/api/snapshot_pumps",
        "/api/snapshot_temps",
        "/api/snapshot_flow",
      ];

      const results = await Promise.allSettled(
        paths.map((p) => fetchJson<OneShotOk>(p, { plantId, timeoutMs: 8000 }))
      );

      const merged: Item[] = [];
      for (const r of results) {
        if (r.status === "fulfilled" && r.value?.ok) {
          merged.push(...(r.value.items ?? []));
        }
      }

      setState({ loading: false, error: null, items: merged });
    } catch (e) {
      setState((s) => ({
        ...s,
        loading: false,
        error: e instanceof Error ? e.message : "snapshot error",
      }));
    } finally {
      inFlight.current = false;
    }
  }

  useEffect(() => {
    loadOnce();
    const id = setInterval(loadOnce, POLL_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plantId]);

  const map = useMemo(() => {
    const m = new Map<string, Item>();
    for (const it of state.items) m.set(it.name, it);
    return m;
  }, [state.items]);

  return { ...state, map, reload: loadOnce };
}
