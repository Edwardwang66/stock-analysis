"use client";
// 前端错误自采集:window.onerror / unhandledrejection → localStorage 环形日志(最近 50 条)。
// /sources 页可查看;用户报障时不再凭记忆描述。零外发,数据只在本机。
import { useEffect } from "react";

const KEY = "err:log:v1";
const MAX = 50;

export function readErrors(): { at: string; msg: string; src?: string }[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
export function clearErrors(): void {
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
}

function push(msg: string, src?: string) {
  try {
    const list = readErrors();
    list.push({ at: new Date().toISOString(), msg: msg.slice(0, 300), src });
    localStorage.setItem(KEY, JSON.stringify(list.slice(-MAX)));
  } catch { /* ignore */ }
}

export default function ErrorCollector() {
  useEffect(() => {
    const onErr = (e: ErrorEvent) => push(e.message || "unknown error", `${e.filename}:${e.lineno}`);
    const onRej = (e: PromiseRejectionEvent) => push(`unhandledrejection: ${String(e.reason).slice(0, 200)}`);
    window.addEventListener("error", onErr);
    window.addEventListener("unhandledrejection", onRej);
    return () => {
      window.removeEventListener("error", onErr);
      window.removeEventListener("unhandledrejection", onRej);
    };
  }, []);
  return null;
}
