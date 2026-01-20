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

// Sticky สำหรับ "Online (มีข้อมูล/ต่ออยู่)" เท่านั้น
const ONLINE_STICKY_TTL_MS = 30_000;
const RUN_STICKY_TTL_MS = 10_000;

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
    limitEndpoint: "/api/limit_chiller_power_input", //  ของจริงที่คุณใช้

  },
  pump_pw: {
    label: "Pump Power (kW)",
    endpoint: "/api/pump_pw_history",
    limitEndpoint: undefined
    // ไม่มี limitEndpoint = จะไม่ดึง limit
  },
  pump_flow: {
    label: "Pump Flow",
    endpoint: "/api/pump_flow_history",
    limitEndpoint: undefined
  },
  chiller_temp: {
    label: "Chiller Temp",
    endpoint: "/api/chiller_temp_history",
    limitEndpoint: undefined
  },
  thermoform_power: {
    label: "Thermoform Power (kW)",
    endpoint: "/api/thermoform_power_history",
    limitEndpoint: undefined
  },
} as const;

type ChartKey = keyof typeof CHARTS;
type ApiStatus = "online" | "offline";
type TwoStatus = "online" | "offline";

type OneShotOk = {
  ok: true;
  ts: string;
  param: Record<string, { online: boolean; data: number }>;
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
 * SPEED CACHE (ทำให้ reload/refresh เร็วขึ้น)
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

async function fetchJson<T>(url: string, timeoutMs = 2500): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: ctrl.signal, cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(t);
  }
}

const sanitizeKey = (k: string) => k.replace(/[^a-zA-Z0-9_]/g, "_");

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

const ArrowRight = () => <div style={{ color: "#555", fontSize: 20 }}>➔</div>;

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
  const [apiStatus, setApiStatus] = useState<ApiStatus>("offline");
  const [apiErrMsg, setApiErrMsg] = useState("FastAPI not connected");

  const [liveData, setLiveData] = useState<Record<string, { online: boolean; data: number }>>({});

  // limit แยกตามกราฟ
  const [chartLimitsMap, setChartLimitsMap] = useState<Record<string, Limits>>({});

  const [suggestion, setSuggestion] = useState<SuggestionRes | null>(null);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);

  const [cost, setCost] = useState<CostRes | null>(null);
  const [costLoading, setCostLoading] = useState(false);
  const [costError, setCostError] = useState<string | null>(null);

  const [chartKey, setChartKey] = useState<ChartKey>("pump_pw");
  const [chartRange, setChartRange] = useState("24h");
  const [chartData, setChartData] = useState<any[]>([]);
  const [chartSeries, setChartSeries] = useState<any[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);

  // กัน request ซ้อนกัน
  const liveInFlight = useRef(false);
  const chartInFlight = useRef(false);

  // sticky status
  const lastSeenRef = useRef<Record<string, number>>({});
  const lastRunSeenRef = useRef<Record<string, number>>({});

  // ✅ health cache ลด request health
  const healthCacheRef = useRef<{ ts: number; ok: boolean }>({ ts: 0, ok: false });

  /** =========================
   * TAGS
   * ========================= */
  const TAGS = {
    CH1: "Winenergy.P2CH01.kW",
    CH2: "Winenergy.P2CH02.kW",
    P9: "Winenergy.P2CHP09.kW",
    P10: "Winenergy.P2CHP10.kW",
    P11: "Winenergy.P2CHP11.kW",
    TF4: "Modbus_TF4.18CT1.Main_Thermoform_kW_Cal",
    TF5: "Modbus_TF5.18CT1.Main_Thermoform_kW_Cal",
    TF7: "Modbus_TF7.18CT1.Main_Thermoform_kW_Cal",

    TEMP_RETURN: "Chiller.PLANT_Node2.CLG2_TEMP_CHWR",
    TEMP_SUPPLY: "Chiller.PLANT_Node2.CLG2_TEMP_CHWS",
    
    Flow: "Winenergy.P2CH01.Flow_Counter"
  };

  // tag ที่ถือว่า "running" = value > threshold
  const RUN_TAGS = useMemo(
    () => new Set<string>([TAGS.CH1, TAGS.CH2, TAGS.P9, TAGS.P10, TAGS.P11, TAGS.TF4, TAGS.TF5, TAGS.TF7]),
    []
  );

  const chartUrl = useMemo(() => {
    let startStr = "-24h";
    if (chartRange === "1h") startStr = "-1h";
    if (chartRange === "6h") startStr = "-6h";
    return `${API_BASE}${CHARTS[chartKey].endpoint}?start=${encodeURIComponent(startStr)}&every=10m`;
  }, [chartKey, chartRange]);

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
            rotation: -25,         //  กันตัวหนังสือชนกัน
            formatter: (p: any) => {
              const d = new Date(p.value);
              //  ถ้า range สั้น แสดงแค่เวลา
              if (chartRange === "1h" || chartRange === "6h") {
                return new Intl.DateTimeFormat("en-GB", {
                  hour: "2-digit",
                  minute: "2-digit",
                }).format(d);
              }
              //  24h ขึ้นไป แสดงวัน + เวลา
              return new Intl.DateTimeFormat("en-GB", {
                day: "2-digit",
                month: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
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
   * HEALTH (cached)
   * ========================= */
  const pingHealth = useCallback(async () => {
    const now = Date.now();
    if (now - healthCacheRef.current.ts < HEALTH_TTL_MS) {
      return healthCacheRef.current.ok;
    }

    try {
      const res = await fetchJson<{ ok: boolean }>(HEALTH_URL, 2000);
      const ok = !!res?.ok;
      healthCacheRef.current = { ts: now, ok };

      if (!ok) throw new Error("health not ok");
      return true;
    } catch (e: any) {
      healthCacheRef.current = { ts: now, ok: false };
      setApiErrMsg(e?.name === "AbortError" ? "FastAPI timeout" : "FastAPI not connected");
      return false;
    }
  }, []);

  /** =========================
   * STATUS LOGIC
   * ========================= */
  const getOnlineSt = (tag: string): TwoStatus => {
    if (apiStatus === "offline") return "offline";

    const item = liveData?.[tag];
    if (!item) {
      const last = lastSeenRef.current[tag];
      if (last && Date.now() - last < ONLINE_STICKY_TTL_MS) return "online";
      return "offline";
    }

    if (item.online || Number.isFinite(item.data)) {
      lastSeenRef.current[tag] = Date.now();
      return "online";
    }

    const last = lastSeenRef.current[tag];
    if (last && Date.now() - last < ONLINE_STICKY_TTL_MS) return "online";

    return "offline";
  };

  const getRunSt = (tag: string, min = RUN_THRESHOLD_KW): TwoStatus => {
    if (apiStatus === "offline") return "offline";

    const v = Number(liveData?.[tag]?.data);

    if (Number.isFinite(v) && v > min) {
      lastRunSeenRef.current[tag] = Date.now();
      return "online";
    }

    const last = lastRunSeenRef.current[tag];
    if (last && Date.now() - last < RUN_STICKY_TTL_MS) return "online";

    return "offline";
  };

  const getVal = (tag: string) => (tag in liveData ? liveData[tag]?.data ?? null : null);

  /** =========================
   * FETCH: LIVE DATA (NO LIMIT HERE!)
   * ========================= */
  const ONE_SHOT_GROUPS = useMemo(
    () => [
      { endpoint: "/api/chill_pw" },
      { endpoint: "/api/pump_pw" },
      { endpoint: "/api/pump_flow" },
      { endpoint: "/api/chiller_temp" },
      { endpoint: "/api/thermoform_power" },
      { endpoint: "/api/chiller_tank_temp" },
      { endpoint: "/api/pump_flow" }
    ],
    []
  );

  const fetchOneShot = useCallback(async () => {
    if (liveInFlight.current) return;
    liveInFlight.current = true;

    try {
      const ok = await pingHealth();
      if (!ok) {
        setApiStatus("offline");
        setLiveData({});
        return;
      }
      setApiStatus("online");

      const settled = await Promise.allSettled(
        ONE_SHOT_GROUPS.map((g) => fetchJson<OneShotOk>(`${API_BASE}${g.endpoint}`, 15000))
      );

      const combined: Record<string, { online: boolean; data: number }> = {};

      for (const s of settled) {
        if (s.status === "fulfilled" && s.value?.ok && s.value?.param) {
          Object.assign(combined, s.value.param);
        }
      }

      if (Object.keys(combined).length > 0) {
        setLiveData((prev) => ({ ...prev, ...combined }));
      }
    } catch {
      setApiStatus("offline");
      setLiveData({});
    } finally {
      liveInFlight.current = false;
    }
  }, [ONE_SHOT_GROUPS, pingHealth]);

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

      // 2) state cache
      const existing = chartLimitsMap[ck];
      if (existing && (existing.low !== undefined || existing.high !== undefined)) {
        return existing;
      }

      // 3) fetch from API
      try {
        const ok = await pingHealth();
        if (!ok) throw new Error("FastAPI offline");
        setApiStatus("online");

        const res = await fetchJson<LimitsRes>(`${API_BASE}${limitEp}`, 4000);

        const limits: Limits = {
          low: res?.limits?.low,
          high: res?.limits?.high,
        };

        setChartLimitsMap((prev) => ({ ...prev, [ck]: limits }));
        writeCache(cacheKeyLimit(ck), limits);

        return limits;
      } catch {
        return {};
      }
    },
    [chartLimitsMap, pingHealth]
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
      const data = await fetchJson<SuggestionRes>(`${API_BASE}/api/recommend`, 3000);
      setSuggestion(data);
    } catch (e: any) {
      setSuggestion(null);
      setSuggestionError(e?.message ?? "failed");
    } finally {
      setSuggestionLoading(false);
    }
  }, [pingHealth]);

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

      const data = await fetchJson<CostRes>(url, 4000);
      setCost(data);
    } catch (e: any) {
      setCost(null);
      setCostError(e?.message ?? "failed");
    } finally {
      setCostLoading(false);
    }
  }, [pingHealth]);

  /** =========================
   * FETCH: CHART (fast + per-chart limit)
   * ========================= */
  const fetchChart = useCallback(async () => {
    if (chartInFlight.current) return;
    chartInFlight.current = true;

    setChartLoading(true);
    setChartError(null);

    //  1) โชว์ cache ขึ้นก่อนให้เร็ว
    const cachedChart = readCache<{ data: any[]; series: any[] }>(cacheKeyChart(chartKey, chartUrl), CACHE_TTL_CHART_MS);
    if (cachedChart?.data?.length && cachedChart?.series?.length) {
      setChartData(cachedChart.data);
      setChartSeries(cachedChart.series);
    }

    try {
      const ok = await pingHealth();
      if (!ok) throw new Error("FastAPI offline");
      setApiStatus("online");

      const hasLimit = !!CHARTS[chartKey].limitEndpoint;

      // ✅ 2) ดึง history + limit แบบ parallel (limit เฉพาะกราฟที่มี)
      const [json, limits] = await Promise.all([
        fetchJson<any>(chartUrl, 6000),
        hasLimit ? fetchLimitsForChart(chartKey) : Promise.resolve<Limits>({}),
      ]);

      const history = Array.isArray(json?.history) ? json.history : [];
      if (!json?.ok || history.length === 0) {
        setChartData([]);
        setChartSeries([]);
        setChartError("No data");
        return;
      }

      const data = history
        .map((d: any) => ({ ...d, ts: new Date(d.ts) }))
        .sort((a: any, b: any) => +a.ts - +b.ts);

      const rawKeys = Object.keys(data[0] || {}).filter((k) => k !== "ts");
      const keys = rawKeys.filter((k) => data.some((r: any) => r[k] !== null && r[k] !== undefined));

      if (keys.length === 0) {
        setChartData([]);
        setChartSeries([]);
        setChartError("No series");
        return;
      }

      const keyMap: Record<string, string> = {};
      keys.forEach((k) => (keyMap[k] = sanitizeKey(k)));

      //  สำคัญ: ถ้าไม่ใช่กราฟที่มี limit ให้เป็น NaN
      const low = hasLimit ? Number(limits.low) : NaN;
      const high = hasLimit ? Number(limits.high) : NaN;

      const safeData = data.map((row: any) => {
        const out: any = { ts: row.ts };
        keys.forEach((k) => (out[keyMap[k]] = row[k]));

        //  limit ของกราฟตัวเองเท่านั้น
        if (hasLimit && Number.isFinite(low)) out.limit_low = low;
        if (hasLimit && Number.isFinite(high)) out.limit_high = high;

        return out;
      });

      const baseSeries = keys.map((k) => ({
        type: "line",
        xKey: "ts",
        yKey: keyMap[k],
        yName: k,
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
          stroke: "#ff5252",   
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
          stroke: "#fa6060", 
          strokeWidth: 2,
          marker: { enabled: false },
          lineDash: [6, 6],
        });
      }

      const finalSeries = [...baseSeries, ...limitSeries];

      setChartData(safeData);
      setChartSeries(finalSeries);

      // ✅ 3) เขียน cache ให้ reload ครั้งต่อไปเร็วมาก
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
  }, [chartKey, chartUrl, fetchLimitsForChart, pingHealth]);

  /** =========================
   * EFFECTS
   * ========================= */
  useEffect(() => {
    fetchOneShot();
    fetchSuggestion();
    fetchCost();
    fetchChart();

    const interval = setInterval(() => {
      fetchOneShot();
    }, 10_000);

    return () => clearInterval(interval);
  }, [fetchOneShot, fetchSuggestion, fetchCost, fetchChart]);

  useEffect(() => {
    fetchChart();
  }, [chartUrl, fetchChart]);

  const banner =
    apiStatus === "online"
      ? { text: "ONLINE", sub: "FastAPI connected", color: "#22c55e" }
      : { text: "OFFLINE", sub: apiErrMsg, color: "#ef4444" };

  /** =========================
   * RENDER
   * ========================= */
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

          <div style={{ textAlign: "center", marginBottom: 30 }}>
            <div style={{ color: banner.color, fontSize: 24, fontWeight: "bold" }}>{banner.text}</div>
            <div style={{ fontSize: 12, color: "#666" }}>{banner.sub}</div>
          </div>

          <SectionHeader title="Chiller Power" />
          <StatusDot label="P2CH01" value={getVal(TAGS.CH1)} status={getRunSt(TAGS.CH1)} unit="kW" />
          <StatusDot label="P2CH02" value={getVal(TAGS.CH2)} status={getRunSt(TAGS.CH2)} unit="kW" />

          <SectionHeader title="Pump Power" />
          <StatusDot label="P2CHP09" value={getVal(TAGS.P9)} status={getRunSt(TAGS.P9)} unit="kW" />
          <StatusDot label="P2CHP10" value={getVal(TAGS.P10)} status={getRunSt(TAGS.P10)} unit="kW" />
          <StatusDot label="P2CHP11" value={getVal(TAGS.P11)} status={getRunSt(TAGS.P11)} unit="kW" />

          <SectionHeader title="Temperature" />
          <StatusDot label="Return" value={getVal(TAGS.TEMP_RETURN)} status={getOnlineSt(TAGS.TEMP_RETURN)} unit="°C" />
          <StatusDot label="Supply" value={getVal(TAGS.TEMP_SUPPLY)} status={getOnlineSt(TAGS.TEMP_SUPPLY)} unit="°C" />

          <SectionHeader title="Flow" />
          <StatusDot label="Return" value={getVal(TAGS.Flow)} status={getOnlineSt(TAGS.Flow)} unit="m³/h" />
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
                <marker
                  id="arrow"
                  markerUnits="strokeWidth"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="4"
                  orient="auto"
                >
                  <path d="M0,0 L8,4 L0,8 Z" fill="rgba(255,255,255,0.95)" />
                </marker>

                <filter id="glow">
                  <feGaussianBlur stdDeviation="1.6" result="b" />
                  <feMerge>
                    <feMergeNode in="b" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Main header line */}
              <path
                d="M60 160 H390"
                stroke="rgba(255,255,255,0.85)"
                strokeWidth="3"
                fill="none"
                markerEnd="url(#arrow)"
                filter="url(#glow)"
              />

              <path d="M320 195 V150 H260" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />
              <path d="M320 195 V228 H260" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />

              <path d="M320 190 H460" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />

              {/* Node 1 */}
              <circle cx="320" cy="190" r="7" fill="#000000" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />

              {/* TF branches */}
              <path d="M460 190 V128  H550" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <path d="M460 190       H550" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              <path d="M460 190 V248 H550" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              
              <circle cx="460" cy="190" r="7" fill="#000000" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />
              
              <path d="M760 190 V128 H640" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />
              <path d="M760 190       H640" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M760 190 V248 H640" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />


              {/* Back to main line */}
              <path d="M760 190 H870" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />

              {/* Node 2 */}
              <circle cx="760" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />

                {/**ทิศทางซ้ายขวา ซ้ายขวา ทิศทางบนล่าง สูง ทิศทางซ้ายขวา*/}
              <path d="M870 190 V115 H935" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)"/>
              <path d="M870 190       H935" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)"/>
              <path d="M870 190 V263 H935" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" markerEnd="url(#arrow)"/>

              <circle cx="870" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />

              <path d="M1100 190 V115 H1030" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M1100 190       H1030" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />
              <path d="M1100 190 V263 H1030" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />

              <path d="M1150 190 H1100" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />

              <circle cx="1100" cy="190" r="7" fill="#0a0a0a" stroke="rgba(255,255,255,0.85)" strokeWidth="2" />

              <path d="M1150 190 V70" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />

              <path d="M60 70 H1150" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />

              <path d="M60 190 V70" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none" />

              <path d="M60 190 H100" stroke="rgba(255,255,255,0.85)" strokeWidth="2" fill="none"  />

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
                <MachineBox label="CH1" subLabel="P2CH01" status={getRunSt(TAGS.CH1)} />
                <MachineBox label="CH2" subLabel="P2CH02" status={getRunSt(TAGS.CH2)} />
              </div>

              {/* TF */}
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <MachineBox label="TF4" status={getRunSt(TAGS.TF4)} />
                <MachineBox label="TF5" status={getRunSt(TAGS.TF5)} />
                <MachineBox label="TF7" status={getRunSt(TAGS.TF7)} />
              </div>

              {/* PUMP */}
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <MachineBox label="P9" subLabel="P2CHP09" status={getRunSt(TAGS.P9)} />
                <MachineBox label="P10" subLabel="P2CHP10" status={getRunSt(TAGS.P10)} />
                <MachineBox label="P11" subLabel="P2CHP11" status={getRunSt(TAGS.P11)} />
              </div>
            </div>

            {/* เส้นโค้งล่างเดิม (จะเอาออกก็ได้) */}
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
