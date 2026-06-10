#!/usr/bin/env python3
"""盘中增量更新管道(给 Winter 的 LLM 侧用,2026-06-10 第十六轮)。

把「一句话盘中解读」一条命令落到两处:
  1) feed/stock-notes/<SYM>.json 的 intraday_update 字段(个股页 ⚡盘中更新 徽章)
  2) feed/screener/analysis-intraday-<date>.md 滚动追加一行(/desk 盘中滚动卡 + 日报)

用法(LLM 对每个触发标的生成一句话后调用):
    python scripts/openclaw_intraday_update.py --symbol US:NVDA \
        --note "异动 +1.4% 放量突破周 R1 5183,SuperTrend 多头无恙,维持看多" [--push]

    # 查看待处理事件(读 INTRADAY_EVENTS.flag,处理完后 --clear-flag 删除)
    python scripts/openclaw_intraday_update.py --list-events
    python scripts/openclaw_intraday_update.py --clear-flag

约定:
  - 只 merge intraday_update 字段,note 其他内容(stance/thesis/...)一概不动;
  - 收盘后全量投递会自然覆盖当日 intraday_update(次日新 note 不带它,符合预期);
  - --push 时自动 rebase,撞车安全;不带 --push 则只改本地(随你下次投递一起 push)。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "feed" / "stock-notes"
FLAG = ROOT / "INTRADAY_EVENTS.flag"


def now_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M ET")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def update_note(symbol: str, note_text: str, at: str) -> bool:
    p = NOTES / f"{symbol.replace(':', '-')}.json"
    if not p.exists():
        print(f"⚠ {p.name} 不存在(该标的今天还没全量 note),只写滚动 md", file=sys.stderr)
        return False
    doc = json.loads(p.read_text())
    doc["intraday_update"] = {"at": at, "note": note_text}
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return True


def append_rolling(symbol: str, note_text: str, at: str) -> Path:
    md = ROOT / "feed" / "screener" / f"analysis-intraday-{today()}.md"
    if not md.exists():
        md.write_text(f"# 盘中事件解读 {today()}(滚动追加,最新在下)\n\n")
    with md.open("a") as f:
        f.write(f"- **{at} · {symbol}** {note_text}\n")
    return md


def git_push(paths: list[Path]) -> None:
    def run(*cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

    run("git", "add", *[str(p.relative_to(ROOT)) for p in paths])
    if run("git", "diff", "--cached", "--quiet").returncode == 0:
        return
    c = run("git", "-c", "user.name=openclaw-intraday", "-c", "user.email=winter@local",
            "commit", "-m", f"openclaw: 盘中增量 {datetime.now(timezone.utc).strftime('%H:%M')}Z")
    if c.returncode != 0:
        print(f"commit 失败: {c.stderr.strip()}", file=sys.stderr)
        return
    for i in range(3):
        if run("git", "pull", "--rebase", "origin", "main").returncode == 0 \
           and run("git", "push", "origin", "main").returncode == 0:
            print("已 push")
            return
    print("push 失败(3次)", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol")
    ap.add_argument("--note")
    ap.add_argument("--at", default=None, help="默认当前美东时间")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--list-events", action="store_true")
    ap.add_argument("--clear-flag", action="store_true")
    args = ap.parse_args()

    if args.list_events:
        if not FLAG.exists():
            print("[]")
            return 0
        print(FLAG.read_text())
        return 0
    if args.clear_flag:
        FLAG.unlink(missing_ok=True)
        print("flag cleared")
        return 0
    if not args.symbol or not args.note:
        ap.error("--symbol 与 --note 必填(或用 --list-events / --clear-flag)")

    at = args.at or now_et()
    touched: list[Path] = []
    if update_note(args.symbol, args.note, at):
        touched.append(NOTES / f"{args.symbol.replace(':', '-')}.json")
    touched.append(append_rolling(args.symbol, args.note, at))
    print(f"✓ {args.symbol} @ {at}:note {'已更' if len(touched) == 2 else '跳过'} + 滚动 md 已追加")
    if args.push:
        git_push(touched)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
