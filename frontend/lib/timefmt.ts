// 全站统一时间格式化:交易者可选时区(默认美东 ET,可切 北京/本地/UTC),
// 所有时间戳必须带时区标签 —— 不再出现裸 toLocaleTimeString()。
"use client";
import { useEffect, useState } from "react";

export type TzKey = "ET" | "CN" | "LOCAL" | "UTC";
const KEY = "ui:tz:v1";

export const TZ_OPTIONS: { key: TzKey; label: string; tz?: string }[] = [
  { key: "ET", label: "美东 ET", tz: "America/New_York" },
  { key: "CN", label: "北京", tz: "Asia/Shanghai" },
  { key: "LOCAL", label: "本地" },
  { key: "UTC", label: "UTC", tz: "UTC" },
];

export function getTz(): TzKey {
  if (typeof window === "undefined") return "ET";
  const v = localStorage.getItem(KEY);
  return (v === "ET" || v === "CN" || v === "LOCAL" || v === "UTC") ? v : "ET";
}

export function setTz(k: TzKey): void {
  try { localStorage.setItem(KEY, k); } catch { /* ignore */ }
  window.dispatchEvent(new Event("tz-changed"));
}

/** React hook:时区变化自动重渲染。 */
export function useTz(): TzKey {
  const [tz, set] = useState<TzKey>("ET");
  useEffect(() => {
    const sync = () => set(getTz());
    sync();
    window.addEventListener("tz-changed", sync);
    return () => window.removeEventListener("tz-changed", sync);
  }, []);
  return tz;
}

function opt(k: TzKey) { return TZ_OPTIONS.find((o) => o.key === k)!; }

function fmt(d: Date, k: TzKey, withDate: boolean, withSec = false): string {
  const o = opt(k);
  const s = new Intl.DateTimeFormat("zh-CN", {
    timeZone: o.tz,
    ...(withDate ? { month: "2-digit", day: "2-digit" } : {}),
    hour: "2-digit", minute: "2-digit", ...(withSec ? { second: "2-digit" } : {}),
    hour12: false,
  }).format(d);
  return `${s} ${o.label}`;
}

/** 时:分(+标签),如 "09:41 美东 ET"。 */
export function fmtTime(input: Date | string | number | null | undefined, k?: TzKey, withSec = false): string {
  if (input == null) return "—";
  const d = new Date(input);
  if (!isFinite(d.getTime())) return "—";
  return fmt(d, k ?? getTz(), false, withSec);
}

/** 月-日 时:分(+标签)。 */
export function fmtDateTime(input: Date | string | number | null | undefined, k?: TzKey): string {
  if (input == null) return "—";
  const d = new Date(input);
  if (!isFinite(d.getTime())) return "—";
  return fmt(d, k ?? getTz(), true);
}
