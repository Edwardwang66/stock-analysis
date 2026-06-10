"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Chart from "@/components/Chart";
import AINote from "@/components/AINote";
import News from "@/components/News";
import MoneyFlow from "@/components/MoneyFlow";
import Chips from "@/components/Chips";
import Fundamentals from "@/components/Fundamentals";
import { addAlert, getAlerts, removeAlert, type PriceAlert } from "@/lib/alerts";
import { subscribeCryptoLive } from "@/lib/livePrice";
import { getOHLCV, getQuote, type Bar, type Quote } from "@/lib/datasource";
import { analyze, type Analysis } from "@/lib/analysis";
import { computeChan } from "@/lib/chan";
import { LOCAL_SYMBOLS, nameOf } from "@/lib/markets";
import { inWatchlist, toggleWatchlist } from "@/lib/watchlist";

const RANGES = ["6mo", "1y", "2y", "5y"];
const INTERVALS = [{ k: "1d", label: "日线" }, { k: "1wk", label: "周线" }, { k: "1h", label: "小时" }];

function fmt(n: number | null | undefined, d = 2): string {
  return n == null ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: d });
}

function exportCSV(symbol: string, range: string, interval: string, bars: Bar[]) {
  const head = "time,open,high,low,close,volume";
  const lines = bars.map((b) =>
    `${new Date(b.time * 1000).toISOString()},${b.open},${b.high},${b.low},${b.close},${b.volume}`);
  const blob = new Blob(["﻿" + [head, ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${symbol.replace(/[:^.]/g, "_")}_${range}_${interval}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function SymbolView() {
  const params = useSearchParams();
  const symbol = (params.get("s") || "US:AAPL").toUpperCase();
  const [range, setRange] = useState("2y");
  const [interval, setInterval] = useState("1d");
  const [bars, setBars] = useState<Bar[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [an, setAn] = useState<Analysis | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [starred, setStarred] = useState(false);
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [alertInput, setAlertInput] = useState("");
  const [compareSym, setCompareSym] = useState("");
  const [compareBars, setCompareBars] = useState<Bar[]>([]);
  const [compareErr, setCompareErr] = useState("");

  // 对比标的 K线:同 range/interval 拉取(走统一缓存层)
  useEffect(() => {
    if (!compareSym) { setCompareBars([]); setCompareErr(""); return; }
    let alive = true;
    setCompareErr("");
    getOHLCV(compareSym, range, interval)
      .then((b) => { if (alive) setCompareBars(b); })
      .catch((e: any) => { if (alive) { setCompareBars([]); setCompareErr(e?.message || "对比标的加载失败"); } });
    return () => { alive = false; };
  }, [compareSym, range, interval]);

  useEffect(() => {
    const sync = () => setAlerts(getAlerts(symbol));
    sync();
    window.addEventListener("alerts-changed", sync);
    return () => window.removeEventListener("alerts-changed", sync);
  }, [symbol]);

  useEffect(() => { setStarred(inWatchlist(symbol)); }, [symbol]);

  // 末根 bar 跟价(日/周线):价格、K线、指标保持同源
  const patchLastBar = (price: number) => {
    setBars((prev) => {
      if (!prev.length) return prev;
      const last = prev[prev.length - 1];
      if (last.close === price) return prev;
      const next = [...prev];
      next[next.length - 1] = {
        ...last, close: price,
        high: Math.max(last.high, price), low: Math.min(last.low, price),
      };
      return next;
    });
  };

  // 实时价:加密走 Binance WebSocket(~1s 推送,零轮询延迟);股票 5s 短轮询
  //(免费股票源本身有交易所级延迟,这是免费数据的物理上限,UI 如实标注)
  useEffect(() => {
    if (symbol.startsWith("CRYPTO:")) {
      return subscribeCryptoLive([symbol], (q) => {
        setQuote(q);
        if (q.price != null && (interval === "1d" || interval === "1wk")) patchLastBar(q.price);
      });
    }
    const id = window.setInterval(async () => {
      if (document.hidden) return;
      try {
        const q = await getQuote(symbol);
        setQuote(q);
        if (q?.price != null && (interval === "1d" || interval === "1wk")) patchLastBar(q.price);
      } catch { /* 单次失败忽略,下一轮再试 */ }
    }, 5_000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval]);

  // 动态页标题:股票名 + 实时价(标签页可当迷你行情看)
  useEffect(() => {
    const base = `${nameOf(symbol)} ${symbol}`;
    document.title = quote?.price != null
      ? `${quote.price.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${quote.changePct != null ? `${quote.changePct >= 0 ? "+" : ""}${quote.changePct.toFixed(2)}%` : ""} · ${base}`
      : `${base} · 多市场股票数据看板`;
    return () => { document.title = "多市场股票数据看板"; };
  }, [symbol, quote]);

  useEffect(() => {
    let alive = true;
    setLoading(true); setErr("");
    (async () => {
      try {
        const [b, q] = await Promise.all([getOHLCV(symbol, range, interval), getQuote(symbol)]);
        if (!alive) return;
        // 日/周线:用实时报价修正最后一根 bar,保证页头价格、K线末根与指标同源一致
        if (b.length && q?.price != null && (interval === "1d" || interval === "1wk")) {
          const last = b[b.length - 1];
          b[b.length - 1] = {
            ...last, close: q.price,
            high: Math.max(last.high, q.price), low: Math.min(last.low, q.price),
          };
        }
        setBars(b); setQuote(q); setAn(analyze(b)); setLoading(false);
      } catch (e: any) {
        if (alive) { setErr(e?.message || "加载失败"); setLoading(false); }
      }
    })();
    return () => { alive = false; };
  }, [symbol, range, interval]);

  const dir = quote && quote.changePct != null ? (quote.changePct >= 0 ? "up" : "down") : "muted";
  const ind = an?.indicators ?? {};

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <h1>{nameOf(symbol)}</h1>
        <span className="muted">{symbol}</span>
        <button className="btn" style={{ background: starred ? "var(--accent)" : "transparent", border: "1px solid var(--border)" }}
          onClick={() => { toggleWatchlist(symbol); setStarred(inWatchlist(symbol)); }}>
          {starred ? "★ 已自选" : "☆ 加入自选"}
        </button>
        {quote && (
          <>
            <span className={`price ${dir}`} style={{ fontSize: 22 }}>{fmt(quote.price)}</span>
            <span className={dir}>
              {quote.change != null ? `${quote.change >= 0 ? "+" : ""}${fmt(quote.change)} ` : ""}
              {quote.changePct != null ? `${quote.changePct >= 0 ? "+" : ""}${quote.changePct.toFixed(2)}%` : ""}
            </span>
            <span className="muted" style={{ fontSize: 13 }}>
              {symbol.startsWith("CRYPTO:") ? "24h" : "今日"} 最高 {fmt(quote.high)} · 最低 {fmt(quote.low)}
              {!symbol.startsWith("CRYPTO:") && quote.change != null && quote.price != null && ` · 昨收 ${fmt(quote.price - quote.change)}`}
            </span>
            <span className="muted">{quote.currency} · 来源 {quote.source}</span>
          </>
        )}
      </div>

      {err && <div className="err">加载失败:{err}(后端首次访问可能在唤醒,约 30 秒;请稍候刷新重试)</div>}

      {/* 价格提醒:纯前端 localStorage,首页 30s 刷新循环检查,触发浏览器通知+横幅 */}
      <div className="alert-bar">
        <span className="src">⏰ 价格提醒</span>
        <input
          type="number" inputMode="decimal" placeholder={quote?.price != null ? `目标价(现 ${fmt(quote.price)})` : "目标价"}
          value={alertInput} onChange={(e) => setAlertInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && Number(alertInput) > 0) { addAlert(symbol, Number(alertInput), quote?.price ?? null); setAlertInput(""); }
          }}
        />
        <button className="btn subtle" disabled={!(Number(alertInput) > 0)}
          onClick={() => { addAlert(symbol, Number(alertInput), quote?.price ?? null); setAlertInput(""); }}>设置</button>
        {alerts.map((a) => (
          <span key={a.id} className={`badge ${a.triggeredAt ? "muted" : a.dir === "above" ? "up" : "down"}`}>
            {a.dir === "above" ? "≥" : "≤"} {a.target}{a.triggeredAt ? "(已触发)" : ""}
            <button className="x" onClick={() => removeAlert(a.id)} aria-label="删除提醒">✕</button>
          </span>
        ))}
        {alerts.length === 0 && <span className="src">高于/低于目标价时通知(看板页打开时检查,约 30s 一轮)</span>}
      </div>

      <div className="section">
        <div className="ranges">
          {INTERVALS.map((it) => (
            <button key={it.k} className={it.k === interval ? "active" : ""} onClick={() => setInterval(it.k)}>{it.label}</button>
          ))}
          <span style={{ width: 12 }} />
          {RANGES.map((r) => (
            <button key={r} className={r === range ? "active" : ""} onClick={() => setRange(r)}>{r}</button>
          ))}
          <span style={{ width: 12 }} />
          <input
            list="compare-list" placeholder="对比标的(如 US:MSFT)" value={compareSym}
            onChange={(e) => setCompareSym(e.target.value.trim().toUpperCase())}
            style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)",
                     borderRadius: 6, padding: "4px 10px", fontSize: 12, width: 180 }}
          />
          <datalist id="compare-list">
            {LOCAL_SYMBOLS.filter((s) => s.symbol !== symbol).map((s) => (
              <option key={s.symbol} value={s.symbol}>{s.name}</option>
            ))}
          </datalist>
          {compareSym && <button onClick={() => setCompareSym("")}>✕ 取消对比</button>}
          <button style={{ marginLeft: "auto" }} disabled={!bars.length}
            onClick={() => exportCSV(symbol, range, interval, bars)} title="导出当前K线为 CSV">⬇ CSV</button>
        </div>
        {compareErr && <p className="src" style={{ color: "var(--down)" }}>{compareErr}</p>}
        {loading ? <div className="loading">加载中…</div> : (
          <Chart bars={bars} compare={compareBars.length ? { name: nameOf(compareSym), bars: compareBars } : null} />
        )}
      </div>

      {/* 每日 AI 解读(外部 OpenClaw 投递,无数据自隐藏) */}
      <AINote symbol={symbol} />

      {/* 相关新闻(Yahoo RSS,失败自隐藏) */}
      <News symbol={symbol} />

      {/* 富途式看板:主力资金 + 筹码分布 + 基本面(指数无个股微观结构,不展示) */}
      {!symbol.startsWith("IDX:") && (
        <>
          <MoneyFlow symbol={symbol} />
          {!loading && bars.length > 10 && <Chips bars={bars} price={quote?.price ?? an?.price ?? null} />}
          <Fundamentals symbol={symbol} />
        </>
      )}

      {an && (
        <>
          <div className="section">
            <h2>技术分析结论(规则化,非 LLM)</h2>
            <p><span className="badge" style={{ fontSize: 14 }}>{an.verdict}</span> <span className="muted">评分 {an.score} / [-100, 100]</span></p>
            <p style={{ color: "var(--muted)", fontSize: 13 }}>{an.summary}</p>
            <div className="signal-list">
              {an.signals.map((s, i) => (
                <div className="signal" key={i}>
                  <span>{s.name}</span>
                  <span><span className="badge">{s.verdict}</span> <span className="muted" style={{ fontSize: 12 }}>{s.detail}</span></span>
                </div>
              ))}
            </div>
          </div>

          {ind.high_52w != null && ind.low_52w != null && quote?.price != null && (
            <div className="section">
              <h2>52 周区间位置</h2>
              <div className="range52">
                <div className="range52-fill" style={{
                  width: `${Math.max(0, Math.min(100, ((quote.price - ind.low_52w) / (ind.high_52w - ind.low_52w)) * 100))}%`,
                }} />
              </div>
              <div className="range52-labels">
                <span>低 {fmt(ind.low_52w)}</span>
                <span className="muted">当前 {fmt(quote.price)}</span>
                <span>高 {fmt(ind.high_52w)}</span>
              </div>
            </div>
          )}

          {bars.length >= 8 && (
            <div className="section">
              <h2>缠论结构(简化版,非 LLM)</h2>
              <p style={{ color: "var(--muted)", fontSize: 13 }}>{computeChan(bars).note}</p>
              <p className="src">在上方 K 线点击「缠论结构」可叠加显示 笔 / 分型 / 中枢。算法:包含处理 → 分型 → 笔 → 中枢。
                灵感来自 <a href="https://guanchaotv.com/" target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>观潮 TideView</a>(独立简化实现)。</p>
            </div>
          )}

          <div className="section">
            <h2>关键指标</h2>
            <table>
              <tbody>
                <tr><th>MA50</th><td>{fmt(ind.sma50)}</td><th>MA200</th><td>{fmt(ind.sma200)}</td></tr>
                <tr><th>RSI(14)</th><td>{fmt(ind.rsi14, 1)}</td><th>MACD</th><td>{fmt(ind.macd, 3)}</td></tr>
                <tr><th>布林上轨</th><td>{fmt(ind.bb_upper)}</td><th>布林下轨</th><td>{fmt(ind.bb_lower)}</td></tr>
                <tr><th>近1月%</th><td>{fmt(ind.return_1m_pct)}</td><th>近3月%</th><td>{fmt(ind.return_3m_pct)}</td></tr>
                <tr><th>52周高</th><td>{fmt(ind.high_52w)}</td><th>52周低</th><td>{fmt(ind.low_52w)}</td></tr>
                <tr><th>ATR(14)</th><td>{fmt(ind.atr14)}</td><th>量比(20)</th><td>{ind.vol_ratio == null ? "—" : `${ind.vol_ratio.toFixed(2)}×${ind.vol_ratio >= 1.5 ? " 放量" : ind.vol_ratio <= 0.6 ? " 缩量" : ""}`}</td></tr>
                <tr><th>KDJ·K/D</th><td>{fmt(ind.kdj_k, 1)} / {fmt(ind.kdj_d, 1)}</td><th>KDJ·J</th><td>{ind.kdj_j == null ? "—" : `${ind.kdj_j.toFixed(1)}${ind.kdj_j >= 100 ? " 超买" : ind.kdj_j <= 0 ? " 超卖" : ""}`}</td></tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="disclaimer">本页分析为规则化技术指标,<strong>仅供信息参考,不构成投资建议</strong>(Not financial advice)。</div>
    </div>
  );
}

export default function SymbolPage() {
  return (
    <Suspense fallback={<div className="container"><div className="loading">加载中…</div></div>}>
      <SymbolView />
    </Suspense>
  );
}
