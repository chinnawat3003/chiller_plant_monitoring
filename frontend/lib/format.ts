// lib/format.ts

export function fmt(n: number | null | undefined, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return n.toFixed(digits);
}

// สร้างช่วงเดือนเป็น YYYY-MM-01..YYYY-MM-last แบบ ISO
export function monthRangeISO(year: number, month1to12: number) {
  const start = new Date(Date.UTC(year, month1to12 - 1, 1, 0, 0, 0));
  const end = new Date(Date.UTC(year, month1to12, 0, 23, 59, 59)); // day 0 => last day of prev month
  return { startISO: start.toISOString(), endISO: end.toISOString() };
}
