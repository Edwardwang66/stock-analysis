# 系统优化记录(2026-06-09)
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [current architecture](../../current-architecture.md); historical relative links below are preserved verbatim and may not resolve from this archived location.


四个维度的全面优化:数据库、接口接入、响应、交互。**零新增依赖、零新增基础设施**,Render 免费实例照常跑。

## 1. 数据库(存储层)

| 改动 | 文件 | 效果 |
|------|------|------|
| SQLite 升级 WAL + `synchronous=NORMAL` + autocommit | `backend/app/cache.py` | 写入快一个量级,读写不互斥 |
| 过期宽限期(24h)+ `get_entry()` 返回 (值, 是否新鲜) | 同上 | 支撑 stale-while-revalidate |
| 周期清理 + 2 万条上限 | 同上 | /tmp 不会膨胀 |
| **K线持久入库 + 增量同步**(新增 `bars` / `bars_meta` 表) | `backend/app/barstore.py` | 历史 K线只拉一次;之后每次只补"尾巴"(日线补 1mo、分钟补 1d),外呼流量降 ~90% |
| 跨源时间戳归一(日/周/月 → UTC 零点) | 同上 | Yahoo/腾讯切换不产生重复 K线 |
| 分钟级数据保留 35 天自动清理 | 同上 | 控制库体积 |

`STORE_DB` 环境变量指到持久磁盘即可长期累积历史(默认 /tmp,重启等同冷缓存)。

## 2. 接口接入(数据源)

| 数据源 | 角色 | 文件 |
|--------|------|------|
| Yahoo | 美股主源;A股/港股备源 | `providers/yahoo.py` |
| **腾讯(qt.gtimg.cn)** | **A股/港股主源**(快、稳、支持一次请求批量报价);美股报价备源 | `providers/tencent.py`(新) |
| Binance | 加密主源(新增批量报价) | `providers/binance.py` |
| **OKX** | 加密备源 | `providers/okx.py`(新) |
| **Stooq** | 美股日线兜底(EOD) | `providers/stooq.py`(新) |

降级机制(`providers/router.py`):
- 每市场一条 provider 链,首选失败自动切下一个;
- 熔断:连续失败 3 次 → 冷却 120s 内直接跳过(不再反复等超时),全熔断时半开重试;
- `Unsupported` 能力不匹配跳过不计失败;
- 看板批量报价:20 个标的从 20 次外呼 → 通常 2-3 次(腾讯/Binance 批量接口)。

## 3. 响应(后端性能)

- **共享 `httpx.AsyncClient`**(lifespan 管理):连接池 + keep-alive,告别每请求新建连接/TLS 握手;
- **单飞合并**:同 key 并发请求只外呼一次,防外部源被击穿;
- **SWR**:报价过期 ≤10min 旧值直接回 + 后台刷新,下个轮询周期自然拿到新值;
- 外部源全挂 → 降级返回库内旧数据(source 标 `·stale`),好过 502;
- **GZip**(K线 JSON 50KB+ → ~5KB)+ `Cache-Control: stale-while-revalidate` 响应头;
- analysis/chan/chips/moneyflow 计算结果短缓存(键含最新 bar 时间戳,数据更新自动失效);
- 修复双层缓存键不一致问题(原 store 与 router 各缓存一份)。

## 4. 交互(前端)

- **秒开**:报价 + K线持久化到 localStorage,刷新/重开页面先用上次数据渲染,再后台更新(`getCachedQuotesSync`);
- **30s 自动刷新**:页面隐藏自动暂停,回到前台立即补一次;
- **骨架屏**替代"加载中…"文字(`prefers-reduced-motion` 适配);
- 断网/源全挂降级:10min 内旧报价、24h 内旧 K线兜底展示;
- K线 localStorage 上限 30 组序列,LRU 淘汰。

## 验证

```bash
cd backend
python tests/test_backend.py   # 15 项:缓存/单飞/增量/降级/熔断/批量
python tests/test_api.py       # 13 项:端点/GZip/Cache-Control/错误码
cd ../frontend && npx tsc --noEmit && npx next build   # 编译通过
```

注意:`requirements.txt` 无变化;部署无需任何配置改动。

---

## 2026-06-09 第二轮:看板一致性 + 指数 + 渐进加载

### 一致性修复(用户报告)
- 首页默认 tab `CRYPTO` → `ALL`:打开即并行加载全部市场;
- `getQuotes` 新增 `onPartial` 渐进回调:每个报价一到立即上屏,快源(加密直连/缓存)不再等最慢的公共代理;
- 看板统计(已加载/涨/跌/均值)与实际渲染集合(自选+当前tab)同源,数字与卡片一一对应;
- QuoteCard / Heatmap 改纯展示组件,删除"各自拉数据"的死代码路径(消除同屏数值漂移);
- 涨跌幅语义标注:加密=24h 滚动,股票=较前收盘(卡片"24h/当日"、热力图 tooltip、页脚);
- screener 页加载后经统一数据层拉实时价,覆盖清单生成时的冻结价(跨页一致,上限 60 只);
- 个股页:日/周线用实时报价修正末根 bar,页头价、K线末根、技术指标三者同源(缓存仍存原始数据)。

### 新能力
- **指数市场 IDX**:前后端均支持 `IDX:^GSPC / ^IXIC / ^DJI / ^HSI / 000001.SS`(Yahoo 代码直传);
  首页指数概览行(60s 自刷新,不计入涨跌统计),搜索联想含指数;前端对 IDX 直走浏览器
  Yahoo 路径(兼容未升级的旧后端);
- **开闭市状态**:`lib/marketstatus.ts` 按交易所时区推算 盘中/盘前/盘后/午休/休市(不含节假日),
  显示在分组标题与单市场视图;
- tab / 排序选择 localStorage 记忆(挂载后恢复,避免水合不一致);
- 「全部」视图按市场分组渲染。

### 验证
- `python tests/test_backend.py` 19 项(新增 IDX 4 项)、`python tests/test_api.py` 13 项、`tsc --noEmit` + `next build` 通过。

### 2026-06-09 第 5-13 轮(同日追加)
- 行情卡片 ★ 一键自选、失败单卡重试;「全部」视图组内涨/跌/均值统计;
- 今日强弱 Top3 涨跌榜(报价派生,零请求);指数概览行;开闭市徽标;
- ⏰ 价格提醒:lib/alerts.ts 纯前端,30s 循环检查,Notification + 横幅,一次性触发;
- K线对比叠加(PriceScaleMode.Percentage 归一);ATR/KDJ/量比展示指标(不动评分);
- 📰 个股新闻:Yahoo RSS(fetchTextViaProxy),全市场代码映射,失败静默;
- 自选+提醒 JSON 导入导出;PWA manifest;移动端 @640px;搜索 / 快捷键;个股页动态标题;
- 热力图按市场分区;IDX 页隐藏微观模块;sources 页后端健康面板;feed 陈旧首页提示;
- 修复:getQuotes 后端批量按 50 分块(screener 60 只整批 422);
- 协作流程:远端被 Actions 推进时 rebase + 解冲突再推(AINote 与本地新模块共存先例)。
