"use client";
// 📜 报告中心:OpenClaw 四类报告(盘前/盘中滚动/收盘前/收盘后汇总)站内阅读。
// 数据 = feed/screener/analysis-*.md(raw GitHub 即时可见);最近 N 个交易日探测存在性。
import Link from "next/link";
import { useEffect, useState } from "react";
import { getAnalysisMd } from "@/lib/feed";
import LangSelect from "@/components/LangSelect";

const KINDS = [
  { k: "premarket" as const, label: "盘前", icon: "🌅" },
  { k: "intraday" as const, label: "盘中滚动", icon: "⚡" },
  { k: "close" as const, label: "收盘前", icon: "🔔" },
  { k: "" as const, label: "收盘后汇总", icon: "📋" },
];

function lastTradingDays(n: number): string[] {
  const out: string[] = [];
  const d = new Date();
  while (out.length < n) {
    const dow = d.getUTCDay();
    if (dow >= 1 && dow <= 5) out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() - 1);
  }
  return out;
}

interface Item { date: string; kind: typeof KINDS[number]["k"]; label: string; icon: string; text: string }

export default function ReportsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      const days = lastTradingDays(5);
      const found: Item[] = [];
      // 逐日逐类探测(串行按天、并行按类,控请求峰值)
      for (const date of days) {
        const r = await Promise.all(KINDS.map(async (kk) => {
          const text = await getAnalysisMd(kk.k, date);
          return text ? { date, kind: kk.k, label: kk.label, icon: kk.icon, text } : null;
        }));
        for (const x of r) if (x) found.push(x);
        if (!alive) return;
        setItems([...found]);
      }
      setLoading(false);
    })();
    return () => { alive = false; };
  }, []);

  const todayKey = new Date().toISOString().slice(0, 10);

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <h1>📜 报告中心</h1>
        <span className="tag">OpenClaw 四类报告 · 最近 5 个交易日 · 即投即读(raw 直连)</span>
        <span style={{ marginLeft: "auto" }} />
        <LangSelect />
      </div>

      {loading && items.length === 0 && <div className="loading">扫描报告中…</div>}
      {!loading && items.length === 0 && (
        <div className="hint">最近 5 个交易日没有任何报告投递。盘前(13:30 UTC)/收盘前(19:30 UTC)/收盘后由 OpenClaw 按 playbook 投递,缺投会被看门狗开 Issue 点名。</div>
      )}

      {Array.from(new Set(items.map((i) => i.date))).map((date) => (
        <div className="section" key={date}>
          <h2>{date}{date === todayKey && <span className="badge" style={{ marginLeft: 8, fontSize: 11 }}>今天</span>}
            <span className="src" style={{ marginLeft: 10 }}>
              {KINDS.map((kk) => {
                const has = items.some((i) => i.date === date && i.kind === kk.k);
                return <span key={kk.k} style={{ marginRight: 10, opacity: has ? 1 : 0.4 }}>{kk.icon} {kk.label} {has ? "✅" : "—"}</span>;
              })}
            </span>
          </h2>
          {items.filter((i) => i.date === date).map((i) => {
            const id = `${i.date}-${i.kind}`;
            const isOpen = open === id;
            return (
              <div key={id} style={{ marginBottom: 8 }}>
                <button className="linklike" style={{ fontSize: 13 }} onClick={() => setOpen(isOpen ? null : id)}>
                  {isOpen ? "▼" : "▶"} {i.icon} {i.label}
                  <span className="src" style={{ marginLeft: 8 }}>{i.text.length.toLocaleString()} 字符 · {i.text.split("\n").filter(Boolean).length} 行</span>
                </button>
                {isOpen && (
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.75, color: "var(--text)",
                                background: "var(--bg)", borderRadius: 8, padding: 14, marginTop: 6, maxHeight: 560, overflow: "auto" }}>
                    {i.text.trim()}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      ))}

      <div className="disclaimer">报告由 OpenClaw(Winter)按 playbook 投递,机器盘中流见 /desk;均为信息整理,<strong>非投资建议</strong>。</div>
    </div>
  );
}
