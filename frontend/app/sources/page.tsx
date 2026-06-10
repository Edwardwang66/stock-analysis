"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { SOURCES } from "@/lib/sources";
import { getBackendHealth, HAS_BACKEND } from "@/lib/datasource";
import { getForex, type Forex } from "@/lib/forex";
import { getCrossExchange, type ExPrice } from "@/lib/multiprice";
import LangSelect from "@/components/LangSelect";

const UP = "#26a69a", DOWN = "#ef5350";
const STATUS_C: Record<string, string> = { 已接入: UP, 可接入: "#f7b500", 不可用: DOWN };

export default function SourcesPage() {
  const [fx, setFx] = useState<Forex | null>(null);
  const [xc, setXc] = useState<ExPrice[]>([]);
  const [health, setHealth] = useState<any | null>(null);

  useEffect(() => {
    getForex("USD").then(setFx).catch(() => {});
    getCrossExchange("BTCUSDT").then(setXc).catch(() => {});
    getBackendHealth().then(setHealth).catch(() => {});
  }, []);

  const live = xc.filter((x) => x.price != null).map((x) => x.price as number);
  const spread = live.length > 1 ? ((Math.max(...live) - Math.min(...live)) / Math.min(...live)) * 100 : 0;
  const counts = SOURCES.reduce((a, s) => { a[s.status] = (a[s.status] || 0) + 1; return a; }, {} as Record<string, number>);

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <h1>🔌 免费数据源接入</h1>
        <LangSelect />
        <span className="tag">
          已接入 <b style={{ color: UP }}>{counts["已接入"] || 0}</b> · 可接入 <b style={{ color: "#f7b500" }}>{counts["可接入"] || 0}</b> · 不可用 <b style={{ color: DOWN }}>{counts["不可用"] || 0}</b>(2026-06 实测)
        </span>
      </div>

      {/* 后端状态:未配置 → 全部浏览器直连;配置了 → 健康/熔断一览 */}
      <div className="section">
        <h2>后端状态</h2>
        {!HAS_BACKEND ? (
          <p className="src">未配置 <code>NEXT_PUBLIC_API_BASE</code> —— 股票经公共 CORS 代理、加密直连浏览器获取。
            部署 FastAPI 后端后此处显示 缓存/熔断 实况。</p>
        ) : !health ? (
          <p className="loading">检测中…(Render 免费实例冷启动可能需 30s)</p>
        ) : !health.ok ? (
          <p className="src" style={{ color: DOWN }}>后端不可达(可能在唤醒中)。前端已自动回退浏览器直连,功能不受影响。</p>
        ) : (
          <>
            <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))" }}>
              <div className="card"><div className="src">状态</div><div style={{ color: UP, fontWeight: 700, marginTop: 4 }}>在线 ✓</div></div>
              <div className="card"><div className="src">运行时长</div><div style={{ fontWeight: 700, marginTop: 4 }}>{Math.floor((health.uptime_s || 0) / 3600)}h {Math.floor(((health.uptime_s || 0) % 3600) / 60)}m</div></div>
              <div className="card"><div className="src">缓存条目</div><div style={{ fontWeight: 700, marginTop: 4 }}>{health.cache?.entries ?? "—"}</div></div>
              <div className="card"><div className="src">K线库</div><div style={{ fontWeight: 700, marginTop: 4 }}>{health.barstore?.symbols ?? health.barstore?.rows ?? "—"}</div></div>
            </div>
            {health.breakers && Object.keys(health.breakers).length > 0 && (
              <p className="src" style={{ marginTop: 8, color: "#f7b500" }}>
                熔断中:{Object.entries(health.breakers).map(([k, v]: [string, any]) => `${k}(${v.fails}次,冷却${v.cooling_s}s)`).join(" · ")}
              </p>
            )}
          </>
        )}
      </div>

      {/* 实时演示 1:跨交易所暗号报价(多源并发 + 校验) */}
      <div className="section">
        <h2>实时演示 · BTC 跨交易所聚合报价(多源并发)</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))" }}>
          {xc.map((x) => (
            <div className="card" key={x.exchange}>
              <div className="sym">{x.exchange}</div>
              <div className="price" style={{ fontSize: 18 }}>{x.price != null ? `$${x.price.toLocaleString()}` : "—"}</div>
              <div className="src">{x.err ? `失败:${x.err}` : "USD"}</div>
            </div>
          ))}
        </div>
        {live.length > 1 && <p className="src" style={{ marginTop: 8 }}>各所最大价差 {spread.toFixed(3)}%（价差越小说明报价越一致;免费 key-free 源即可交叉校验)。</p>}
      </div>

      {/* 实时演示 2:外汇 */}
      <div className="section">
        <h2>实时演示 · 外汇汇率(1 USD =)</h2>
        {fx ? (
          <>
            <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))" }}>
              {Object.entries(fx.rates).map(([k, v]) => (
                <div className="card" key={k}><div className="sym">{k}</div><div className="price" style={{ fontSize: 18 }}>{v}</div></div>
              ))}
            </div>
            <p className="src" style={{ marginTop: 8 }}>{fx.date} · 来源 {fx.source}</p>
          </>
        ) : <div className="loading">加载汇率…</div>}
      </div>

      {/* 登记表 */}
      <div className="section">
        <h2>数据源登记表</h2>
        <table>
          <thead>
            <tr><th>状态</th><th>数据源</th><th>提供</th><th>市场</th><th>浏览器直连</th><th>Key</th><th>备注</th></tr>
          </thead>
          <tbody>
            {SOURCES.map((s) => (
              <tr key={s.name}>
                <td><span className="badge" style={{ color: STATUS_C[s.status], borderColor: STATUS_C[s.status], fontSize: 11 }}>{s.status}</span></td>
                <td style={{ fontWeight: 600 }}>{s.name}</td>
                <td>{s.provides}</td>
                <td className="muted">{s.market}</td>
                <td style={{ textAlign: "center" }}>{s.cors}</td>
                <td className="muted">{s.key}</td>
                <td className="muted" style={{ fontSize: 12 }}>{s.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="disclaimer">
        以上均为<strong>免费 / 无 key 或免费 key</strong> 公开源,<strong>仅供演示/自用</strong>;商用对外重分发须更换授权数据源(见仓库 docs/compliance.md)。
        「浏览器直连 ❌」者需经公共 CORS 代理或自建后端。本页所有数据为信息参考,非投资建议。
      </div>
    </div>
  );
}
