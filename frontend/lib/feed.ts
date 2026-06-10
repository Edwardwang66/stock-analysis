// 情报馈送(feed/)客户端 —— 让静态网页「不断接受」例行任务 / OpenClaw 投递的报告。
//
// 取数策略(双源,前者新鲜、后者兜底):
//   1) 远端 raw GitHub(默认 main 分支 feed/):新 commit 即时可见,无需重建 Pages —— 这就是
//      「静态页不断接受」的关键(raw.githubusercontent 支持 CORS)。
//   2) 同源捆绑快照(public/feed/,部署时由 CI 从仓库 feed/ 拷入):远端失败时兜底,保证首屏有内容。
// 可用 NEXT_PUBLIC_FEED_BASE 覆盖远端地址。全部带时间戳 cache-bust。

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";
const REMOTE =
  process.env.NEXT_PUBLIC_FEED_BASE ||
  "https://raw.githubusercontent.com/edwardwang66/stock-analysis/main/feed";
const LOCAL = `${BASE_PATH}/feed`;

export interface FeedFreshness {
  last_report_at: string | null;
  market_data_asof: string | null;
  report_age_hours: number | null;
  data_age_days: number | null;
  stale: boolean;
}
export interface ReportSummary {
  id: string; kind: string; produced_at: string; asof_data: string | null;
  producer: string | null; agent_role: string | null;
  net_sharpe: number | null; verdict: string | null;
  n_alerts: number; n_candidates: number;
  contribution_type: string | null; contribution_summary: string | null;
  path: string;
}
export interface Contribution {
  at: string; producer: string | null; id: string; type: string; summary?: string;
  candidates_proposed?: number; candidates_accepted?: number; net_sharpe_delta?: number | null;
}
export interface FeedIndex {
  schema_version: string; updated_at: string;
  freshness: FeedFreshness;
  latest: { report: string | null; signals: string; market: string; factory: string;
            net_sharpe: number | null; verdict: string | null };
  stats: { total_reports: number; by_kind: Record<string, number>;
           by_producer: Record<string, number>; last_24h: number; last_7d: number };
  timeline: Record<string, number>;
  reports: ReportSummary[];
  contributions: Contribution[];
}
export interface Position {
  ticker: string; side: "LONG" | "SHORT"; weight: number; s_score?: number;
  halflife_days?: number; kappa?: number; hurst?: number; sector?: string;
}
export interface Signals {
  updated_at: string; source_report: string; asof: string;
  n_long: number; n_short: number; gross_leverage: number; net_exposure: number;
  positions: Position[];
}
export interface MarketState {
  updated_at: string; asof_data?: string; regime?: string;
  spy_above_200dma?: boolean | null; spy_vol_20d_annual?: number | null;
  breadth_pct_above_50dma?: number | null; crowding_proxy?: number | null;
  crowding_alert?: boolean; residual_dispersion?: number | null;
}
export interface Candidate {
  expr: string; hypothesis: string; incremental_ic?: number; post_cutoff?: boolean;
  pbo?: number; t_stat?: number; passed_gates?: boolean; decision?: string; note?: string;
  _source?: string; _at?: string;
}
export interface FactoryStore { updated_at: string | null; candidates: Candidate[] }
export interface Alert { level: string; code?: string; message: string; tickers?: string[] }
export interface FullReport {
  id: string; kind: string; produced_at: string; asof_data: string;
  producer: { name: string; model?: string; agent_role?: string; run_url?: string };
  engine?: any; book?: Signals; market_state?: MarketState;
  factory_candidates?: Candidate[]; alerts?: Alert[]; contribution?: any; notes?: string;
}

async function fetchJson<T>(rel: string): Promise<T | null> {
  const bust = `?t=${Date.now()}`;
  for (const base of [REMOTE, LOCAL]) {
    try {
      const r = await fetch(`${base}/${rel}${bust}`, { cache: "no-store" });
      if (r.ok) return (await r.json()) as T;
    } catch { /* try next source */ }
  }
  return null;
}

export interface StockNote {
  symbol: string; date: string; model?: string; producer?: string;
  stance: string; thesis: string; earnings?: string; news?: string;
  risks?: string; view: string; sources?: { title: string; url: string }[];
  _placeholder?: boolean;
}
export const getStockNote = (symbol: string) =>
  fetchJson<StockNote>(`stock-notes/${symbol.replace(":", "-")}.json`);

export interface ScreenerItem {
  symbol: string; name: string; indices: string[];
  score: number; verdict: string; price: number; change_pct: number;
  rsi14: number; bullish_signals: number;
}
export interface ScreenerList {
  date: string; generated_at: string; threshold: number;
  universe_size: number; scanned: number; count: number;
  items: ScreenerItem[]; note: string;
}
export const getScreener = () => fetchJson<ScreenerList>("screener/latest.json");

// 每日市场快照历史(market-snapshot.yml 工作日两次追加,保留 400 天)
export interface MarketSnapshot {
  date: string; at: string;
  indices: Record<string, { close: number | null; change_pct: number | null }>;
  fng: { value: number | null; label: string | null };
  btc: { price: number | null; change_pct_24h: number | null };
}
export const getMarketHistory = () => fetchJson<MarketSnapshot[]>("market/history.json");

export const getIndex = () => fetchJson<FeedIndex>("index.json");
export const getSignals = () => fetchJson<Signals>("signals/latest.json");
export const getMarket = () => fetchJson<MarketState>("market/state.json");
export const getFactory = () => fetchJson<FactoryStore>("factory/candidates.json");
export const getReport = (path: string) => fetchJson<FullReport>(path);
