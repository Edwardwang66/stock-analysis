"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Chart from "@/components/Chart";
import AINote from "@/components/AINote";
import ChanPanel from "@/components/ChanPanel";
import News from "@/components/News";
import MoneyFlow from "@/components/MoneyFlow";
import Chips from "@/components/Chips";
import Fundamentals from "@/components/Fundamentals";
import StatBar from "@/components/StatBar";
import SymbolSwitcher from "@/components/SymbolSwitcher";
import OrderBookPanel from "@/components/OrderBookPanel";
import type { MyLine } from "@/components/Chart";
import { addAlert, getAlerts, removeAlert, updateAlertTarget, type PriceAlert } from "@/lib/alerts";
import { getHoldings, type Holding } from "@/lib/portfolio";
import { subscribeCryptoLive } from "@/lib/livePrice";
import { getExtendedQuote, getOHLCV, getQuote, type Bar, type ExtendedQuote, type Quote } from "@/lib/datasource";
import { analyze, type Analysis } from "@/lib/analysis";
import { pivotPoints, prevWeekHLC } from "@/lib/indicators";
import { useMemo } from "react";
import { computeChan } from "@/lib/chan";
import { LOCAL_SYMBOLS, nameOf } from "@/lib/markets";
import { useLang } from "@/lib/names";
import { useNightQuotes } from "@/lib/nightquotes";
import { marketStatus as mktStatus } from "@/lib/marketstatus";
import { inWatchlist, toggleWatchlist } from "@/lib/watchlist";
import { usePref } from "@/lib/prefs";

const RANGES = ["6mo", "1y", "2y", "5y"];
const INTERVALS = [{ k: "1d", label: "日线" }, { k: "1wk", label: "周线" }, { k: "1h", label: "小时" }];

// 次级模块(Hyperliquid 式:图表占 C 位,分析模块收进 tabs;研报模式可全展开)
type ModKey = "ta" | "chan" | "flow" | "fund" | "news" | "ai";
const MODULES: { key: ModKey; label: string }[] = [
  { key: "ta", label: "技术分析" },
  { key: "chan", label: "缠论" },
  { key: "flow", label: "资金·筹码" },
  { key: "fund", label: "基本面" },
  { key: "news", label: "新闻" },
  { key: "ai", label: "AI 解读" },
];

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
  const lang = useLang();
  const night = useNightQuotes();
  const params = useSearchParams();
  const symbol = (params.get("s") || "US:AAPL").toUpperCase();
  // 周期/范围/视图模式持久化:上次怎么看,这次还怎么看(Hyperliquid 式偏好记忆)
  const [range, setRange] = usePref("symbol:range", "2y");
  const [interval, setInterval] = usePref("symbol:interval", "1d");
  const [view, setView] = usePref<"tabs" | "report">("symbol:view", "tabs");
  const [tabPref, setTabPref] = usePref<ModKey>("symbol:tab", "ta");
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

  // 本标的持仓(画成本线用),跟随组合页变更实时同步
  const [holdings, setHoldings] = useState<Holding[]>([]);
  useEffect(() => {
    const sync = () => setHoldings(getHoldings().filter((h) => h.symbol === symbol));
    sync();
    window.addEventListener("portfolio-changed", sync);
    return () => window.removeEventListener("portfolio-changed", sync);
  }, [symbol]);

  // 美股盘前/盘后报价(扩展时段才显示;30s 一刷,常规时段自动隐藏)
  const [ext, setExt] = useState<ExtendedQuote | null>(null);
  useEffect(() => {
    if (!symbol.startsWith("US:")) { setExt(null); return; }
    let alive = true;
    const load = () => getExtendedQuote(symbol)
      .then((e) => { if (alive) setExt(e); })
      .catch(() => { if (alive) setExt(null); });
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 30_000);
    return () => { alive = false; window.clearInterval(id); };
  }, [symbol]);

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

  // "我的"信息上图:持仓成本线(实线) + 未触发提醒线(虚线,可拖拽改价)
  const myLines = useMemo<MyLine[]>(() => {
    const out: MyLine[] = [];
    const qty = holdings.reduce((s, h) => s + h.qty, 0);
    if (qty > 0) {
      const cost = holdings.reduce((s, h) => s + h.qty * h.cost, 0) / qty;
      out.push({ id: "cost", price: cost, title: `持仓成本(${qty})`, color: "#f7b500" });
    }
    for (const a of alerts) {
      if (a.triggeredAt) continue;
      out.push({ id: `alert:${a.id}`, price: a.target, title: a.dir === "above" ? "提醒≥" : "提醒≤", color: "#4c8dff", draggable: true });
    }
    return out;
  }, [holdings, alerts]);

  const onLineDrag = (id: string, price: number) => {
    if (!id.startsWith("alert:")) return;
    updateAlertTarget(id.slice(6), Number(price.toFixed(price < 10 ? 4 : 2)), quote?.price ?? null);
  };

  // 周 Pivot 支撑压力(日线才有意义;上一完整周 HLC)
  const pivotLevels = useMemo(() => {
    if (interval !== "1d" || bars.length < 10) return null;
    const w = prevWeekHLC(bars);
    if (!w) return null;
    const p = pivotPoints(w.H, w.L, w.C);
    return [
      { price: p.R2, label: "周R2", color: "#ef5350" },
      { price: p.R1, label: "周R1", color: "#ef9a9a" },
      { price: p.P, label: "周P", color: "#9aa0aa" },
      { price: p.S1, label: "周S1", color: "#80cbc4" },
      { price: p.S2, label: "周S2", color: "#26a69a" },
    ];
  }, [bars, interval]);

  const isIdx = symbol.startsWith("IDX:");
  // 指数无个股微观结构:资金/筹码、基本面不展示
  const visibleModules = MODULES.filter((m) => !(isIdx && (m.key === "flow" || m.key === "fund")));
  const tab = visibleModules.some((m) => m.key === tabPref) ? tabPref : "ta";

  // 各分析模块。工作台(tabs)模式按需渲染:切到哪个 tab 才挂载哪个(自带请求的模块切到才发请求);
  // 研报模式保留原长页体验,全部展开。
  const renderModule = (key: ModKey) => {
    switch (key) {
      case "ta":
        return !an ? <div className="section"><div className="loading">加载中…</div></div> : (
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
                <h2>52 周区间位置
                  <span className="badge" style={{ marginLeft: 10, fontSize: 12 }}>
                    距 52 周高 {(((quote.price / ind.high_52w) - 1) * 100).toFixed(1)}%
                    {quote.price / ind.high_52w >= 0.95 ? " · 接近新高(动量学术上偏强)" : ""}
                  </span>
                </h2>
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
        );
      case "chan":
        return (
          <>
            <ChanPanel bars={bars} />
            {bars.length >= 8 && (
              <div className="section">
                <h2>缠论结构(简化版,非 LLM)</h2>
                <p style={{ color: "var(--muted)", fontSize: 13 }}>{computeChan(bars).note}</p>
                <p className="src">在上方 K 线点击「缠论结构」可叠加显示 笔 / 分型 / 中枢。算法:包含处理 → 分型 → 笔 → 中枢。
                  灵感来自 <a href="https://guanchaotv.com/" target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>观潮 TideView</a>(独立简化实现)。</p>
              </div>
            )}
          </>
        );
      case "flow":
        return (
          <>
            <MoneyFlow symbol={symbol} />
            {!loading && bars.length > 10 && <Chips bars={bars} price={quote?.price ?? an?.price ?? null} />}
          </>
        );
      case "fund":
        return <Fundamentals symbol={symbol} />;
      case "news":
        return <News symbol={symbol} />;
      case "ai":
        return <AINote symbol={symbol} />;
    }
  };

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <SymbolSwitcher symbol={symbol} />
        <span className="muted">{symbol}</span>
        <button className="btn" style={{ background: starred ? "var(--accent)" : "transparent", border: "1px solid var(--border)" }}
          onClick={() => { toggleWatchlist(symbol); setStarred(inWatchlist(symbol)); }}>
          {starred ? "★ 已自选" : "☆ 加入自选"}
        </button>
      </div>

      {/* Hyperliquid 式一行统计条:现价/涨跌/高低/昨收/量/52周/盘前盘后/夜盘 */}
      <StatBar
        symbol={symbol} quote={quote} ext={ext}
        night={(() => {
          const nq = night.map[symbol];
          return nq && !mktStatus(symbol.split(":")[0]).open ? nq : null;
        })()}
        volume={interval === "1d" && bars.length ? bars[bars.length - 1].volume : null}
        high52={ind.high_52w ?? null} low52={ind.low_52w ?? null}
      />

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
          <div className="chart-row">
            <div className="chart-main">
              <Chart bars={bars} levels={pivotLevels}
                myLines={myLines} onLineDrag={onLineDrag}
                compare={compareBars.length ? { name: nameOf(compareSym, lang), bars: compareBars } : null} />
            </div>
            {/* 盘口:仅加密有真实 L2(Binance WS);股票免费源无深度,不做估算冒充 */}
            <OrderBookPanel symbol={symbol} />
          </div>
        )}
      </div>

      {/* 模块区:工作台模式(tabs,按需加载,图表保持 C 位) / 研报模式(传统长页全展开) */}
      <div className="tabs" style={{ marginTop: 18 }}>
        {view === "tabs"
          ? visibleModules.map((m) => (
              <button key={m.key} className={m.key === tab ? "active" : ""} onClick={() => setTabPref(m.key)}>{m.label}</button>
            ))
          : <span className="muted" style={{ fontSize: 13, alignSelf: "center" }}>研报模式:全部模块展开</span>}
        <button className="linklike" style={{ marginLeft: "auto" }}
          onClick={() => setView(view === "tabs" ? "report" : "tabs")}
          title={view === "tabs" ? "切到传统长页:全部模块一次展开,适合通读" : "切回工作台:模块收进标签页,按需加载"}>
          {view === "tabs" ? "☰ 研报模式" : "▦ 工作台模式"}
        </button>
      </div>
      {view === "tabs"
        ? renderModule(tab)
        : visibleModules.map((m) => <div key={m.key}>{renderModule(m.key)}</div>)}

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
