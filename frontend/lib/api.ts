// lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export function getApiBase() {
  return API_BASE.replace(/\/$/, "");
}

export async function fetchJson<T>(
  path: string,
  opts?: {
    plantId?: string;
    timeoutMs?: number;
    method?: "GET" | "POST";
    body?: unknown;
  }
): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith("http") ? path : `${base}${path.startsWith("/") ? "" : "/"}${path}`;

  const controller = new AbortController();
  const timeoutMs = opts?.timeoutMs ?? 8000;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      method: opts?.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(opts?.plantId ? { "X-Plant-ID": opts.plantId } : {}),
      },
      body: opts?.body ? JSON.stringify(opts.body) : undefined,
      signal: controller.signal,
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${res.statusText} ${text}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export async function pingHealth(plantId?: string) {
  // สมมติ backend มี /health
  return fetchJson<{ ok: boolean }>("/health", { plantId, timeoutMs: 3000 });
}
