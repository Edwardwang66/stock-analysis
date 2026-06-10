"use client";
import { fmtTime, useNow, useTz } from "@/lib/timefmt";

/** 秒级走动的全局时钟(跟随所选时区)。 */
export default function LiveClock() {
  const now = useNow(1000);
  const tz = useTz();
  return (
    <span className="src" style={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
      {fmtTime(now, tz, true)}
    </span>
  );
}
