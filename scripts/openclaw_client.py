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


def sample_report(agent_role: str = "residual-analyst", model: str = "claude-opus-4-8") -> dict:
    """一份示例 OpenClaw 分析报告(残差分析师角色)。真实场景由 agent 填充。"""
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "1.0",
        "id": f"openclaw-{agent_role}-{now.strftime('%Y-%m-%dT%H%M')}Z",
        "kind": "openclaw",
        "produced_at": fl.now_iso(),
        "asof_data": now.strftime("%Y-%m-%d"),
        "producer": {"name": f"openclaw-agent:{agent_role}", "model": model,
                     "agent_role": agent_role, "run_url": os.environ.get("OPENCLAW_RUN_URL", "")},
        "market_state": {"regime": "neutral", "crowding_proxy": 0.41, "crowding_alert": False},
        "factory_candidates": [{
            "expr": "rank(residual_meanrev_zscore(5)) - rank(residual_meanrev_zscore(20))",
            "hypothesis": "短周期残差反转相对长周期的相对强弱;事前机制=短期过度反应、长期信息扩散。",
            "incremental_ic": 0.011, "post_cutoff": True, "pbo": 0.18, "t_stat": 2.1,
            "passed_gates": False, "decision": "reject",
            "note": "OpenClaw 残差分析师候选:截止后 IC 为正但 PBO=0.18>0.10、t=2.1<3 -> 未过门控,拒绝(R6/§6.7)。",
        }],
        "alerts": [{"level": "info", "code": "event-risk",
                    "message": "下周 FOMC + CPI:建议组合层临时收紧毛杠杆 0.2x,空头腿检查 SSR/借券费。",
                    "tickers": []}],
        "contribution": {"type": "new_factor", "candidates_proposed": 1, "candidates_accepted": 0,
                         "summary": "OpenClaw 残差分析师投递 1 条候选(被门控拒绝)+ 1 条事件风险提示。"},
        "notes": "OpenClaw 投递示例。LLM 只生成可审计假设、不决策(R6);一律须过六门控与真 holdout。",
    }


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
    ap.add_argument("--role", default="residual-analyst")
    ap.add_argument("--report-file", default=None, help="读取自定义报告 JSON;缺省用内置示例")
    args = ap.parse_args()

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
