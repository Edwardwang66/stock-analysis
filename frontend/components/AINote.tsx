"use client";
import { useEffect, useState } from "react";
import { getRepoWatchlist, getStockNote, type StockNote } from "@/lib/feed";

const STANCE: Record<string, string> = { "看多": "#26a69a", "看空": "#ef5350", "中性": "#f7b500" };

// 每日个股 AI 解读 —— 由外部 OpenClaw(stock-analyst 角色)产出,投递到 feed/stock-notes/。
// 没有解读时静默(只在有数据时显示),避免占位噪音;但本仓自带 AAPL 占位示例演示形态。
export default function AINote({ symbol }: { symbol: string }) {
  const [note, setNote] = useState<StockNote | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [inPool, setInPool] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoaded(false); setNote(null); setInPool(false);
    getStockNote(symbol).then((n) => { if (alive) { setNote(n); setLoaded(true); } });
    getRepoWatchlist().then((w) => { if (alive) setInPool((w?.symbols ?? []).includes(symbol)); }).catch(() => {});
    return () => { alive = false; };
  }, [symbol]);

  if (!loaded) return null;
  if (!note) {
    // 在云端分析池但当日还没投递 → 显示待投递占位(而不是看起来"没有这个功能")
    if (inPool) {
      return (
        <div className="section">
          <h2>🤖 AI 解读(OpenClaw)<span className="badge" style={{ marginLeft: 8, fontSize: 11 }}>排队中</span></h2>
          <p className="src">本标的已在云端分析池(feed/watchlist.json),等待 OpenClaw 当日投递
            (每交易日 16:30 美西全量覆盖;盘中异动会触发增量更新)。缺投会在日报 Issue 里被点名。</p>
        </div>
      );
    }
    return null; // 不在池内则不显示
  }

  return (
    <div className="section">
      <h2>
        🤖 AI 解读(OpenClaw){" "}
        <span className="badge" style={{ borderColor: STANCE[note.stance] || "var(--border)", color: STANCE[note.stance] || "var(--muted)", fontSize: 12 }}>
          {note.stance}
        </span>
        {note._placeholder && <span className="badge" style={{ marginLeft: 8, fontSize: 11 }}>占位示例</span>}
      </h2>
      <p style={{ fontSize: 14, lineHeight: 1.7 }}>{note.view}</p>
      <table>
        <tbody>
          {note.thesis && <tr><th style={{ width: 80 }}>多空逻辑</th><td>{note.thesis}</td></tr>}
          {note.earnings && <tr><th>财报要点</th><td>{note.earnings}</td></tr>}
          {note.news && <tr><th>新闻解读</th><td>{note.news}</td></tr>}
          {note.risks && <tr><th>风险点</th><td>{note.risks}</td></tr>}
        </tbody>
      </table>
      {note.sources && note.sources.length > 0 && (
        <p className="src" style={{ marginTop: 8 }}>
          来源:{note.sources.map((s, i) => (
            <span key={i}>{i > 0 && " · "}<a href={s.url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>{s.title}</a></span>
          ))}
        </p>
      )}
      <p className="src" style={{ marginTop: 8 }}>
        {note.date} · {note.model || "OpenClaw"} · 由外部 OpenClaw agent 产出 · <strong>非投资建议</strong>
      </p>
    </div>
  );
}
