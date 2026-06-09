"""OpenClaw 投递参考客户端 —— 外部 agent 如何把分析结果 POST 回本 GitHub 仓。

OpenClaw(外部 Claude/agent 编队)在自己的环境里跑分析,产出一份符合 report.schema.json 的报告,
用本客户端签名 + 投递到本仓 feed/inbox/,经 CI(scripts/validate_feed.py)校验后并入 feed/reports/。

三种投递通道(详见 docs/openclaw-integration.md):
  --mode github-api : 用 GitHub Contents API 把文件 PUT 到 feed/inbox/(需 GITHUB_TOKEN,最小权限)。
  --mode dispatch   : 触发 repository_dispatch 事件,由工作流接收(payload 内含报告)。
  --mode local      : 直接写本地 feed/inbox/(在仓内/CI 内测试用)。

签名:设 FEED_HMAC_SECRET 后自动对报告做 HMAC-SHA256。无第三方依赖(urllib)。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_lib as fl  # noqa: E402

DEFAULT_REPO = "edwardwang66/stock-analysis"


ROLES = ["residual-analyst", "crowding-monitor", "event-risk", "factor-factory", "red-team"]


def _residual_analyst() -> dict:
    """残差/协整健康度:κ、半衰期、Hurst 漂移,协整断裂剔除信号。"""
    return {
        "market_state": {"residual_dispersion": 0.018, "crowding_proxy": 0.39},
        "alerts": [
            {"level": "warning", "code": "cointegration_break",
             "message": "XOM 残差 Hurst 0.61>0.55 且 κ 滚动下降 38%:协整漂向随机游走,建议从套利簿剔除"
                        "(R2 禁止『会回归』式向下加仓)。", "tickers": ["XOM"]},
            {"level": "info", "code": "residual_health",
             "message": "半衰期中位数 9.2 交易日(在 5–25 区间内),残差离散度回升,均值回归机会改善。", "tickers": []},
        ],
        "contribution": {"type": "risk_alert", "summary": "1 个协整断裂剔除信号 + 残差健康度回升。"},
        "notes": "残差=对 [SPY,行业ETF] 滚动回归;κ/半衰期/Hurst 用滚动窗口估计,全程无未来函数。",
    }


def _crowding_monitor() -> dict:
    """拥挤/同质化:同类持仓重叠、尾部相关、short interest、Amihud 趋势。"""
    return {
        "market_state": {"crowding_proxy": 0.58, "crowding_alert": True, "breadth_pct_above_50dma": 0.42},
        "alerts": [{"level": "warning", "code": "crowding",
                    "message": "动量/低波因子拥挤度上升(同类基金载荷相关 0.58>0.55、半导体持仓重叠走高):"
                               "按 R7 应『先于人群』预防性减对应敞口 0.2x,勿做去杠杆级联中的边际持有者。",
                    "tickers": ["NVDA", "AMD", "AVGO"]}],
        "contribution": {"type": "risk_alert", "summary": "拥挤告警:建议预防性降动量/低波敞口(尾部风险,非做空信号)。"},
        "notes": "拥挤代理=持仓重叠+尾部特定收益相关+short interest+Amihud 非流动性趋势(§7.2)。拥挤是尾部风险信号。",
    }


def _event_risk() -> dict:
    """事件日历:财报、FOMC/CPI、指数重构、SSR。仅标注/回避,不做方向 alpha(D4)。"""
    return {
        "alerts": [
            {"level": "warning", "code": "macro_event",
             "message": "下周二 CPI、周三 FOMC:组合层临时收紧毛杠杆 0.2x,事件窗口避免大额建仓。", "tickers": []},
            {"level": "info", "code": "earnings",
             "message": "NVDA 财报 T+2 盘后:统计套利簿该名敞口建议降至 ≤1% NAV,防跳空。", "tickers": ["NVDA"]},
            {"level": "info", "code": "ssr",
             "message": "昨日 RUN 触发 SSR(Reg SHO Rule 201):今日+次日空头腿仅 uptick 成交,下单前 locate 校验。",
             "tickers": ["RUN"]},
        ],
        "contribution": {"type": "risk_alert", "summary": "3 条事件风险标注(CPI/FOMC/财报/SSR);仅回避降敞口,不做方向 alpha。"},
        "notes": "事件风险只用于回避/降敞口,不作方向性新闻 alpha(延迟-半衰期错配 D4)。日历须 PIT 对齐。",
    }


def _factor_factory() -> dict:
    """进化式挖掘可审计公式因子(Alpha101 风格),每条自带六门控结果。"""
    return {
        "factory_candidates": [
            {"expr": "rank(ts_zscore(residual_return, 3)) - rank(ts_zscore(residual_return, 15))",
             "hypothesis": "短残差过度反应 vs 长残差信息扩散的相对强弱(事前机制:有限注意力)。",
             "incremental_ic": 0.013, "post_cutoff": True, "pbo": 0.07, "t_stat": 3.2,
             "passed_gates": True, "decision": "shadow",
             "note": "六门控全过 -> 进 60 日 shadow(R3),绝不直接上线。"},
            {"expr": "-ts_rank(turnover_20, 60) * sign(residual_meanrev_z(5))",
             "hypothesis": "低换手名的残差反转更干净(以流动性为门)。",
             "incremental_ic": 0.006, "post_cutoff": True, "pbo": 0.21, "t_stat": 1.8,
             "passed_gates": False, "decision": "reject",
             "note": "PBO 0.21>0.10 且 t 1.8<3 -> 未过门控,拒绝。"},
        ],
        "contribution": {"type": "new_factor", "candidates_proposed": 2, "candidates_accepted": 0,
                         "summary": "2 条可审计公式因子:1 进 shadow、1 被拒;均截止后验证。"},
        "notes": "所有候选只在模型训练截止日之后的数据上评分(R6 防 Profit Mirage);锁定 producer.model 版本。",
    }


def _red_team() -> dict:
    """对抗核验:Profit Mirage / 五偏差 / 增量正交 IC 复核;有否决权。"""
    return {
        "factory_candidates": [
            {"expr": "rank(ts_zscore(residual_return, 3)) - rank(ts_zscore(residual_return, 15))",
             "hypothesis": "(复核 factor-factory 同名候选)",
             "incremental_ic": 0.012, "post_cutoff": True, "pbo": 0.08, "t_stat": 3.0,
             "passed_gates": True, "decision": "shadow",
             "note": "红队复核:风险中性化后增量 IC 仍显著、成员推断未命中记忆性前视;维持 shadow,但要求真 holdout 终检(R5)。"},
        ],
        "alerts": [{"level": "info", "code": "red-team",
                    "message": "五偏差自查:本批未见前视/幸存/叙事/目标/成本明显泄漏;factor-factory 申报试验次数 N=180,已计入 DSR。",
                    "tickers": []}],
        "contribution": {"type": "new_factor", "summary": "对 1 条候选做对抗复核,维持 shadow 并要求 holdout 终检。"},
        "notes": "红队有否决权:可把 accept 打回 reject。任何候选证不出截止后增量 IC 即整条删除(R6)。",
    }


ROLE_BUILDERS = {
    "residual-analyst": _residual_analyst, "crowding-monitor": _crowding_monitor,
    "event-risk": _event_risk, "factor-factory": _factor_factory, "red-team": _red_team,
}


def sample_report(agent_role: str = "residual-analyst", model: str | None = None) -> dict:
    # 与模型无关:OpenClaw 用任意 LLM(如 GPT-5.5)均可;OPENCLAW_MODEL 覆盖
    model = model or os.environ.get("OPENCLAW_MODEL", "OpenClaw")
    """按角色生成一份贴近实战的 OpenClaw 报告模板。真实场景由 agent 用真实分析填充这些字段。

    每个角色只填它职责内的字段(见 ROLE_BUILDERS);公共信封(id/kind/producer/asof)统一生成。
    """
    now = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "id": f"openclaw-{agent_role}-{now.strftime('%Y-%m-%dT%H%M')}Z",
        "kind": "openclaw",
        "produced_at": fl.now_iso(),
        "asof_data": now.strftime("%Y-%m-%d"),
        "producer": {"name": f"openclaw-agent:{agent_role}", "model": model,
                     "agent_role": agent_role, "run_url": os.environ.get("OPENCLAW_RUN_URL", "")},
    }
    report.update(ROLE_BUILDERS.get(agent_role, _residual_analyst)())
    return report


# ---- 每日个股 AI 解读(stock-analyst 角色)——解耦的 stock-notes 投递 ----
def stock_note_template(symbol: str) -> dict:
    """个股解读模板。真实场景由 OpenClaw 的 stock-analyst 角色用真实数据填充。"""
    return {
        "symbol": symbol.upper(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "model": os.environ.get("OPENCLAW_MODEL", "OpenClaw"),
        "producer": "openclaw-agent:stock-analyst",
        "stance": "中性",
        "thesis": "<多空逻辑:多头/空头各自核心论点>",
        "earnings": "<最近一季营收/EPS/指引要点>",
        "news": "<近一周关键新闻与多空含义>",
        "risks": "<监管/供应链/事件窗口等风险点>",
        "view": "<一句话综合看法>",
        "sources": [],
    }


def stock_note_relpath(symbol: str) -> str:
    return f"feed/stock-notes/{symbol.upper().replace(':', '-')}.json"


def put_github_path(obj: dict, repo: str, token: str, relpath: str, msg: str) -> None:
    """用 GitHub Contents API 把任意 JSON PUT 到指定路径(创建或更新)。"""
    url = f"https://api.github.com/repos/{repo}/contents/{relpath}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}
    sha = None
    try:  # 已存在则取 sha 以更新
        g = urllib.request.Request(url + f"?ref={os.environ.get('OPENCLAW_BRANCH', 'main')}", headers=headers)
        with urllib.request.urlopen(g, timeout=30) as r:
            sha = json.loads(r.read()).get("sha")
    except Exception:  # noqa: BLE001
        pass
    content = base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": msg, "content": content, "branch": os.environ.get("OPENCLAW_BRANCH", "main")}
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[openclaw] stock-note {r.status}: {relpath}")


def post_github_api(report: dict, repo: str, token: str) -> None:
    """用 GitHub Contents API 把报告 PUT 到 feed/inbox/<id>.json。"""
    path = f"feed/inbox/{report['id']}.json"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    content = base64.b64encode(json.dumps(report, ensure_ascii=False, indent=2).encode()).decode()
    body = json.dumps({"message": f"openclaw: 投递 {report['id']}", "content": content,
                       "branch": os.environ.get("OPENCLAW_BRANCH", "openclaw-inbox")}).encode()
    req = urllib.request.Request(url, data=body, method="PUT", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[openclaw] github-api {r.status}: {path}")


def post_dispatch(report: dict, repo: str, token: str) -> None:
    """触发 repository_dispatch,payload 携带报告(由 .github/workflows/feed-validate.yml 接收)。"""
    url = f"https://api.github.com/repos/{repo}/dispatches"
    body = json.dumps({"event_type": "openclaw-report", "client_payload": {"report": report}}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[openclaw] dispatch {r.status}: event=openclaw-report")


def post_local(report: dict) -> None:
    path = os.path.join(fl.FEED, "inbox", f"{report['id']}.json")
    fl.save_json(path, report)
    print(f"[openclaw] 本地写入 {os.path.relpath(path, fl.REPO_ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["github-api", "dispatch", "local"], default="local")
    ap.add_argument("--repo", default=os.environ.get("OPENCLAW_REPO", DEFAULT_REPO))
    ap.add_argument("--role", default="residual-analyst", choices=ROLES,
                    help="OpenClaw agent 角色,决定填充哪些字段")
    ap.add_argument("--report-file", default=None, help="读取自定义报告 JSON;缺省用内置示例")
    ap.add_argument("--stock-note", default=None, metavar="SYMBOL",
                    help="个股解读模式(stock-analyst):如 US:AAPL。投递到 feed/stock-notes/,供个股页展示")
    args = ap.parse_args()

    # ---- 个股解读分支(与量化报告解耦)----
    if args.stock_note:
        note = fl.load_json(args.report_file) if args.report_file else stock_note_template(args.stock_note)
        rel = stock_note_relpath(note["symbol"])
        if args.mode == "local":
            fl.save_json(os.path.join(fl.REPO_ROOT, rel), note)
            print(f"[openclaw] 本地写入 {rel}")
        else:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENCLAW_TOKEN")
            if not token:
                print("[openclaw] 缺少 GITHUB_TOKEN/OPENCLAW_TOKEN"); sys.exit(2)
            put_github_path(note, args.repo, token, rel, f"openclaw: 个股解读 {note['symbol']} {note['date']}")
        print(f"[openclaw] 完成: {note['symbol']}")
        return

    report = fl.load_json(args.report_file) if args.report_file else sample_report(args.role)
    secret = os.environ.get("FEED_HMAC_SECRET")
    if secret:
        fl.sign_report(report, secret)
        print("[openclaw] 已签名 (HMAC-SHA256)")
    ok, errs = fl.validate_report(report)
    if not ok:
        print("[openclaw] 本地校验失败,放弃投递:", errs)
        sys.exit(1)

    if args.mode == "local":
        post_local(report)
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENCLAW_TOKEN")
        if not token:
            print("[openclaw] 缺少 GITHUB_TOKEN/OPENCLAW_TOKEN,无法用 API 投递。")
            sys.exit(2)
        (post_github_api if args.mode == "github-api" else post_dispatch)(report, args.repo, token)
    print(f"[openclaw] 完成: {report['id']}")


if __name__ == "__main__":
    main()
