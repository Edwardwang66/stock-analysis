# 后端 — FastAPI(行情 + 非 LLM 技术分析)

多市场行情聚合 + 规则化技术分析。当前覆盖 **美股(Yahoo)+ 加密(Binance 镜像)**。

> ⚠️ GitHub Pages 是静态托管,**跑不了本后端**。本后端用于本地开发 / 未来部署到 Render/Railway/Fly 等;
> 静态前端默认浏览器直连公开 API,无需后端即可运行(见 `../frontend`)。

## 运行

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 接口

| 端点 | 说明 |
|------|------|
| `GET /api/v1/health` | 健康检查 |
| `GET /api/v1/quotes?symbols=US:AAPL,CRYPTO:BTCUSDT` | 批量实时报价 |
| `GET /api/v1/ohlcv?symbol=US:AAPL&interval=1d&range=1y` | K线 |
| `GET /api/v1/analysis?symbol=US:AAPL&range=1y` | **非 LLM 技术分析**(指标 + 多空信号 + 评分 + 中文摘要) |
| `GET /api/v1/chan?symbol=US:AAPL&interval=1d&range=2y` | **简化版缠论**(分型/笔/中枢/买卖点 1·2·3 + MACD 背驰) |

`interval` 支持 `1d`(日)/ `1wk`(周)/ `1h`(小时);多周期分析。

Symbol 格式:`US:AAPL` / `CRYPTO:BTCUSDT` / `HK:00700` / `CN:600519`。

## 让前端用后端

前端构建时设 `NEXT_PUBLIC_API_BASE=https://你的后端域名`,即从浏览器直连改为走后端(更稳、避开公共 CORS 代理)。

## 结构

```
app/
  models.py              # Symbol/Quote/Bar/OHLCV/AnalysisResult
  providers/             # 数据源适配器(可插拔)
    yahoo.py binance.py router.py base.py
  analysis/
    indicators.py        # 纯 Python:SMA/EMA/RSI/MACD/Bollinger/ATR…
    signals.py           # 规则化多空信号 + 评分 + 摘要(非 LLM)
  main.py                # FastAPI 入口 + CORS
```

技术分析逻辑与前端 `frontend/lib/{indicators,analysis}.ts` 保持一致。
