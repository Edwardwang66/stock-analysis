"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  getIndex, getSignals, getMarket, getFactory, getMarketHistory, getReport,
  type FeedIndex, type Signals, type MarketState, type FactoryStore, type FullReport, type MarketSnapshot,
} from "@/lib/feed";

const UP = "#26a69a", DOWN = "#ef5350", WARN = "#f7b500", MUT = "#787b86";
const pct = (x?: number | null, d = 1) => (x == null ? "—" : `${(x * 100).toFixed(d)}%`);
const num = (x?: number | null, d = 2) => (x == null ? "—" : x.toFixed(d));
const REGIME: Record<string, { c: string; t: string }> = {
  risk_on: { c: UP, t: "风险偏好 (risk-on)" }, neutral: { c: WARN, t: "中性 (neutral)" },
  risk_off: { c: DOWN, t: "避险 (risk-off)" }, unknown: { c: MUT, t: "未知" },
};
const LVL: Record<string, string> = { info: MUT, warning: WARN, critical: DOWN };

export default function IntelDashboard() {
  const [idx, setIdx] = useState<FeedIndex | null>(null);
  const [sig, setSig] = useState<Signals | null>(null);
  const [mkt, setMkt] = useState<MarketState | null>(null);
  const [fac, setFac] = useState<FactoryStore | null>(null);
  const [rep, setRep] = useState<FullReport | null>(null);
  const [hist, setHist] = useState<MarketSnapshot[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const i = await getIndex();
    if (!i) { setErr("无法加载 feed/index.json(远端与捆绑快照均失败)。"); return; }
    setIdx(i); setErr(null);
    setSig(await getSignals()); setMkt(await getMarket()); setFac(await getFactory());
    setHist((await getMarketHistory()) ?? []);
    if (i.latest.report) setRep(await getReport(i.latest.report));
  }
  useEffect(() => { load(); const t = setInterval(load, 5 * 60 * 1000); return () => clearInterval(t); }, []);

  const fresh = idx?.freshness;
  const stale = fresh?.stale;
  const longs = (sig?.positions || []).filter((p) => p.side === "LONG").slice(-8).reverse();
  const shorts = (sig?.positions || []).filter((p) => p.side === "SHORT").slice(0, 8);
  const tl = Object.entries(idx?.timeline || {}).slice(-21);
  const tlMax = Math.max(1, ...tl.map(([, n]) => n));

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>← 返回</Link>
        <h1>🛰️ 市场情报看板</h1>
        <span className="tag">例行任务 + OpenClaw 投递 → feed/ → 本页 · 做多做空引擎(流 B 残差统计套利)</span>
        <button className="btn" style={{ marginLeft: "auto" }} onClick={load}>↻ 刷新</button>
      </div>

      {err && <div className="err">{err}</div>}

      {/* 新鲜度横幅:这个 repo 是否拿到了最新市场情况 */}
      <div className="section" style={{ borderColor: stale ? DOWN : UP }}>
        <h2>① 新鲜度 — 仓库是否最新?</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))" }}>
          <Stat label="状态" value={stale ? "陈旧 ⚠" : "最新 ✓"} color={stale ? DOWN : UP} />
          <Stat label="最新数据日期" value={fresh?.market_data_asof || "—"} />
          <Stat label="数据滞后" value={fresh?.data_age_days != null ? `${fresh.data_age_days.toFixed(1)} 天` : "—"} />
          <Stat label="上次报告" value={fresh?.report_age_hours != null ? `${fresh.report_age_hours.toFixed(1)} 小时前` : "—"} />
          <Stat label="index 更新于" value={idx ? idx.updated_at.replace("T", " ").replace("Z", " UTC") : "—"} />
        </div>
      </div>

      {/* 信息量统计:什么时候获得了多少信息 */}
      <div className="section">
        <h2>② 获取了多少信息?</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(150px,1fr))" }}>
          <Stat label="报告总数" value={String(idx?.stats.total_reports ?? "—")} />
          <Stat label="近 24h" value={String(idx?.stats.last_24h ?? "—")} color={UP} />
          <Stat label="近 7 天" value={String(idx?.stats.last_7d ?? "—")} />
          <Stat label="来源数" value={String(Object.keys(idx?.stats.by_producer || {}).length || "—")} />
        </div>
        <p className="src" style={{ marginTop: 10 }}>按类别:{Object.entries(idx?.stats.by_kind || {}).map(([k, v]) => `${k} ${v}`).join(" · ") || "—"}
          ；按来源:{Object.entries(idx?.stats.by_producer || {}).map(([k, v]) => `${k}(${v})`).join(" · ") || "—"}</p>
        {/* 每日投递时间线 */}
        <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 80, marginTop: 12 }}>
          {tl.length === 0 && <span className="src">暂无时间线数据(例行任务每运行一次 +1)。</span>}
          {tl.map(([day, n]) => (
            <div key={day} title={`${day}: ${n} 份`} style={{ flex: 1, textAlign: "center" }}>
              <div style={{ background: "var(--accent)", height: `${(n / tlMax) * 64}px`, borderRadius: 3, minHeight: 3 }} />
              <div style={{ fontSize: 9, color: MUT, marginTop: 3, transform: "rotate(-45deg)", whiteSpace: "nowrap" }}>{day.slice(5)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 市场状态 + 做多做空引擎裁决 */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 16 }}>
        <div className="section">
          <h2>③ 最新市场状态</h2>
          {mkt ? (
            <>
              <div style={{ marginBottom: 10 }}>
                <span className="badge" style={{ borderColor: (REGIME[mkt.regime || "unknown"]).c, color: (REGIME[mkt.regime || "unknown"]).c }}>
                  {(REGIME[mkt.regime || "unknown"]).t}
                </span>
                {mkt.crowding_alert && <span className="badge" style={{ marginLeft: 8, borderColor: DOWN, color: DOWN }}>拥挤告警</span>}
              </div>
              <table>
                <tbody>
                  <tr><td>SPY 在 200 日均线上</td><td>{mkt.spy_above_200dma == null ? "—" : (mkt.spy_above_200dma ? "是 ✓" : "否 ✗")}</td></tr>
                  <tr><td>SPY 20 日年化波动</td><td>{pct(mkt.spy_vol_20d_annual)}</td></tr>
                  <tr><td>广度(50 日线上占比)</td><td>{pct(mkt.breadth_pct_above_50dma)}</td></tr>
                  <tr><td>拥挤代理(平均相关)</td><td style={{ color: (mkt.crowding_proxy || 0) > 0.55 ? DOWN : "inherit" }}>{num(mkt.crowding_proxy)}</td></tr>
                  <tr><td>残差离散度</td><td>{num(mkt.residual_dispersion, 4)}</td></tr>
                </tbody>
              </table>
            </>
          ) : <p className="loading">加载中…</p>}
        </div>

        <div className="section">
          <h2>④ 做多做空引擎裁决(净·扣成本)</h2>
          {rep?.engine ? (
            <>
              <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <Stat label="净 Sharpe" value={num(rep.engine.net?.sharpe)} color={(rep.engine.net?.sharpe || 0) > 0 ? UP : DOWN} />
                <Stat label="毛 Sharpe" value={num(rep.engine.gross?.sharpe)} />
                <Stat label="年化(净)" value={pct(rep.engine.net?.ann_return)} />
                <Stat label="最大回撤" value={pct(rep.engine.net?.max_drawdown)} color={DOWN} />
                <Stat label="成本拖累/年" value={pct(rep.engine.cost_drag_ann)} color={WARN} />
                <Stat label="Deflated SR" value={num(rep.engine.deflated_sharpe?.dsr, 3)} />
              </div>
              <p className="src" style={{ marginTop: 10, lineHeight: 1.6 }}>{rep.engine.verdict}</p>
            </>
          ) : <p className="loading">加载中…</p>}
        </div>
      </div>

      {/* 做多做空簿 */}
      <div className="section">
        <h2>⑤ 当前做多做空簿 {sig && <span className="src">@ {sig.asof} · 多 {sig.n_long} / 空 {sig.n_short} · 毛杠杆 {num(sig.gross_leverage)} · 净敞口 {pct(sig.net_exposure, 2)}</span>}</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 16 }}>
          <BookTable title="做多 (Top)" rows={longs} color={UP} />
          <BookTable title="做空 (Top)" rows={shorts} color={DOWN} />
        </div>
        <p className="src" style={{ marginTop: 8 }}>s = OU 标准化偏离(s&lt;0 做多 / s&gt;0 做空);hl = 半衰期(交易日);H = Hurst(&gt;0.55 触发协整断裂熔断)。</p>
      </div>

      {/* 每日快照历史(market-snapshot.yml 自动累积) */}
      <div className="section">
        <h2>⑤+ 市场历史快照(自动累积,工作日两次)</h2>
        {hist.length < 2 ? (
          <p className="src">数据积累中({hist.length}/2 天起绘图)。market-snapshot 工作流每个工作日
            A股/美股收盘后各跑一次,把 8 大指数、恐惧贪婪指数、BTC 写入 feed/market/history.json(留 400 天)。</p>
        ) : (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(210px,1fr))", gap: 10 }}>
            {([["^GSPC", "标普500"], ["^IXIC", "纳斯达克"], ["000001.SS", "上证指数"], ["^HSI", "恒生指数"]] as const).map(([code, label]) => (
              <Spark key={code} label={label} values={hist.map((h) => h.indices?.[code]?.close ?? null)} last={hist[hist.length - 1]?.indices?.[code]} />
            ))}
            <Spark label="恐惧贪婪" values={hist.map((h) => h.fng?.value ?? null)}
              lastText={`${hist[hist.length - 1]?.fng?.value ?? "—"} ${hist[hist.length - 1]?.fng?.label ?? ""}`} />
            <Spark label="BTC" values={hist.map((h) => h.btc?.price ?? null)}
              lastText={hist[hist.length - 1]?.btc?.price?.toLocaleString() ?? "—"} />
          </div>
        )}
      </div>

      {/* LLM 假设工厂候选 */}
      <div className="section">
        <h2>⑥ LLM 假设工厂候选(受门控,LLM 不决策)</h2>
        {fac && fac.candidates.length ? (
          <div className="signal-list">
            {fac.candidates.slice(0, 8).map((c, i) => (
              <div className="signal" key={i} style={{ flexDirection: "column", alignItems: "stretch", gap: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <code style={{ color: "var(--text)" }}>{c.expr}</code>
                  <span className="badge" style={{ borderColor: c.decision === "accept" ? UP : c.decision === "shadow" ? WARN : DOWN, color: c.decision === "accept" ? UP : c.decision === "shadow" ? WARN : DOWN }}>{c.decision || "—"}</span>
                </div>
                <span className="src">{c.hypothesis}</span>
                <span className="src">增量IC {num(c.incremental_ic, 3)} · PBO {num(c.pbo, 2)} · t {num(c.t_stat, 1)} · 截止后 {c.post_cutoff ? "是" : "否"} · 过门控 {c.passed_gates ? "✓" : "✗"} · 来源 {c._source || "—"}</span>
                {c.note && <span className="src" style={{ color: MUT }}>{c.note}</span>}
              </div>
            ))}
          </div>
        ) : <p className="src">暂无候选。LLM 工厂默认关闭,接入后产出可审计公式因子(须过六门控,见 routines/daily-alpha-routine.md)。</p>}
      </div>

      {/* 贡献日志:这些情报怎么帮助到你了 */}
      <div className="section">
        <h2>⑦ 情报贡献日志 — 怎么帮助到系统?</h2>
        <table>
          <thead><tr><th>时间</th><th>来源</th><th>类型</th><th>摘要</th><th>净SR变化</th></tr></thead>
          <tbody>
            {(idx?.contributions || []).slice(0, 12).map((c, i) => (
              <tr key={i}>
                <td className="src">{c.at.replace("T", " ").replace("Z", "")}</td>
                <td>{c.producer}</td>
                <td><span className="badge">{c.type}</span></td>
                <td>{c.summary || "—"}</td>
                <td style={{ color: (c.net_sharpe_delta || 0) > 0 ? UP : (c.net_sharpe_delta || 0) < 0 ? DOWN : MUT }}>{c.net_sharpe_delta == null ? "—" : (c.net_sharpe_delta > 0 ? "+" : "") + c.net_sharpe_delta}</td>
              </tr>
            ))}
            {(!idx || idx.contributions.length === 0) && <tr><td colSpan={5} className="src">暂无。</td></tr>}
          </tbody>
        </table>
      </div>

      {/* 告警 */}
      {rep?.alerts && rep.alerts.length > 0 && (
        <div className="section">
          <h2>⑧ 风险告警(最新报告)</h2>
          <div className="signal-list">
            {rep.alerts.map((a, i) => (
              <div className="signal" key={i}>
                <span><span className="badge" style={{ borderColor: LVL[a.level], color: LVL[a.level], marginRight: 8 }}>{a.level}</span>{a.message}</span>
                {a.tickers && a.tickers.length > 0 && <span className="src">{a.tickers.join(", ")}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="disclaimer">
        本看板消费 <code>feed/</code>(GitHub raw 优先、捆绑快照兜底,每 5 分钟自动刷新)。做多做空引擎为
        <strong>流 B 条件因子统计套利残差均值回归</strong>,全程<strong>扣成本(净·压力成本为唯一计价货币)</strong>。
        当前在可得免费数据(含幸存者偏差的流动大盘)上净 alpha ≈0/为负 —— 这与设计文档第 10 章结论一致:
        真 alpha 在容量受限冷门层,免费数据触及不到。<strong>研究/演示用途,非投资建议(Not financial advice)。</strong>
      </div>
    </div>
  );
}

function Spark({ label, values, last, lastText }: {
  label: string;
  values: (number | null)[];
  last?: { close: number | null; change_pct: number | null };
  lastText?: string;
}) {
  const pts = values.map((v, i) => [i, v] as const).filter((p): p is readonly [number, number] => p[1] != null);
  const w = 200, h = 44;
  let path = "";
  if (pts.length >= 2) {
    const vs = pts.map((p) => p[1]);
    const min = Math.min(...vs), max = Math.max(...vs);
    const sx = (i: number) => (i / (values.length - 1 || 1)) * w;
    const sy = (v: number) => 4 + (1 - (v - min) / (max - min || 1)) * (h - 8);
    path = pts.map(([i, v], j) => `${j ? "L" : "M"}${sx(i).toFixed(1)} ${sy(v).toFixed(1)}`).join(" ");
  }
  const up = pts.length >= 2 ? pts[pts.length - 1][1] >= pts[0][1] : true;
  return (
    <div className="card">
      <div className="src">{label}</div>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
        {path && <path d={path} fill="none" stroke={up ? UP : DOWN} strokeWidth="1.8" />}
      </svg>
      <div style={{ fontSize: 13, fontWeight: 600 }}>
        {lastText ?? (last?.close != null ? last.close.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—")}
        {last?.change_pct != null && (
          <span style={{ color: last.change_pct >= 0 ? UP : DOWN, marginLeft: 6, fontWeight: 400 }}>
            {last.change_pct >= 0 ? "+" : ""}{last.change_pct.toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="card">
      <div className="src">{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4, color: color || "var(--text)" }}>{value}</div>
    </div>
  );
}

function BookTable({ title, rows, color }: { title: string; rows: any[]; color: string }) {
  return (
    <div>
      <div className="src" style={{ color, fontWeight: 600, marginBottom: 6 }}>{title}</div>
      <table>
        <thead><tr><th>代码</th><th>权重</th><th>s</th><th>hl</th><th>H</th><th>行业</th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={6} className="src">—</td></tr>}
          {rows.map((p) => (
            <tr key={p.ticker}>
              <td style={{ fontWeight: 600 }}>{p.ticker}</td>
              <td style={{ color }}>{(p.weight * 100).toFixed(2)}%</td>
              <td>{p.s_score?.toFixed(2)}</td>
              <td>{p.halflife_days}</td>
              <td style={{ color: (p.hurst || 0) > 0.55 ? DOWN : "inherit" }}>{p.hurst}</td>
              <td className="src">{p.sector}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
