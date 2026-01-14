"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { AgCharts } from "ag-charts-react";
import { ModuleRegistry, AllCommunityModule } from "ag-charts-community";

declare global {
  // eslint-disable-next-line no-var
  var __agChartsRegistered: boolean | undefined;
}
if (!globalThis.__agChartsRegistered) {
  ModuleRegistry.registerModules([AllCommunityModule]);
  globalThis.__agChartsRegistered = true;
}

/** =========================
 *  CONFIG
 *  ========================= */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

// time-series endpoints
const CHARTS = {
  chiller_pw: { label: "Chiller Power (kW)", endpoint: "/api/chiller_pw_history" },
  pump_pw: { label: "Pump Power (kW)", endpoint: "/api/pump_pw_history" },
  pump_flow: { label: "Pump Flow", endpoint: "/api/pump_flow_history" },
  chiller_temp: { label: "Chiller Temp", endpoint: "/api/chiller_temp_history" },
  chiller_cop: { label: "Chiller COP", endpoint: "/api/chiller_cop_history" },
  pump_total_pred: { label: "Pump Total (kW) + VSD_control", endpoint: "/api/pump_total_predict_history" },
} as const;
type ChartKey = keyof typeof CHARTS;

type Range = "1h" | "6h" | "24h" | "3d" | "custom";
type Every = "10s" | "30s" | "1m" | "5m" | "10m" | "30m" | "1h";

// one-shot groups (endpoint ของใครของมัน)
const GROUPS = {
  chill_pw: { endpoint: "/api/chill_pw" },
  pump_pw_now: { endpoint: "/api/pump_pw" },
  pump_flow_now: { endpoint: "/api/pump_flow" },
  chiller_temp_now: { endpoint: "/api/chiller_temp" },
  cop_now: { endpoint: "/api/cop" },
} as const;

type GroupKey = keyof typeof GROUPS;

// ยิง oneshot เฉพาะ group ที่ใช้จริง
const NEEDED_GROUPS: GroupKey[] = ["chill_pw", "pump_pw_now", "chiller_temp_now", "cop_now", "pump_flow_now"];

/** =========================
 *  Types
 *  ========================= */
type OneShotOk = {
  ok: true;
  ts: string;
  param: Record<string, { online: boolean; data: number }>;
  total?: number;
};

type OneShotErr = { ok: false; error?: string };

type OneShotResponse = OneShotOk | OneShotErr;

type PredictSummary = {
  saving_rate: number;
  cost_before: number;
  cost_after: number;
  cost_saving: number;
};

type TsOk = { ok: true; history: HistoryPoint[]; summary?: PredictSummary };
type TsErr = { ok: false; error?: string };
type TimeSeriesResponse = TsOk | TsErr;

type HistoryPoint = { ts: string } & Record<string, number | string | null | undefined>;

type NormalizedPoint = {
  ts: Date;
  [key: string]: number | null | Date;
};

type PowerCostHistoryOk = {
  ok: true;
  meta?: { start_ts?: string; end_ts?: string; window_hours?: number; rate?: number };
  summary?: { total_kwh?: number; total_thb?: number };
  total_kwh?: number;
  total_thb?: number;
};
type PowerCostHistoryErr = { ok: false; error?: string };
type PowerCostHistoryResponse = PowerCostHistoryOk | PowerCostHistoryErr;

/** =========================
 *  Helpers
 *  ========================= */
function safeKey(k: string) {
  return k.replace(/[^a-zA-Z0-9_]/g, "_");
}
function toNumberOrNull(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmt(n: number | null, digits = 2) {
  if (n === null) return "-";
  return n.toFixed(digits);
}

type LiveValue = { value: number | null; online: boolean; ts?: string };

function buildLiveMap(input: Partial<Record<GroupKey, OneShotOk>>): Record<string, LiveValue> {
  const out: Record<string, LiveValue> = {};
  for (const g of Object.keys(input) as GroupKey[]) {
    const json = input[g];
    if (!json?.ok) continue;

    const ts = json.ts;
    const param = json.param ?? {};
    for (const k of Object.keys(param)) {
      const p = param[k];
      out[k] = {
        value: typeof p?.data === "number" ? p.data : null,
        online: !!p?.online,
        ts,
      };
    }
  }
  return out;
}

/**return to milliseconds */
function rangeToMs(range: Range) {
  if (range === "1h") return 1 * 60 * 60 * 1000;
  if (range === "6h") return 6 * 60 * 60 * 1000;
  return 24 * 60 * 60 * 1000;
}

/** =========================
 *  UI components
 *  ========================= */
function GlassCard(props: {
  title?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
}) {
  return (
    <div
      style={{
        borderRadius: 38,
        padding: 18,
        border: "2px solid rgba(255,255,255,0.85)",
        background: "linear-gradient(180deg, rgba(140,140,140,0.22), rgba(0,0,0,0.60))",
        boxShadow: "inset 0 0 70px rgba(0,0,0,0.55)",
        overflow: "hidden",
        ...props.style,
      }}
    >
      {props.title && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 12,
          }}
        >
          <div style={{ color: "white", fontWeight: 900, fontSize: 13 }}>{props.title}</div>
          <div>{props.actions}</div>
        </div>
      )}
      <div style={{ ...props.bodyStyle }}>{props.children}</div>
    </div>
  );
}

type ValueItem =
  | { type?: "value"; id: string; label: string; paramKey: string; unit?: string }
  | { type: "divider"; id: string };

type RealtimeGroupDef = { id: "left" | "right"; columns?: number; items: ValueItem[] };
type RealtimePanelDef = { left: RealtimeGroupDef; right: RealtimeGroupDef };

function RealtimePanel(props: { def: RealtimePanelDef; live: Record<string, LiveValue> }) {
  return (
    <div style={{ width: "100%" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1px 1fr", gap: 0, alignItems: "start" }}>
        <RealtimeGroup group={props.def.left} live={props.live} />
        <div style={{ width: 1, height: "100%", background: "rgba(255,255,255,0.85)" }} />
        <RealtimeGroup group={props.def.right} live={props.live} />
      </div>
    </div>
  );
}

function RealtimeGroup(props: { group: RealtimeGroupDef; live: Record<string, LiveValue> }) {
  
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(2, minmax(0, 1fr))`,
        columnGap: 10,
        rowGap: 14,
        alignContent: "start",
        padding: "2px 6px",
      }}
    >
      {props.group.items.map((it) => {
      if ((it as any).type === "divider") {
        return (
          <div
            key={(it as any).id}
            style={{
              gridColumn: `1 / span ${2}`,
              height: 2,
              background: "rgba(255,255,255,0.85)",
              borderRadius: 999,
              margin: "8px 0",
            }}
          />
        );
      }

      const v = props.live[(it as any).paramKey];
      return (
        <ValueTile
          key={(it as any).id}
          label={(it as any).label}
          value={v?.value ?? null}
          online={v?.online ?? false}
          unit={(it as any).unit}
        />
      );
    })}

    </div>
  );
}

function ValueTile(props: { label: string; value: number | null; online: boolean; unit?: string }) {
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", minWidth: 0 }}>
      <span
        style={{
          width: 10,
          height: 10,
          marginTop: 6,
          borderRadius: 999,
          background: props.online ? "#22c55e" : "rgba(255,255,255,0.25)",
          boxShadow: props.online ? "0 0 10px rgba(34,197,94,0.6)" : "none",
          flex: "0 0 auto",
        }}
      />

      <div style={{ minWidth: 0 }}>
        <div
          style={{
            color: "rgba(255,255,255,0.80)",
            fontSize: 11,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {props.label}
        </div>

        <div
          style={{
            color: "white",
            fontWeight: 500,
            fontSize: 28,
            lineHeight: 1.05,
            marginTop: 4,
            fontVariantNumeric: "tabular-nums",
            display: "flex",
            alignItems: "baseline",
            gap: 6,
            flexWrap: "wrap",
          }}
        >
          <span style={{ whiteSpace: "nowrap" }}>{props.value === null ? "--" : fmt(props.value, 2)}</span>
          {props.unit ? (
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.75)", whiteSpace: "nowrap" }}>{props.unit}</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}


// mini chart
const CHART_COLORS = ["#00bcd4", "#ffa726", "#ef5350", "#66bb6a", "#ab47bc"];

function MiniChart(props: { title: string; data: NormalizedPoint[]; yKeys: string[] }) {
  const series = props.yKeys.map((key, index) => ({
    type: "line",
    xKey: "ts",
    yKey: key,
    stroke: CHART_COLORS[index % CHART_COLORS.length],
    fillOpacity: 0.25,
    strokeWidth: 2,
    marker: { enabled: false },
    tooltip: {
      renderer: (params: any) => ({
        content: typeof params.yValue === "number" ? params.yValue.toFixed(2) : "-",
      }),
    },
  }));

  const options = {
    theme: "ag-default-dark",
    background: { fill: "transparent" },
    padding: { top: 10, right: 10, bottom: 10, left: 10 },
    title: {
      text: props.title,
      fontSize: 14,
      color: "rgba(255,255,255,0.95)",
      spacing: 6,
    },
    data: props.data,
    series,
    axes: [
      { type: "time", position: "bottom", label: { enabled: false }, tick: { enabled: false }, line: { enabled: false } },
      {
        type: "number",
        position: "left",
        label: { fontSize: 10, color: "rgba(255,255,255,0.6)" },
        tick: { count: 3 },
        gridLine: { style: { stroke: "rgba(255,255,255,0.10)" } },
      },
    ],
    legend: { enabled: true },
  };

  return (
    <div style={{ height: 150 }}>
      <AgCharts options={options as any} />
    </div>
  );
}

/** =========================
 *  Page
 *  ========================= */
export default function Page() {
  const [miniChart1, setMiniChart1] = useState<{ rows: NormalizedPoint[]; keys: string[] }>({ rows: [], keys: [] });
  const [miniChart2, setMiniChart2] = useState<{ rows: NormalizedPoint[]; keys: string[] }>({ rows: [], keys: [] });

  const [chartKey, setChartKey] = useState<ChartKey>("chiller_pw");
  const isPumpPowerChart = chartKey === "pump_total_pred";

  const [range, setRange] = useState<Range>("6h");
  const [every, setEvery] = useState<Every>("10m");

  const [customFrom, setCustomFrom] = useState<string>("");
  const [customTo, setCustomTo] = useState<string>("");
  const [customTick, setCustomTick] = useState(0);

  const [rows, setRows] = useState<NormalizedPoint[]>([]);
  const [series, setSeries] = useState<Array<Record<string, unknown>>>([]);
  const [online, setOnline] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // one-shot groups
  const [groups, setGroups] = useState<Partial<Record<GroupKey, OneShotOk>>>({});
  const [groupErr, setGroupErr] = useState<string | null>(null);

  const liveMap = useMemo(() => buildLiveMap(groups), [groups]);

  const realtimeDef: RealtimePanelDef = {
    left: {
      id: "left",
      columns: 2, //  2 ช่องต่อแถว
      items: [
        // ====== TOP 4 (2x2) ======
        { id: "top1", label: "Winenergy.P1CH01.kW", paramKey: "Winenergy.P1CH01.kW", unit: "kW" },
        { id: "top2", label: "Winenergy.P1CH02.kW", paramKey: "Winenergy.P1CH02.kW", unit: "kW" },
        { id: "top3", label: "Winenergy.P2CH01.kW", paramKey: "Winenergy.P2CH01.kW", unit: "kW" },
        { id: "top4", label: "Winenergy.P2CH02.kW", paramKey: "Winenergy.P2CH02.kW", unit: "kW" },

        // เส้นคั่น
        { type: "divider", id: "div1" },

        // ====== BOTTOM 6 (3x2) ======
        { id: "bot1", label: "Winenergy.P2CHP09.kW", paramKey: "Winenergy.P2CHP09.kW", unit: "kW" },
        { id: "bot2", label: "Winenergy.P2CHP10.kW", paramKey: "Winenergy.P2CHP10.kW", unit: "kW" },
        { id: "bot3", label: "Winenergy.P2CHP11.kW", paramKey: "Winenergy.P2CHP11.kW", unit: "kW" },

        // ใส่เพิ่มอีก 3 ตัวให้ครบ 6 ตัวด้านล่าง (ตัวอย่าง)
        { id: "bot4", label: "Winenergy.P2CHP12.kW", paramKey: "Winenergy.P2CHP12.kW", unit: "kW" },
        { id: "bot5", label: "Winenergy.P2CHP13.kW", paramKey: "Winenergy.P2CHP13.kW", unit: "kW" },
        { id: "bot6", label: "Winenergy.P2CHP14.kW", paramKey: "Winenergy.P2CHP14.kW", unit: "kW" },
      ],
    },

    // ถ้าไม่อยากใช้ฝั่งขวาใน Status ให้ปล่อยว่างได้
    right: {
      id: "right",
      columns: 2,
      items: [],
    },
  };

  const [tariff, setTariff] = useState(4.0);

  const [costKWh, setCostKWh] = useState<number | null>(null);
  const [costTHBServer, setCostTHBServer] = useState<number | null>(null);
  const [costRange, setCostRange] = useState<{ start?: string; end?: string } | null>(null);
  const [costLoading, setCostLoading] = useState(false);
  const [costErr, setCostErr] = useState<string | null>(null);

  const [predictOn, setPredictOn] = useState(false);
  const [predictPct, setPredictPct] = useState(90); // 0-100
  const [predLoading, setPredLoading] = useState(false);
  const [predErr, setPredErr] = useState<string | null>(null);
  const [predResult, setPredResult] = useState<{
    saving_rate?: number;
    cost_before?: number;
    cost_after?: number;
    cost_saving?: number;
  } | null>(null);

  async function fetchPowerCostHistory() {
    setCostErr(null);
    setCostLoading(true);

    const now = new Date();
    let from: Date;
    let to: Date;

    if (range === "custom") {
      if (!customFrom || !customTo) throw new Error("Please select From/To time");
      from = new Date(customFrom);
      to = new Date(customTo);
    } else {
      from = new Date(now.getTime() - rangeToMs(range));
      to = now;
    }

    const url =
      `${API_BASE}/api/pump_power_cost_history` +
      `?from=${encodeURIComponent(from.toISOString())}` +
      `&to=${encodeURIComponent(to.toISOString())}` +
      `&every=${encodeURIComponent(every)}` +
      `&rate=${encodeURIComponent(String(tariff))}`;

    const res = await fetch(url, { cache: "no-store" });
    const json = (await res.json()) as PowerCostHistoryResponse;

    if (!res.ok) throw new Error(`power_cost_history HTTP ${res.status}`);
    if (!json.ok) throw new Error(json.error ?? "power_cost_history ok=false");

    const kwh = (json.summary?.total_kwh ?? (json as any).total_kwh) as number | undefined;
    const thb = (json.summary?.total_thb ?? (json as any).total_thb) as number | undefined;

    setCostKWh(Number.isFinite(kwh as number) ? (kwh as number) : null);
    setCostTHBServer(Number.isFinite(thb as number) ? (thb as number) : null);

    setCostRange({
      start: (json as any).start_iso ?? json.meta?.start_ts,
      end: (json as any).end_iso ?? json.meta?.end_ts,
    });

    setCostLoading(false);
  }

  const abortRef = useRef<AbortController | null>(null);

  async function fetchGroup(g: GroupKey) {
    const url = `${API_BASE}${GROUPS[g].endpoint}`;
    const res = await fetch(url, { cache: "no-store" });
    const json = (await res.json()) as OneShotResponse;

    if (!res.ok) throw new Error(`${g} HTTP ${res.status}`);
    if (!json.ok) throw new Error(`${g} ok=false: ${json.error ?? "-"}`);
    return json;
  }

  async function fetchTimeSeries() {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    const now = new Date();
    let from: Date;
    let to: Date;

    if (range === "custom") {
      if (!customFrom || !customTo) throw new Error("Please select From/To time");
      from = new Date(customFrom);
      to = new Date(customTo);
      if (!Number.isFinite(from.getTime()) || !Number.isFinite(to.getTime())) throw new Error("Invalid date/time");
      if (from >= to) throw new Error("From must be earlier than To");
    } else {
      from = new Date(now.getTime() - rangeToMs(range));
      to = now;
    }

    const endpoint = CHARTS[chartKey].endpoint;
    let url =
      `${API_BASE}${endpoint}` +
      `?from=${encodeURIComponent(from.toISOString())}` +
      `&to=${encodeURIComponent(to.toISOString())}` +
      `&every=${encodeURIComponent(every)}`;

    if (chartKey === "pump_total_pred") {
      const rpm_drop = Math.max(0, Math.min(100, predictPct)) / 100;
      url += `&rate=${encodeURIComponent(String(tariff))}`;
      url += `&rpm_drop=${encodeURIComponent(String(rpm_drop))}`;
    }

    const res = await fetch(url, { cache: "no-store", signal: ac.signal });
    const json = (await res.json()) as TimeSeriesResponse;

    if (!res.ok) throw new Error(`History HTTP ${res.status}`);
    if (!json.ok) throw new Error(json.error ?? "history ok=false");

    if (chartKey === "pump_total_pred") {
      const s = json.summary ?? null;
      setPredResult(
        s
          ? { saving_rate: s.saving_rate, cost_before: s.cost_before, cost_after: s.cost_after, cost_saving: s.cost_saving }
          : null
      );
    }

    const history = json.history ?? [];
    if (history.length === 0) {
      setRows([]);
      setSeries([]);
      return;
    }

    const rawKeys = Object.keys(history[0]).filter((k) => k !== "ts");
    const keyMap: Record<string, string> = {};
    rawKeys.forEach((k) => (keyMap[k] = safeKey(k)));

    const normalized: NormalizedPoint[] = history.map((p) => {
      const out: NormalizedPoint = { ts: new Date(p.ts) };
      for (const k of rawKeys) out[keyMap[k]] = toNumberOrNull(p[k]);
      return out;
    });

    const autoSeries = rawKeys.map((k) => ({
      type: "line",
      xKey: "ts",
      yKey: keyMap[k],
      yName: k,
      marker: { enabled: false },
    }));

    setRows(normalized);
    setSeries(autoSeries);
  }

  async function loadAll() {
    setErr(null);
    setGroupErr(null);

    const settled = await Promise.allSettled(NEEDED_GROUPS.map(async (g) => [g, await fetchGroup(g)] as const));
    const next: Partial<Record<GroupKey, OneShotOk>> = {};
    const failed: string[] = [];

    for (const r of settled) {
      if (r.status === "fulfilled") {
        const [g, json] = r.value;
        next[g] = json;
      } else {
        const msg = r.reason instanceof Error ? r.reason.message : String(r.reason);
        failed.push(msg);
      }
    }

    setGroups(next);
    if (failed.length) setGroupErr(failed.join(" | "));

    try {
      await fetchTimeSeries();
      setOnline(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setErr(msg);
      setOnline(false);
    }
  }

  async function fetchMiniHistory(key: ChartKey) {
    const now = new Date();
    const from = new Date(now.getTime() - rangeToMs("6h"));

    const url =
      `${API_BASE}${CHARTS[key].endpoint}` +
      `?from=${encodeURIComponent(from.toISOString())}` +
      `&to=${encodeURIComponent(now.toISOString())}` +
      `&every=${encodeURIComponent("10m")}`;

    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`[mini:${key}] HTTP ${res.status} ${text}`);
      }
      const json = (await res.json()) as TimeSeriesResponse;
      if (!json.ok || !json.history || json.history.length === 0) return { rows: [], keys: [] };

      const rawKeys = Object.keys(json.history[0]).filter((k) => k !== "ts");
      const keyMap: Record<string, string> = {};
      const cleanKeys: string[] = [];

      rawKeys.forEach((k) => {
        const safe = safeKey(k);
        keyMap[k] = safe;
        cleanKeys.push(safe);
      });

      const rows = json.history.map((p) => {
        const out: NormalizedPoint = { ts: new Date(p.ts) };
        for (const k of rawKeys) out[keyMap[k]] = toNumberOrNull(p[k]);
        return out;
      });

      return { rows, keys: cleanKeys };
    } catch (e) {
      console.error(e);
      return { rows: [], keys: [] };
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    fetchMiniHistory("chiller_temp").then(setMiniChart1);
    fetchMiniHistory("pump_flow").then(setMiniChart2);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        await fetchPowerCostHistory();
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        setCostErr(msg);
        setCostLoading(false);
        setCostKWh(null);
        setCostTHBServer(null);
        setCostRange(null);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartKey, range, every, customTick, tariff]);

  useEffect(() => {
    if (!isPumpPowerChart && predictOn) setPredictOn(false);
  }, [isPumpPowerChart, predictOn]);

  const chartOptions = useMemo(
    () => ({
      theme: "ag-default-dark",
      background: { fill: "transparent" },
      title: { text: CHARTS[chartKey].label },
      data: rows,
      series: series,
      axes: [
        { type: "time", position: "bottom" },
        { type: "number", position: "left", tick: { count: 4 } },
      ],
      legend: { enabled: true, position: "bottom" as const },
    }),
    [chartKey, rows, series]
  );

  return (
    <div
      style={{
        height: "100vh",
        overflow: "hidden",
        padding: 18,
        background: "radial-gradient(1200px 700px at 50% 0%, #1b1b1b 0%, #0b0b0b 55%, #050505 100%)",
      }}
    >
      {/* Outer frame เหมือนรูป */}
      <div
        style={{
          maxWidth: 1800,
          margin: "0 auto",
          border: "2px solid rgba(255,255,255,0.85)",
          padding: 18,
        }}
      >
        <div style={{ textAlign: "center", color: "white", fontWeight: 900, fontSize: 26, marginBottom: 18 }}>
          RMC-Monitor
        </div>

        {/* Layout ใหม่: 3 cols + 3 rows (top, label, bottom) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(260px, 320px) minmax(0, 1fr) minmax(260px, 320px)",
            gridTemplateRows: "auto 28px auto",
            gap: 16,
            alignItems: "start",
          }}
        >
          {/* STATUS (ซ้ายยาว) */}
          <div style={{ gridColumn: 1, gridRow: "1 / span 3" }}>
            <GlassCard
              title="Status"
              actions={
                <button
                  onClick={loadAll}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 12,
                    background: "rgba(255,255,255,0.18)",
                    border: "1px solid rgba(255,255,255,0.35)",
                    color: "white",
                    fontWeight: 900,
                    cursor: "pointer",
                  }}
                >
                  Reload
                </button>
              }
              style={{ minHeight: 720 }}
            >
              {/* top summary */}
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                <div style={{ color: "white", fontWeight: 500, fontSize: 22 }}>PLANT1</div>
                <div style={{ color: "white", fontWeight: 500, fontSize: 22 }}>{online ? "ON" : "OFF"}</div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                <div style={{ color: "white", fontWeight: 500, fontSize: 22 }}>PLANT2</div>
                <div style={{ color: "white", fontWeight: 500, fontSize: 22 }}>{online ? "ON" : "OFF"}</div>
              </div>   

              {/* realtime values (เหมือนในรูป) */}
              <RealtimeGroup group={realtimeDef.left} live={liveMap} />

              <div style={{ height: 14 }} />

              <div style={{ height: 1, background: "rgba(255,255,255,0.85)" }} />

              
            </GlassCard>
          </div>

          {/* CENTER TOP: Setting + Time-series */}
          <div style={{ gridColumn: 2, gridRow: 1 }}>
            <div
              style={{
                border: "2px solid rgba(255,255,255,0.85)",
                borderRadius: 18,
                overflow: "hidden",
                background: "rgba(0,0,0,0.25)",
                boxShadow: "inset 0 0 60px rgba(0,0,0,0.55)",
              }}
            >
              {/* header row (Setting time-series) */}
              <div style={{ padding: 14, borderBottom: "2px solid rgba(255,255,255,0.85)" }}>
                <div style={{ color: "white", fontWeight: 900, fontSize: 20, marginBottom: 12 }}>Setting time-series</div>

                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                    flexWrap: "wrap",
                    rowGap: 10,
                  }}
                >
                  <span style={{ color: "white", fontWeight: 800 }}>Chart</span>
                  <select
                    value={chartKey}
                    onChange={(e) => setChartKey(e.target.value as ChartKey)}
                    style={{
                      padding: 8,
                      background: "rgba(0,0,0,0.55)",
                      color: "white",
                      border: "1px solid rgba(255,255,255,0.35)",
                      borderRadius: 10,
                    }}
                  >
                    {Object.keys(CHARTS).map((k) => (
                      <option key={k} value={k}>
                        {CHARTS[k as ChartKey].label}
                      </option>
                    ))}
                  </select>

                  <span style={{ color: "white", fontWeight: 800 }}>Range</span>
                  <select
                    value={range}
                    onChange={(e) => setRange(e.target.value as Range)}
                    style={{
                      padding: 8,
                      background: "rgba(0,0,0,0.55)",
                      color: "white",
                      border: "1px solid rgba(255,255,255,0.35)",
                      borderRadius: 10,
                    }}
                  >
                    <option value="1h">Last 1h</option>
                    <option value="6h">Last 6h</option>
                    <option value="24h">Last 24h</option>
                    <option value="custom">Custom</option>
                  </select>

                  {range === "custom" && (
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <input
                        type="datetime-local"
                        value={customFrom}
                        onChange={(e) => setCustomFrom(e.target.value)}
                        style={{ padding: 6, borderRadius: 10 }}
                      />
                      <span style={{ color: "white" }}>to</span>
                      <input
                        type="datetime-local"
                        value={customTo}
                        onChange={(e) => setCustomTo(e.target.value)}
                        style={{ padding: 6, borderRadius: 10 }}
                      />
                      <button
                        onClick={() => setCustomTick((n) => n + 1)}
                        style={{
                          padding: "8px 12px",
                          borderRadius: 12,
                          border: "1px solid rgba(255,255,255,0.35)",
                          background: "rgba(37,99,235,0.90)",
                          color: "white",
                          fontWeight: 900,
                          cursor: "pointer",
                        }}
                      >
                        Apply
                      </button>
                    </div>
                  )}

                  <span style={{ color: "white", fontWeight: 800 }}>Every</span>
                  <select
                    value={every}
                    onChange={(e) => setEvery(e.target.value as Every)}
                    style={{
                      padding: 8,
                      background: "rgba(0,0,0,0.55)",
                      color: "white",
                      border: "1px solid rgba(255,255,255,0.35)",
                      borderRadius: 10,
                    }}
                  >
                    <option value="10s">10s</option>
                    <option value="30s">30s</option>
                    <option value="1m">1m</option>
                    <option value="5m">5m</option>
                    <option value="10m">10m</option>
                    <option value="30m">30m</option>
                    <option value="1h">1h</option>
                  </select>

                  <span style={{ color: "white", fontWeight: 800 }}>VSD_control</span>
                  <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <input
                      type="checkbox"
                      checked={predictOn}
                      disabled={!isPumpPowerChart}
                      onChange={(e) => setPredictOn(e.target.checked)}
                    />
                    <span style={{ color: isPumpPowerChart ? "white" : "rgba(255,255,255,0.4)" }}>
                      {isPumpPowerChart ? "Enable" : "Only Pump Power"}
                    </span>
                  </label>

                  {predictOn && isPumpPowerChart && (
                    <>
                      <span style={{ color: "rgba(255,255,255,0.8)" }}>Hz_ratio</span>
                      <input
                        type="number"
                        step="0.01"
                        min={0}
                        max={1}
                        value={predictPct / 100}
                        onChange={(e) => setPredictPct(Math.round((Number(e.target.value) || 0) * 100))}
                        style={{ width: 110, padding: 6, borderRadius: 10 }}
                      />
                    </>
                  )}

                  <div style={{ marginLeft: "auto", color: "rgba(255,255,255,0.8)", fontSize: 12 }}>
                    Points: <b>{rows.length}</b>
                  </div>
                </div>
              </div>

              {/* chart block (Time-series) */}
              <div style={{ padding: 14 }}>
                <div style={{ color: "white", fontWeight: 900, fontSize: 18, marginBottom: 10 }}>Time-series</div>
                <div style={{ height: 280 }}>
                  <AgCharts options={chartOptions as unknown as Record<string, unknown>} />
                </div>
              </div>
            </div>
          </div>

          {/* COST (ขวายาว) */}
          <div style={{ gridColumn: 3, gridRow: "1 / span 3" }}>
            <GlassCard title="Cost" style={{ minHeight: 720 }}>
              {/* กล่อง cost บน (เหมือนในรูปที่มีกรอบด้านใน) */}
              <div
                style={{
                  border: "2px solid rgba(255,255,255,0.85)",
                  borderRadius: 22,
                  padding: 14,
                  background: "rgba(0,0,0,0.20)",
                }}
              >
                <div style={{ color: "rgba(255,255,255,0.85)", fontSize: 12 }}>Tariff (THB/kWh)</div>
                <input
                  type="number"
                  value={tariff}
                  step={0.1}
                  onChange={(e) => setTariff(Number(e.target.value))}
                  style={{ width: "100%", padding: 8, marginTop: 6, borderRadius: 12, border: "none" }}
                />

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14 }}>
                  <div>
                    <div style={{ color: "rgba(255,255,255,0.8)", fontSize: 11 }}>Energy</div>
                    <div style={{ color: "white", fontWeight: 900, fontSize: 18 }}>
                      {costLoading ? "..." : costKWh === null ? "-" : fmt(costKWh, 1)}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ color: "rgba(255,255,255,0.8)", fontSize: 11 }}>THB</div>
                    <div style={{ color: "white", fontWeight: 900, fontSize: 18 }}>
                      {costLoading ? "..." : costTHBServer === null ? "-" : fmt(costTHBServer, 0)}
                    </div>
                  </div>
                </div>

                {costErr && <div style={{ color: "salmon", marginTop: 10, fontSize: 12 }}>⚠ {costErr}</div>}
                {costRange?.start && costRange?.end && (
                  <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 10, marginTop: 10 }}>
                    {costRange.start} → {costRange.end}
                  </div>
                )}

                <div style={{ height: 14 }} />

              </div>

              <div style={{ height: 14 }} />

              {/* VSD control summary */}
              <div
                style={{
                  borderRadius: 22,
                  border: "1px solid rgba(255,255,255,0.25)",
                  padding: 14,
                  background: "rgba(0,0,0,0.18)",
                }}
              >
                <div style={{ color: "white", fontWeight: 900, fontSize: 18 }}>VSD_control</div>
                <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 12, marginTop: 6 }}>
                  {predictOn ? `Hz @ ${predictPct}%` : "OFF"}
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
                  <div>
                    <div style={{ color: "rgba(255,255,255,0.8)", fontSize: 10 }}>After (THB)</div>
                    <div style={{ color: "white", fontWeight: 900, fontSize: 18 }}>
                      {!predictOn ? "-" : predLoading ? "..." : predResult?.cost_after == null ? "-" : fmt(predResult.cost_after, 2)}
                    </div>
                  </div>

                  <div style={{ textAlign: "right" }}>
                    <div style={{ color: "rgba(255,255,255,0.8)", fontSize: 10 }}>Saving</div>
                    <div style={{ color: "#22c55e", fontWeight: 900, fontSize: 18 }}>
                      {!predictOn ? "-" : predLoading ? "..." : predResult?.cost_saving == null ? "-" : fmt(predResult.cost_saving, 2)}
                    </div>
                    <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 11, marginTop: 4 }}>
                      {!predictOn ? "" : predResult?.saving_rate == null ? "" : `${fmt(predResult.saving_rate, 2)}%`}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <input
                      type="checkbox"
                      checked={predictOn}
                      disabled={!isPumpPowerChart}
                      onChange={(e) => setPredictOn(e.target.checked)}
                    />
                    <span style={{ color: isPumpPowerChart ? "white" : "rgba(255,255,255,0.4)" }}>
                      {isPumpPowerChart ? "Enable" : "Only Pump Power"}
                    </span>
                  </label>
                </div>

                {predErr && <div style={{ color: "salmon", marginTop: 10, fontSize: 12 }}>⚠ {predErr}</div>}
              </div>

              <div style={{ height: 16 }} />

              {/* กล่องว่างด้านล่าง */}
              <div
                style={{
                  flex: 1,
                  borderRadius: 34,
                  background: "rgba(0,0,0,0.22)",
                  boxShadow: "inset 0 0 80px rgba(0,0,0,0.55)",
                }}
              />
            </GlassCard>
          </div>

          {/* bottom charts (กลางล่าง 2 กล่อง) */}
          <div style={{ gridColumn: 2, gridRow: 3 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
              <GlassCard title="Graph Temp" style={{ borderRadius: 34 }} bodyStyle={{ paddingTop: 4 }}>
                <MiniChart title="Area chart" data={miniChart1.rows} yKeys={miniChart1.keys} />
              </GlassCard>

              <GlassCard title="Graph Flow" style={{ borderRadius: 34 }} bodyStyle={{ paddingTop: 4 }}>
                <MiniChart title="Area chart" data={miniChart2.rows} yKeys={miniChart2.keys} />
              </GlassCard>
            </div>
          </div>
        </div>

        {/* ปุ่มวงกลมมุมล่างซ้าย */}
        <div
          style={{
            position: "fixed",
            left: 18,
            bottom: 18,
            width: 44,
            height: 44,
            borderRadius: 999,
            border: "2px solid rgba(255,255,255,0.9)",
            display: "grid",
            placeItems: "center",
            color: "white",
            fontWeight: 900,
            background: "rgba(0,0,0,0.15)",
            userSelect: "none",
          }}
        >
          N
        </div>
      </div>
    </div>
  );
}
