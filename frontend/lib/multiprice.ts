// 跨交易所暗号报价聚合 —— 同一币种并发多家免费源,演示「多源接入 + 互相校验」。
// 全部无 key、CORS OK:Binance / OKX / Coinbase / CoinPaprika。
export interface ExPrice { exchange: string; price: number | null; err?: string }

function base(code: string): string {
  return code.replace(/USDT$|USD$|BUSD$/i, "").toUpperCase();
}

// CoinPaprika 需要 id;内置常见映射
const PAPRIKA: Record<string, string> = {
  BTC: "btc-bitcoin", ETH: "eth-ethereum", SOL: "sol-solana", BNB: "bnb-binance-coin",
  XRP: "xrp-xrp", DOGE: "doge-dogecoin", ADA: "ada-cardano", AVAX: "avax-avalanche",
};

async function j(url: string): Promise<any> { const r = await fetch(url); if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }

export async function getCrossExchange(code: string): Promise<ExPrice[]> {
  const b = base(code);
  const jobs: { exchange: string; run: () => Promise<number> }[] = [
    { exchange: "Binance", run: async () => +(await j(`https://data-api.binance.vision/api/v3/ticker/price?symbol=${code}`)).price },
    { exchange: "OKX", run: async () => +(await j(`https://www.okx.com/api/v5/market/ticker?instId=${b}-USDT`)).data[0].last },
    { exchange: "Coinbase", run: async () => +(await j(`https://api.coinbase.com/v2/prices/${b}-USD/spot`)).data.amount },
  ];
  if (PAPRIKA[b]) jobs.push({ exchange: "CoinPaprika", run: async () => (await j(`https://api.coinpaprika.com/v1/tickers/${PAPRIKA[b]}`)).quotes.USD.price });

  return Promise.all(jobs.map(async (job) => {
    try { return { exchange: job.exchange, price: await job.run() }; }
    catch (e: any) { return { exchange: job.exchange, price: null, err: e?.message || "失败" }; }
  }));
}
