"use client";
// Hyperliquid 式一行统计条:现价/涨跌/高低/昨收/成交量/52周位置/盘前盘后/夜盘 一行排开,
// 信息密度高、每项 hover 有解释;替代原先散落在页头的报价碎片。
import { useEffect, useRef, useState } from "react";
import type { ExtendedQuote, Quote } from "@/lib/datasource";
import type { NightQuote } from "@/lib/nightquotes";

function fmt(n: number | null | undefined, d = 2): string {
  return n == null ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: d });
}
function fmtVol(v: number | null): string {
  if (v == null || !isFinite(v)) return "—";
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(0);
}

function Item({ label, title, children, cls }: { label: string; title?: string; children: React.ReactNode; cls?: string }) {
  return (
    <div className={`stat-item ${cls || ""}`} title={title}>
      <span className="lbl">{label}</span>
      <span className="val">{children}</span>
    </div>
  );
}

export default function StatBar({
  symbol, quote, ext, night, volume, high52, low52,
}: {
  symbol: string;
  quote: Quote | null;
  ext: ExtendedQuote | null;
  night: NightQuote | null;
  /** 今日(日线末根)成交量;拿不到传 null 即不显示 */
  volume: number | null;
  high52: number | null;
  low52: number | null;
}) {
  const isCrypto = symbol.startsWith("CRYPTO:");
  const dir = quote && quote.changePct != null ? (quote.changePct >= 0 ? "up" : "down") : "";

  // 价格变动 flash(同 Hyperliquid:每次跳价闪一下背景)
  const prevRef = useRef<number | null>(null);
  const [flash, setFlash] = useState<{ dir: "up" | "down"; at: number } | null>(null);
  useEffect(() => {
    const p = quote?.price ?? null;
    if (p != null && prevRef.current != null && p !== prevRef.current) {
      setFlash({ dir: p > prevRef.current ? "up" : "down", at: Date.now() });
    }
    prevRef.current = p;
  }, [quote?.price]);

  if (!quote) return null;
  const pos52 = high52 != null && low52 != null && high52 > low52
    ? Math.max(0, Math.min(100, ((quote.price - low52) / (high52 - low52)) * 100))
    : null;

  return (
    <div className="statbar">
      <Item label="现价" cls={`price ${dir}`} title={`数据源:${quote.source}${isCrypto ? " · WebSocket 实时" : " · 免费源有交易所级延迟"}`}>
        <span key={flash?.at ?? 0} className={flash ? (flash.dir === "up" ? "flash-up" : "flash-down") : ""}>
          {fmt(quote.price)}
        </span>
      </Item>
      <Item label={isCrypto ? "24h 涨跌" : "今日涨跌"} cls={dir} title="较昨收的涨跌额 / 涨跌幅">
        {quote.change != null ? `${quote.change >= 0 ? "+" : ""}${fmt(quote.change)}` : "—"}
        {quote.changePct != null && ` (${quote.changePct >= 0 ? "+" : ""}${quote.changePct.toFixed(2)}%)`}
      </Item>
      <Item label={isCrypto ? "24h 高 / 低" : "今日高 / 低"} title="当日(加密为滚动24小时)最高价 / 最低价">
        {fmt(quote.high)} / {fmt(quote.low)}
      </Item>
      {!isCrypto && quote.change != null && quote.price != null && (
        <Item label="昨收" title="上一交易日收盘价(涨跌幅基准)">{fmt(quote.price - quote.change)}</Item>
      )}
      {volume != null && volume > 0 && (
        <Item label="成交量" title="今日(最新一根日K)成交量">{fmtVol(volume)}</Item>
      )}
      {pos52 != null && high52 != null && (
        <Item label="52周位置" title={`52周区间 ${fmt(low52)} ~ ${fmt(high52)} · 当前处于区间 ${pos52.toFixed(0)}% 处 · 距52周高 ${(((quote.price / high52) - 1) * 100).toFixed(1)}%`}>
          <span className="mini52">
            <span className="mini52-track"><span className="mini52-dot" style={{ left: `${pos52}%` }} /></span>
            <span className="muted" style={{ fontSize: 11 }}>{pos52.toFixed(0)}%</span>
          </span>
        </Item>
      )}
      {ext && (
        <Item label={ext.session} cls={ext.change >= 0 ? "up" : "down"}
          title={`美股扩展时段报价 · ${new Date(ext.at * 1000).toLocaleTimeString("zh-CN", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit" })}(美东) · ${ext.session === "盘后" ? "较今日收盘" : "较昨收"}`}>
          {fmt(ext.price)} ({ext.changePct >= 0 ? "+" : ""}{ext.changePct.toFixed(2)}%)
        </Item>
      )}
      {night && (
        <Item label="🌙 夜盘" cls={(night.chg24h ?? 0) >= 0 ? "up" : "down"}
          title={`Hyperliquid 永续 ${night.hlSymbol} · 实证 corr 0.965 · 资金费率 ${night.fundingApr != null ? (night.fundingApr * 100).toFixed(0) + "%" : "—"}`}>
          {fmt(night.mark)}{night.chg24h != null && ` (${night.chg24h >= 0 ? "+" : ""}${(night.chg24h * 100).toFixed(2)}%)`}
        </Item>
      )}
      <Item label="货币 · 来源" title="报价货币与数据来源">{quote.currency || "—"} · {quote.source}</Item>
    </div>
  );
}
