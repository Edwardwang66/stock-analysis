# 消幸存者偏差的数据源调研(2026-06-10)

> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.

> 背景:本仓所有回测结论都带「universe=当前成分股 → 幸存者偏差,结果高估」的诚实声明。
> 本调研回答:免费/低成本路径能把这个偏差消掉多少?

## 结论(TL;DR)

| 路径 | 成本 | 能消多少偏差 | 判定 |
|---|---|---|---|
| Yahoo/Stooq 等免费源 | $0 | **0%**——退市股价格史基本不存在,ticker 变更无记录 | 现状,只能声明偏差 |
| **Wikipedia 历史变更表重建时点成分(PIT membership)** | $0 | **部分**:能拿到「何时谁在指数里」,但退市者价格仍缺 → 可以①把横截面限制在时点成分、②**量化缺失率**(偏差大小可测) | **本仓下一步,免费可做** |
| FMP 旧版 survivorship-bias API | 低 | 部分(成分史,质量待验) | 备选 |
| EODHD(含退市价格/基本面) | ~$20-80/月 | 大部分 | 预算内可考虑 |
| **Norgate Data**(退市价格+历史成分+板块) | ~$50/月 | **基本全部**(US 股票) | **设计文档 §7 工具栈推荐,真解** |
| CRSP/Compustat(WRDS) | 学术授权 | 全部 | 不适用个人 |

## 关键事实

1. 免费源(Yahoo)没有退市股票数据,ticker 更名也无记录——这是行业共识,不是本仓数据管道的问题。
2. Wikipedia「List of S&P 500/600 companies」带 **Selected changes 表(日期+加入+移除)**,可重建
   2000 年至今的时点成分(Teddy Koker 2019 给出过完整做法)。
3. Norgate 提供退市股全量价格 + 历史指数成员资格 + 板块元数据,有 21 天试用;
   被设计文档明确列入推荐工具栈(「Norgate 无幸存者偏差回测/历史成分」)。

## 对本仓的行动建议(按性价比排序)

1. **免费第一步(下一迭代实现)**:`scripts/pit_membership.py` 从 Wikipedia 变更表重建
   S&P500 时点成分 → 回测横截面只取「当日确实在指数里且有数据」的票,
   并输出**缺失率曲线**(每个时点:应在成分里但无价格数据的比例)——把"偏差多大"从未知变成可测。
2. **量化偏差上界**:用缺失率 × 退市股平均超额(-X%,文献区间 1-4%/年)给现有结论打折,写进报告 notes。
3. **若上实盘前**:订 Norgate($50/月,设计文档成本估算内),替换 data.py 数据层,
   引擎与验证管线零改动(只换 loader)。

## Sources

- [EODHD: Addressing Survivorship Bias](https://eodhd.com/financial-academy/financial-faq/survivorship-bias-free-financial-analysis)
- [Norgate survivorship-bias-free database (Concretum)](https://concretumgroup.com/how-to-construct-a-survivorship-bias-free-database-in-norgate-using-python/)
- [Teddy Koker: Creating a Survivorship Bias-Free S&P 500 Dataset with Python](https://teddykoker.com/2019/05/creating-a-survivorship-bias-free-sp-500-dataset-with-python/)
- [FMP Survivorship Bias Free API (legacy)](https://site.financialmodelingprep.com/developer/docs/survivorship-bias-api)
- [Optuma: Survivorship Bias-Free Data](https://www.optuma.com/kb/optuma/data/end-of-day-data-options/survivorship-bias-free-data)
- [Elite Trader thread: unadjusted survivorship-bias-free EOD data](https://www.elitetrader.com/et/threads/looking-for-unadjusted-survivorship-bias-free-eod-data.382018/)
