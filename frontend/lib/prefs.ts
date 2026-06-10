// UI 偏好持久化(localStorage):指标开关、周期、视图模式等"上次怎么用,这次还怎么用"。
// 静态导出安全:首帧用默认值渲染,挂载后恢复存档(与全站 watchlist/alerts 同一模式)。
import { useEffect, useState } from "react";

const PREFIX = "pref:";

export function loadPref<T>(key: string, def: T): T {
  if (typeof window === "undefined") return def;
  try {
    const s = localStorage.getItem(PREFIX + key);
    if (s == null) return def;
    const v = JSON.parse(s);
    // 对象偏好与默认值浅合并:新版本加的开关在老存档上也能拿到默认值
    if (v && typeof v === "object" && !Array.isArray(v) && def && typeof def === "object" && !Array.isArray(def)) {
      return { ...(def as object), ...(v as object) } as T;
    }
    return v as T;
  } catch {
    return def;
  }
}

export function savePref(key: string, v: unknown): void {
  if (typeof window === "undefined") return;
  try { localStorage.setItem(PREFIX + key, JSON.stringify(v)); } catch { /* 配额满忽略 */ }
}

/** useState + localStorage:变更即持久化,刷新/下次进入自动恢复。 */
export function usePref<T>(key: string, def: T): [T, (v: T | ((p: T) => T)) => void] {
  const [val, setVal] = useState<T>(def);
  useEffect(() => {
    setVal(loadPref(key, def));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  const set = (v: T | ((p: T) => T)) => {
    setVal((prev) => {
      const next = typeof v === "function" ? (v as (p: T) => T)(prev) : v;
      savePref(key, next);
      return next;
    });
  };
  return [val, set];
}
