"use client";
// ❓ 功能地图:全站能力一页说明(给 Edward 和新用户的导览;口径细节见 routines/methodology.md)。
import Link from "next/link";
import LangSelect from "@/components/LangSelect";

const SECTIONS: { title: string; href: string; items: [string, string][] }[] = [
  {
    title: "📈 首页 · 多市场看板", href: "/",
    items: [
      ["每市场代表票", "美股50/A股49/港股50/加密25/日20/韩15/德15/英15,组内默认 12 张卡可展开"],
      ["指数条 + 30天迷你走势", "9 大指数;美股闭市时自动追加标普/纳指/道指期货卡"],
      ["🌙 夜盘体系", "闭市时:卡片夜盘行(隐含高低开)、热力图夜盘上色、夜盘异动行"],
      ["云端跟踪池", "OpenClaw 每日全析的 119 只,默认收起,▼ 展开为热力图"],
      ["语言切换", "右上「中 | EN」,330 条双语名称库,搜索框中英代码三路联想"],
    ],
  },
  {
    title: "📋 总览 /desk · 一页作战台", href: "/desk/",
    items: [
      ["📌 今日要点", "期货/亚洲异动、自选夜盘异动、自选缠论信号、≥80 名单进出、🚀领涨且加速、Winter 盘前观点"],
      ["⚡ 盘中流", "5 分钟机器报告(Winter 循环→Actions 自续链三层保障),来源徽章:Winter 在岗/备胎顶班"],
      ["🤖 OpenClaw 节拍", "盘前/盘中滚动/收盘前三报告状态 + 盘前要素行(期货/亚洲/BTC)"],
      ["🌙 24/7 夜盘代理", "Hyperliquid 永续:美股个股(实证 corr 0.965)、Pre-IPO(SpaceX/Anthropic/OpenAI)、商品、加密情绪"],
      ["🔥 高波动榜 / ☯ 缠论进行中", "Winter PG 7天事件聚合;最近3根内的买卖点信号"],
      ["📡 轮动象限(RRG)", "RS分位×63日动量四象限,▲▼=动量加速/减速,⭐金🦅青80+绿"],
      ["主表", "标签(⭐自选/🦅SALP/评分档)+行业+评分+RS(7日迁移↗↘)+夜盘列(闭市)+AI 状态,多维过滤排序"],
    ],
  },
  {
    title: "📄 个股页 /symbol", href: "/symbol/?s=US:NVDA",
    items: [
      ["📡 信号雷达", "一行秒读:九转/RS/52周/SuperTrend/缠论/Squeeze/AVWAP/夜盘 + 多空计票"],
      ["K线十件套", "MA·九转·SuperTrend·周Pivot·☯缠论(笔/中枢/买卖点)·AVWAP双锚·Squeeze·斐波·一目·VSA,开关随点随画"],
      ["☯ 缠论结构面板", "当前笔/中枢位置/背驰度(原文24课口径+确认三件套)/买卖点历史表(事后+5/+20根)"],
      ["🤖 AI 解读", "Winter 每日投递:多空逻辑/财报/新闻/风险 + 方法论徽章 + 📊基本面层(Codex 插件)+ 态度轨迹 ▲●▼"],
      ["对比叠加 / CSV 导出 / 盘前盘后", "百分比模式对比任意标的;K线一键导出"],
    ],
  },
  {
    title: "🎯 追踪 /tracker · 体系验证", href: "/tracker/",
    items: [
      ["当日持仓回看", "每天 ≥80 全量入库,逐日「选中后涨没涨」,实时估值"],
      ["🏆 周度胜率报告", "Winter·PG 全历史 picks:d1/d5/d20 窗口 + 分数段(周五自动)"],
      ["☯ 缠论买卖点统计", "全宇宙 7,359 样本真回测:三买 +20根 75% 最稳;进行中信号 40 个(周六重算)"],
    ],
  },
  {
    title: "📜 报告中心 /reports + ⏰ 告警 /alerts", href: "/reports/",
    items: [
      ["四类报告站内读", "盘前/盘中滚动/收盘前/收盘后,最近5个交易日投递状态 ✅/—"],
      ["价格提醒", "突破/跌破自动方向,30s 轮询,闭市时夜盘永续价也触发"],
    ],
  },
  {
    title: "🛰️ 情报 /intel + 📊 选股 /screener + 🔌 数据源 /sources", href: "/intel/",
    items: [
      ["量化引擎(Cycle 线)", "残差统计套利净值/holdout 终检/因子工厂/PBO 研究/健康审计/Hyperliquid 持仓面"],
      ["每日选股", "标普500∪纳指100 全扫描,v2 十因子 ≥80,RS/距52周高列,🏔 52周新高接近榜"],
      ["链路状态", "每个数据端口的来源/新鲜度/降级链"],
    ],
  },
  {
    title: "🤖 自动化(你不用做任何事)", href: "/desk/",
    items: [
      ["选股 22:30 UTC", "≥80 自动入池 → Winter 全量分析(技术面+基本面双层)"],
      ["日报 Issue 23:30 UTC", "选股表现/覆盖率/态度翻转/缠论信号/胜率,邮件推送"],
      ["盘前 12:40 要素包 → 13:30 Winter 盘前报告 → 13:40 看门狗", "缺投自动开 Issue 点名"],
      ["13F 周一/四查新", "SA LP 换仓自动进池;每 2h Hyperliquid 快照 + Pre-IPO 历史积累"],
      ["你的本地定时任务", "每交易日早 6:51 自动验收盘前节拍并向你汇报"],
    ],
  },
];

export default function HelpPage() {
  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <Link href="/desk/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>📋</Link>
        <h1>❓ 功能地图</h1>
        <span className="tag">全站能力一页速查 · 口径细节见 routines/methodology.md</span>
        <span style={{ marginLeft: "auto" }} />
        <LangSelect />
      </div>

      {SECTIONS.map((sec) => (
        <div className="section" key={sec.title}>
          <h2><Link href={sec.href} style={{ color: "var(--text)" }}>{sec.title}</Link>
            <Link href={sec.href} className="src" style={{ marginLeft: 10, color: "var(--accent)" }}>打开 →</Link></h2>
          <table>
            <tbody>
              {sec.items.map(([k, v]) => (
                <tr key={k}><th style={{ width: 180, fontWeight: 600 }}>{k}</th><td className="src" style={{ fontSize: 13 }}>{v}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      <div className="disclaimer">
        三个 agent 协作维护:看板侧 Claude(开发)· Winter/OpenClaw(每日分析投递+盘中循环+本地数据仓)· Cycle Claude(量化引擎)。
        全部数据与分析<strong>仅供信息参考,非投资建议</strong>。
      </div>
    </div>
  );
}
