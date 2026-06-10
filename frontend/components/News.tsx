"use client";
import { useEffect, useState } from "react";
import { getNews, timeAgo, type NewsItem } from "@/lib/news";

// 个股新闻(Yahoo RSS,免费无 key)。拉取失败/为空时整个模块静默隐藏,不产生占位噪音。
export default function News({ symbol }: { symbol: string }) {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [state, setState] = useState<"load" | "ok" | "none">("load");

  useEffect(() => {
    let alive = true;
    setState("load"); setItems([]);
    getNews(symbol, 6)
      .then((list) => { if (alive) { setItems(list); setState(list.length ? "ok" : "none"); } })
      .catch(() => { if (alive) setState("none"); });
    return () => { alive = false; };
  }, [symbol]);

  if (state === "none") return null;

  return (
    <div className="section">
      <h2>📰 相关新闻 <span className="badge" style={{ marginLeft: 8, fontSize: 11 }}>Yahoo RSS</span></h2>
      {state === "load" ? (
        <div className="loading">新闻加载中…</div>
      ) : (
        <div className="signal-list">
          {items.map((n, i) => (
            <a key={i} href={n.link} target="_blank" rel="noreferrer" className="signal" style={{ alignItems: "baseline", gap: 12 }}>
              <span style={{ fontSize: 13, lineHeight: 1.5 }}>{n.title}</span>
              <span className="src" style={{ whiteSpace: "nowrap" }}>{timeAgo(n.ts)}</span>
            </a>
          ))}
        </div>
      )}
      <p className="src" style={{ marginTop: 8 }}>新闻为英文源(Yahoo Finance),链接跳转外站;免费源仅供参考。</p>
    </div>
  );
}
