"use client";
import { setTz, TZ_OPTIONS, useTz } from "@/lib/timefmt";

/** 全局时区切换器(默认美东 ET;选择持久化,全站时间戳即时联动)。 */
export default function TzSelect() {
  const tz = useTz();
  return (
    <select
      value={tz}
      onChange={(e) => setTz(e.target.value as any)}
      title="所有时间戳的显示时区"
      style={{ background: "var(--panel)", color: "var(--muted)", border: "1px solid var(--border)",
               borderRadius: 8, padding: "6px 8px", fontSize: 12 }}
    >
      {TZ_OPTIONS.map((o) => <option key={o.key} value={o.key}>🕐 {o.label}</option>)}
    </select>
  );
}
