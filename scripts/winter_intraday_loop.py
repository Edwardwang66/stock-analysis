#!/usr/bin/env python3
"""Winter 常驻盘中循环(Edward 选定方案,2026-06-10)。

在 Winter 的机器上常驻运行:
    cd stock-analysis && nohup python3 scripts/winter_intraday_loop.py >> intraday.log 2>&1 &

行为:
  - 全球覆盖市场时段(UTC 00:00 -> 20:05,周一到五)每 5 分钟:
      1) 跑 scripts/intraday_report.py(全池报价快照 + 异动/新高/新低事件)
      2) 把 feed/intraday/latest.json 提交到 live 分支(SSH,单写者)
      3) 若 events 非空 -> 在仓库根写 INTRADAY_EVENTS.flag(给你的 LLM 侧循环一个触发信号,
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
LIVE_DIR = Path.home() / ".cache/stock-analysis/live-worktree"
PERIOD = 300  # 5 分钟


def sh(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=True, text=True)


def live_git(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=LIVE_DIR, check=check, capture_output=True, text=True)


def ensure_live_checkout() -> bool:
    if not LIVE_DIR.exists():
        LIVE_DIR.parent.mkdir(parents=True, exist_ok=True)
        origin = sh("git", "config", "--get", "remote.origin.url").stdout.strip()
        r = subprocess.run(
            ["git", "clone", "--branch", "live", "--single-branch", origin, str(LIVE_DIR)],
            check=False,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"live clone failed: {r.stderr.strip()}", file=sys.stderr)
            return False
    live_git("git", "fetch", "origin", "live", check=False)
    pull = live_git("git", "pull", "--ff-only", "origin", "live", check=False)
    if pull.returncode != 0:
        print(f"live pull failed: {pull.stderr.strip()}", file=sys.stderr)
        return False
    status = live_git("git", "status", "--porcelain", check=False).stdout.strip()
    if status:
        print(f"live worktree dirty, skip push: {status}", file=sys.stderr)
        return False
    return True


def archive_pg() -> None:
    """Best-effort local warehouse ingest; never break the live snapshot loop."""
    r = subprocess.run(
        [sys.executable, "scripts/winter_pg/ingest.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    msg = (r.stdout or r.stderr).strip()
    if msg:
        print(f"pg {msg}")


def in_session(now: datetime) -> bool:
    """全球任一覆盖市场开市即跑(亚->欧->美接力,约 UTC 00:00-20:00 工作日)。"""
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 0 <= minutes < 20 * 60 + 5


def tick() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/intraday_report.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(r.stdout.strip() or r.stderr.strip()[:200])
    if r.returncode != 0:
        return
    archive_pg()
    # live branch writes use an isolated checkout so this repo can stay on main.
    try:
        if not ensure_live_checkout():
            return
        src = ROOT / "feed" / "intraday" / "latest.json"
        dst = LIVE_DIR / "feed" / "intraday" / "latest.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        live_git("git", "add", "feed/intraday/latest.json")
        diff = live_git("git", "diff", "--cached", "--quiet", check=False)
        if diff.returncode != 0:
            commit = live_git(
                "git",
                "-c",
                "user.name=winter-loop",
                "-c",
                "user.email=winter@local",
                "commit",
                "-m",
                f"intraday: {datetime.now(timezone.utc).strftime('%H:%M')}",
                check=False,
            )
            if commit.returncode != 0:
                print(f"live commit failed: {commit.stderr.strip()}", file=sys.stderr)
                return
            push = live_git("git", "push", "origin", "live", check=False)
            if push.returncode != 0:
                print(f"live push failed: {push.stderr.strip()}", file=sys.stderr)
        # 事件触发信号:latest.json 里有 events 则落 flag
        import json

        doc = json.loads((ROOT / "feed" / "intraday" / "latest.json").read_text())
        flag = ROOT / "INTRADAY_EVENTS.flag"
        if doc.get("events"):
            flag.write_text(json.dumps(doc["events"], ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print(f"git: {e}", file=sys.stderr)


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
