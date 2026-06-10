// 各市场开闭市状态(本地时钟推算,不含节假日;仅供展示参考)。
// 用 Intl 时区取目标市场当地时间,避免用户时区影响。

export interface MarketStatus { open: boolean; label: string }

function localParts(tz: string): { dow: number; minutes: number } {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: tz, hour12: false, weekday: "short", hour: "2-digit", minute: "2-digit",
  });
  const parts = Object.fromEntries(fmt.formatToParts(now).map((p) => [p.type, p.value]));
  const dows: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return { dow: dows[parts.weekday] ?? 0, minutes: parseInt(parts.hour) * 60 + parseInt(parts.minute) };
}

function inAny(minutes: number, ranges: [number, number][]): boolean {
  return ranges.some(([a, b]) => minutes >= a && minutes < b);
}

const H = (h: number, m = 0) => h * 60 + m;

/** market ∈ US/HK/CN/CRYPTO/IDX */
export function marketStatus(market: string): MarketStatus {
  if (market === "CRYPTO") return { open: true, label: "24h" };
  if (market === "US") {
    const { dow, minutes } = localParts("America/New_York");
    const weekday = dow >= 1 && dow <= 5;
    if (!weekday) return { open: false, label: "休市" };
    if (inAny(minutes, [[H(9, 30), H(16)]])) return { open: true, label: "盘中" };
    if (inAny(minutes, [[H(4), H(9, 30)]])) return { open: false, label: "盘前" };
    if (inAny(minutes, [[H(16), H(20)]])) return { open: false, label: "盘后" };
    return { open: false, label: "休市" };
  }
  if (market === "HK") {
    const { dow, minutes } = localParts("Asia/Hong_Kong");
    const weekday = dow >= 1 && dow <= 5;
    if (!weekday) return { open: false, label: "休市" };
    if (inAny(minutes, [[H(9, 30), H(12)], [H(13), H(16)]])) return { open: true, label: "盘中" };
    if (minutes >= H(12) && minutes < H(13)) return { open: false, label: "午休" };
    return { open: false, label: "休市" };
  }
  if (market === "CN") {
    const { dow, minutes } = localParts("Asia/Shanghai");
    const weekday = dow >= 1 && dow <= 5;
    if (!weekday) return { open: false, label: "休市" };
    if (inAny(minutes, [[H(9, 30), H(11, 30)], [H(13), H(15)]])) return { open: true, label: "盘中" };
    if (minutes >= H(11, 30) && minutes < H(13)) return { open: false, label: "午休" };
    return { open: false, label: "休市" };
  }
  if (market === "JP") {
    const { dow, minutes } = localParts("Asia/Tokyo");
    if (!(dow >= 1 && dow <= 5)) return { open: false, label: "休市" };
    if (inAny(minutes, [[H(9), H(11, 30)], [H(12, 30), H(15, 30)]])) return { open: true, label: "盘中" };
    if (minutes >= H(11, 30) && minutes < H(12, 30)) return { open: false, label: "午休" };
    return { open: false, label: "休市" };
  }
  if (market === "KR") {
    const { dow, minutes } = localParts("Asia/Seoul");
    if (!(dow >= 1 && dow <= 5)) return { open: false, label: "休市" };
    if (inAny(minutes, [[H(9), H(15, 30)]])) return { open: true, label: "盘中" };
    return { open: false, label: "休市" };
  }
  if (market === "DE") {
    const { dow, minutes } = localParts("Europe/Berlin");
    if (!(dow >= 1 && dow <= 5)) return { open: false, label: "休市" };
    if (inAny(minutes, [[H(9), H(17, 30)]])) return { open: true, label: "盘中" };
    return { open: false, label: "休市" };
  }
  if (market === "GB") {
    const { dow, minutes } = localParts("Europe/London");
    if (!(dow >= 1 && dow <= 5)) return { open: false, label: "休市" };
    if (inAny(minutes, [[H(8), H(16, 30)]])) return { open: true, label: "盘中" };
    return { open: false, label: "休市" };
  }
  return { open: false, label: "" };
}

// ---- 距开/收盘倒计时(Hyperliquid 资金费率倒计时的股市类比) ----
// 与上面的常规时段一致;分钟精度,不含节假日。加密/未知市场返回 null。
const SESSIONS: Record<string, [number, number][]> = {
  US: [[H(9, 30), H(16)]],
  HK: [[H(9, 30), H(12)], [H(13), H(16)]],
  CN: [[H(9, 30), H(11, 30)], [H(13), H(15)]],
  JP: [[H(9), H(11, 30)], [H(12, 30), H(15, 30)]],
  KR: [[H(9), H(15, 30)]],
  DE: [[H(9), H(17, 30)]],
  GB: [[H(8), H(16, 30)]],
};
const TZ: Record<string, string> = {
  US: "America/New_York", HK: "Asia/Hong_Kong", CN: "Asia/Shanghai", JP: "Asia/Tokyo",
  KR: "Asia/Seoul", DE: "Europe/Berlin", GB: "Europe/London",
};

function fmtDur(mins: number): string {
  if (mins >= 1440) return `${Math.floor(mins / 1440)}天${Math.floor((mins % 1440) / 60)}时`;
  if (mins >= 60) return `${Math.floor(mins / 60)}时${mins % 60}分`;
  return `${mins}分`;
}

/** 下一个开/收盘事件倒计时,如 "距收盘 2时15分" / "距开盘 1天3时"。 */
export function marketCountdown(market: string): { open: boolean; text: string } | null {
  const sessions = SESSIONS[market];
  const tz = TZ[market];
  if (!sessions || !tz) return null;
  const { dow, minutes } = localParts(tz);
  // 向后找 8 天内最近的开/收盘边界(开盘边界=open 事件,收盘边界=close 事件)
  let bestAt = Infinity;
  let bestIsOpen = false;
  for (let d = 0; d < 8 && !isFinite(bestAt); d++) {
    const day = (dow + d) % 7;
    if (day === 0 || day === 6) continue;
    for (const [a, b] of sessions) {
      for (const [m, isOpen] of [[a, true], [b, false]] as const) {
        const at = d * 1440 + m - minutes;
        if (at <= 0) continue;
        if (at < bestAt) { bestAt = at; bestIsOpen = isOpen; }
      }
    }
  }
  if (!isFinite(bestAt)) return null;
  const open = marketStatus(market).open;
  return { open, text: `${bestIsOpen ? "距开盘" : "距收盘"} ${fmtDur(bestAt)}` };
}
