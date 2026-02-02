// hooks/useHealth.ts
"use client";

import { useEffect, useState } from "react";
import { pingHealth } from "@/lib/api";
import { readCache, writeCache } from "@/lib/cache";

const HEALTH_TTL = 5000; // 5s

export function useHealth(plantId: string) {
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    let alive = true;

    async function run() {
      const cached = readCache<boolean>(`health:${plantId}`);
      if (cached !== null) setOk(cached);

      try {
        const res = await pingHealth(plantId);
        if (!alive) return;
        setOk(!!res.ok);
        writeCache(`health:${plantId}`, !!res.ok, HEALTH_TTL);
      } catch {
        if (!alive) return;
        setOk(false);
        writeCache(`health:${plantId}`, false, HEALTH_TTL);
      }
    }

    run();
    const id = setInterval(run, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [plantId]);

  return { ok };
}
