"use client";

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { AgCharts } from "ag-charts-react";
import { ModuleRegistry, AllCommunityModule } from "ag-charts-community";
import type { AgChartOptions } from "ag-charts-community";

ModuleRegistry.registerModules([AllCommunityModule]);

/** =========================
 * CONFIG
 * ========================= */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const HEALTH_URL = `${API_BASE}/health`;

// เงื่อนไข "เครื่องทำงาน" (Power kW > threshold)
const RUN_THRESHOLD_KW = 10;

/**
 * CHARTS
 * - endpoint: history ของกราฟ
 * - limitEndpoint: limit ของกราฟนั้น ๆ (มีเฉพาะบางกราฟ)
 */
const CHARTS = {
  chiller_pw: {
    label: "Chiller Power (kW)",
    endpoint: "/api/chiller_pw_history",
    limitEndpoint: "/api/limit_chiller_power_input",
    snapshotGroup: "chiller_power",
  },
  pump_pw: {
    label: "Pump Power (kW)",
    endpoint: "/api/pump_pw_history",
    limitEndpoint: undefined,
    snapshotGroup: "pump_power",
  },
  pump_flow: {
    label: "Pump Flow",
    endpoint: "/api/pump_flow_history",
    limitEndpoint: undefined,
    snapshotGroup: "flow",
  },
  chiller_temp: {
    label: "Chiller Temp",
    endpoint: "/api/chiller_temp_history",
    limitEndpoint: undefined,
    snapshotGroup: "chiller_temp",
  },
  thermoform_power: {
    label: "Thermoform Power (kW)",
    endpoint: "/api/thermoform_power_history",
    limitEndpoint: undefined,
    snapshotGroup: "thermoform_power",
  },
} as const;

type ChartKey = keyof typeof CHARTS;
type ApiStatus = "online" | "offline";
type TwoStatus = "online" | "offline";

type Item = {
  id: string;
  label: string;
  unit?: string;
  value: number | null;
  online: boolean;
};
type OneShotOk = {
  ok: true;
  ts: string;
  items: Item[];
  total?: number;
};

type SuggestionRes = {
  ok: true;
  status: string;
  suggest: string;
  reason: string;
};

type CostRes = {
  ok: true;
  summary: { total_kwh: number; total_thb: number };
};

type Limits = { low?: number; high?: number };
type LimitsRes = { ok: true; limits: { low: number; high: number } };

/** =========================
 * SPEED CACHE
 * ========================= */
const HEALTH_TTL_MS = 5_000;
const CACHE_TTL_CHART_MS = 60_000; // cache chart 60s
const CACHE_TTL_LIMIT_MS = 10 * 60_000; // cache limit 10 นาที

function cacheKeyChart(chartKey: ChartKey, chartUrl: string) {
  return `dash_cache_chart::${chartKey}::${chartUrl}`;
}
function cacheKeyLimit(chartKey: ChartKey) {
  return `dash_cache_limit::${chartKey}`;
}
function readCache<T>(key: string, ttlMs: number): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const obj = JSON.parse(raw) as { ts: number; value: T };
    if (!obj?.ts) return null;
    if (Date.now() - obj.ts > ttlMs) return null;
    return obj.value;
  } catch {
    return null;
  }
}
function writeCache<T>(key: string, value: T) {
  try {
    sessionStorage.setItem(key, JSON.stringify({ ts: Date.now(), value }));
  } catch {
    // ignore
  }
}

/** =========================
 * HELPERS
 * ========================= */
function fmt(n: number | null, digits = 2) {
  if (n === null || n === undefined) return "-";
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(digits);
}

function monthRangeISO() {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
  return { fromIso: from.toISOString(), toIso: now.toISOString() };
}

async function fetchJson<T>(url: string, plantId: string, timeoutMs = 15000): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: ctrl.signal,
      cache: "no-store",
      headers: { "X-Plant-ID": plantId },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(t);
  }
}


const sanitizeKey = (k: string) => k.replace(/[^a-zA-Z0-9_]/g, "_");

function runStatus(item: Item | undefined, threshold = RUN_THRESHOLD_KW): TwoStatus {
  if (!item) return "offline";
  const v = Number(item.value ?? 0);
  return item.online && Number.isFinite(v) && v > threshold ? "online" : "offline";
}
function onlineStatus(item: Item | undefined): TwoStatus {
  if (!item) return "offline";
  return item.online ? "online" : "offline";
}

/** =========================
 * UI COMPONENTS
 * ========================= */
const SectionHeader = ({ title }: { title: string }) => (
  <div
    style={{
      color: "#888",
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: 1,
      marginTop: 20,
      marginBottom: 10,
      borderBottom: "1px solid #222",
      paddingBottom: 6,
    }}
  >
    {title}
  </div>
);

const inputStyle: React.CSSProperties = {
  background: "#222",
  border: "1px solid #444",
  color: "white",
  padding: "5px 10px",
  borderRadius: 4,
};

const StatusDot = ({
  status,
  label,
  value,
  unit,
}: {
  status: TwoStatus;
  label: string;
  value: number | null;
  unit?: string;
}) => {
  const color = status === "online" ? "#22c55e" : "#ef4444";
  const glow = status === "online" ? "0 0 8px #22c55e" : "none";
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, boxShadow: glow }} />
        <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 12 }}>{label}</div>
      </div>
      <div style={{ color: "white", fontWeight: "bold", fontSize: 14 }}>
        {fmt(value)} <span style={{ fontSize: 10, fontWeight: "normal" }}>{unit}</span>
      </div>
    </div>
  );
};

const MachineBox = ({
  label,
  status,
  subLabel,
}: {
  label: string;
  status: TwoStatus;
  subLabel?: string;
}) => {
  const bg = status === "online" ? "#15803d" : "#991b1b";
  const border = status === "online" ? "#4ade80" : "#f87171";
  const shadow = status === "online" ? "0 0 15px rgba(74, 222, 128, 0.4)" : "none";
  return (
    <div
      style={{
        background: bg,
        border: `2px solid ${border}`,
        borderRadius: 12,
        padding: "10px 15px",
        minWidth: 80,
        textAlign: "center",
        color: "white",
        fontWeight: "bold",
        boxShadow: shadow,
      }}
    >
      <div style={{ fontSize: 14 }}>{label}</div>
      {subLabel && <div style={{ fontSize: 10, opacity: 0.85 }}>{subLabel}</div>}
    </div>
  );
};

/** =========================
 * MAIN PAGE
 * ========================= */
export default function DashboardPage() {
  const PLANTS = useMemo(() => ["P2", "P1"], []);
  const [plantId, setPlantId] = useState<string>(PLANTS[0] ?? "P2");

  const [apiStatus, setApiStatus] = useState<ApiStatus>("offline");
  const [apiErrMsg, setApiErrMsg] = useState("FastAPI not connected");

  const [snapshots, setSnapshots] = useState<Record<string, OneShotOk | null>>({
    chiller_power: null,
    pump_power: null,
    tank_temp: null,
    flow: null,
    chiller_temp: null,
    thermoform_power: null,
  });

  // limit แยกตามกราฟ
  const [chartLimitsMap, setChartLimitsMap] = useState<Record<string, Limits>>({});

  const [suggestion, setSuggestion] = useState<SuggestionRes | null>(null);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);

  const [cost, setCost] = useState<CostRes | null>(null);
  const [costLoading, setCostLoading] = useState(false);
  const [costError, setCostError] = useState<string | null>(null);

  const [chartKey, setChartKey] = useState<ChartKey>("chiller_pw"); /**default show */
  const [chartRange, setChartRange] = useState("24h");
  const [chartData, setChartData] = useState<any[]>([]);
  const [chartSeries, setChartSeries] = useState<any[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);

  // กัน request ซ้อนกัน
  const liveInFlight = useRef(false);
  const chartInFlight = useRef(false);

  // ลด request health
  const healthCacheRef = useRef<{ ts: number; ok: boolean }>({ ts: 0, ok: false });

  const ONE_SHOT_GROUPS = useMemo(
    () => [
      { key: "chiller_power", endpoint: "/api/chill_pw", kind: "power" as const },
      { key: "pump_power", endpoint: "/api/pump_pw", kind: "power" as const },
      { key: "tank_temp", endpoint: "/api/chiller_tank_temp", kind: "online" as const },
      { key: "flow", endpoint: "/api/pump_flow", kind: "online" as const },
      { key: "chiller_temp", endpoint: "/api/chiller_temp", kind: "online" as const },
      { key: "thermoform_power", endpoint: "/api/thermoform_power", kind: "power" as const },
    ],
    []
  );

  const chartUrl = useMemo(() => {
    let startStr = "-24h";
    if (chartRange === "1h") startStr = "-1h";
    if (chartRange === "6h") startStr = "-6h";
    return `${API_BASE}${CHARTS[chartKey].endpoint}?start=${encodeURIComponent(startStr)}&every=10m`;
  }, [chartKey, chartRange]);

  const banner =
    apiStatus === "online"
      ? { text: "ONLINE", sub: "FastAPI connected", color: "#22c55e" }
      : { text: "OFFLINE", sub: apiErrMsg, color: "#ef4444" };

  /** =========================
   * HEALTH (cached)
   * ========================= */
  const pingHealth = useCallback(async () => {
    const now = Date.now();
    if (now - healthCacheRef.current.ts < HEALTH_TTL_MS) {
      return healthCacheRef.current.ok;
    }

    try {
      const res = await fetchJson<{ ok: boolean }>(HEALTH_URL, plantId, 2000);
      const ok = !!res?.ok;
      healthCacheRef.current = { ts: now, ok };
      if (!ok) throw new Error("health not ok");
      return true;
    } catch (e: any) {
      healthCacheRef.current = { ts: now, ok: false };
      setApiErrMsg(e?.name === "AbortError" ? "FastAPI timeout" : "FastAPI not connected");
      return false;
    }
  }, [plantId]);

  /** =========================
   * SNAPSHOT HELPERS
   * ========================= */
  const itemsMap = useMemo(() => {
    const out: Record<string, Record<string, Item>> = {};
    for (const g of Object.keys(snapshots)) {
      const items = snapshots[g]?.items ?? [];
      out[g] = {};
      for (const it of items) out[g][it.id] = it;
    }
    return out;
  }, [snapshots]);

  const groupItems = useCallback(
    (groupKey: string) => {
      return snapshots[groupKey]?.items ?? [];
    },
    [snapshots]
  );

  /** =========================
   * FETCH: SNAPSHOTS
   * ========================= */
  const fetchOneShot = useCallback(async () => {
    if (liveInFlight.current) return;
    liveInFlight.current = true;

    try {
      const ok = await pingHealth();
      if (!ok) {
        setApiStatus("offline");
        setSnapshots((prev) => {
          const cleared: any = { ...prev };
          for (const k of Object.keys(cleared)) cleared[k] = null;
          return cleared;
        });
        return;
      }
      setApiStatus("online");

      const settled = await Promise.allSettled(
        ONE_SHOT_GROUPS.map(async (g) => {
          const res = await fetchJson<OneShotOk>(`${API_BASE}${g.endpoint}`, plantId, 15000);
          return { key: g.key, res };
        })
      );

      setSnapshots((prev) => {
        const next: Record<string, OneShotOk | null> = { ...prev };

        for (const s of settled) {
          if (s.status === "fulfilled" && s.value?.res?.ok) {
            next[s.value.key] = s.value.res;
          }
        }
        return next;
      });

    } catch {
      setApiStatus("offline");
      setSnapshots((prev) => {
        const cleared: any = { ...prev };
        for (const k of Object.keys(cleared)) cleared[k] = null;
        return cleared;
      });
    } finally {
      liveInFlight.current = false;
    }
  }, [ONE_SHOT_GROUPS, pingHealth, plantId]);

  /** =========================
   * FETCH: LIMIT PER CHART (cached)
   * ========================= */
  const fetchLimitsForChart = useCallback(
    async (ck: ChartKey): Promise<Limits> => {
      const limitEp = CHARTS[ck]?.limitEndpoint;
      if (!limitEp) return {};

      // 1) session cache
      const cached = readCache<Limits>(cacheKeyLimit(ck), CACHE_TTL_LIMIT_MS);
      if (cached && (cached.low !== undefined || cached.high !== undefined)) {
        setChartLimitsMap((prev) => ({ ...prev, [ck]: cached }));
        return cached;
      }

      const existing = chartLimitsMap[ck];
      if (existing && (existing.low !== undefined || existing.high !== undefined)) {
        return existing;
      }

      // 3) fetch from API
      try {
        const ok = await pingHealth();
        if (!ok) throw new Error("FastAPI offline");
        setApiStatus("online");

        const res = await fetchJson<LimitsRes>(`${API_BASE}${limitEp}`, plantId, 4000);
        const limits: Limits = { low: res?.limits?.low, high: res?.limits?.high };

        setChartLimitsMap((prev) => ({ ...prev, [ck]: limits }));
        writeCache(cacheKeyLimit(ck), limits);
        return limits;
      } catch {
        return {};
      }
    },
    [chartLimitsMap, pingHealth, plantId]
  );

  /** =========================
   * FETCH: SUGGESTION
   * ========================= */
  const fetchSuggestion = useCallback(async () => {
    setSuggestionLoading(true);
    setSuggestionError(null);
    try {
      const ok = await pingHealth();
      if (!ok) throw new Error("FastAPI offline");
      setApiStatus("online");
      const data = await fetchJson<SuggestionRes>(`${API_BASE}/api/recommend`, plantId, 8000);
      setSuggestion(data);
    } catch (e: any) {
      setSuggestion(null);
      setSuggestionError(e?.message ?? "failed");
    } finally {
      setSuggestionLoading(false);
    }
  }, [pingHealth, plantId]);

  /** =========================
   * FETCH: COST
   * ========================= */
  const fetchCost = useCallback(async () => {
    setCostLoading(true);
    setCostError(null);
    try {
      const ok = await pingHealth();
      if (!ok) throw new Error("FastAPI offline");
      setApiStatus("online");

      const { fromIso, toIso } = monthRangeISO();
      const url = `${API_BASE}/api/pump_power_cost_history?from=${encodeURIComponent(fromIso)}&to=${encodeURIComponent(
        toIso
      )}&every=1h`;

      const data = await fetchJson<CostRes>(url, plantId, 6000);
      setCost(data);
    } catch (e: any) {
      setCost(null);
      setCostError(e?.message ?? "failed");
    } finally {
      setCostLoading(false);
    }
  }, [pingHealth, plantId]);

  /** =========================
   * FETCH: CHART (series + per-chart limit)
   * ========================= */
  const fetchChart = useCallback(async () => {
    if (chartInFlight.current) return;
    chartInFlight.current = true;

    setChartLoading(true);
    setChartError(null);

    const LIMIT_LOW_COLOR  = "#ff4040"; 
    const LIMIT_HIGH_COLOR = "#ff4040"; 
     
    const cachedChart = readCache<{ data: any[]; series: any[] }>(
      cacheKeyChart(chartKey, chartUrl),
      CACHE_TTL_CHART_MS
    );
    if (cachedChart?.data?.length && cachedChart?.series?.length) {
      const rehydrated = cachedChart.data.map((r) => ({
        ...r,
        ts: new Date(r.ts), // << สำคัญ
      }));
      setChartData(rehydrated);
      setChartSeries(cachedChart.series);
    }

    try {
      const ok = await pingHealth();
      if (!ok) throw new Error("FastAPI offline");
      setApiStatus("online");

      const hasLimit = !!CHARTS[chartKey].limitEndpoint;

      const [json, limits] = await Promise.all([
        fetchJson<any>(chartUrl, plantId, 8000),
        hasLimit ? fetchLimitsForChart(chartKey) : Promise.resolve<Limits>({}),
      ]);

      const seriesArr = Array.isArray(json?.series) ? json.series : [];
      if (!json?.ok || seriesArr.length === 0) {
        setChartData([]);
        setChartSeries([]);
        setChartError("No data");
        return;
      }

      const data = seriesArr
        .map((d: any) => ({ ...d, ts: new Date(d.ts) }))
        .sort((a: any, b: any) => +a.ts - +b.ts);

      // Keys ที่ "ต้องการ" = จาก snapshot group (ถ้ามี) เพื่อให้ล็อคตาม backend
      const snapGroupKey = CHARTS[chartKey].snapshotGroup;
      const preferredKeys = (snapshots[snapGroupKey]?.items ?? []).map((it) => it.id);
      const rawKeysFromData = Object.keys(data[0] || {}).filter((k) => k !== "ts");

      const keys = (preferredKeys.length ? preferredKeys : rawKeysFromData).filter(
        (k) => k !== "ts" && (preferredKeys.length ? true : data.some((r: any) => r[k] !== null && r[k] !== undefined))
      );

      if (keys.length === 0) {
        setChartData([]);
        setChartSeries([]);
        setChartError("No series");
        return;
      }

      const keyMap: Record<string, string> = {};
      keys.forEach((k) => (keyMap[k] = sanitizeKey(k)));

      const low = hasLimit ? Number(limits.low) : NaN;
      const high = hasLimit ? Number(limits.high) : NaN;

      const safeData = data.map((row: any) => {
        const out: any = { ts: row.ts };
        keys.forEach((k) => {
          out[keyMap[k]] = row[k] ?? null; // กัน missing key
        });

        if (hasLimit && Number.isFinite(low)) out.limit_low = low;
        if (hasLimit && Number.isFinite(high)) out.limit_high = high;
        return out;
      });

      // map ชื่อใน legend: ใช้ label จาก snapshot ถ้ามี
      const idToLabel = (snapshots[snapGroupKey]?.items ?? []).reduce<Record<string, string>>((acc, it) => {
        acc[it.id] = it.label;
        return acc;
      }, {});

      const baseSeries = keys.map((k) => ({
        type: "line",
        xKey: "ts",
        yKey: keyMap[k],
        yName: idToLabel[k] ? `${idToLabel[k]} (${k})` : k,
        strokeWidth: 2,
        marker: { enabled: false },
      }));

      const limitSeries: any[] = [];
      if (hasLimit && Number.isFinite(low)) {
        limitSeries.push({
          type: "line",
          xKey: "ts",
          yKey: "limit_low",
          yName: "Limit Low",
          stroke: LIMIT_LOW_COLOR,
          strokeWidth: 2,
          marker: { enabled: false },
          lineDash: [6, 6],
        });
      }
      if (hasLimit && Number.isFinite(high)) {
        limitSeries.push({
          type: "line",
          xKey: "ts",
          yKey: "limit_high",
          yName: "Limit High",
          stroke: LIMIT_HIGH_COLOR,
          strokeWidth: 2,
          marker: { enabled: false },
          lineDash: [6, 6],
        });
      }

      const finalSeries = [...baseSeries, ...limitSeries];

      setChartData(safeData);
      setChartSeries(finalSeries);

      writeCache(cacheKeyChart(chartKey, chartUrl), { data: safeData, series: finalSeries });
    } catch (e: any) {
      setChartData([]);
      setChartSeries([]);
      setChartError(e?.message ?? "failed");
      setApiStatus("offline");
    } finally {
      setChartLoading(false);
      chartInFlight.current = false;
    }
  }, [chartKey, chartUrl, fetchLimitsForChart, pingHealth, plantId, snapshots]);

  const chartOptions = useMemo<AgChartOptions>(
    () => ({
      theme: "ag-default-dark" as any,
      background: { fill: "transparent" },
      data: chartData as any,
      series: chartSeries as any,
      axes: [
        {
          type: "time",
          position: "bottom",
          label: {
            rotation: -25,
            formatter: (p: any) => {
              const d = new Date(p.value);
              return new Intl.DateTimeFormat("th-TH", {
                timeZone: "Asia/Bangkok",
                hour: "2-digit",
                minute: "2-digit",
                day: "2-digit",
                month: "2-digit",
              }).format(d);
            },
          },
        } as any,
        { type: "number", position: "left" } as any,
      ],
      legend: { position: "bottom" } as any,
    }),
    [chartData, chartSeries, chartRange]
  );

  /** =========================
   * EFFECTS
   * ========================= */

  useEffect(() => {
    fetchChart();
  }, [chartUrl]);

 useEffect(() => {
    healthCacheRef.current = { ts: 0, ok: false };

    (async () => {
      await fetchOneShot();
      fetchCost();
      fetchChart();
      fetchSuggestion();
    })();
    
    const interval = setInterval(fetchOneShot, 10_000);
    return () => clearInterval(interval);

  }, [plantId]);

  /** =========================
   * RENDER
   * ========================= */
  const chillerPower = groupItems("chiller_power");
  const pumpPower = groupItems("pump_power");
  const tankTemp = groupItems("tank_temp");
  const flow = groupItems("flow");

  const thermoform = groupItems("thermoform_power");

  const renderMachineColumn = (slots: string[], items: Item[], prefixKey: string) => {
    return slots.map((slot, idx) => {
      const it = items[idx];
      if (it) {
        return <MachineBox key={it.id} label={it.id} subLabel={it.label} status={runStatus(it)} />;
      }
      // placeholder ตอนไม่มี data -> สีแดง (offline)
      return <MachineBox key={`${prefixKey}-${slot}`} label={slot} subLabel="No data" status="offline" />;
    });
  };


  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#000",
        color: "white",
        fontFamily: "Inter, sans-serif",
        padding: 20,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr 280px",
          gap: 20,
          width: "100%",
          maxWidth: 1600,
          height: "calc(100vh - 40px)",
        }}
      >
        {/* LEFT PANEL */}
        <div
          style={{
            border: "1px solid #333",
            borderRadius: 4,
            padding: 20,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <h2 style={{ textAlign: "center", borderBottom: "1px solid #333", paddingBottom: 10, marginBottom: 20 }}>
            Plant Status
          </h2>

          {/* Plant selector */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: "#888" }}>Plant</div>
            <select value={plantId} onChange={(e) => setPlantId(e.target.value)} style={inputStyle}>
              {PLANTS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          <div style={{ textAlign: "center", marginBottom: 22 }}>
            <div style={{ color: banner.color, fontSize: 24, fontWeight: "bold" }}>{banner.text}</div>
            <div style={{ fontSize: 12, color: "#666" }}>{banner.sub}</div>
          </div>

          <SectionHeader title="Chiller Power" />
          {chillerPower.length ? (
            chillerPower.map((it) => (
              <StatusDot key={it.id} label={it.label} value={it.value} unit={it.unit ?? "kW"} status={runStatus(it)} />
            ))
          ) : (
            <div style={{ fontSize: 12, color: "#666" }}>No data</div>
          )}

          <SectionHeader title="Pump Power" />
          {pumpPower.length ? (
            pumpPower.map((it) => (
              <StatusDot key={it.id} label={it.label} value={it.value} unit={it.unit ?? "kW"} status={runStatus(it)} />
            ))
          ) : (
            <div style={{ fontSize: 12, color: "#666" }}>No data</div>
          )}

          <SectionHeader title="Temperature" />
          {tankTemp.length ? (
            tankTemp.map((it) => (
              <StatusDot key={it.id} label={it.label} value={it.value} unit={it.unit ?? "°C"} status={onlineStatus(it)} />
            ))
          ) : (
            <div style={{ fontSize: 12, color: "#666" }}>No data</div>
          )}

          <SectionHeader title="Flow" />
          {flow.length ? (
            flow.map((it) => (
              <StatusDot key={it.id} label={it.label} value={it.value} unit={it.unit ?? "m³/h"} status={onlineStatus(it)} />
            ))
          ) : (
            <div style={{ fontSize: 12, color: "#666" }}>No data</div>
          )}
        </div>

        {/* CENTER PANEL */}
        <div style={{ display: "grid", gridTemplateRows: "auto 1fr", gap: 20 }}>
          {/* Diagram */}
          <div
            style={{
              border: "1px solid #333",
              borderRadius: 8,
              padding: 20,
              position: "relative",
              background: "#0a0a0a",
              overflow: "hidden",
              height: 320,
            }}
          >
            <h2 style={{ textAlign: "center", marginBottom: 18 }}>Chiller Plant Diagram</h2>

            {/* === SVG PIPE + ARROWS (BACKGROUND) === */}
            <svg
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                width: "100%",
                height: "100%",
                pointerEvents: "none",
                zIndex: 1,
                opacity: 0.95,
              }}
              viewBox="0 0 1200 320"
              preserveAspectRatio="none"
            >
              <defs>
                <marker id="arrow" markerUnits="strokeWidth" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 Z" fill="rgba(255,255,255,0.95)" />
                </marker>
              </defs>

              {/* (คง SVG เดิมไว้) */}
              <path d="M300 190 V150  H260" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />
              <path d="M300 190 V227  H260" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />

              <path d="M300 190 H460" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <circle cx="300" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />
              <path d="M460 190 V115 H540" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <path d="M460 190       H540" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <path d="M460 190 V263 H540" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <circle cx="460" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />
              
              <path d="M760 190 V115 H660" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M760 190       H660" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M760 190 V263 H660" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />

              <path d="M560 190 H760" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M760 190 H870" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <circle cx="760" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />
              <path d="M870 190 V115 H935" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <path d="M870 190       H935" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <path d="M870 190 V263 H935" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <circle cx="870" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />
              <path d="M1100 190 V115 H1030" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M1100 190       H1030" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M1100 190 V263 H1030" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M1150 190 H1100" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <circle cx="1100" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />
              <path d="M1150 190 V70" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M60 70 H1150" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M60 190 V70" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M60 190 H100" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M100 190 V150  H165" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <path d="M100 190 V227  H165" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <circle cx="100" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />
            </svg>

            {/* === CONTENT (FOREGROUND) === */}
            <div
              style={{
                position: "relative",
                zIndex: 2,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-around",
                height: 240,
                paddingTop: 10,
              }}
            >
              {/* CH */}
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                {renderMachineColumn(["CH1", "CH2"], chillerPower.slice(0, 2), "ch")}
              </div>

              {/* TF */}
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {renderMachineColumn(["TF1", "TF2", "TF3"], thermoform.slice(0, 3), "tf")}
              </div>

              {/* PUMP */}
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {renderMachineColumn(["P1", "P2", "P3"], pumpPower.slice(0, 3), "pump")}
              </div>

            </div>

            <div
              style={{
                position: "absolute",
                bottom: 18,
                left: 40,
                right: 40,
                height: 10,
                border: "1px dashed #444",
                borderTop: "none",
                borderRadius: "0 0 20px 20px",
                zIndex: 0,
              }}
            />
          </div>

          {/* Chart */}
          <div style={{ border: "1px solid #333", borderRadius: 4, padding: 10, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", gap: 15, padding: 10, borderBottom: "1px solid #222", alignItems: "center" }}>
              <div>
                <span style={{ fontSize: 12, color: "#888", marginRight: 5 }}>Chart Group:</span>
                <select value={chartKey} onChange={(e) => setChartKey(e.target.value as ChartKey)} style={inputStyle}>
                  {Object.entries(CHARTS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <span style={{ fontSize: 12, color: "#888", marginRight: 5 }}>Range:</span>
                <select value={chartRange} onChange={(e) => setChartRange(e.target.value)} style={inputStyle}>
                  <option value="1h">1 Hour</option>
                  <option value="6h">6 Hours</option>
                  <option value="24h">24 Hours</option>
                </select>
              </div>

              <button
                onClick={fetchChart}
                style={{ ...inputStyle, cursor: "pointer", background: "#111", borderColor: "#555" }}
                disabled={chartLoading}
              >
                {chartLoading ? "Loading..." : "Refresh"}
              </button>

              <div style={{ marginLeft: "auto", fontSize: 12, color: "#777" }}>
                {chartError ? `Status: ${chartError}` : `Series: ${chartSeries.length}`}
              </div>
            </div>

            <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
              {apiStatus === "offline" ? (
                <div style={{ padding: 18, color: "#888" }}>Chart unavailable: FastAPI offline</div>
              ) : chartError && chartData.length === 0 ? (
                <div style={{ padding: 18, color: "#888" }}>
                  {chartError === "No data" ? "No data to display" : `Chart error: ${chartError}`}
                </div>
              ) : (
                <AgCharts options={chartOptions} />
              )}
            </div>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div style={{ border: "1px solid #333", borderRadius: 4, padding: 20 }}>
          <h2 style={{ textAlign: "center", marginBottom: 30 }}>Cost & Suggestion</h2>

          {/* Cost */}
          <div style={{ background: "#111", borderRadius: 12, padding: 20, marginBottom: 30, border: "1px solid #333" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: 14, color: "#aaa", marginBottom: 5 }}>This Month Energy</div>
              <button onClick={fetchCost} style={{ ...inputStyle, cursor: "pointer", background: "#0f0f0f" }} disabled={costLoading}>
                {costLoading ? "..." : "↻"}
              </button>
            </div>

            <div style={{ fontSize: 28, fontWeight: "bold", color: "white" }}>
              {cost ? fmt(cost.summary.total_kwh, 0) : "-"} <span style={{ fontSize: 14 }}>kWh</span>
            </div>

            <div style={{ height: 1, background: "#333", margin: "15px 0" }} />

            <div style={{ fontSize: 14, color: "#aaa", marginBottom: 5 }}>This Month Cost</div>
            <div style={{ fontSize: 28, fontWeight: "bold", color: "#fbbf24" }}>
              {cost ? fmt(cost.summary.total_thb, 0) : "-"} <span style={{ fontSize: 14 }}>THB</span>
            </div>

            {costError && <div style={{ marginTop: 10, fontSize: 12, color: "#888" }}>Cost error: {costError}</div>}
            {apiStatus === "offline" && <div style={{ marginTop: 10, fontSize: 12, color: "#888" }}>FastAPI offline</div>}
          </div>

          {/* Suggestion */}
          <div style={{ marginTop: 40 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h4 style={{ color: "#aaa", marginBottom: 15 }}>Recommendation</h4>
              <button
                onClick={fetchSuggestion}
                style={{ ...inputStyle, cursor: "pointer", background: "#0f0f0f" }}
                disabled={suggestionLoading}
              >
                {suggestionLoading ? "..." : "↻"}
              </button>
            </div>

            {apiStatus === "offline" ? (
              <div style={{ fontStyle: "italic", color: "#666" }}>FastAPI offline</div>
            ) : suggestionError ? (
              <div style={{ fontStyle: "italic", color: "#666" }}>Suggestion error: {suggestionError}</div>
            ) : suggestion ? (
              <div style={{ borderLeft: "4px solid #3b82f6", background: "rgba(59, 130, 246, 0.1)", padding: 15, borderRadius: "0 8px 8px 0" }}>
                <div style={{ fontSize: 12, color: "#888" }}>Status: {suggestion.status}</div>
                <div style={{ fontSize: 16, fontWeight: "bold", margin: "5px 0", color: "#fff" }}>
                  {suggestion.suggest === "-" ? "No Action Needed" : suggestion.suggest}
                </div>
                <div style={{ fontSize: 12, color: "#ccc" }}>Reason: {suggestion.reason}</div>
              </div>
            ) : (
              <div style={{ fontStyle: "italic", color: "#666" }}>No suggestion</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
