// app/dashboard/_components/CenterPanel.tsx
"use client";

import { useMemo, useState } from "react";
import SectionHeader from "./SectionHeader";
import { CHARTS, type ChartKey } from "@/lib/charts";
import { useChart } from "@/hooks/useChart";
import { AgCharts } from "ag-charts-react";
export default function CenterPanel({ plantId }: { plantId: string }) {
  const [chartKey, setChartKey] = useState<ChartKey>(CHARTS[0].key);
  const chart = useChart(plantId, chartKey);

  const title = useMemo(
    () => CHARTS.find((c) => c.key === chartKey)?.title ?? "",
    [chartKey]
  );

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <SectionHeader title={`Chart: ${title}`} />
        <select
          value={chartKey}
          onChange={(e) => setChartKey(e.target.value as ChartKey)}
          style={{ marginLeft: "auto", padding: 8, borderRadius: 10 }}
        >
          {CHARTS.map((c) => (
            <option key={c.key} value={c.key}>
              {c.title}
            </option>
          ))}
        </select>
      </div>

      {chart.loading && <div style={{ marginTop: 12 }}>Loading chart...</div>}
      {chart.error && <div style={{ marginTop: 12, color: "#ef4444" }}>{chart.error}</div>}

      <div style={{ marginTop: 12 }}>
        {chart.options ? (
          <AgCharts options={chart.options} />
        ) : (
          <div style={{ color: "#666" }}>No chart data.</div>
        )}
      </div>
    </div>
  );
}
