"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { AgCharts } from "ag-charts-react";
import { ModuleRegistry, AllCommunityModule } from "ag-charts-community";
import type { AgChartOptions } from "ag-charts-community";

ModuleRegistry.registerModules([AllCommunityModule]);

/** =========================
 * CONFIG
 * ========================= */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const HEALTH_URL = `${API_BASE}/health`;

//  Sticky สำหรับ "Online (มีข้อมูล/ต่ออยู่)" เท่านั้น
const ONLINE_STICKY_TTL_MS = 30_000;
const RUN_STICKY_TTL_MS = 10_000; // เขียวค้าง 10 วิถ้าเพิ่งทำงาน

//  เงื่อนไข "เครื่องทำงาน" (Power kW > 0)
const RUN_THRESHOLD_KW = 10;

const CHARTS = {
  chiller_pw: { label: "Chiller Power (kW)", endpoint: "/api/chiller_pw_history" },
  pump_pw: { label: "Pump Power (kW)", endpoint: "/api/pump_pw_history" },
  pump_flow: { label: "Pump Flow", endpoint: "/api/pump_flow_history" },
  chiller_temp: { label: "Chiller Temp", endpoint: "/api/chiller_temp_history" },
  thermoform_power: { label: "Thermoform Power (kW)", endpoint: "/api/thermoform_power_history" },
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

  // ✅ Sticky online สำหรับ "data มาได้" เท่านั้น
  const lastSeenRef = useRef<Record<string, number>>({});
  const lastRunSeenRef = useRef<Record<string, number>>({});

  /** =========================
   * TAGS (ปรับตรงนี้ได้ง่าย)
   * ========================= */
  const TAGS = {
    // kW (ใช้ Running logic)
    CH1: "Winenergy.P2CH01.kW",
    CH2: "Winenergy.P2CH02.kW",
    P9: "Winenergy.P2CHP09.kW",
    P10: "Winenergy.P2CHP10.kW",
    P11: "Winenergy.P2CHP11.kW",
    TF4: "Modbus_TF4.18CT1.Main_Thermoform_kW_Cal",
    TF5: "Modbus_TF5.18CT1.Main_Thermoform_kW_Cal",
    TF7: "Modbus_TF7.18CT1.Main_Thermoform_kW_Cal",

    // Temp (ใช้ Online logic)
    TEMP_RETURN: "Chiller.PLANT_Node2.CLG2_TEMP_CHWR",
    TEMP_SUPPLY: "Chiller.PLANT_Node2.CLG2_TEMP_CHWS",
  };

  // ✅ กลุ่ม TAG ที่ถือว่า "เครื่องทำงาน" = value > 0
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
        { type: "time", position: "bottom" } as any,
        { type: "number", position: "left" } as any,
      ],
      legend: { position: "bottom" } as any,
    }),
    [chartData, chartSeries]
  );

  const pingHealth = async () => {
    try {
      const res = await fetchJson<{ ok: boolean }>(HEALTH_URL, 2000);
      if (!res?.ok) throw new Error("health not ok");
      return true;
    } catch (e: any) {
      setApiErrMsg(e?.name === "AbortError" ? "FastAPI timeout" : "FastAPI not connected");
      return false;
    }
  };

  /** =========================
   * ✅ STATUS LOGIC (สะอาด + ตรงเงื่อนไข)
   * ========================= */

  // 1) Online = เช็คว่ามีข้อมูลส่งมาหรือไม่ (มี sticky ลดกระพริบ)
  const getOnlineSt = (tag: string): TwoStatus => {
    if (apiStatus === "offline") return "offline";

    const item = liveData?.[tag];
    if (!item) {
      const last = lastSeenRef.current[tag];
      if (last && Date.now() - last < ONLINE_STICKY_TTL_MS) return "online";
      return "offline";
    }

    // online flag จาก backend (หรือจะใช้ isFinite(data) ก็ได้)
    if (item.online || Number.isFinite(item.data)) {
      lastSeenRef.current[tag] = Date.now();
      return "online";
    }

    const last = lastSeenRef.current[tag];
    if (last && Date.now() - last < ONLINE_STICKY_TTL_MS) return "online";

    return "offline";
  };

  // 2) Running = เครื่องทำงานเมื่อ value > 0 (ไม่มี sticky เพื่อให้ตรงเงื่อนไข)
  const getRunSt = (tag: string, min = RUN_THRESHOLD_KW): TwoStatus => {
    if (apiStatus === "offline") return "offline";

    const v = Number(liveData?.[tag]?.data);

    //  มีค่า > 0 = เครื่องทำงาน
    if (Number.isFinite(v) && v > min) {
      lastRunSeenRef.current[tag] = Date.now();
      return "online";
    }

    //  ถ้าข้อมูลหาย/เป็น 0 แต่เพิ่งทำงานเมื่อกี้ ให้เขียวต่อกันกระพริบ
    const last = lastRunSeenRef.current[tag];
    if (last && Date.now() - last < RUN_STICKY_TTL_MS) return "online";

    return "offline";
  };


  // helper เลือกสถานะให้ถูก type
  const getSt = (tag: string): TwoStatus => {
    return RUN_TAGS.has(tag) ? getRunSt(tag) : getOnlineSt(tag);
  };

  const getVal = (tag: string) => (tag in liveData ? liveData[tag]?.data ?? null : null);

  /** =========================
   * FETCH: LIVE DATA
   * ========================= */
  const ONE_SHOT_GROUPS = useMemo(
    () => [
      { endpoint: "/api/chill_pw" },
      { endpoint: "/api/pump_pw" },
      { endpoint: "/api/pump_flow" },
      { endpoint: "/api/chiller_temp" },
      { endpoint: "/api/thermoform_power" },
      { endpoint: "/api/chiller_tank_temp" },
    ],
    []
  );

  const fetchOneShot = async () => {
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
        ONE_SHOT_GROUPS.map((g) => fetchJson<OneShotOk>(`${API_BASE}${g.endpoint}`, 3000))
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

    } catch (e) {
      setApiStatus("offline");
      setLiveData({});
    } finally {
      liveInFlight.current = false;
    }
  };

  /** =========================
   * FETCH: SUGGESTION
   * ========================= */
  const fetchSuggestion = async () => {
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
  };

  /** =========================
   * FETCH: COST
   * ========================= */
  const fetchCost = async () => {
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
  };

  /** =========================
   * FETCH: CHART
   * ========================= */
  const fetchChart = async () => {
    if (chartInFlight.current) return;
    chartInFlight.current = true;

    setChartLoading(true);
    setChartError(null);

    try {
      const ok = await pingHealth();
      if (!ok) throw new Error("FastAPI offline");
      setApiStatus("online");

      const json = await fetchJson<any>(chartUrl, 6000);
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

      const safeData = data.map((row: any) => {
        const out: any = { ts: row.ts };
        keys.forEach((k) => (out[keyMap[k]] = row[k]));
        return out;
      });

      setChartData(safeData);
      setChartSeries(
        keys.map((k) => ({
          type: "line",
          xKey: "ts",
          yKey: keyMap[k],
          yName: k,
          strokeWidth: 2,
          marker: { enabled: false },
        }))
      );
    } catch (e: any) {
      setChartData([]);
      setChartSeries([]);
      setChartError(e?.message ?? "failed");
      setApiStatus("offline");
    } finally {
      setChartLoading(false);
      chartInFlight.current = false;
    }
  };

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
      fetchSuggestion();
    }, 10_000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchChart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartUrl]);

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
          {/* ✅ Power ใช้ Running: value > 0 */}
          <StatusDot label="P2CH01" value={getVal(TAGS.CH1)} status={getRunSt(TAGS.CH1)} unit="kW" />
          <StatusDot label="P2CH02" value={getVal(TAGS.CH2)} status={getRunSt(TAGS.CH2)} unit="kW" />

          <SectionHeader title="Pump Power" />
          {/* ✅ Power ใช้ Running */}
          <StatusDot label="P2CHP09" value={getVal(TAGS.P9)} status={getRunSt(TAGS.P9)} unit="kW" />
          <StatusDot label="P2CHP10" value={getVal(TAGS.P10)} status={getRunSt(TAGS.P10)} unit="kW" />
          <StatusDot label="P2CHP11" value={getVal(TAGS.P11)} status={getRunSt(TAGS.P11)} unit="kW" />

          <SectionHeader title="Temperature" />
          {/* ✅ Temp ใช้ Online (เช็คว่ามีข้อมูลมา/ต่ออยู่) */}
          <StatusDot label="Return" value={getVal(TAGS.TEMP_RETURN)} status={getOnlineSt(TAGS.TEMP_RETURN)} unit="°C" />
          <StatusDot label="Supply" value={getVal(TAGS.TEMP_SUPPLY)} status={getOnlineSt(TAGS.TEMP_SUPPLY)} unit="°C" />
        </div>

        {/* CENTER PANEL */}
        <div style={{ display: "grid", gridTemplateRows: "auto 1fr", gap: 20 }}>
          {/* Diagram */}
          <div
            style={{
              border: "1px solid #333",
              borderRadius: 4,
              padding: 20,
              position: "relative",
              background: "#0a0a0a",
            }}
          >
            <h2 style={{ textAlign: "center", marginBottom: 30 }}>Chiller Plant Diagram</h2>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-around", height: 200 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                <MachineBox label="CH1" subLabel="P2CH01" status={getRunSt(TAGS.CH1)} />
                <MachineBox label="CH2" subLabel="P2CH02" status={getRunSt(TAGS.CH2)} />
              </div>

              <ArrowRight />

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <MachineBox label="TF4" status={getRunSt(TAGS.TF4)} />
                <MachineBox label="TF5" status={getRunSt(TAGS.TF5)} />
                <MachineBox label="TF7" status={getRunSt(TAGS.TF7)} />
              </div>

              <ArrowRight />

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <MachineBox label="P9" subLabel="P2CHP09" status={getRunSt(TAGS.P9)} />
                <MachineBox label="P10" subLabel="P2CHP10" status={getRunSt(TAGS.P10)} />
                <MachineBox label="P11" subLabel="P2CHP11" status={getRunSt(TAGS.P11)} />
              </div>
            </div>

            <div
              style={{
                position: "absolute",
                bottom: 20,
                left: 40,
                right: 40,
                height: 10,
                border: "1px dashed #444",
                borderTop: "none",
                borderRadius: "0 0 20px 20px",
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
