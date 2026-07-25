# 数据模型 / API 契约
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [current architecture](../../current-architecture.md) and the [backend README](../../../backend/README.md); historical prose below is preserved, and moved local link targets are redirected to their current repository locations.


> 配套:[`architecture.md`](../../architecture.md)(§5 数据服务层 · §6 AI 层)· [`roadmap.md`](roadmap.md)
> 目的:把架构里的"统一数据模型 + 可插拔适配器"落成**具体 schema 与 REST/WS 契约**,供 P1 编码直接对照。

---

## 1. 统一 Symbol 编码

跨市场统一标识:`MARKET:CODE`。

| 市场 | 前缀 | 示例 | 备注 |
|------|------|------|------|
| 美股 | `US` | `US:AAPL` | |
| 港股 | `HK` | `HK:00700` | 5 位数字代码 |
| A股 | `CN` | `CN:600519` / `CN:000001` | 沪/深 |
| 加密 | `CRYPTO` | `CRYPTO:BTCUSDT` | 交易对 |

```python
# 解析/构造
@dataclass(frozen=True)
class Symbol:
    market: Literal["US", "HK", "CN", "CRYPTO"]
    code: str
    def __str__(self) -> str: return f"{self.market}:{self.code}"
    @classmethod
    def parse(cls, s: str) -> "Symbol":
        market, code = s.split(":", 1)
        return cls(market, code)  # type: ignore
```

---

## 2. 核心数据模型(Pydantic 风格)

```python
class Quote(BaseModel):              # 实时/快照报价
    symbol: str                      # "US:AAPL"
    price: Decimal
    change: Decimal                  # 涨跌额
    change_pct: float                # 涨跌幅 %
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    prev_close: Decimal | None
    volume: int | None
    currency: str                    # USD / HKD / CNY / USDT
    market_state: Literal["pre", "open", "post", "closed"]
    ts: datetime                     # 报价时间(UTC)
    source: str                      # 数据来源(合规署名/降级追踪)

class Bar(BaseModel):                # K线/OHLCV 单根
    ts: datetime                     # 该 bar 起始时间(UTC)
    open: Decimal; high: Decimal; low: Decimal; close: Decimal
    volume: int

class Fundamentals(BaseModel):       # 基本面(P2)
    symbol: str
    market_cap: Decimal | None
    pe: float | None
    pb: float | None
    eps: Decimal | None
    dividend_yield: float | None
    revenue_ttm: Decimal | None
    currency: str
    as_of: date | None
    source: str

class NewsItem(BaseModel):           # 新闻/舆情(P4)
    id: str
    symbol: str | None               # 关联标的(可空=大盘新闻)
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None
    sentiment: Literal["positive", "neutral", "negative"] | None
    sentiment_score: float | None    # FinBERT 输出 [-1,1]
```

**约定**:所有时间统一 **UTC**(前端按市场时区展示);金额用 `Decimal` 避免浮点误差;每条记录带 `source` 字段(合规署名 + 多源降级排查)。

---

## 3. DataProvider 适配器接口

```python
class DataProvider(Protocol):
    name: str
    markets: set[str]                       # 支持的市场
    commercial_redistribution: bool         # 是否可对外重分发(见 compliance.md)

    async def get_quote(self, s: Symbol) -> Quote: ...
    async def get_ohlcv(self, s: Symbol, interval: str, range: str) -> list[Bar]: ...
    async def get_fundamentals(self, s: Symbol) -> Fundamentals | None: ...
    async def get_news(self, s: Symbol | None) -> list[NewsItem]: ...

# interval: 1m 5m 15m 1h 1d 1wk 1mo
# range:    1d 5d 1mo 3mo 6mo 1y 5y max
```

**ProviderRouter**:按 `Symbol.market` + 能力 + 健康状态选主源,失败降级备源;对外 API 仅返回 `commercial_redistribution=True` 的源数据(或已授权源)。

---

## 4. REST API 契约(OpenAPI 草图)

基址 `/api/v1`。鉴权:`Authorization: Bearer <JWT>`(只读行情可匿名 + 限流)。

```yaml
openapi: 3.1.0
info: { title: Stock Dashboard API, version: 0.1.0 }
paths:
  /quotes:
    get:
      summary: 批量实时报价
      parameters:
        - { name: symbols, in: query, required: true,
            description: "逗号分隔,如 US:AAPL,CRYPTO:BTCUSDT", schema: { type: string } }
      responses:
        "200": { description: OK, content: { application/json:
          { schema: { type: array, items: { $ref: "#/components/schemas/Quote" } } } } }

  /ohlcv:
    get:
      summary: K线/历史
      parameters:
        - { name: symbol, in: query, required: true, schema: { type: string } }
        - { name: interval, in: query, schema: { type: string, default: "1d" } }
        - { name: range, in: query, schema: { type: string, default: "1y" } }
      responses:
        "200": { description: OK, content: { application/json:
          { schema: { type: object, properties: {
              symbol: { type: string },
              interval: { type: string },
              bars: { type: array, items: { $ref: "#/components/schemas/Bar" } } } } } } }

  /moneyflow:
    get:
      summary: 资金流向 / 主力资金(估算,对标富途看板)
      description: >
        分钟 K 线成交额按分位数分档(特大/大/中/小),收盘涨跌定方向,主力=特大+大。
        ⚠️ 非真实逐笔(Level-2)数据,趋势性估算,非投资建议。
      parameters:
        - { name: symbol, in: query, required: true, schema: { type: string } }
        - { name: interval, in: query, schema: { type: string, default: "5m" } }
        - { name: range, in: query, schema: { type: string, default: "1d" } }
      responses:
        "200": { description: OK, content: { application/json: { schema: { type: object, properties: {
            inflow: { type: number }, outflow: { type: number }, net: { type: number },
            main_inflow: { type: number }, main_outflow: { type: number }, main_net: { type: number },
            buckets: { type: array, items: { type: object, properties: {
              name: { type: string }, inflow: { type: number }, outflow: { type: number }, net: { type: number } } } },
            series: { type: array, items: { type: object, properties: {
              time: { type: integer }, cum_all: { type: number }, cum_main: { type: number } } } },
            note: { type: string } } } } } }

  /chips:
    get:
      summary: 筹码分布(成本分布 · 估算)
      description: >
        历史日 K 量价堆积 + 时间衰减,得获利比例 / 平均成本 / 支撑位 / 压力位。
        ⚠️ 非真实持仓成本,估算参考。
      parameters:
        - { name: symbol, in: query, required: true, schema: { type: string } }
        - { name: interval, in: query, schema: { type: string, default: "1d" } }
        - { name: range, in: query, schema: { type: string, default: "1y" } }
      responses:
        "200": { description: OK, content: { application/json: { schema: { type: object, properties: {
            price: { type: number }, profit_ratio: { type: number }, avg_cost: { type: number },
            support: { type: number }, resistance: { type: number },
            conc90: { type: object }, levels: { type: array }, note: { type: string } } } } } }

  /fundamentals/{symbol}:
    get: { summary: 基本面, responses: { "200": { description: OK,
      content: { application/json: { schema: { $ref: "#/components/schemas/Fundamentals" } } } },
      "404": { description: 无数据 } } }

  /news:
    get:
      summary: 新闻+情绪
      parameters:
        - { name: symbol, in: query, required: false, schema: { type: string } }
        - { name: limit, in: query, schema: { type: integer, default: 20 } }
      responses: { "200": { description: OK, content: { application/json:
        { schema: { type: array, items: { $ref: "#/components/schemas/NewsItem" } } } } } }

  /market/overview:
    get:
      summary: 市场总览(指数 + 涨跌热力图数据)
      parameters:
        - { name: market, in: query, schema: { type: string, enum: [US, HK, CN, CRYPTO] } }
      responses: { "200": { description: OK } }

  /ai/chat:
    post:
      summary: AI 助手(SSE 流式)
      description: 返回 text/event-stream;AI 经工具取真实数据,回答带引用。
      requestBody: { content: { application/json: { schema: { type: object, properties: {
        message: { type: string },
        symbols: { type: array, items: { type: string } },
        session_id: { type: string } } } } } }
      responses: { "200": { description: "SSE 流", content: { text/event-stream: {} } } }
```

**统一错误体**:
```json
{ "error": { "code": "RATE_LIMITED", "message": "...", "retry_after": 30 } }
```
常见 code:`BAD_SYMBOL` / `NOT_FOUND` / `RATE_LIMITED` / `UPSTREAM_UNAVAILABLE` / `UNAUTHORIZED`。

---

## 5. WebSocket / SSE 契约

### 行情推送(WebSocket)`/ws/quotes`
```jsonc
// 客户端订阅
{ "action": "subscribe", "symbols": ["CRYPTO:BTCUSDT", "US:AAPL"] }
// 服务端推送(单条 Quote 增量)
{ "type": "quote", "data": { /* Quote */ } }
// 取消
{ "action": "unsubscribe", "symbols": ["US:AAPL"] }
```
- 加密:后端订阅 Binance WS 转发。
- 美/港/A:看板用轮询/快照(实时受数据源与成本限制,见 cost-estimate)。

### AI 流式(SSE)`/api/v1/ai/chat`
```
event: token        data: {"text":"苹果"}
event: tool_call    data: {"name":"get_ohlcv","args":{"symbol":"US:AAPL"}}
event: citation     data: {"source":"Finnhub","url":"..."}
event: done         data: {"usage":{"input_tokens":5300,"output_tokens":1500}}
```

---

## 6. 存储 schema 要点(PostgreSQL + TimescaleDB)

```sql
-- 时序行情:TimescaleDB hypertable
CREATE TABLE bars (
  symbol      text        NOT NULL,
  interval    text        NOT NULL,
  ts          timestamptz NOT NULL,
  open numeric, high numeric, low numeric, close numeric, volume bigint,
  source      text        NOT NULL,
  PRIMARY KEY (symbol, interval, ts)
);
SELECT create_hypertable('bars', 'ts');
-- 连续聚合做日线/周线,压缩旧数据

CREATE TABLE instruments (        -- 标的元数据
  symbol text PRIMARY KEY, market text, name text, currency text,
  exchange text, type text        -- equity / crypto / index
);

CREATE TABLE news (
  id text PRIMARY KEY, symbol text, title text, url text, source text,
  published_at timestamptz, summary text,
  sentiment text, sentiment_score real
);
-- 用户/自选/会话:常规表;新闻&财报原文向量入 pgvector
```

- **Redis**:`quote:{symbol}` 短 TTL 缓存 + 限流计数器 + AI 会话。
- **pgvector**:`embeddings(doc_id, symbol, chunk, embedding vector)` 供 RAG 引用溯源。

---

## 7. 与 AI 工具层的映射

AI 编排器(Claude)调用的工具**直接复用上面的 REST/服务层**,保证 AI 与看板"同一份真实数据":

| AI 工具 | 背后 | 说明 |
|---------|------|------|
| `get_quote(symbol)` | `/quotes` | 实时报价 |
| `get_ohlcv(symbol,interval,range)` | `/ohlcv` | 走势 |
| `get_fundamentals(symbol)` | `/fundamentals` | 估值/财务 |
| `get_news(symbol)` | `/news` | 舆情 |
| `compute_indicator(...)` | pandas-ta | 技术指标 |

> 也可接现成 MCP(financial-datasets / Alpha Vantage / CoinGecko,见研究报告)以减少自研;统一在工具层封装。
