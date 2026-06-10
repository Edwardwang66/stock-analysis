"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import QuoteCard from "@/components/QuoteCard";
import Heatmap from "@/components/Heatmap";
import SearchBox from "@/components/SearchBox";
import { checkAlerts, clearTriggered, notify, type PriceAlert } from "@/lib/alerts";
import { getAlerts } from "@/lib/alerts";
import { getCachedQuotesSync, getQuotes, HAS_BACKEND, type Quote } from "@/lib/datasource";
import { getIndex, getRepoWatchlist } from "@/lib/feed";
import { GROUP_ORDER, INDEX_SYMBOLS, MARKETS, MARKET_LABEL, marketOf, nameOf, symbolsForTab } from "@/lib/markets";
import { subscribeCryptoLive } from "@/lib/livePrice";
import { marketStatus } from "@/lib/marketstatus";
import { fngColor, getFearGreed, type FearGreed } from "@/lib/sentiment";
import { exportUserData, getWatchlist, importUserData } from "@/lib/watchlist";

type SortMode = "default" | "gainers" | "losers";
const LS_TAB = "ui:tab:v1";
const LS_SORT = "ui:sort:v1";

export default function Home() {
  // 默认「全部」:打开即并行加载所有市场(加密直连最快先上屏,股票渐进补齐)
  const [tab, setTab] = useState("ALL");
  const [watch, setWatch] = useState<string[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote | null>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadingQuotes, setLoadingQuotes] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshId, setRefreshId] = useState(0);
  const [sortMode, setSortMode] = useState<SortMode>("default");

  useEffect(() => {
    const sync = () => setWatch(getWatchlist());
    sync();
    window.addEventListener("watchlist-changed", sync);
    return () => window.removeEventListener("watchlist-changed", sync);
  }, []);

  // 云端跟踪池(feed/watchlist.json):OpenClaw 每日全覆盖分析的标的,自动并入自选区
  const [cloudWatch, setCloudWatch] = useState<string[]>([]);
  useEffect(() => {
    getRepoWatchlist().then((w) => setCloudWatch(w?.symbols ?? [])).catch(() => {});
  }, []);
  const watchAll = useMemo(
    () => Array.from(new Set([...cloudWatch, ...watch])),
    [cloudWatch, watch],
  );

  // 记住上次的 tab / 排序(挂载后恢复,避免 SSR 水合不一致)
  useEffect(() => {
    try {
      const t = localStorage.getItem(LS_TAB);
      if (t && MARKETS.some((m) => m.key === t)) setTab(t);
      const s = localStorage.getItem(LS_SORT);
      if (s === "default" || s === "gainers" || s === "losers") setSortMode(s);
    } catch { /* ignore */ }
  }, []);
  const pickTab = (t: string) => { setTab(t); try { localStorage.setItem(LS_TAB, t); } catch { /* ignore */ } };
  const pickSort = (s: SortMode) => { setSortMode(s); try { localStorage.setItem(LS_SORT, s); } catch { /* ignore */ } };

  // 加密恐惧贪婪指数(免费 CORS 源,失败静默)
  const [fng, setFng] = useState<FearGreed | null>(null);
  useEffect(() => { getFearGreed().then(setFng).catch(() => {}); }, []);

  // 价格提醒:随 30s 刷新循环检查(提醒标的不在当前视图也会被拉取,缓存命中近乎零成本)
  const [firedAlerts, setFiredAlerts] = useState<PriceAlert[]>([]);
  useEffect(() => {
    const syms = Array.from(new Set(getAlerts().filter((a) => !a.triggeredAt).map((a) => a.symbol)));
    if (!syms.length) return;
    let alive = true;
    getQuotes(syms).then((m) => {
      if (!alive) return;
      const prices = Object.fromEntries(Object.entries(m).map(([k, v]) => [k, v?.price]));
      const fired = checkAlerts(prices);
      if (fired.length) {
        setFiredAlerts((prev) => [...prev, ...fired]);
        notify(fired, nameOf);
      }
    }).catch(() => {});
    return () => { alive = false; };
  }, [refreshId]);

  // 情报 feed 新鲜度:陈旧时在首页轻提示(与情报看板同一判定)
  const [feedStale, setFeedStale] = useState<{ asof: string | null } | null>(null);
  useEffect(() => {
    let alive = true;
    getIndex().then((i) => {
      if (alive && i?.freshness?.stale) setFeedStale({ asof: i.freshness.market_data_asof });
    }).catch(() => {});
    return () => { alive = false; };
  }, []);

  // 指数概览:独立加载(不计入看板涨跌统计),60s 自刷新
  const [idxQuotes, setIdxQuotes] = useState<Record<string, Quote | null>>({});
  useEffect(() => {
    let alive = true;
    const cached = getCachedQuotesSync(INDEX_SYMBOLS);
    if (Object.keys(cached).length) setIdxQuotes((prev) => ({ ...cached, ...prev }));
    const load = () => getQuotes(INDEX_SYMBOLS, (q) => {
      if (alive) setIdxQuotes((prev) => ({ ...prev, [q.symbol]: q }));
    }).catch(() => {});
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 60_000);
    return () => { alive = false; window.clearInterval(id); };
  }, []);

  const baseSymbols = useMemo(() => symbolsForTab(tab), [tab]);
  // 页面上实际渲染的全集 = 自选(云端+本地)+ 当前 tab(看板统计也用同一个集合,保证一致)
  const allVisibleSymbols = useMemo(
    () => Array.from(new Set([...watchAll, ...baseSymbols])),
    [baseSymbols, watchAll],
  );

  useEffect(() => {
    if (!allVisibleSymbols.length) return;
    let alive = true;
    // 先用上次会话的缓存即时渲染(秒开),再后台拉新
    const cached = getCachedQuotesSync(allVisibleSymbols);
    if (Object.keys(cached).length) setQuotes((prev) => ({ ...cached, ...prev }));
    setLoadingQuotes(true);
    setErrors({});
    (async () => {
      try {
        // 渐进式:每到一个报价立即上屏,快源(加密/缓存)不等慢源(代理股票)
        const next = await getQuotes(allVisibleSymbols, (q) => {
          if (alive) setQuotes((prev) => ({ ...prev, [q.symbol]: q }));
        });
        if (!alive) return;
        setQuotes((prev) => ({ ...prev, ...next }));
        setErrors(Object.fromEntries(
          allVisibleSymbols.filter((s) => !next[s] && !cached[s]).map((s) => [s, "暂时无数据"]),
        ));
        setLastUpdated(new Date());
      } finally {
        if (alive) setLoadingQuotes(false);
      }
    })();
    return () => { alive = false; };
  }, [allVisibleSymbols, refreshId]);

  // 加密实时推送:可见的加密标的合并到一条 Binance WebSocket(~1s 跳动,零轮询)
  useEffect(() => {
    const cryptos = allVisibleSymbols.filter((s) => s.startsWith("CRYPTO:"));
    if (!cryptos.length) return;
    return subscribeCryptoLive(cryptos, (q) => {
      setQuotes((prev) => ({ ...prev, [q.symbol]: q }));
    });
  }, [allVisibleSymbols]);

  // 10s 自动刷新(数据层分级新鲜期:加密 8s 实时跳动,股票 30s 内走缓存零外呼);
  // 页面隐藏时暂停,回到前台立即补一次
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) setRefreshId((x) => x + 1);
    }, 10_000);
    const onVis = () => { if (!document.hidden) setRefreshId((x) => x + 1); };
    document.addEventListener("visibilitychange", onVis);
    return () => { window.clearInterval(id); document.removeEventListener("visibilitychange", onVis); };
  }, []);

  const sortFn = useMemo(() => {
    if (sortMode === "gainers") {
      return (a: string, b: string) => (quotes[b]?.changePct ?? -Infinity) - (quotes[a]?.changePct ?? -Infinity);
    }
    if (sortMode === "losers") {
      return (a: string, b: string) => (quotes[a]?.changePct ?? Infinity) - (quotes[b]?.changePct ?? Infinity);
    }
    return null;
  }, [quotes, sortMode]);

  const symbols = useMemo(() => {
    const arr = [...baseSymbols];
    return sortFn ? arr.sort(sortFn) : arr;
  }, [baseSymbols, sortFn]);

  // 「全部」视图按市场分组渲染(美股/A股优先),排序在组内生效
  const groups = useMemo(() => {
    if (tab !== "ALL") return null;
    return GROUP_ORDER.map((mkt) => {
      const arr = baseSymbols.filter((s) => marketOf(s) === mkt);
      return { mkt, label: MARKET_LABEL[mkt] ?? mkt, symbols: sortFn ? arr.sort(sortFn) : arr };
    }).filter((g) => g.symbols.length);
  }, [tab, baseSymbols, sortFn]);

  // 看板统计与页面渲染同一个集合(自选 + 当前 tab),数字和卡片一一对应
  const marketStats = useMemo(() => {
    const rows = allVisibleSymbols.map((s) => quotes[s]).filter((x): x is Quote => Boolean(x));
    const gainers = rows.filter((x) => (x.changePct ?? 0) > 0).length;
    const losers = rows.filter((x) => (x.changePct ?? 0) < 0).length;
    const avg = rows.length ? rows.reduce((sum, x) => sum + (x.changePct ?? 0), 0) / rows.length : null;
    return { loaded: rows.length, total: allVisibleSymbols.length, gainers, losers, avg };
  }, [quotes, allVisibleSymbols]);

  // 单卡重试:只拉这一只,成功后清除其错误(绕过 30s 内存缓存由 refreshId 整体刷新负责)
  const retryOne = async (s: string) => {
    setErrors((prev) => { const next = { ...prev }; delete next[s]; return next; });
    const got = await getQuotes([s]);
    if (got[s]) setQuotes((prev) => ({ ...prev, [s]: got[s] }));
    else setErrors((prev) => ({ ...prev, [s]: "仍无数据,稍后再试" }));
  };

  // 今日强弱:从已加载报价零成本派生(不发任何额外请求)
  const movers = useMemo(() => {
    const rows = allVisibleSymbols
      .map((s) => quotes[s])
      .filter((x): x is Quote => Boolean(x && x.changePct != null));
    if (rows.length < 6) return null;
    const sorted = [...rows].sort((a, b) => (b.changePct ?? 0) - (a.changePct ?? 0));
    return { top: sorted.slice(0, 3), bottom: sorted.slice(-3).reverse() };
  }, [quotes, allVisibleSymbols]);

  const renderCards = (list: string[]) => (
    <div className="grid">{list.map((s) => (
      <QuoteCard key={s} symbol={s} quote={quotes[s] ?? null} error={errors[s]} loading={loadingQuotes}
        onRetry={() => { void retryOne(s); }} />
    ))}</div>
  );

  return (
    <div className="container">
      <div className="header">
        <h1>📈 多市场股票数据看板</h1>
        <span className="tag">美股 · 港股 · A股 · 加密 · 实时行情 · 主力资金 · 非 LLM 技术分析</span>
        <Link href="/portfolio/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)", marginLeft: "auto" }}>💼 持仓</Link>
        <Link href="/screener/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>📈 每日选股</Link>
        <Link href="/tracker/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>🎯 追踪</Link>
        <Link href="/intel/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>🛰️ 情报看板</Link>
        <Link href="/sources/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>🔌 数据源</Link>
      </div>

      <div className="search"><SearchBox /></div>

      <div className="indices">
        {fng && (
          <span className="index-pill" title={`加密恐惧贪婪指数(alternative.me)· 更新 ${new Date(fng.at).toLocaleDateString()}`}>
            <span className="muted">加密情绪</span>
            <strong style={{ color: fngColor(fng.value) }}>{fng.value}</strong>
            <span style={{ color: fngColor(fng.value) }}>{fng.label}</span>
          </span>
        )}
        {INDEX_SYMBOLS.map((s) => {
          const q = idxQuotes[s];
          const d = q && q.changePct != null ? (q.changePct >= 0 ? "up" : "down") : "muted";
          return (
            <Link key={s} href={`/symbol/?s=${encodeURIComponent(s)}`} className="index-pill">
              <span className="muted">{nameOf(s)}</span>
              <strong>{q?.price != null ? q.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—"}</strong>
              <span className={d}>{q?.changePct != null ? `${q.changePct >= 0 ? "+" : ""}${q.changePct.toFixed(2)}%` : ""}</span>
            </Link>
          );
        })}
      </div>

      {firedAlerts.length > 0 && (
        <div className="hint" style={{ borderColor: "var(--up)", background: "rgba(38,166,154,.08)" }}>
          ⏰ 价格提醒触发:{firedAlerts.map((a) => `${nameOf(a.symbol)} ${a.dir === "above" ? "≥" : "≤"} ${a.target}(现 ${a.triggeredPrice})`).join(" · ")}
          <button className="btn subtle" style={{ marginLeft: 10, padding: "2px 10px", fontSize: 12 }}
            onClick={() => { clearTriggered(); setFiredAlerts([]); }}>知道了</button>
        </div>
      )}

      {feedStale && (
        <div className="hint">
          🛰️ 情报 feed 数据已陈旧{feedStale.asof ? `(最新数据 ${feedStale.asof})` : ""},
          策略/选股结论可能滞后 —— 详见 <Link href="/intel/" style={{ color: "var(--accent)" }}>情报看板</Link>。行情卡片不受影响(实时拉取)。
        </div>
      )}

      {!HAS_BACKEND && tab !== "CRYPTO" && (
        <div className="hint">
          ⚠️ 美股 / 港股 / A股 当前经<strong>公共代理</strong>获取,代理不稳时可能较慢或失败(已渐进加载:先到先显示)。
          加密为直连,秒开。部署后端并设 <code>API_BASE</code> 后,股票也将免代理秒开。
        </div>
      )}

      <div className="toolbar">
        <div className="stat">
          <span>已加载 {marketStats.loaded}/{marketStats.total}</span>
          <span className="up">涨 {marketStats.gainers}</span>
          <span className="down">跌 {marketStats.losers}</span>
          <span>均值 {marketStats.avg == null ? "—" : `${marketStats.avg >= 0 ? "+" : ""}${marketStats.avg.toFixed(2)}%`}</span>
        </div>
        <div className="segmented">
          <button className={sortMode === "default" ? "active" : ""} onClick={() => pickSort("default")}>默认</button>
          <button className={sortMode === "gainers" ? "active" : ""} onClick={() => pickSort("gainers")}>强势</button>
          <button className={sortMode === "losers" ? "active" : ""} onClick={() => pickSort("losers")}>弱势</button>
        </div>
        <button className="btn subtle" onClick={() => setRefreshId((x) => x + 1)} disabled={loadingQuotes}>
          {loadingQuotes ? "刷新中" : "刷新行情"}
        </button>
        {lastUpdated && <span className="src">更新 {lastUpdated.toLocaleTimeString()}</span>}
      </div>

      {movers && (
        <div className="movers">
          <span className="src">今日强弱</span>
          {movers.top.map((q) => (
            <Link key={q.symbol} href={`/symbol/?s=${encodeURIComponent(q.symbol)}`} className="mover up">
              {nameOf(q.symbol)} +{(q.changePct ?? 0).toFixed(2)}%
            </Link>
          ))}
          <span className="src">|</span>
          {movers.bottom.map((q) => (
            <Link key={q.symbol} href={`/symbol/?s=${encodeURIComponent(q.symbol)}`} className="mover down">
              {nameOf(q.symbol)} {(q.changePct ?? 0).toFixed(2)}%
            </Link>
          ))}
        </div>
      )}

      {watchAll.length > 0 && (
        <>
          <h2 className="block-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            ⭐ 我的自选 <span className="src">☁ = 云端跟踪池(OpenClaw 每日全面分析)</span>
            <button className="linklike" onClick={() => exportUserData()}>导出备份</button>
            <label className="linklike" style={{ cursor: "pointer" }}>
              导入
              <input type="file" accept="application/json" style={{ display: "none" }}
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  try {
                    const n = importUserData(await f.text());
                    alert(`导入成功,新增 ${n} 只自选`);
                  } catch (err: any) { alert(`导入失败:${err?.message || err}`); }
                  e.target.value = "";
                }} />
            </label>
          </h2>
          <div className="grid">{watchAll.map((s) => (
            <QuoteCard key={s} symbol={s} quote={quotes[s] ?? null} error={errors[s]} loading={loadingQuotes}
              tag={cloudWatch.includes(s) ? "☁" : undefined} onRetry={() => { void retryOne(s); }} />
          ))}</div>
        </>
      )}

      <div className="tabs">
        {MARKETS.map((m) => (
          <button key={m.key} className={m.key === tab ? "active" : ""} onClick={() => pickTab(m.key)}>{m.label}</button>
        ))}
      </div>

      <h2 className="block-title">涨跌热力图</h2>
      <Heatmap
        symbols={symbols}
        quotes={quotes}
        loading={loadingQuotes && marketStats.loaded === 0}
        sections={groups?.map((g) => ({ label: `${g.label}${g.mkt === "CRYPTO" ? "(24h)" : ""}`, symbols: g.symbols }))}
      />

      <h2 className="block-title">行情卡片</h2>
      {groups ? groups.map((g) => {
        const st = marketStatus(g.mkt);
        const rows = g.symbols.map((s) => quotes[s]).filter((x): x is Quote => Boolean(x));
        const up = rows.filter((x) => (x.changePct ?? 0) > 0).length;
        const down = rows.filter((x) => (x.changePct ?? 0) < 0).length;
        const avg = rows.length ? rows.reduce((sum, x) => sum + (x.changePct ?? 0), 0) / rows.length : null;
        return (
          <div key={g.mkt}>
            <h3 className="group-title">{g.label} <span className="src">{g.symbols.length} 只</span>
              {st.label && <span className={`badge ${st.open ? "up" : "muted"}`} style={{ fontSize: 11 }}>{st.label}</span>}
              {rows.length > 0 && (
                <span className="src">涨 <span className="up">{up}</span> / 跌 <span className="down">{down}</span>
                  {avg != null && <> · 均值 <span className={avg >= 0 ? "up" : "down"}>{avg >= 0 ? "+" : ""}{avg.toFixed(2)}%</span></>}
                  {g.mkt === "CRYPTO" ? "(24h)" : ""}
                </span>
              )}
            </h3>
            {renderCards(g.symbols)}
          </div>
        );
      }) : (
        <>
          {tab !== "ALL" && marketStatus(tab).label && (
            <p className="src" style={{ margin: "0 0 8px" }}>
              市场状态:<span className={marketStatus(tab).open ? "up" : "muted"}>{marketStatus(tab).label}</span>(本地推算,不含节假日)
            </p>
          )}
          {renderCards(symbols)}
        </>
      )}

      <div className="disclaimer">
        数据来源:暗号 = Binance(data-api.binance.vision)· 美/港/A股 = Yahoo Finance(经公共 CORS 代理,自动多代理回退)。
        加密涨跌为 <strong>24h 滚动</strong>,股票为 <strong>较上一交易日收盘</strong>。
        免费源仅供演示/自用,商用对外须更换授权数据源。
        本页所有分析为<strong>规则化技术指标 + 简化缠论(非投资建议 / Not financial advice)</strong>。
        缠论结构识别灵感来自 <a href="https://guanchaotv.com/" target="_blank" rel="noreferrer">观潮 TideView</a>(独立简化实现,非其代码)。
      </div>
    </div>
  );
}
