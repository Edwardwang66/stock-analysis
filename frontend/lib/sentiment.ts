// 加密恐惧贪婪指数(alternative.me,免费、CORS 开放、无 key)。
export interface FearGreed { value: number; label: string; at: number }

const LABELS: Record<string, string> = {
  "Extreme Fear": "极度恐惧", Fear: "恐惧", Neutral: "中性",
  Greed: "贪婪", "Extreme Greed": "极度贪婪",
};

let cache: { v: FearGreed; at: number } | null = null;

export async function getFearGreed(): Promise<FearGreed | null> {
  if (cache && Date.now() - cache.at < 10 * 60_000) return cache.v;
  try {
    const r = await fetch("https://api.alternative.me/fng/?limit=1");
    const j = await r.json();
    const d = j?.data?.[0];
    if (!d) return null;
    const v: FearGreed = {
      value: Number(d.value),
      label: LABELS[d.value_classification] || d.value_classification || "",
      at: Number(d.timestamp) * 1000,
    };
    cache = { v, at: Date.now() };
    return v;
  } catch {
    return null;
  }
}

export function fngColor(value: number): string {
  if (value <= 25) return "#ef5350";
  if (value <= 45) return "#f7935a";
  if (value <= 55) return "#f7b500";
  if (value <= 75) return "#9ccc65";
  return "#26a69a";
}
