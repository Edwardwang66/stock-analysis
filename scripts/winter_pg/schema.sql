-- Winter 本地 Postgres 数据仓(2026-06-10)。角色:OpenClaw 侧分析仓,不对公网开放。
-- 价值:tracker 60天/事件不归档/全量K线 这些"git 当数据库"的限制全部解除,
--       支撑 RS 全市场排名、跨日事件统计、信号回测。产出仍聚合成 JSON push 进 feed/。
CREATE TABLE IF NOT EXISTS bars (
  symbol TEXT NOT NULL, interval TEXT NOT NULL, ts TIMESTAMPTZ NOT NULL,
  open DOUBLE PRECISION, high DOUBLE PRECISION, low DOUBLE PRECISION,
  close DOUBLE PRECISION, volume DOUBLE PRECISION,
  PRIMARY KEY (symbol, interval, ts)
);
CREATE TABLE IF NOT EXISTS intraday_snapshots (
  at TIMESTAMPTZ NOT NULL, symbol TEXT NOT NULL,
  price DOUBLE PRECISION, pct DOUBLE PRECISION,
  high DOUBLE PRECISION, low DOUBLE PRECISION,
  PRIMARY KEY (at, symbol)
);
CREATE TABLE IF NOT EXISTS intraday_events (
  at TIMESTAMPTZ NOT NULL, symbol TEXT NOT NULL, type TEXT NOT NULL,
  detail TEXT, price DOUBLE PRECISION,
  PRIMARY KEY (at, symbol, type)
);
CREATE TABLE IF NOT EXISTS notes (
  symbol TEXT NOT NULL, date DATE NOT NULL, stance TEXT, view TEXT,
  payload JSONB NOT NULL, PRIMARY KEY (symbol, date)
);
CREATE TABLE IF NOT EXISTS scores (
  date DATE NOT NULL, symbol TEXT NOT NULL, score INT, sector TEXT,
  PRIMARY KEY (date, symbol)
);
CREATE TABLE IF NOT EXISTS picks (
  date DATE NOT NULL, symbol TEXT NOT NULL, score INT, pick_price DOUBLE PRECISION,
  PRIMARY KEY (date, symbol)
);
CREATE TABLE IF NOT EXISTS fund_positions (
  asof DATE NOT NULL, ticker TEXT NOT NULL, name TEXT, type TEXT,
  value BIGINT, shares BIGINT, PRIMARY KEY (asof, ticker)
);
CREATE INDEX IF NOT EXISTS idx_events_symbol ON intraday_events (symbol, at DESC);
CREATE INDEX IF NOT EXISTS idx_bars_symbol ON bars (symbol, interval, ts DESC);
