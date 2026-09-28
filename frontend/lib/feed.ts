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

// 模块级 30s 内存缓存 + 单飞:同页多组件请求同一 feed 时只发一次网络请求
const _mem = new Map<string, { at: number; data: unknown }>();
const _inflight = new Map<string, Promise<unknown>>();
const FEED_TTL = 30_000;

async function fetchJson<T>(rel: string): Promise<T | null> {
  const hit = _mem.get(rel);
  if (hit && Date.now() - hit.at < FEED_TTL) return hit.data as T;
  const fly = _inflight.get(rel);
  if (fly) return fly as Promise<T | null>;
  const p = (async () => {
    const bust = `?t=${Date.now()}`;
    for (const base of [REMOTE, LOCAL]) {
      try {
        const r = await fetch(`${base}/${rel}${bust}`, { cache: "no-store" });
        if (r.ok) {
          const data = (await r.json()) as T;
          _mem.set(rel, { at: Date.now(), data });
          return data;
        }
      } catch { /* try next source */ }
    }
    return null;
  })().finally(() => _inflight.delete(rel));
  _inflight.set(rel, p);
  return p as Promise<T | null>;
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
  // v2.1(2026-06-10):Codex public-equity-investing 插件的基本面层(全部可选,松约束)
  fundamentals?: {
    valuation?: string;   // 估值:PE/PS/EV-EBITDA vs 同行
    quality?: string;     // 质地:毛利率/FCF/盈利质量趋势
    catalysts?: string;   // 催化剂:财报日/产品/回购/政策
    peers?: string;       // 同行对比一句话
    verdict?: string;     // 基本面结论:强/中性/弱 + 一句话
  };
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
  at: string; producer?: string; pool_size: number; quoted: number;
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
  ranks: Record<string, { rs: number | null; r63: number | null; r126?: number | null; r252: number | null; w52dd?: number | null; w52pos?: number | null }>;
}
export const getRsRanks = () => fetchJson<RsTable>("signals/rs-ranks.json");

// RS 历史(daily_screener 每日追加 40 天;分位迁移趋势)
export interface RsHistoryDay { date: string; rs: Record<string, number> }
export const getRsHistory = () => fetchJson<RsHistoryDay[]>("signals/rs-history.json");

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


// 盘前隔夜要素包(premarket-pack.yml 12:40 UTC;盘前报告与 /desk 共用)
export interface OvernightBlock { name: string; price: number; pct: number }
export interface OvernightDoc {
  date?: string; generated_at?: string;
  futures?: Record<string, OvernightBlock>; asia?: Record<string, OvernightBlock>;
  europe?: Record<string, OvernightBlock>; crypto?: Record<string, { price: number; pct: number }>;
  yesterday_movers?: { symbol: string; pct: number; price?: number }[];
  perp_movers?: { symbol: string; kind?: string; mark?: number; chg24h: number; funding_apr?: number | null }[];
}
export const getOvernight = () => fetchJson<OvernightDoc>("intraday/overnight.json");

// 事件热度榜(Winter PG intraday_events 近7天聚合,每日收盘后投递)
export interface EventHeatItem { symbol: string; moves: number; highs: number; lows: number; total: number }
export interface EventHeatDoc { generated_at?: string; window_days?: number; items?: EventHeatItem[] }
export const getEventHeat = () => fetchJson<EventHeatDoc>("signals/event-heat.json");

// Pre-IPO/24-7 历史(hyperliquid-monitor 每 2h 追加 preipo_history.py)
export interface PreipoPoint { at: string; marks: Record<string, number> }
export const getPreipoHistory = () => fetchJson<PreipoPoint[]>("crypto/preipo-history.json");

// 缠论买卖点全宇宙统计(chan-stats.yml 每周六;chan_engine.py 与前端 chan.ts 同口径)
export interface ChanStatCell { n: number; win_rate: number | null; avg_ret: number | null }
export interface ChanStatsDoc {
  generated_at?: string; universe?: number;
  stats?: Record<string, { d5: ChanStatCell; d20: ChanStatCell }>;
  active?: { symbol: string; kind: string; price: number }[];
}
export const getChanStats = () => fetchJson<ChanStatsDoc>("signals/chan-stats.json");

// stance 历史(daily-digest 追加维护 30 天;翻转检测与个股轨迹同源)
export interface StanceDay { date: string; stances: Record<string, string> }
export const getStanceHistory = () => fetchJson<StanceDay[]>("stock-notes/stance-history.json");

// 深度研究简报(scripts/deep_research.py 产出;确定性引擎,不调用 LLM)
// 四段流水:立题 → 并发取证 → 对抗验证(red-team 反驳器) → 合成。
// 被反驳(refuted)与未验证(unverified)的论断一律保留在简报里供审计,前端也照实展示。
export interface ResearchEvidence {
  artifact: string; field: string; value?: number | string | boolean | null; asof?: string | null;
}
export interface ResearchRefutation { code: string; message: string }
export interface ResearchClaim {
  id: string; role: string; question: string; statement: string;
  metric?: string | null; value?: number | string | boolean | null; unit?: string | null;
  direction?: string | null; n?: number | null; severity?: string | null;
  cites?: string[]; evidence?: ResearchEvidence[];
  verdict?: string | null; refutations?: ResearchRefutation[];
}
export interface ResearchQuestion {
  id: string; role: string; title: string; needs?: string[];
  test?: string | null; triggered_by?: string | null; answered?: boolean;
}
export interface ResearchOpenQuestion { id: string; title: string; reason: string; missing?: string[] }
export interface ResearchNextAction { priority: string; action: string; because: string }
export interface ResearchCoverageArtifact {
  key: string; path: string; exists: boolean; asof?: string | null; age_days?: number | null;
}
export interface ResearchBrief {
  schema_version: string; id: string; kind: string; produced_at: string; asof_data?: string | null;
  producer: { name: string; agent_role?: string; method?: string; run_url?: string };
  run?: { workers?: number; roles?: string[]; questions_derived?: number; lenses_run?: number;
          lenses_failed?: number; reports_scanned?: number; duration_ms?: number };
  questions?: ResearchQuestion[];
  findings?: ResearchClaim[];
  refuted?: ResearchClaim[];
  verdicts?: { confirmed: number; refuted: number; unverified: number };
  open_questions?: ResearchOpenQuestion[];
  next_actions?: ResearchNextAction[];
  alerts?: Alert[];
  coverage?: { artifacts?: ResearchCoverageArtifact[]; artifacts_read?: number; artifacts_missing?: number };
  notes?: string;
}
export interface ResearchBriefSummary {
  id: string; produced_at: string; asof_data?: string | null; headline?: string | null;
  n_questions?: number; n_findings?: number;
  confirmed?: number; refuted?: number; unverified?: number;
  n_alerts?: number; path: string;
}
export interface ResearchIndex {
  schema_version: string; updated_at: string; note?: string;
  latest?: ResearchBriefSummary | null;
  stats?: { total_briefs?: number; by_role?: Record<string, number>; last_7d?: number };
  briefs?: ResearchBriefSummary[];
  open_questions?: ResearchOpenQuestion[];
}
export const getResearchIndex = () => fetchJson<ResearchIndex>("research/index.json");
export const getResearchBrief = (path: string) => fetchJson<ResearchBrief>(path);

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

// Hyperliquid 衍生品情报(scripts/hyperliquid_monitor.py,2h 定时)
export interface HlAsset {
  symbol: string; dex?: string; kind?: string; mark: number;
  chg24h?: number | null; vol24h_usd: number; funding_apr?: number;
}
export interface HlCoinBrief {
  coin: string; funding_apr: number; oi_usd: number; premium: number;
  chg24h?: number | null; vol24h_usd: number;
}
export interface CryptoState {
  updated_at: string; source: string;
  crypto?: {
    n_perps: number; n_liquid: number; btc?: HlCoinBrief; eth?: HlCoinBrief;
    pct_positive_funding: number; total_oi_usd: number;
    oi_change_since_last?: number | null; funding_extremes: HlCoinBrief[];
    crowding_flag: boolean;
  } | null;
  venues?: { n_compared: number; n_dislocated: number; threshold_apr: number;
             top: { coin: string; hl_apr: number; binance_apr: number; spread_apr: number }[] } | null;
  equity_perps?: { dexes_alive: string[]; n_assets: number; indices: HlAsset[];
                   stocks: HlAsset[]; commodities: HlAsset[]; private: HlAsset[]; note: string } | null;
  errors?: string[];
}
export const getCryptoState = () => fetchJson<CryptoState>("crypto/state.json");
