// lib/cache.ts

type CacheEntry<T> = {
  t: number;      // saved time (ms)
  ttl: number;    // ttl (ms)
  v: T;           // value
};

const PREFIX = "rmc_cache:";

export function readCache<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(PREFIX + key);
    if (!raw) return null;

    const entry = JSON.parse(raw) as CacheEntry<T>;
    const age = Date.now() - entry.t;

    if (age > entry.ttl) {
      sessionStorage.removeItem(PREFIX + key);
      return null;
    }
    return entry.v;
  } catch {
    return null;
  }
}

export function writeCache<T>(key: string, value: T, ttlMs: number) {
  if (typeof window === "undefined") return;
  try {
    const entry: CacheEntry<T> = { t: Date.now(), ttl: ttlMs, v: value };
    sessionStorage.setItem(PREFIX + key, JSON.stringify(entry));
  } catch {
    // ignore (quota/blocked)
  }
}
