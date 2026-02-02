// app/dashboard/_components/StatusDot.tsx
"use client";

export default function StatusDot({ ok }: { ok: boolean | null }) {
  const color = ok === null ? "#999" : ok ? "#22c55e" : "#ef4444"; // gray/green/red
  return (
    <span
      style={{
        width: 10,
        height: 10,
        borderRadius: 999,
        display: "inline-block",
        background: color,
        marginRight: 8,
      }}
    />
  );
}
