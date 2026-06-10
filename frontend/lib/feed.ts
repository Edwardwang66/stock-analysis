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
  // schema v2(2026-06-10 起,OpenClaw 渐进投递;全部可选,向后兼容)
  methodology?: {
    td9?: string;          // 如 "下行7(防衰竭)"
    week52?: string;       // 如 "距高 -8.5% · 78分位"
    supertrend?: string;   // 如 "空头·3日前翻转"
    chan?: string;         // 如 "下行笔·近中枢下沿·背驰迹象"
    rs?: number | null;    // RS 1-99
  };
  intraday_update?: { at: string; note: string };  // 盘中事件触发的增量更新
  _placeholder?: boolean;
}

// OpenClaw 盘中三报告(markdown 文本;存在性=投递状态)
export async function getAnalysisMd(kind: "premarket" | "intraday" | "close" | "", date: string): Promise<string | null> {
  const name = kind ? `analysis-${kind}-${date}.md` : `analysis-${date}.md`;
  for (const base of [REMOTE, LOCAL]) {
    try {
      const r = await fetch(`${base}/screener/${name}?t=${Date.now()}`, { cache: "no-store" });
      if (r.ok) {
        const t = await r.text();
        if (t && !t.startsWith("<!DOCTYPE") && !t.startsWith("404")) return t;
      }
    } catch { /* next */ }
  }
  return null;
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

// 盘中机器报告(live 分支,Winter 循环每5分钟推;Actions 备胎)
const LIVE_REMOTE = REMOTE.replace("/main/feed", "/live/feed");
export interface IntradayDoc {
  at: string; pool_size: number; quoted: number;
  summary: { up: number; down: number; median_pct: number | null;
             top: { symbol: string; pct: number }[]; bottom: { symbol: string; pct: number }[] };
  events: { symbol: string; type: string; detail: string; price: number }[];
  snapshot: Record<string, { price: number; pct: number | null; high: number | null; low: number | null }>;
}
export async function getIntradayLive(): Promise<IntradayDoc | null> {
  try {
    const r = await fetch(`${LIVE_REMOTE}/intraday/latest.json?t=${Date.now()}`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as IntradayDoc;
  } catch { /* live 分支可能还没建 */ }
  return null;
}

// 全宇宙评分表(daily_screener 输出;看板任意分档打标签用)
export interface ScoreTable {
  date: string; generated_at: string;
  scores: Record<string, number>;
  sectors?: Record<string, string>;  // GICS Sector(标普500 全量)
}
export const getScores = () => fetchJson<ScoreTable>("screener/scores.json");

// RS 相对强度排名(daily_screener 全宇宙百分位 1-99;methodology §6)
export interface RsTable {
  date: string; generated_at: string; universe: number;
  ranks: Record<string, { rs: number | null; r63: number | null; r252: number | null }>;
}
export const getRsRanks = () => fetchJson<RsTable>("signals/rs-ranks.json");

// 个股 AI 解读索引(OpenClaw 投递;updated_at 用于判断当日覆盖)
export interface NotesIndex {
  updated_at: string;
  symbols: { symbol: string; date: string; stance: string; view: string }[];
}
export const getNotesIndex = () => fetchJson<NotesIndex>("stock-notes/index.json");

// 跟踪基金 13F 持仓(funds-13f.yml 周检自动更新)
export interface FundPosition {
  ticker: string; name: string; type: string; value: number; shares: number; theme?: string;
}
export interface FundHoldings {
  fund: string; manager?: string; asof: string; filed: string; note?: string;
  positions: FundPosition[];
  summary?: { total_value: number; n_positions: number; themes?: string };
}
export const getFundHoldings = (slug: string) => fetchJson<FundHoldings>(`funds/${slug}.json`);

// 云端自选池(Edward 重点跟踪 = OpenClaw 每日必须全覆盖)
export interface RepoWatchlist { version: number; updated_at: string; symbols: string[] }
export const getRepoWatchlist = () => fetchJson<RepoWatchlist>("watchlist.json");

// 选股追踪历史(daily-digest.yml 每日入库;/tracker 页消费)
export interface TrackedPick { symbol: string; name?: string; score?: number; pick_price?: number }
export interface TrackedDay { date: string; generated_at?: string; threshold?: number; items: TrackedPick[] }
export const getScreenerHistory = () => fetchJson<TrackedDay[]>("screener/history.json");

// 周度胜率(Winter 本地 Postgres winrate.py,每周五收盘后投递)
export interface WinratePick { symbol: string; date: string; score?: number; pick_price?: number; current_price?: number; ret?: number }
export interface WinrateCell { n: number; win_rate: number | null; avg_ret: number | null; best?: WinratePick | null; worst?: WinratePick | null }
export interface WinrateDoc {
  generated_at?: string; total_picks?: number;
  windows?: Record<string, WinrateCell>;
  by_score_band?: Record<string, WinrateCell>;
}
export const getWinrate = () => fetchJson<WinrateDoc>("screener/winrate.json");

// 事件热度榜(Winter PG intraday_events 近7天聚合,每日收盘后投递)
export interface EventHeatItem { symbol: string; moves: number; highs: number; lows: number; total: number }
export interface EventHeatDoc { generated_at?: string; window_days?: number; items?: EventHeatItem[] }
export const getEventHeat = () => fetchJson<EventHeatDoc>("signals/event-heat.json");

// stance 历史(daily-digest 追加维护 30 天;翻转检测与个股轨迹同源)
export interface StanceDay { date: string; stances: Record<string, string> }
export const getStanceHistory = () => fetchJson<StanceDay[]>("stock-notes/stance-history.json");

export const getIndex = () => fetchJson<FeedIndex>("index.json");
export const getSignals = () => fetchJson<Signals>("signals/latest.json");
export const getMarket = () => fetchJson<MarketState>("market/state.json");
export const getFactory = () => fetchJson<FactoryStore>("factory/candidates.json");
export const getReport = (path: string) => fetchJson<FullReport>(path);

// feed 健康审计(scripts/audit_feed.py 产出;watchdog 每日两次刷新)
export interface HealthIssue { level: string; code: string; message: string }
export interface SourceFreshness { exists: boolean; asof?: string | null; age_days?: number | null }
export interface FeedHealth {
  checked_at: string; ok: boolean; critical: number; warn: number;
  issues: HealthIssue[]; sources: Record<string, SourceFreshness>;
}
export const getHealth = () => fetchJson<FeedHealth>("health.json");
