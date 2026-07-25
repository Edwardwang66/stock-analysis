# 部署后端(彻底摆脱公共 CORS 代理限流)
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [deployment matrix](../../deployment-matrix.md); historical relative links below are preserved verbatim and may not resolve from this archived location.


静态前端默认在浏览器直连公开 API(美/港/A 走公共 corsproxy,易限流)。
把 `backend/` 部署到一个免费云,再让前端指向它,数据就稳定、快、且不再依赖公共代理。

已提供的部署文件:
- `render.yaml`(Render Blueprint,一键)
- `backend/Dockerfile`(Render/Railway/Fly/任意平台通用)
- `backend/Procfile` + `backend/runtime.txt`(Railway/Heroku 风格)

---

## 方案 A:Render(免费,推荐,最省事)

1. 注册 https://render.com(可用 GitHub 登录)。
2. 控制台 **New → Blueprint** → 连接本仓库 `Edwardwang66/stock-analysis`。
3. Render 自动读取根目录 `render.yaml`,创建一个 `stock-dashboard-api`(free)服务。
   - 构建:`pip install -r requirements.txt`(rootDir=backend)
   - 启动:`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - 健康检查:`/api/v1/health`
4. 部署完成后拿到地址,形如 `https://stock-dashboard-api.onrender.com`。
   打开 `https://<域名>/api/v1/health` 应返回 `{"ok":true}`。

> ⚠️ Render free 实例闲置会休眠,首次访问冷启动约 30–50 秒,属正常。

---

## 方案 B:Railway

1. https://railway.app → New Project → Deploy from GitHub repo。
2. 设 **Root Directory = `backend`**;Railway 会用 `Procfile` 启动(或用 `Dockerfile`)。
3. 生成公网域名(Settings → Networking → Generate Domain)。

## 方案 C:Fly.io / 任意支持 Docker 的平台

用 `backend/Dockerfile` 即可(容器监听 `$PORT`)。

---

## 让前端用上后端(关键最后一步)

1. 仓库 **Settings → Secrets and variables → Actions → Variables → New repository variable**
   - Name: `API_BASE`
   - Value: 你的后端地址(不带结尾斜杠),如 `https://stock-dashboard-api.onrender.com`
2. 触发一次前端重新部署(Actions → Deploy frontend to GitHub Pages → Run workflow,或随便推一次)。
3. 之后前端所有行情/分析/缠论都走你的后端:**更稳、更快、无公共代理限流**,且美股由后端直连 Yahoo(无需代理)。

> 想回退到"无后端、纯静态直连"模式:删除 `API_BASE` 变量再重部署即可。

---

## 本地自测后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# 浏览器/命令行:
curl localhost:8000/api/v1/health
curl "localhost:8000/api/v1/analysis?symbol=US:AAPL&range=2y"
curl "localhost:8000/api/v1/chan?symbol=CRYPTO:BTCUSDT&interval=1wk&range=2y"
```

## 指数(IDX)支持(2026-06-09)

后端已支持 `IDX:` 市场(Yahoo 代码直传):`IDX:^GSPC / ^IXIC / ^DJI / ^HSI / 000001.SS`。
**重新部署后端后生效**(Render 自动跟 main)。注意:前端当前对 IDX 一律走浏览器直连 Yahoo
(兼容未升级后端);后端确认升级后,可把 `frontend/lib/datasource.ts` 里两处
`!symbol.startsWith("IDX:")` 守卫移除,让指数也吃后端缓存。

```bash
curl "localhost:8000/api/v1/quotes?symbols=IDX:%5EGSPC,IDX:000001.SS"
curl "localhost:8000/api/v1/ohlcv?symbol=IDX:%5EHSI&range=1y"
```
