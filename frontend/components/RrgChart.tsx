"use client";
import Link from "next/link";
import { useMemo } from "react";

// 轮动象限图(RRG 近似):x = RS 分位(1-99,全宇宙相对强度),y = 63日动量(%)。
// 右上=领涨(强+动量),右下=高位转弱,左下=落后,左上=底部改善。
// 经典 RRG 用 RS-Ratio/RS-Momentum;此处以现有 rs/r63 近似,口径见 methodology §6。

export interface RrgItem { symbol: string; name: string; rs: number; r63: number; r126?: number | null; color: string }

const W = 720, H = 420, PAD = 42;

export default function RrgChart({ items }: { items: RrgItem[] }) {
  const pts = useMemo(() => {
    const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
    return items
      .filter((d) => isFinite(d.rs) && isFinite(d.r63))
      .map((d) => ({
        ...d,
        x: PAD + (clamp(d.rs, 0, 100) / 100) * (W - PAD * 2),
        y: H - PAD - ((clamp(d.r63, -40, 40) + 40) / 80) * (H - PAD * 2),
      }));
  }, [items]);

  // 文字标注:按 |rs-50|+|r63| 强度取前几个,避免重叠刷屏(hooks 必须在条件 return 之前)
  const labeled = useMemo(() => {
    const score = (p: typeof pts[number]) => Math.abs(p.rs - 50) + Math.abs(p.r63);
    return [...pts].sort((a, b) => score(b) - score(a)).slice(0, 16);
  }, [pts]);

  if (!pts.length) return null;
  const midX = PAD + 0.5 * (W - PAD * 2);
  const midY = H - PAD - (40 / 80) * (H - PAD * 2);

  return (
    <div style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 880, display: "block" }}>
        {/* 象限底色 */}
        <rect x={midX} y={PAD} width={W - PAD - midX} height={midY - PAD} fill="rgba(38,166,154,0.07)" />
        <rect x={midX} y={midY} width={W - PAD - midX} height={H - PAD - midY} fill="rgba(247,181,0,0.06)" />
        <rect x={PAD} y={midY} width={midX - PAD} height={H - PAD - midY} fill="rgba(239,83,80,0.07)" />
        <rect x={PAD} y={PAD} width={midX - PAD} height={midY - PAD} fill="rgba(76,141,255,0.06)" />
        {/* 轴与中线 */}
        <line x1={PAD} y1={midY} x2={W - PAD} y2={midY} stroke="var(--border)" strokeDasharray="4 4" />
        <line x1={midX} y1={PAD} x2={midX} y2={H - PAD} stroke="var(--border)" strokeDasharray="4 4" />
        <text x={W - PAD - 4} y={PAD + 14} textAnchor="end" fontSize={12} fill="#26a69a">领涨(强·升)</text>
        <text x={W - PAD - 4} y={H - PAD - 6} textAnchor="end" fontSize={12} fill="#f7b500">高位转弱</text>
        <text x={PAD + 4} y={H - PAD - 6} fontSize={12} fill="#ef5350">落后(弱·跌)</text>
        <text x={PAD + 4} y={PAD + 14} fontSize={12} fill="#4c8dff">底部改善</text>
        <text x={W / 2} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--muted)">RS 相对强度分位(0-100)→</text>
        <text x={12} y={H / 2} fontSize={11} fill="var(--muted)" transform={`rotate(-90 12 ${H / 2})`} textAnchor="middle">63日动量 % →</text>
        {/* 散点 */}
        {pts.map((p) => {
          const accel = p.r126 != null ? p.r63 - p.r126 : null; // 短期动量 vs 中期:>0 加速
          return (
            <Link key={p.symbol} href={`/symbol/?s=${encodeURIComponent(p.symbol)}`}>
              <g>
                <circle cx={p.x} cy={p.y} r={4.5} fill={p.color} fillOpacity={0.85} stroke="var(--bg)" strokeWidth={1} />
                {accel != null && Math.abs(accel) >= 3 && (
                  <path d={accel > 0
                    ? `M ${p.x - 3} ${p.y - 7} L ${p.x + 3} ${p.y - 7} L ${p.x} ${p.y - 12} Z`
                    : `M ${p.x - 3} ${p.y + 7} L ${p.x + 3} ${p.y + 7} L ${p.x} ${p.y + 12} Z`}
                    fill={accel > 0 ? "#26a69a" : "#ef5350"} fillOpacity={0.9} />
                )}
                <title>{`${p.name} · RS ${p.rs} · 63日 ${p.r63 >= 0 ? "+" : ""}${p.r63}%${p.r126 != null ? ` · 126日 ${p.r126 >= 0 ? "+" : ""}${p.r126}%(${(accel ?? 0) > 0 ? "动量加速" : "动量减速"})` : ""}`}</title>
              </g>
            </Link>
          );
        })}
        {/* 重点标注 */}
        {labeled.map((p) => (
          <text key={`t${p.symbol}`} x={p.x + 7} y={p.y + 4} fontSize={10.5} fill="var(--text)" opacity={0.92}>
            {p.name}
          </text>
        ))}
      </svg>
    </div>
  );
}
