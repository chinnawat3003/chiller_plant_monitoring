// app/dashboard/_components/LeftPanel.tsx
"use client";

import SectionHeader from "./SectionHeader";
import { useSnapshots } from "@/hooks/useSnapshots";
import { fmt } from "@/lib/format";

export default function LeftPanel({ plantId }: { plantId: string }) {
  const snap = useSnapshots(plantId);

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
      <SectionHeader title="Snapshot" />

      {snap.loading && <div>Loading snapshot...</div>}
      {snap.error && <div style={{ color: "#ef4444" }}>{snap.error}</div>}

      <div style={{ display: "grid", gap: 8 }}>
        {/* ✅ ปรับ key ให้ตรงกับ backend ของคุณ */}
        <div>
          <b>CHW Temp:</b> {fmt(snap.map.get("chw_temp")?.value ?? null, 1)} °C
        </div>
        <div>
          <b>CHW Flow:</b> {fmt(snap.map.get("chw_flow")?.value ?? null, 1)} m³/h
        </div>
        <div>
          <b>Plant Power:</b> {fmt(snap.map.get("plant_kw")?.value ?? null, 1)} kW
        </div>
      </div>

      <button
        onClick={snap.reload}
        style={{ marginTop: 12, padding: "8px 10px", borderRadius: 10 }}
      >
        Reload
      </button>
    </div>
  );
}
