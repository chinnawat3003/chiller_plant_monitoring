// types/dashboard.ts

export type Item = {
  name: string;
  value: number | null;
  unit?: string;
  ts?: string; // ISO time (optional)
};

export type OneShotOk = {
  ok: boolean;
  items: Item[];
};

export type SuggestionRes = {
  ok: boolean;
  suggestion?: string;
  reason?: string;
  data?: unknown;
};

export type CostRes = {
  ok: boolean;
  kwh?: number;
  thb?: number;
  peak_kwh?: number;
  peak_thb?: number;
};

export type LimitsRes = {
  ok: boolean;
  // example: { min: 0, max: 100 } or null
  min?: number | null;
  max?: number | null;
};

export type ChartPoint = {
  t: string; // ISO time
  v: number; // value
};

export type ChartRes = {
  ok: boolean;
  points: ChartPoint[];
};
