// lib/charts.ts

export type ChartKey =
  | "plant_power"
  | "thermoform_power"
  | "chilled_water_temp"
  | "chilled_water_flow";

export type ChartConfig = {
  key: ChartKey;
  title: string;
  unit?: string;

  // endpoints
  historyPath: string; // returns { ok, points: [{t,v}] }
  limitPath?: string;  // returns { ok, min, max }
};

export const CHARTS: ChartConfig[] = [
  {
    key: "plant_power",
    title: "Plant Power",
    unit: "kW",
    historyPath: "/api/plant_power_history",
    limitPath: "/api/plant_power_limits",
  },
  {
    key: "thermoform_power",
    title: "Thermoform Power",
    unit: "kW",
    historyPath: "/api/thermoform_power_history",
    limitPath: "/api/thermoform_power_limits",
  },
  {
    key: "chilled_water_temp",
    title: "Chilled Water Temp",
    unit: "°C",
    historyPath: "/api/chw_temp_history",
    limitPath: "/api/chw_temp_limits",
  },
  {
    key: "chilled_water_flow",
    title: "Chilled Water Flow",
    unit: "m³/h",
    historyPath: "/api/chw_flow_history",
    limitPath: "/api/chw_flow_limits",
  },
];

export function chartByKey(key: ChartKey) {
  const c = CHARTS.find((x) => x.key === key);
  if (!c) throw new Error(`Unknown chart key: ${key}`);
  return c;
}
