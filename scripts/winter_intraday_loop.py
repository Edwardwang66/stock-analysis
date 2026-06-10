#!/usr/bin/env python3
"""Winter 常驻盘中循环(Edward 选定方案,2026-06-10)。

在 Winter 的机器上常驻运行:
    cd stock-analysis && nohup python3 scripts/winter_intraday_loop.py >> intraday.log 2>&1 &

行为:
  - 美股时段(盘前最后30分钟 13:00 UTC → 收盘 20:00 UTC,周一到五)每 5 分钟:
      1) 跑 scripts/intraday_report.py(全池报价快照 + 异动/新高/新低事件)
      2) 把 feed/intraday/latest.json 提交到 live 分支(SSH,单写者)
      3) 若 events 非空 → 在仓库根写 INTRADAY_EVENTS.flag(给你的 LLM 侧循环一个触发信号,
         按 playbook §7 对触发标的做增量深读;处理完删除 flag)
  - 非交易时段粗睡眠;GitHub Actions 的 intraday-report.yml 自动退位
    (它只在 live 分支数据 >10 分钟陈旧时才补跑,双写不冲突)。
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERIOD = 300  # 5 分钟


def sh(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=True, text=True)


def in_session(now: datetime) -> bool:
    """全球任一覆盖市场开市即跑(亚→欧→美接力,约 UTC 00:00-20:00 工作日)。"""
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 0 <= minutes < 20 * 60 + 5


def tick() -> None:
    r = subprocess.run([sys.executable, "scripts/intraday_report.py"], cwd=ROOT,
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[:200])
    if r.returncode != 0:
        return
    # 提交 live 分支(单写者;失败不致命,下轮重试)
    try:
        fetch = sh("git", "fetch", "origin", "live", check=False)
        sh("git", "stash", "-u", check=False)
        if fetch.returncode == 0:
            checkout = sh("git", "checkout", "-B", "live", "origin/live", check=False)
        else:
            checkout = sh("git", "checkout", "-B", "live", "main", check=False)
        if checkout.returncode != 0:
            print(f"git checkout live failed: {checkout.stderr.strip()}", file=sys.stderr)
            sh("git", "checkout", "main", check=False)
            return
        sh("git", "stash", "pop", check=False)
        sh("git", "add", "feed/intraday/latest.json")
        diff = sh("git", "diff", "--cached", "--quiet", check=False)
        if diff.returncode != 0:
            sh("git", "-c", "user.name=winter-loop", "-c", "user.email=winter@local",
               "commit", "-m", f"intraday: {datetime.now(timezone.utc).strftime('%H:%M')}")
            sh("git", "push", "origin", "live", check=False)
        # 事件触发信号:latest.json 里有 events 则落 flag
        import json
        doc = json.loads((ROOT / "feed" / "intraday" / "latest.json").read_text())
        flag = ROOT / "INTRADAY_EVENTS.flag"
        if doc.get("events"):
            flag.write_text(json.dumps(doc["events"], ensure_ascii=False))
        sh("git", "checkout", "main", check=False)
        sh("git", "stash", "pop", check=False)
    except Exception as e:  # noqa: BLE001
        print(f"git: {e}", file=sys.stderr)
        sh("git", "checkout", "main", check=False)


def main() -> None:
    print("winter-intraday-loop 启动(5 分钟节拍,全球时段 00:00-20:00 UTC 工作日)")
    while True:
        now = datetime.now(timezone.utc)
        if in_session(now):
            t0 = time.time()
            try:
                tick()
            except Exception as e:  # noqa: BLE001
                print(f"tick 异常:{e}", file=sys.stderr)
            # 对齐到下一个 5 分钟边界
            time.sleep(max(30, PERIOD - (time.time() - t0)))
        else:
            time.sleep(120)


if __name__ == "__main__":
    main()
