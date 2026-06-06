// 美股基本面 —— SEC EDGAR XBRL(data.sec.gov,无 key、CORS *,官方权威数据)。
//   companyconcept 端点按单一会计科目返回历年数值,取最近一份年报(10-K)口径。
// 仅美国注册公司有 XBRL 申报(部分 ADR/外国私企无)。

import { fetchViaProxy } from "./datasource";

// 常见美股 ticker→CIK(种子表);其余懒加载 SEC 全量映射(经代理,无 CORS)。
const CIK_SEED: Record<string, number> = {
  AAPL: 320193, MSFT: 789019, NVDA: 1045810, GOOGL: 1652044, GOOG: 1652044, AMZN: 1018724,
  META: 1326801, TSLA: 1318605, AVGO: 1730168, AMD: 2488, MU: 723125, INTC: 50863,
  NFLX: 1065280, CRM: 1108524, ORCL: 1341439, ADBE: 796343, QCOM: 804328, PYPL: 1633917,
  DIS: 1744489, BA: 12927, JPM: 19617, BAC: 70858, V: 1403161, MA: 1141391, KO: 21344,
  PEP: 77476, WMT: 104169, COST: 909832, XOM: 34088, CVX: 93410, PFE: 78003, MRK: 310158,
  UNH: 731766, HD: 354950, NKE: 320187, PLTR: 1321655, COIN: 1679788, UBER: 1543151,
};

let _cikMap: Record<string, number> | null = null;
async function resolveCik(ticker: string): Promise<number | null> {
  const t = ticker.toUpperCase();
  if (CIK_SEED[t]) return CIK_SEED[t];
  if (!_cikMap) {
    try {
      const raw = await fetchViaProxy("https://www.sec.gov/files/company_tickers.json");
      const m: Record<string, number> = {};
      for (const v of Object.values<any>(raw)) m[v.ticker] = v.cik_str;
      _cikMap = m;
    } catch { _cikMap = {}; }
  }
  return _cikMap[t] ?? null;
}

export interface FundRow { key: string; label: string; value: number | null; prev: number | null; yoyPct: number | null; unit: string; fy: string }
export interface Fundamentals { ticker: string; rows: FundRow[]; source: string }

// 每个指标的候选 us-gaap 科目(按优先级回退)
const METRICS: { key: string; label: string; tags: string[]; ns?: string; unit?: string }[] = [
  { key: "revenue", label: "营业收入", tags: ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"] },
  { key: "netIncome", label: "净利润", tags: ["NetIncomeLoss"] },
  { key: "grossProfit", label: "毛利", tags: ["GrossProfit"] },
  { key: "opCashFlow", label: "经营现金流", tags: ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"] },
  { key: "assets", label: "总资产", tags: ["Assets"] },
  { key: "liabilities", label: "总负债", tags: ["Liabilities"] },
  { key: "equity", label: "股东权益", tags: ["StockholdersEquity"] },
  { key: "eps", label: "摊薄EPS", tags: ["EarningsPerShareDiluted"], unit: "USD/shares" },
];

async function concept(cik: number, ns: string, tag: string): Promise<any | null> {
  const c = String(cik).padStart(10, "0");
  try {
    const r = await fetch(`https://data.sec.gov/api/xbrl/companyconcept/CIK${c}/${ns}/${tag}.json`);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

// 取最近两个完整年度:流量科目 frame=CY2024(全年合计),
// 资产负债表时点科目 frame=CY2024Q4I(财年末余额);均排除中间季度。
function annual(units: any[]): { last: any; prev: any } | null {
  const fy = units
    .filter((u) => typeof u.frame === "string" && /^CY\d{4}(Q4I)?$/.test(u.frame))
    .sort((a, b) => a.end.localeCompare(b.end));
  if (!fy.length) {
    // 退化:用 10-K / FY 口径
    const k = units.filter((u) => u.form === "10-K" && u.fp === "FY").sort((a, b) => a.end.localeCompare(b.end));
    if (!k.length) return null;
    return { last: k[k.length - 1], prev: k[k.length - 2] ?? null };
  }
  return { last: fy[fy.length - 1], prev: fy[fy.length - 2] ?? null };
}

export async function getFundamentals(ticker: string): Promise<Fundamentals | null> {
  const cik = await resolveCik(ticker);
  if (!cik) return null;

  const rows = await Promise.all(METRICS.map(async (m) => {
    const unitKey = m.unit ?? "USD";
    let data: any = null;
    for (const tag of m.tags) {
      data = await concept(cik, "us-gaap", tag);
      if (data?.units?.[unitKey]) break;
      data = null;
    }
    const row: FundRow = { key: m.key, label: m.label, value: null, prev: null, yoyPct: null, unit: unitKey, fy: "" };
    const units = data?.units?.[unitKey];
    if (units) {
      const a = annual(units);
      if (a) {
        row.value = a.last.val;
        row.fy = (a.last.frame || `FY${a.last.fy || a.last.end?.slice(0, 4)}`).replace("Q4I", "");
        row.prev = a.prev?.val ?? null;
        if (row.value != null && row.prev) row.yoyPct = ((row.value - row.prev) / Math.abs(row.prev)) * 100;
      }
    }
    return row;
  }));

  if (rows.every((r) => r.value == null)) return null;
  return { ticker: ticker.toUpperCase(), rows, source: "SEC EDGAR" };
}
