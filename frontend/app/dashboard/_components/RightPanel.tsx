// app/dashboard/_components/RightPanel.tsx
"use client";

import { useMemo, useState } from "react";
import SectionHeader from "./SectionHeader";
import { useCost } from "@/hooks/useCost";
import { useSuggestion } from "@/hooks/useSuggestion";
import { fmt } from "@/lib/format";

function nowYearMonth() {
  const d = new Date();
  return { y: d.getFullYear(), m: d.getMonth() + 1 };
}

export default function RightPanel({ plantId }: { plantId: string }) {
  const init = useMemo(() => nowYearMonth(), []);
  const [year, setYear] = useState(init.y);
  const [month, setMonth] = useState(init.m);

  const cost = useCost(plantId, year, month);
  const sug = useSuggestion(plantId);

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
      <SectionHeader title="Cost & Suggestion" />

      {/* Cost controls */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
        <input
          type="number"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          style={{ width: 90, padding: 8, borderRadius: 10 }}
        />
        <input
          type="number"
          min={1}
          max={12}
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          style={{ width: 70, padding: 8, borderRadius: 10 }}
        />
        <span style={{ color: "#666", fontSize: 13 }}>YYYY / MM</span>
      </div>

      {/* Cost summary */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>Cost Summary</div>
        {cost.loading && <div>Loading cost...</div>}
        {cost.error && <div style={{ color: "#ef4444" }}>{cost.error}</div>}

        {cost.data?.ok ? (
          <div style={{ display: "grid", gap: 6 }}>
            <div>
              <b>Energy:</b> {fmt(cost.data.kwh ?? null, 1)} kWh
            </div>
            <div>
              <b>Cost:</b> {fmt(cost.data.thb ?? null, 0)} THB
            </div>
            <div style={{ color: "#666", fontSize: 13 }}>
              Peak: {fmt(cost.data.peak_kwh ?? null, 1)} kWh / {fmt(cost.data.peak_thb ?? null, 0)} THB
            </div>
          </div>
        ) : (
          !cost.loading && <div style={{ color: "#666" }}>No cost data.</div>
        )}
      </div>

      {/* Suggestion */}
      <div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{ fontWeight: 600 }}>Recommendation</div>
          <button
            onClick={sug.reload}
            style={{ marginLeft: "auto", padding: "6px 10px", borderRadius: 10 }}
          >
            Refresh
          </button>
        </div>

        {sug.loading && <div style={{ marginTop: 8 }}>Loading suggestion...</div>}
        {sug.error && <div style={{ marginTop: 8, color: "#ef4444" }}>{sug.error}</div>}

        {sug.data?.ok ? (
          <div style={{ marginTop: 8 }}>
            <div style={{ whiteSpace: "pre-wrap" }}>
              {sug.data.suggestion ?? "-"}
            </div>
            {sug.data.reason && (
              <div style={{ marginTop: 8, color: "#666", fontSize: 13 }}>
                Reason: {sug.data.reason}
              </div>
            )}
          </div>
        ) : (
          !sug.loading && <div style={{ marginTop: 8, color: "#666" }}>No suggestion.</div>
        )}
      </div>
    </div>
  );
}
