// app/dashboard/_components/SectionHeader.tsx
"use client";

export default function SectionHeader({ title }: { title: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
      <h3 style={{ margin: 0 }}>{title}</h3>
      <div style={{ flex: 1 }} />
    </div>
  );
}
