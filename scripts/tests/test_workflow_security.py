"""Static regression checks for security-sensitive workflows."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shlex
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
PROTECTED_PYTHON_WORKFLOWS = {
    "alpha-routine.yml",
    "chan-stats.yml",
    "daily-digest.yml",
    "daily-screener.yml",
    "dependabot-automerge.yml",
    "feed-validate.yml",
    "feed-watchdog.yml",
    "funds-13f.yml",
    "hyperliquid-monitor.yml",
    "intraday-report.yml",
    "market-snapshot.yml",
    "monthly-studies.yml",
    "openclaw-notes.yml",
    "premarket-pack.yml",
}
PRODUCTION_PYTHON_JOBS = {
    ("alpha-routine.yml", "run"): (
        ".python-version",
        "requirements/automation.txt",
    ),
    ("monthly-studies.yml", "studies"): (
        ".python-version",
        "requirements/automation.txt",
    ),
    ("chan-stats.yml", "stats"): (
        ".python-version",
        "backend/requirements.txt",
    ),
    ("daily-screener.yml", "screen"): (
        ".python-version",
        "backend/requirements.txt",
    ),
    ("feed-validate.yml", "pr-validate"): (
        "trusted/.python-version",
        "trusted/scripts/requirements.txt",
    ),
    ("feed-validate.yml", "publish"): (
        ".python-version",
        "scripts/requirements.txt",
    ),
    ("hyperliquid-monitor.yml", "monitor"): (
        ".python-version",
        "scripts/requirements.txt",
    ),
    ("daily-digest.yml", "digest"): (".python-version", None),
    ("funds-13f.yml", "track"): (".python-version", None),
    ("intraday-report.yml", "report"): (".python-version", None),
    ("market-snapshot.yml", "snapshot"): (".python-version", None),
    ("openclaw-notes.yml", "notes"): (".python-version", None),
    ("premarket-pack.yml", "pack"): (".python-version", None),
    ("feed-watchdog.yml", "audit"): (".python-version", None),
    ("dependabot-automerge.yml", "on-pr"): (".python-version", None),
    ("dependabot-automerge.yml", "sweep"): (".python-version", None),
}
BASELINE_MISSING_SETUP_JOBS = {
    ("feed-watchdog.yml", "audit"),
    ("dependabot-automerge.yml", "on-pr"),
    ("dependabot-automerge.yml", "sweep"),
}
DEPENDENCY_JOBS = {
    ("alpha-routine.yml", "run"),
    ("monthly-studies.yml", "studies"),
    ("chan-stats.yml", "stats"),
    ("daily-screener.yml", "screen"),
    ("feed-validate.yml", "pr-validate"),
    ("feed-validate.yml", "publish"),
    ("hyperliquid-monitor.yml", "monitor"),
}
APPROVED_PYTHON_RUN_BODY_KEYS = {
    (
        "dependabot-automerge.yml",
        "on-pr",
        "清理旧资格并撤销 auto-merge",
    ),
    (
        "dependabot-automerge.yml",
        "on-pr",
        "根据 metadata 同步 auto-merge 资格标签",
    ),
    (
        "dependabot-automerge.yml",
        "on-pr",
        "检查 required checks 后启用 auto-merge",
    ),
    (
        "dependabot-automerge.yml",
        "sweep",
        "清扫存量 dependabot PR",
    ),
    ("funds-13f.yml", "track", "提交 + 新披露开 Issue"),
    (
        "intraday-report.yml",
        "report",
        "三轮循环(5 分钟节拍 × 3,内嵌备胎守卫)",
    ),
    (
        "feed-watchdog.yml",
        "audit",
        "三级备胎:live 盘中流 >30 分钟陈旧则就地补跑一轮",
    ),
    ("feed-watchdog.yml", "audit", "运行审计并写 health.json"),
}

CURRENT_SETUP_311 = """      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
"""
CURRENT_SETUP_312 = """      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
"""
CURRENT_SETUP_311_OPENCLAW = """      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"

"""
FINAL_SETUP_STANDARD = """      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
"""
FINAL_SETUP_STANDARD_OPENCLAW = """      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version

"""
FINAL_SETUP_AUTOMATION = """      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
          cache: pip
          cache-dependency-path: requirements/automation.txt
"""
FINAL_SETUP_BACKEND = """      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
          cache: pip
          cache-dependency-path: backend/requirements.txt
"""
FINAL_SETUP_SCRIPTS = """      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
          cache: pip
          cache-dependency-path: scripts/requirements.txt
"""
FINAL_SETUP_TRUSTED = """      - uses: actions/setup-python@v6
        with:
          python-version-file: trusted/.python-version
          cache: pip
          cache-dependency-path: trusted/scripts/requirements.txt
"""
CURRENT_SETUP_STEPS = {
    ("alpha-routine.yml", "run"): CURRENT_SETUP_312,
    ("monthly-studies.yml", "studies"): CURRENT_SETUP_312,
    ("chan-stats.yml", "stats"): CURRENT_SETUP_311,
    ("daily-screener.yml", "screen"): CURRENT_SETUP_311,
    ("feed-validate.yml", "pr-validate"): CURRENT_SETUP_312,
    ("feed-validate.yml", "publish"): CURRENT_SETUP_312,
    ("hyperliquid-monitor.yml", "monitor"): CURRENT_SETUP_312,
    ("daily-digest.yml", "digest"): CURRENT_SETUP_311,
    ("funds-13f.yml", "track"): CURRENT_SETUP_311,
    ("intraday-report.yml", "report"): CURRENT_SETUP_311,
    ("market-snapshot.yml", "snapshot"): CURRENT_SETUP_311,
    ("openclaw-notes.yml", "notes"): CURRENT_SETUP_311_OPENCLAW,
    ("premarket-pack.yml", "pack"): CURRENT_SETUP_311,
}
FINAL_SETUP_STEPS = {
    ("alpha-routine.yml", "run"): FINAL_SETUP_AUTOMATION,
    ("monthly-studies.yml", "studies"): FINAL_SETUP_AUTOMATION,
    ("chan-stats.yml", "stats"): FINAL_SETUP_BACKEND,
    ("daily-screener.yml", "screen"): FINAL_SETUP_BACKEND,
    ("feed-validate.yml", "pr-validate"): FINAL_SETUP_TRUSTED,
    ("feed-validate.yml", "publish"): FINAL_SETUP_SCRIPTS,
    ("hyperliquid-monitor.yml", "monitor"): FINAL_SETUP_SCRIPTS,
    ("daily-digest.yml", "digest"): FINAL_SETUP_STANDARD,
    ("funds-13f.yml", "track"): FINAL_SETUP_STANDARD,
    ("intraday-report.yml", "report"): FINAL_SETUP_STANDARD,
    ("market-snapshot.yml", "snapshot"): FINAL_SETUP_STANDARD,
    ("openclaw-notes.yml", "notes"): FINAL_SETUP_STANDARD_OPENCLAW,
    ("premarket-pack.yml", "pack"): FINAL_SETUP_STANDARD,
    ("feed-watchdog.yml", "audit"): FINAL_SETUP_STANDARD,
    ("dependabot-automerge.yml", "on-pr"): FINAL_SETUP_STANDARD,
    ("dependabot-automerge.yml", "sweep"): FINAL_SETUP_STANDARD,
}
CURRENT_INSTALL_STEPS = {
    (
        "alpha-routine.yml",
        "run",
    ): """      - name: 安装依赖
        run: pip install -r scripts/requirements.txt
""",
    (
        "monthly-studies.yml",
        "studies",
    ): """      - run: pip install -r scripts/requirements.txt
""",
    (
        "chan-stats.yml",
        "stats",
    ): """      - run: pip install -r backend/requirements.txt
""",
    (
        "daily-screener.yml",
        "screen",
    ): """      - run: pip install -r backend/requirements.txt
""",
    (
        "feed-validate.yml",
        "pr-validate",
    ): """      - name: Install trusted validator dependencies
        run: python -m pip install -r trusted/scripts/requirements.txt
""",
    (
        "feed-validate.yml",
        "publish",
    ): """      - run: python -m pip install -r scripts/requirements.txt
""",
    (
        "hyperliquid-monitor.yml",
        "monitor",
    ): """      - run: pip install -r scripts/requirements.txt
""",
}
FINAL_INSTALL_STEPS = {
    (
        "alpha-routine.yml",
        "run",
    ): """      - name: 安装依赖
        run: python -m pip install --require-hashes -r requirements/automation.txt
""",
    (
        "monthly-studies.yml",
        "studies",
    ): """      - run: python -m pip install --require-hashes -r requirements/automation.txt
""",
    (
        "chan-stats.yml",
        "stats",
    ): """      - run: python -m pip install --require-hashes -r backend/requirements.txt
""",
    (
        "daily-screener.yml",
        "screen",
    ): """      - run: python -m pip install --require-hashes -r backend/requirements.txt
""",
    (
        "feed-validate.yml",
        "pr-validate",
    ): """      - name: Install trusted validator dependencies
        run: python -m pip install --require-hashes -r trusted/scripts/requirements.txt
""",
    (
        "feed-validate.yml",
        "publish",
    ): """      - run: python -m pip install --require-hashes -r scripts/requirements.txt
""",
    (
        "hyperliquid-monitor.yml",
        "monitor",
    ): """      - run: python -m pip install --require-hashes -r scripts/requirements.txt
""",
}
FINAL_SMOKE_STEPS = {
    (
        "alpha-routine.yml",
        "run",
    ): """      - name: Smoke combined automation imports
        run: PYTHONPATH=backtest:scripts python -c "import factor_factory, feed_lib, run_routine, statarb"
""",
    (
        "monthly-studies.yml",
        "studies",
    ): """      - name: Smoke combined automation imports
        run: PYTHONPATH=backtest:scripts python -c "import feed_lib, statarb, study_downshift, study_pbo"
""",
}
CURRENT_SWEEP_CHECKOUT_STEP = """      - uses: actions/checkout@v7
"""
FINAL_SWEEP_CHECKOUT_STEP = """      - uses: actions/checkout@v7
        with:
          persist-credentials: false
"""
ON_PR_CHECKOUT_STEP = """      - name: Checkout trusted base gate
        uses: actions/checkout@v7
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          persist-credentials: false
"""
PROTECTED_WORKFLOW_SHA256 = (
    "9b634f7b39ea0f1b232bde96db36214b3871618be076f8029d15cce0330d3e35"
)
PROTECTED_WORKFLOW_MUTATIONS = [
    (
        "alpha-routine.yml",
        "python scripts/run_routine.py $ARGS",
        "python scripts/run_routine.py $ARGS --unexpected",
        "unselected producer step",
    ),
    (
        "alpha-routine.yml",
        "  contents: write",
        "  contents: read",
        "permission",
    ),
    (
        "hyperliquid-monitor.yml",
        "    timeout-minutes: 10",
        "    timeout-minutes: 11",
        "timeout",
    ),
    (
        "alpha-routine.yml",
        "FEED_PUBLICATION_MANIFEST: /tmp/feed-publication-${{ github.run_id }}.json",
        "FEED_PUBLICATION_MANIFEST: /tmp/changed-${{ github.run_id }}.json",
        "environment",
    ),
    (
        "alpha-routine.yml",
        '    - cron: "30 22 * * 1-5"',
        '    - cron: "31 22 * * 1-5"',
        "trigger",
    ),
    (
        "alpha-routine.yml",
        "for i in 1 2 3 4; do",
        "for i in 1 2 3; do",
        "retry",
    ),
]
APPROVED_PYTHON_RUN_BODIES = {
    ("funds-13f.yml", "track", "提交 + 新披露开 Issue"): (
        r"""      - name: 提交 + 新披露开 Issue
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add feed/funds
          if git diff --cached --quiet; then echo "无新披露"; exit 0; fi
          git commit -m "funds: 13F 持仓更新 $(date -u +%F)"
          for i in 1 2 3; do
            git pull --rebase origin main && git push origin main && break
            sleep 5
          done
          ASOF=$(python3 -c "import json;print(json.load(open('feed/funds/situational-awareness.json'))['asof'])")
          gh issue create --title "🦅 Situational Awareness LP 新 13F 披露(截至 $ASOF)" \
            --assignee "${{ github.repository_owner }}" \
            --body "新一期 13F 已解析入库 feed/funds/situational-awareness.json,情报看板已自动更新。OpenClaw 将按新持仓调整每日分析池。"
""",
        r"""      - name: 提交 + 新披露开 Issue
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add feed/funds
          if git diff --cached --quiet; then echo "无新披露"; exit 0; fi
          git commit -m "funds: 13F 持仓更新 $(date -u +%F)"
          for i in 1 2 3; do
            git pull --rebase origin main && git push origin main && break
            sleep 5
          done
          ASOF=$(python -c "import json;print(json.load(open('feed/funds/situational-awareness.json'))['asof'])")
          gh issue create --title "🦅 Situational Awareness LP 新 13F 披露(截至 $ASOF)" \
            --assignee "${{ github.repository_owner }}" \
            --body "新一期 13F 已解析入库 feed/funds/situational-awareness.json,情报看板已自动更新。OpenClaw 将按新持仓调整每日分析池。"
""",
        1,
    ),
    (
        "intraday-report.yml",
        "report",
        "三轮循环(5 分钟节拍 × 3,内嵌备胎守卫)",
    ): (
        r"""      - name: 三轮循环(5 分钟节拍 × 3,内嵌备胎守卫)
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          for i in 1 2 3; do
            cd /tmp/live && git pull --ff-only origin live 2>/dev/null || true
            cd "$GITHUB_WORKSPACE"
            AGE=$(python3 -c "import json,datetime as d; at=json.load(open('/tmp/live/feed/intraday/latest.json')).get('at',''); print(int((d.datetime.now(d.timezone.utc)-d.datetime.fromisoformat(at)).total_seconds()) if at else 99999)" 2>/dev/null || echo 99999)
            echo "第 ${i} 轮:live 数据年龄 ${AGE}s"
            if [ "$AGE" -ge 290 ]; then
              mkdir -p /tmp/live/feed/intraday
              INTRADAY_OUT=/tmp/live/feed/intraday/latest.json INTRADAY_PRODUCER=actions-backup python scripts/intraday_report.py || true
              cd /tmp/live
              # -f:live 分支基点的 .gitignore 拦 feed/intraday/,文件未跟踪时裸 add 退出码 1(首跑实测)
              git add -f feed/intraday/latest.json
              if ! git diff --cached --quiet; then
                git commit -m "intraday: $(date -u +%H:%M)"
                git push origin live || { git pull --rebase origin live && git push origin live; } || true
              fi
              cd "$GITHUB_WORKSPACE"
            else
              echo "Winter 循环在岗,本轮退位"
            fi
            # 顺手保活 Render(替代 keep-warm 高频 schedule)
            curl -fsS --max-time 20 "${{ vars.API_BASE }}/api/v1/health" >/dev/null 2>&1 || true
            [ "$i" -lt 2 ] && sleep 310 || true
          done
""",
        r"""      - name: 三轮循环(5 分钟节拍 × 3,内嵌备胎守卫)
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          for i in 1 2 3; do
            cd /tmp/live && git pull --ff-only origin live 2>/dev/null || true
            cd "$GITHUB_WORKSPACE"
            AGE=$(python -c "import json,datetime as d; at=json.load(open('/tmp/live/feed/intraday/latest.json')).get('at',''); print(int((d.datetime.now(d.timezone.utc)-d.datetime.fromisoformat(at)).total_seconds()) if at else 99999)" 2>/dev/null || echo 99999)
            echo "第 ${i} 轮:live 数据年龄 ${AGE}s"
            if [ "$AGE" -ge 290 ]; then
              mkdir -p /tmp/live/feed/intraday
              INTRADAY_OUT=/tmp/live/feed/intraday/latest.json INTRADAY_PRODUCER=actions-backup python scripts/intraday_report.py || true
              cd /tmp/live
              # -f:live 分支基点的 .gitignore 拦 feed/intraday/,文件未跟踪时裸 add 退出码 1(首跑实测)
              git add -f feed/intraday/latest.json
              if ! git diff --cached --quiet; then
                git commit -m "intraday: $(date -u +%H:%M)"
                git push origin live || { git pull --rebase origin live && git push origin live; } || true
              fi
              cd "$GITHUB_WORKSPACE"
            else
              echo "Winter 循环在岗,本轮退位"
            fi
            # 顺手保活 Render(替代 keep-warm 高频 schedule)
            curl -fsS --max-time 20 "${{ vars.API_BASE }}/api/v1/health" >/dev/null 2>&1 || true
            [ "$i" -lt 2 ] && sleep 310 || true
          done
""",
        1,
    ),
    (
        "feed-watchdog.yml",
        "audit",
        "三级备胎:live 盘中流 >30 分钟陈旧则就地补跑一轮",
    ): (
        r"""      - name: 三级备胎:live 盘中流 >30 分钟陈旧则就地补跑一轮
        run: |
          git fetch origin live:live 2>/dev/null || true
          AGE=99999
          if git show live:feed/intraday/latest.json > /tmp/live_latest.json 2>/dev/null; then
            AGE=$(python3 -c "import json,datetime as d; at=json.load(open('/tmp/live_latest.json')).get('at',''); print(int((d.datetime.now(d.timezone.utc)-d.datetime.fromisoformat(at)).total_seconds()) if at else 99999)" 2>/dev/null || echo 99999)
          fi
          echo "live 年龄 ${AGE}s"
          if [ "$AGE" -lt 1800 ]; then echo "盘中流健康,跳过"; exit 0; fi
          echo "⚠️ 盘中流断流(${AGE}s),三级备胎补跑"
          git worktree add /tmp/live live 2>/dev/null || true
          mkdir -p /tmp/live/feed/intraday
          cp /tmp/live_latest.json /tmp/live/feed/intraday/latest.json 2>/dev/null || true
          INTRADAY_OUT=/tmp/live/feed/intraday/latest.json INTRADAY_PRODUCER=watchdog python3 scripts/intraday_report.py || exit 0
          cd /tmp/live
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add feed/intraday/latest.json
          git diff --cached --quiet || { git commit -m "intraday: $(date -u +%H:%M) (watchdog兜底)"; git push origin live || true; }
""",
        r"""      - name: 三级备胎:live 盘中流 >30 分钟陈旧则就地补跑一轮
        run: |
          git fetch origin live:live 2>/dev/null || true
          AGE=99999
          if git show live:feed/intraday/latest.json > /tmp/live_latest.json 2>/dev/null; then
            AGE=$(python -c "import json,datetime as d; at=json.load(open('/tmp/live_latest.json')).get('at',''); print(int((d.datetime.now(d.timezone.utc)-d.datetime.fromisoformat(at)).total_seconds()) if at else 99999)" 2>/dev/null || echo 99999)
          fi
          echo "live 年龄 ${AGE}s"
          if [ "$AGE" -lt 1800 ]; then echo "盘中流健康,跳过"; exit 0; fi
          echo "⚠️ 盘中流断流(${AGE}s),三级备胎补跑"
          git worktree add /tmp/live live 2>/dev/null || true
          mkdir -p /tmp/live/feed/intraday
          cp /tmp/live_latest.json /tmp/live/feed/intraday/latest.json 2>/dev/null || true
          INTRADAY_OUT=/tmp/live/feed/intraday/latest.json INTRADAY_PRODUCER=watchdog python scripts/intraday_report.py || exit 0
          cd /tmp/live
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add feed/intraday/latest.json
          git diff --cached --quiet || { git commit -m "intraday: $(date -u +%H:%M) (watchdog兜底)"; git push origin live || true; }
""",
        2,
    ),
    ("feed-watchdog.yml", "audit", "运行审计并写 health.json"): (
        r"""      - name: 运行审计并写 health.json
        id: audit
        run: |
          set +e
          python3 scripts/audit_feed.py --write | tee /tmp/audit.txt
          echo "exit_code=$?" >> "$GITHUB_OUTPUT"
          {
            echo "report<<AUDIT_EOF"
            cat /tmp/audit.txt
            echo "AUDIT_EOF"
          } >> "$GITHUB_OUTPUT"
""",
        r"""      - name: 运行审计并写 health.json
        id: audit
        run: |
          set +e
          python scripts/audit_feed.py --write | tee /tmp/audit.txt
          echo "exit_code=$?" >> "$GITHUB_OUTPUT"
          {
            echo "report<<AUDIT_EOF"
            cat /tmp/audit.txt
            echo "AUDIT_EOF"
          } >> "$GITHUB_OUTPUT"
""",
        1,
    ),
    (
        "dependabot-automerge.yml",
        "on-pr",
        "清理旧资格并撤销 auto-merge",
    ): (
        r"""      - name: 清理旧资格并撤销 auto-merge
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          if [ -z "$HEAD_SHA" ]; then
            echo "pull_request_target 未提供 head SHA，拒绝清理。" >&2
            exit 1
          fi

          current_head=""
          head_query_failed=0
          current_head="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefOid --jq '.headRefOid // empty'
          )" || head_query_failed=1
          if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] || [ "$current_head" != "$HEAD_SHA" ]; then
            python3 - "$REPO" "$PR_NUMBER" <<'PY'
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY
            echo "事件 head 已过期或当前 head 查询失败；已撤销 auto-merge，拒绝旧事件写入。" >&2
            exit 1
          fi

          cleanup_failed=0
          current_labels="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json labels --jq '.labels[].name'
          )" || cleanup_failed=1
          if grep -Fxq "$AUTOMERGE_ELIGIBLE_LABEL" <<<"$current_labels"; then
            gh pr edit "$PR_NUMBER" --repo "$REPO" \
              --remove-label "$AUTOMERGE_ELIGIBLE_LABEL" \
              || cleanup_failed=1
          fi

          python3 - "$REPO" "$PR_NUMBER" <<'PY' || cleanup_failed=1
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY

          gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
            -f state=pending \
            -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
            -f description="Dependabot auto-merge eligibility is being reclassified" \
            --silent \
            || cleanup_failed=1

          if [ "$cleanup_failed" -ne 0 ]; then
            echo "旧资格清理或 auto-merge 撤销失败，拒绝继续分类。" >&2
            exit 1
          fi

          gh label create "$AUTOMERGE_ELIGIBLE_LABEL" \
            --repo "$REPO" \
            --color "0E8A16" \
            --description "Dependabot update classified by fetch-metadata for guarded auto-merge" \
            --force
""",
        r"""      - name: 清理旧资格并撤销 auto-merge
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          if [ -z "$HEAD_SHA" ]; then
            echo "pull_request_target 未提供 head SHA，拒绝清理。" >&2
            exit 1
          fi

          current_head=""
          head_query_failed=0
          current_head="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefOid --jq '.headRefOid // empty'
          )" || head_query_failed=1
          if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] || [ "$current_head" != "$HEAD_SHA" ]; then
            python - "$REPO" "$PR_NUMBER" <<'PY'
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY
            echo "事件 head 已过期或当前 head 查询失败；已撤销 auto-merge，拒绝旧事件写入。" >&2
            exit 1
          fi

          cleanup_failed=0
          current_labels="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json labels --jq '.labels[].name'
          )" || cleanup_failed=1
          if grep -Fxq "$AUTOMERGE_ELIGIBLE_LABEL" <<<"$current_labels"; then
            gh pr edit "$PR_NUMBER" --repo "$REPO" \
              --remove-label "$AUTOMERGE_ELIGIBLE_LABEL" \
              || cleanup_failed=1
          fi

          python - "$REPO" "$PR_NUMBER" <<'PY' || cleanup_failed=1
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY

          gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
            -f state=pending \
            -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
            -f description="Dependabot auto-merge eligibility is being reclassified" \
            --silent \
            || cleanup_failed=1

          if [ "$cleanup_failed" -ne 0 ]; then
            echo "旧资格清理或 auto-merge 撤销失败，拒绝继续分类。" >&2
            exit 1
          fi

          gh label create "$AUTOMERGE_ELIGIBLE_LABEL" \
            --repo "$REPO" \
            --color "0E8A16" \
            --description "Dependabot update classified by fetch-metadata for guarded auto-merge" \
            --force
""",
        2,
    ),
    (
        "dependabot-automerge.yml",
        "on-pr",
        "根据 metadata 同步 auto-merge 资格标签",
    ): (
        r"""      - name: 根据 metadata 同步 auto-merge 资格标签
        id: eligibility
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
          UPDATE_TYPE: ${{ steps.meta.outputs.update-type }}
          PACKAGE_ECOSYSTEM: ${{ steps.meta.outputs.package-ecosystem }}
        run: |
          current_head=""
          head_query_failed=0
          current_head="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefOid --jq '.headRefOid // empty'
          )" || head_query_failed=1
          if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] || [ "$current_head" != "$HEAD_SHA" ]; then
            python3 - "$REPO" "$PR_NUMBER" <<'PY'
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY
            echo "事件 head 已过期或当前 head 查询失败；已撤销 auto-merge，拒绝资格写入。" >&2
            exit 1
          fi

          classification="$(
            python3 scripts/dependabot_merge_gate.py \
              --classify-ecosystem "$PACKAGE_ECOSYSTEM" \
              --classify-update-type "$UPDATE_TYPE"
          )"
          eligible=false
          case "$classification" in
            eligible)
              gh pr edit "$PR_NUMBER" --repo "$REPO" \
                --add-label "$AUTOMERGE_ELIGIBLE_LABEL"
              gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
                -f state=success \
                -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
                -f description="Dependabot update is eligible for guarded auto-merge" \
                --silent
              eligible=true
              ;;
            ineligible)
              gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
                -f state=failure \
                -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
                -f description="Dependabot update is outside guarded auto-merge policy" \
                --silent
              ;;
            *)
              echo "分类器返回未知结果: $classification" >&2
              exit 1
              ;;
          esac

          echo "eligible=$eligible" >> "$GITHUB_OUTPUT"
""",
        r"""      - name: 根据 metadata 同步 auto-merge 资格标签
        id: eligibility
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
          UPDATE_TYPE: ${{ steps.meta.outputs.update-type }}
          PACKAGE_ECOSYSTEM: ${{ steps.meta.outputs.package-ecosystem }}
        run: |
          current_head=""
          head_query_failed=0
          current_head="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefOid --jq '.headRefOid // empty'
          )" || head_query_failed=1
          if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] || [ "$current_head" != "$HEAD_SHA" ]; then
            python - "$REPO" "$PR_NUMBER" <<'PY'
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY
            echo "事件 head 已过期或当前 head 查询失败；已撤销 auto-merge，拒绝资格写入。" >&2
            exit 1
          fi

          classification="$(
            python scripts/dependabot_merge_gate.py \
              --classify-ecosystem "$PACKAGE_ECOSYSTEM" \
              --classify-update-type "$UPDATE_TYPE"
          )"
          eligible=false
          case "$classification" in
            eligible)
              gh pr edit "$PR_NUMBER" --repo "$REPO" \
                --add-label "$AUTOMERGE_ELIGIBLE_LABEL"
              gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
                -f state=success \
                -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
                -f description="Dependabot update is eligible for guarded auto-merge" \
                --silent
              eligible=true
              ;;
            ineligible)
              gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
                -f state=failure \
                -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
                -f description="Dependabot update is outside guarded auto-merge policy" \
                --silent
              ;;
            *)
              echo "分类器返回未知结果: $classification" >&2
              exit 1
              ;;
          esac

          echo "eligible=$eligible" >> "$GITHUB_OUTPUT"
""",
        2,
    ),
    (
        "dependabot-automerge.yml",
        "on-pr",
        "检查 required checks 后启用 auto-merge",
    ): (
        r"""      - name: 检查 required checks 后启用 auto-merge
        if: steps.eligibility.outputs.eligible == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          python3 scripts/dependabot_merge_gate.py \
            --repo "$REPO" \
            --pr "$PR_NUMBER"

""",
        r"""      - name: 检查 required checks 后启用 auto-merge
        if: steps.eligibility.outputs.eligible == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          python scripts/dependabot_merge_gate.py \
            --repo "$REPO" \
            --pr "$PR_NUMBER"

""",
        1,
    ),
    (
        "dependabot-automerge.yml",
        "sweep",
        "清扫存量 dependabot PR",
    ): (
        r"""      - name: 清扫存量 dependabot PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
        run: |
          gh pr list --repo "$REPO" --author 'app/dependabot' --state open \
            --limit 1000 \
            --json number,title > /tmp/prs.json
          python3 - <<'PY'
          import json
          import os
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import gate_pull_request
          from feed_lib import reject_json_constant

          with open("/tmp/prs.json", encoding="utf-8") as handle:
              prs = json.load(handle, parse_constant=reject_json_constant)
          repo = os.environ["REPO"]
          operational_errors = 0
          print(f"开放 dependabot PR: {len(prs)}")
          for pr in prs:
              number = pr["number"]
              title = pr["title"]
              try:
                  decision = gate_pull_request(
                      repo=repo,
                      pr_number=number,
                  )
              except RuntimeError as exc:
                  operational_errors += 1
                  print(f"  #{number} gate error: {exc}", file=sys.stderr)
              else:
                  print(f"  #{number} {decision.value}: {title}")
          if operational_errors:
              raise SystemExit(1)
          PY
""",
        r"""      - name: 清扫存量 dependabot PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
        run: |
          gh pr list --repo "$REPO" --author 'app/dependabot' --state open \
            --limit 1000 \
            --json number,title > /tmp/prs.json
          python - <<'PY'
          import json
          import os
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import gate_pull_request
          from feed_lib import reject_json_constant

          with open("/tmp/prs.json", encoding="utf-8") as handle:
              prs = json.load(handle, parse_constant=reject_json_constant)
          repo = os.environ["REPO"]
          operational_errors = 0
          print(f"开放 dependabot PR: {len(prs)}")
          for pr in prs:
              number = pr["number"]
              title = pr["title"]
              try:
                  decision = gate_pull_request(
                      repo=repo,
                      pr_number=number,
                  )
              except RuntimeError as exc:
                  operational_errors += 1
                  print(f"  #{number} gate error: {exc}", file=sys.stderr)
              else:
                  print(f"  #{number} {decision.value}: {title}")
          if operational_errors:
              raise SystemExit(1)
          PY
""",
        1,
    ),
}
assert len(PRODUCTION_PYTHON_JOBS) == 16
assert {filename for filename, _ in PRODUCTION_PYTHON_JOBS} == (
    PROTECTED_PYTHON_WORKFLOWS
)
assert len(CURRENT_SETUP_STEPS) == 13
assert set(CURRENT_SETUP_STEPS) == (
    set(PRODUCTION_PYTHON_JOBS) - BASELINE_MISSING_SETUP_JOBS
)
assert len(FINAL_SETUP_STEPS) == 16
assert set(FINAL_SETUP_STEPS) == set(PRODUCTION_PYTHON_JOBS)
assert len(CURRENT_INSTALL_STEPS) == 7
assert len(FINAL_INSTALL_STEPS) == 7
assert set(CURRENT_INSTALL_STEPS) == DEPENDENCY_JOBS
assert set(FINAL_INSTALL_STEPS) == DEPENDENCY_JOBS
assert len(APPROVED_PYTHON_RUN_BODIES) == 8
assert set(APPROVED_PYTHON_RUN_BODIES) == APPROVED_PYTHON_RUN_BODY_KEYS
assert sum(item[2] for item in APPROVED_PYTHON_RUN_BODIES.values()) == 11
assert set(FINAL_SMOKE_STEPS) == {
    ("alpha-routine.yml", "run"),
    ("monthly-studies.yml", "studies"),
}
TASK5_SETUP_SENTINEL = "      - __TASK5_ALLOWED_SETUP__\n"
TASK5_INSTALL_SENTINEL = "      - __TASK5_ALLOWED_INSTALL__\n"
TASK5_SMOKE_SENTINEL = "      - __TASK5_ALLOWED_SMOKE__\n"
CANONICAL_SWEEP_CHECKOUT_STEP = """      - uses: actions/checkout@v7
        __TASK5_ALLOWED_SWEEP_CREDENTIAL__
"""
SHELL_CONTROL = {";", "&&", "||", "|", "&", "(", ")"}
BLOCK_SCALAR_HEADER = re.compile(
    r"^(?P<style>[|>])(?:(?:[+-][1-9]?|[1-9][+-]?))?(?:[ \t]+#.*)?$"
)
PYTHON_INTERPRETER_TOKEN = re.compile(
    r'''(?x)
    (?<![A-Za-z0-9_./$~{}+\-])
    (?:
      "(?:(?:[^"\r\n]*/)?python(?:3(?:\.\d+)*)?)"
     |
      '(?:(?:[^'\r\n]*/)?python(?:3(?:\.\d+)*)?)'
     |
      (?:
        (?:
          (?:/|\./|\.\./|~/|\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*\})/)
          (?:[^\s"';&|()<>]+/)*
        )
       |
        (?:[A-Za-z0-9_.~+${}\-]+/)+
      )?
      python(?:3(?:\.\d+)*)?
    )
    (?=$|[\s;&|()<>])
    '''
)
FORBIDDEN_INTERPRETER_MUTATIONS = (
    "/usr/bin/python scripts/daily_digest.py",
    '"/tmp/venv/bin/python" scripts/daily_digest.py',
    '"/tmp/my env/bin/python" scripts/daily_digest.py',
    "$VENV/bin/python scripts/daily_digest.py",
    "${VENV}/bin/python3.12 scripts/daily_digest.py",
    "'python3.11' scripts/daily_digest.py",
    "python3.12 scripts/daily_digest.py",
)
EXPECTED_PYTHON_POLICY_JOBS = set(PRODUCTION_PYTHON_JOBS) | {
    ("tests.yml", "python")
}
EXPECTED_FALSE_CHECKOUT_COUNTS = {
    ("dependabot-automerge.yml", "on-pr"): 1,
    ("dependabot-automerge.yml", "sweep"): 1,
    ("feed-validate.yml", "pr-validate"): 2,
}
DEPENDABOT_CONCURRENCY_LINES = [
    "  group: dependabot-automerge-${{ github.repository }}",
    "  queue: max",
]
TRUSTED_BASE_CHECKOUT_STEP = """      - name: Checkout trusted base validator
        uses: actions/checkout@v7
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          path: trusted
          persist-credentials: false
"""
UNTRUSTED_DATA_CHECKOUT_STEP = """      - name: Checkout untrusted submission as data only
        uses: actions/checkout@v7
        with:
          repository: ${{ github.event.pull_request.head.repo.full_name }}
          ref: ${{ github.event.pull_request.head.sha }}
          path: submission
          persist-credentials: false
          allow-unsafe-pr-checkout: true
"""
GENERATED_FEED_IGNORES = [
    "feed/crypto/**",
    "feed/factory/**",
    "feed/funds/**",
    "feed/health.json",
    "feed/index.json",
    "feed/intraday/**",
    "feed/market/**",
    "feed/reports/**",
    "feed/screener/**",
    "feed/signals/**",
    "feed/stock-notes/**",
    "feed/watchlist.json",
]
EXPECTED_PAGES_WORKFLOW = """name: Deploy frontend to GitHub Pages

on:
  push:
    branches: [main]
    paths: ["frontend/**", "feed/schema/**", ".node-version", ".github/workflows/deploy-pages.yml"]
  workflow_dispatch:

permissions: {}

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: actions/setup-node@v7
        with:
          node-version-file: .node-version
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Verify exact Node and npm
        run: |
          test "$(node --version)" = "v20.20.2"
          test "$(npm --version)" = "10.8.2"
      - name: Bundle latest feed snapshot
        working-directory: ${{ github.workspace }}
        run: |
          set -euo pipefail
          snapshot="$RUNNER_TEMP/feed-snapshot"
          rm -rf "$snapshot"
          mkdir -p "$snapshot"
          sources=(
            feed/index.json
            feed/health.json
            feed/watchlist.json
            feed/schema
            feed/reports
            feed/signals
            feed/market
            feed/factory
            feed/screener
            feed/stock-notes
            feed/crypto
            feed/intraday
            feed/funds
          )
          for source in "${sources[@]}"; do
            test -e "$source"
          done
          cp -R -- "${sources[@]}" "$snapshot/"
      - run: npm ci
      - name: Build and smoke static profile
        env:
          STATIC_FEED_SOURCE: ${{ runner.temp }}/feed-snapshot
          NEXT_PUBLIC_BASE_PATH: /${{ github.event.repository.name }}
          NEXT_PUBLIC_API_BASE: ${{ vars.API_BASE }}
          NEXT_PUBLIC_EDGE_BASE: ${{ vars.EDGE_BASE }}
          NEXT_PUBLIC_FEED_BASE: https://raw.githubusercontent.com/${{ github.repository }}/${{ github.ref_name }}/feed
        run: |
          npm run build:static
          npm run smoke:static
      - name: Verify complete exported feed snapshot
        run: |
          set -euo pipefail
          entries=(
            index.json
            health.json
            watchlist.json
            schema
            reports
            signals
            market
            factory
            screener
            stock-notes
            crypto
            intraday
            funds
          )
          for entry in "${entries[@]}"; do
            test -e "out/feed/$entry"
          done
          test -f out/feed/funds/situational-awareness.json
          test -f out/feed/intraday/latest.json
          test -f out/feed/intraday/overnight.json
      - uses: actions/upload-pages-artifact@v5
        with:
          path: frontend/out

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
"""
PAGES_SNAPSHOT_ENTRIES = [
    "index.json",
    "health.json",
    "watchlist.json",
    "schema",
    "reports",
    "signals",
    "market",
    "factory",
    "screener",
    "stock-notes",
    "crypto",
    "intraday",
    "funds",
]
PAGES_CRITICAL_OUTPUTS = [
    "funds/situational-awareness.json",
    "intraday/latest.json",
    "intraday/overnight.json",
]
EXPECTED_RENDER_BLUEPRINT = """# Render Blueprint —— 一键部署后端 FastAPI。
services:
  - type: web
    name: stock-dashboard-api
    runtime: python
    rootDir: backend
    plan: free
    buildCommand: python -m pip install --require-hashes -r requirements.txt
    startCommand: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/v1/health
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.15"
"""
EXPECTED_BACKEND_QUICK_START = """## 运行

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
"""
TOP_LEVEL_WORKFLOW_KEYS = ["name", "on", "permissions", "concurrency", "jobs"]
JOB_KEYS = ["frontend", "python", "gate"]
FRONTEND_JOB_KEYS = ["name", "runs-on", "strategy", "defaults", "env", "steps"]
PYTHON_JOB_KEYS = ["name", "runs-on", "strategy", "env", "steps"]
GATE_JOB_KEYS = ["name", "if", "needs", "runs-on", "steps"]
EVENT_POLICY_LINES = [
    "  push:",
    "    branches: [main]",
    "    paths-ignore:",
    *[f'      - "{path}"' for path in GENERATED_FEED_IGNORES],
    "  pull_request:",
    "  workflow_dispatch:",
]
CONCURRENCY_LINES = [
    "  group: ci-${{ github.ref }}",
    "  cancel-in-progress: true",
]
FRONTEND_DEFAULTS_LINES = [
    "      run:",
    "        working-directory: frontend",
]
FRONTEND_ENV_LINES = [
    "      # Approved spec still requires Node 20.20.2 even though Node 20 is EOL.",
    '      NEXT_TELEMETRY_DISABLED: "1"',
    "      NEXT_PUBLIC_BASE_PATH: ${{ matrix.base_path }}",
]
PYTHON_ENV_LINES = [
    '      PYTHONDONTWRITEBYTECODE: "1"',
    '      PIP_DISABLE_PIP_VERSION_CHECK: "1"',
]
COMMON_PYTHON_ENTRYPOINTS = [
    "python tests/test_backend.py",
    "python tests/test_api.py",
    "python scripts/tests/test_chan_engine.py",
    "python scripts/tests/test_validate_feed.py",
    "python scripts/tests/test_feed_validation_security.py",
    "python scripts/tests/test_feed_ingress.py",
    "python scripts/tests/test_validate_feed_cli.py",
    "python scripts/tests/test_feed_publication.py",
    "python scripts/tests/test_dependabot_merge_gate.py",
    "python scripts/tests/test_workflow_security.py",
]
LOCK_COMPILE_FLAGS = [
    "--generate-hashes",
    "--allow-unsafe",
    "--no-reuse-hashes",
    "--resolver=backtracking",
    "--no-strip-extras",
    "--no-header",
]
FRONTEND_STRATEGY_LINES = [
    "      fail-fast: false",
    "      matrix:",
    "        include:",
    "          - profile: static",
    "            base_path: /stock-analysis",
    "          - profile: server",
    '            base_path: ""',
]
PYTHON_STRATEGY_LINES = [
    "      fail-fast: false",
    "      matrix:",
    "        include:",
    '          - python_version: "3.11.15"',
    "            lockfile: requirements/ci-py311.txt",
    '          - python_version: "3.12.13"',
    "            lockfile: requirements/ci-py312.txt",
]
PY311_LOCK_REPRODUCTIONS = [
    ("backend/requirements.txt", "backend.txt", "backend/requirements.in"),
    ("scripts/requirements.txt", "scripts.txt", "scripts/requirements.in"),
    (
        "scripts/requirements-winter-pg.txt",
        "winter-pg.txt",
        "scripts/requirements-winter-pg.in",
    ),
    ("backtest/requirements.txt", "backtest.txt", "backtest/requirements.in"),
    (
        "requirements/automation.txt",
        "automation.txt",
        "requirements/automation.in",
    ),
    ("requirements/ci-py311.txt", "ci-py311.txt", "requirements/ci.in"),
]
PY312_LOCK_REPRODUCTIONS = [
    ("requirements/ci-py312.txt", "ci-py312.txt", "requirements/ci.in"),
]
FRONTEND_STEP_BLOCKS = [
    "\n".join(
        [
            "      - uses: actions/checkout@v7",
            "        with:",
            "          persist-credentials: false",
        ]
    ),
    "\n".join(
        [
            "      - uses: actions/setup-node@v7",
            "        with:",
            "          node-version-file: .node-version",
            "          cache: npm",
            "          cache-dependency-path: frontend/package-lock.json",
        ]
    ),
    "\n".join(
        [
            "      - name: Verify exact Node and npm",
            "        run: |",
            '          test "$(node --version)" = "v20.20.2"',
            '          test "$(npm --version)" = "10.8.2"',
        ]
    ),
    "      - run: npm ci",
    "      - run: npm run lint",
    "      - run: npm run typecheck",
    "      - run: npm run test:scripts",
    "\n".join(
        [
            "      - if: matrix.profile == 'static'",
            "        run: npm run build:static",
        ]
    ),
    "\n".join(
        [
            "      - if: matrix.profile == 'static'",
            "        run: npm run smoke:static",
        ]
    ),
    "\n".join(
        [
            "      - if: matrix.profile == 'server'",
            "        run: npm run build:server",
        ]
    ),
    "\n".join(
        [
            "      - if: matrix.profile == 'server'",
            "        run: npm run smoke:server",
        ]
    ),
]


def expected_reproduction_step(
    name: str,
    version: str,
    rows: list[tuple[str, str, str]],
) -> str:
    compile_flags = " ".join(LOCK_COMPILE_FLAGS)
    lines = [
        f"      - name: {name}",
        f"        if: matrix.python_version == '{version}'",
        "        shell: bash",
        "        run: |",
        "          set -euo pipefail",
        '          tmp="$(mktemp -d)"',
        "          trap 'rm -rf \"$tmp\"' EXIT",
    ]
    lines.extend(
        f'          cp {committed} "$tmp/{temporary}"'
        for committed, temporary, _ in rows
    )
    lines.extend(
        "          python -m piptools compile "
        f'{compile_flags} --output-file="$tmp/{temporary}" {direct_input}'
        for _, temporary, direct_input in rows
    )
    lines.extend(
        f'          cmp "$tmp/{temporary}" {committed}'
        for committed, temporary, _ in rows
    )
    return "\n".join(lines)


PYTHON_STEP_BLOCKS = [
    "\n".join(
        [
            "      - uses: actions/checkout@v7",
            "        with:",
            "          persist-credentials: false",
        ]
    ),
    "\n".join(
        [
            "      - uses: actions/setup-python@v6",
            "        with:",
            "          python-version: ${{ matrix.python_version }}",
            "          cache: pip",
            "          cache-dependency-path: ${{ matrix.lockfile }}",
        ]
    ),
    '      - run: python -m pip install --require-hashes -r "${{ matrix.lockfile }}"',
    "      - run: python -m pip check",
    expected_reproduction_step(
        "Reproduce Python 3.11 locks from direct inputs",
        "3.11.15",
        PY311_LOCK_REPRODUCTIONS,
    ),
    expected_reproduction_step(
        "Reproduce Python 3.12 lock from direct inputs",
        "3.12.13",
        PY312_LOCK_REPRODUCTIONS,
    ),
    "\n".join(
        [
            "      - name: Backend HTTP and data-layer tests",
            "        working-directory: backend",
            "        run: |",
            "          python tests/test_backend.py",
            "          python tests/test_api.py",
        ]
    ),
    "\n".join(
        [
            "      - name: Automation and feed-validation tests",
            "        run: |",
            *[f"          {command}" for command in COMMON_PYTHON_ENTRYPOINTS[2:]],
        ]
    ),
    "\n".join(
        [
            "      - name: Primary-runtime lock consistency",
            "        if: matrix.python_version == '3.11.15'",
            "        run: |",
            "          python scripts/tests/test_check_lock_consistency.py",
            "          python scripts/check_lock_consistency.py --root .",
        ]
    ),
]
GATE_STEP_BLOCKS = [
    "\n".join(
        [
            "      - name: Require every runtime matrix to pass",
            "        env:",
            "          FRONTEND_RESULT: ${{ needs.frontend.result }}",
            "          PYTHON_RESULT: ${{ needs.python.result }}",
            "        run: |",
            '          test "$FRONTEND_RESULT" = success',
            '          test "$PYTHON_RESULT" = success',
        ]
    )
]


def workflow_run_scripts(text: str) -> list[tuple[int, str]]:
    """Extract inline and block-scalar run scripts without a YAML dependency."""
    lines = text.splitlines()
    scripts: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = re.match(
            r"^(?P<indent>\s*)(?:-\s*)?run:\s*(?P<body>.*)$",
            lines[index],
        )
        if match is None:
            index += 1
            continue
        start = index + 1
        body = match.group("body").strip()
        block_header = BLOCK_SCALAR_HEADER.fullmatch(body)
        if block_header is not None:
            base_indent = len(match.group("indent"))
            block: list[str] = []
            index += 1
            while index < len(lines):
                line = lines[index]
                indentation = len(line) - len(line.lstrip())
                if line.strip() and indentation <= base_indent:
                    break
                block.append(line[base_indent + 1 :])
                index += 1
            script = "\n".join(block)
            if block_header.group("style") == ">":
                script = " ".join(part.strip() for part in block)
            scripts.append((start, script))
            continue
        try:
            unquoted = shlex.split(body)
        except ValueError:
            unquoted = []
        scripts.append((start, unquoted[0] if len(unquoted) == 1 else body))
        index += 1
    return scripts


def git_add_pathspecs(script: str) -> list[str]:
    """Return pathspec-like arguments from git add, including git -C DIR add."""
    logical = re.sub(r"\\\r?\n[ \t]*", " ", script)
    pathspecs: list[str] = []
    for line in logical.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        try:
            tokens = list(lexer)
        except ValueError:
            continue
        for cursor, token in enumerate(tokens):
            if token != "git":
                continue
            command = cursor + 1
            while command < len(tokens) and tokens[command] == "-C":
                command += 2
            if command >= len(tokens) or tokens[command] != "add":
                continue
            argument = command + 1
            while argument < len(tokens) and tokens[argument] not in SHELL_CONTROL:
                pathspecs.append(tokens[argument])
                argument += 1
    return pathspecs


def is_broad_feed_pathspec(pathspec: str) -> bool:
    candidate = pathspec
    if candidate.startswith(":(") and ")" in candidate:
        candidate = candidate.split(")", 1)[1]
    elif candidate.startswith(":/"):
        candidate = candidate[2:]
    while candidate.startswith("./"):
        candidate = candidate[2:]
    while candidate.endswith("/."):
        candidate = candidate[:-2]
    if candidate.rstrip("/") == "feed":
        return True
    return candidate.startswith("feed/") and any(
        wildcard in candidate for wildcard in "*?["
    )


def broad_feed_adds(text: str) -> list[tuple[int, str]]:
    offenders: list[tuple[int, str]] = []
    for line_number, script in workflow_run_scripts(text):
        for pathspec in git_add_pathspecs(script):
            if is_broad_feed_pathspec(pathspec):
                offenders.append((line_number, pathspec))
    return offenders


def top_level_mapping_block(text: str, key: str) -> str:
    """Return one top-level YAML mapping block without parsing YAML."""
    return mapping_block(text, key, indent=0)


def mapping_block(text: str, key: str, indent: int) -> str:
    """Return one YAML mapping body at the requested indentation."""
    lines = text.splitlines()
    header = f"{' ' * indent}{key}:"
    starts = [index for index, line in enumerate(lines) if line == header]
    if len(starts) != 1:
        raise AssertionError(
            f"expected one indent-{indent} {key!r} block, found {len(starts)}"
        )
    block: list[str] = []
    for line in lines[starts[0] + 1 :]:
        line_indent = len(line) - len(line.lstrip())
        if line.strip() and line_indent <= indent:
            break
        block.append(line)
    return "\n".join(block)


def direct_mapping_keys(text: str, indent: int) -> list[str]:
    """Return every direct mapping key, rejecting unsupported key syntax."""
    key_pattern = re.compile(
        rf"^{' ' * indent}"
        r"(?P<key>[A-Za-z0-9_-]+|\"[^\"]+\"|'[^']+')\s*:"
    )
    keys: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent != indent:
            continue
        match = key_pattern.match(line)
        if match is None:
            keys.append(f"<invalid:{line.strip()}>")
            continue
        key = match.group("key")
        if key[:1] in {'"', "'"} and key[-1:] == key[:1]:
            key = key[1:-1]
        keys.append(key)
    return keys


def direct_mapping_value(text: str, key: str, indent: int) -> str:
    """Return the raw value from exactly one direct mapping entry."""
    key_pattern = re.compile(
        rf"^{' ' * indent}{re.escape(key)}:\s*(?P<value>.*)$"
    )
    values = [
        match.group("value")
        for line in text.splitlines()
        if (match := key_pattern.match(line)) is not None
    ]
    if len(values) != 1:
        raise AssertionError(
            f"expected one indent-{indent} {key!r} value, found {len(values)}"
        )
    return values[0]


def step_direct_mapping_keys(step: str) -> list[str]:
    """Return one workflow step's direct keys, including its dash-prefixed key."""
    lines = step.splitlines()
    if not lines:
        raise AssertionError("workflow step is empty")
    first = re.match(r"^ {6}- (?P<entry>.+)$", lines[0])
    if first is None:
        raise AssertionError(f"invalid workflow step header: {lines[0]!r}")
    normalized = "\n".join(
        [f"        {first.group('entry')}", *lines[1:]]
    )
    return direct_mapping_keys(normalized, indent=8)


def step_direct_mapping_value(step: str, key: str) -> str:
    """Return one workflow step's raw direct value."""
    lines = step.splitlines()
    if not lines:
        raise AssertionError("workflow step is empty")
    first = re.match(r"^ {6}- (?P<entry>.+)$", lines[0])
    if first is None:
        raise AssertionError(f"invalid workflow step header: {lines[0]!r}")
    normalized = "\n".join(
        [f"        {first.group('entry')}", *lines[1:]]
    )
    return direct_mapping_value(normalized, key, indent=8)


def workflow_step_blocks(job_block: str) -> list[str]:
    """Return step-local blocks so policy strings cannot satisfy another step."""
    lines = job_block.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^ {6}-(?:\s|$)", line)
    ]
    return [
        "\n".join(lines[start : starts[offset + 1] if offset + 1 < len(starts) else None])
        for offset, start in enumerate(starts)
    ]


def normalized_step_blocks(job_block: str) -> list[str]:
    """Return exact step blocks while ignoring only trailing blank separators."""
    return [block.rstrip() for block in workflow_step_blocks(job_block)]


def only_block_containing(blocks: list[str], marker: str) -> str:
    matches = [block for block in blocks if marker in block]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one block containing {marker!r}, found {len(matches)}"
        )
    return matches[0]


def command_lines(*blocks: str) -> list[str]:
    """Return process-level commands from one or more scoped run-step blocks."""
    commands: list[str] = []
    for block in blocks:
        commands.extend(
            line.strip()
            for line in block.splitlines()
            if line.strip().startswith("python ")
        )
    return commands


def step_if_expressions(step: str) -> list[str]:
    """Return every step-level if expression without matching job-level policy."""
    return [
        match.group(1).strip()
        for match in re.finditer(
            r"(?m)^(?:      - |        )if:\s*(.+)$",
            step,
        )
    ]


def step_run_scripts(step: str) -> list[str]:
    """Return normalized run bodies from exactly one scoped step."""
    return [
        "\n".join(line.strip() for line in script.strip().splitlines())
        for _, script in workflow_run_scripts(step)
    ]


def reproduction_lines(block: str, prefix: str) -> list[str]:
    """Return ordered, normalized shell lines for one reproduction operation."""
    return [
        line.strip()
        for line in block.splitlines()
        if line.strip().startswith(prefix)
    ]


def protected_workflow_payload(
    root: pathlib.Path,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Read the complete protected workflow set without newline conversion."""
    replacements = {} if overrides is None else dict(overrides)
    unknown = set(replacements) - PROTECTED_PYTHON_WORKFLOWS
    if unknown:
        raise ValueError(f"unprotected workflow override: {sorted(unknown)!r}")
    if any(not isinstance(value, str) for value in replacements.values()):
        raise ValueError("workflow overrides must be decoded text")

    workflow_root = pathlib.Path(root) / ".github" / "workflows"
    payload: dict[str, str] = {}
    for filename in sorted(PROTECTED_PYTHON_WORKFLOWS):
        payload[filename] = replacements.get(
            filename,
            (workflow_root / filename).read_bytes().decode("utf-8"),
        )
    return payload


def raw_job_step_spans(text: str) -> dict[str, dict[str, object]]:
    """Return exact job and step byte spans for one workflow."""
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    jobs_headers = [
        index
        for index, line in enumerate(lines)
        if line.rstrip("\r\n") == "jobs:"
    ]
    if len(jobs_headers) != 1:
        raise ValueError(f"expected exactly one jobs block, found {len(jobs_headers)}")
    jobs_header = jobs_headers[0]
    jobs_end = len(lines)
    for index in range(jobs_header + 1, len(lines)):
        line = lines[index]
        if line.strip() and len(line) - len(line.lstrip()) == 0:
            jobs_end = index
            break

    headers: list[tuple[int, str]] = []
    job_header = re.compile(
        r"""^[ ]{2}(?:
            (?P<bare>[A-Za-z0-9_-]+)
          | "(?P<double>[A-Za-z0-9_-]+)"
          | '(?P<single>[A-Za-z0-9_-]+)'
        ):$""",
        re.VERBOSE,
    )
    for index in range(jobs_header + 1, jobs_end):
        line = lines[index].rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indentation = len(line) - len(line.lstrip())
        if indentation != 2:
            continue
        match = job_header.fullmatch(line)
        if match is None:
            raise ValueError(
                f"unsupported direct jobs entry at line {index + 1}: "
                f"{line.strip()!r}"
            )
        job_name = next(
            value
            for value in (
                match.group("bare"),
                match.group("double"),
                match.group("single"),
            )
            if value is not None
        )
        headers.append((index, job_name))
    if not headers:
        raise ValueError("workflow has no jobs")
    if len({name for _, name in headers}) != len(headers):
        raise ValueError("workflow contains duplicate job keys")

    jobs: dict[str, dict[str, object]] = {}
    for position, (start_line, job_name) in enumerate(headers):
        end_line = (
            headers[position + 1][0]
            if position + 1 < len(headers)
            else jobs_end
        )
        step_lines = [
            index
            for index in range(start_line + 1, end_line)
            if re.match(r"^      -(?:\s|$)", lines[index])
        ]
        steps: list[dict[str, object]] = []
        for step_index, step_line in enumerate(step_lines):
            step_end_line = (
                step_lines[step_index + 1]
                if step_index + 1 < len(step_lines)
                else end_line
            )
            start = offsets[step_line]
            end = offsets[step_end_line]
            steps.append(
                {
                    "index": step_index,
                    "start": start,
                    "end": end,
                    "raw": text[start:end],
                }
            )
        jobs[job_name] = {
            "start": offsets[start_line],
            "end": offsets[end_line],
            "steps": steps,
        }
    return jobs


def raw_step_name(step: str) -> str | None:
    match = re.match(r"^      - name: (?P<name>[^\r\n]+)(?:\r?\n|$)", step)
    return None if match is None else match.group("name")


def step_action_count(step: str, action: str) -> int:
    return len(
        re.findall(
            rf"(?m)^\s+(?:-\s+)?uses:\s+{re.escape(action)}\S*\s*$",
            step,
        )
    )


def step_has_install_command(step: str) -> bool:
    for _, script in workflow_run_scripts(step):
        logical = re.sub(r"\\\r?\n[ \t]*", " ", script)
        for line in logical.splitlines():
            try:
                lexer = shlex.shlex(
                    line,
                    posix=True,
                    punctuation_chars=";&|()",
                )
                lexer.whitespace_split = True
                lexer.commenters = "#"
                tokens = list(lexer)
            except ValueError:
                continue
            segments: list[list[str]] = [[]]
            for token in tokens:
                if re.fullmatch(r"[;&|()]+", token):
                    if segments[-1]:
                        segments.append([])
                    continue
                segments[-1].append(token)
            for command in (segment for segment in segments if segment):
                cursor = 1 if command[:1] == ["env"] else 0
                while cursor < len(command) and re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*=.*",
                    command[cursor],
                ):
                    cursor += 1
                if cursor >= len(command):
                    continue
                executable = command[cursor].rsplit("/", 1)[-1]
                arguments = command[cursor + 1 :]
                if (
                    re.fullmatch(r"python(?:3(?:\.\d+)*)?", executable)
                    and arguments[:3] == ["-m", "pip", "install"]
                ) or (
                    re.fullmatch(r"pip(?:3(?:\.\d+)*)?", executable)
                    and arguments[:1] == ["install"]
                ):
                    return True
    return False


def step_is_smoke_candidate(step: str) -> bool:
    return (
        "name: Smoke combined automation imports" in step
        or re.search(
            r"""PYTHONPATH=backtest:scripts\s+python(?:3)?\s+-c\s+
                ["']import\s+""",
            step,
            re.VERBOSE,
        )
        is not None
    )


def protected_workflow_structure(
    payload: dict[str, str],
) -> dict[str, object]:
    jobs_by_file: dict[str, dict[str, dict[str, object]]] = {}
    setup_by_site: dict[tuple[str, str], list[dict[str, object]]] = {}
    install_by_site: dict[tuple[str, str], list[dict[str, object]]] = {}
    smoke_by_site: dict[tuple[str, str], list[dict[str, object]]] = {}
    parsed_setup_actions = 0
    raw_setup_actions = 0

    if set(payload) != PROTECTED_PYTHON_WORKFLOWS:
        raise ValueError("protected workflow payload is incomplete")
    for filename in sorted(payload):
        text = payload[filename]
        jobs = raw_job_step_spans(text)
        jobs_by_file[filename] = jobs
        raw_setup_actions += len(re.findall(r"actions/setup-python@", text))
        for job_name, job in jobs.items():
            site = (filename, job_name)
            for step in job["steps"]:
                raw = step["raw"]
                setup_count = step_action_count(raw, "actions/setup-python@")
                parsed_setup_actions += setup_count
                if setup_count:
                    setup_by_site.setdefault(site, []).append(step)
                if step_has_install_command(raw):
                    install_by_site.setdefault(site, []).append(step)
                if step_is_smoke_candidate(raw):
                    smoke_by_site.setdefault(site, []).append(step)

    if parsed_setup_actions != raw_setup_actions:
        raise ValueError(
            "setup-python occurrence exists outside an exact parsed step"
        )
    python3_count = sum(
        len(
            re.findall(
                r"(?<![A-Za-z0-9_])python3(?=$|[\s;&|()<>])",
                text,
            )
        )
        for text in payload.values()
    )
    return {
        "jobs": jobs_by_file,
        "setup": setup_by_site,
        "install": install_by_site,
        "smoke": smoke_by_site,
        "python3_count": python3_count,
        "raw_setup_count": raw_setup_actions,
    }


def only_step_with_name(
    structure: dict[str, object],
    filename: str,
    job_name: str,
    step_name: str,
) -> dict[str, object] | None:
    job = structure["jobs"].get(filename, {}).get(job_name)
    if job is None:
        return None
    matches = [
        step
        for step in job["steps"]
        if raw_step_name(step["raw"]) == step_name
    ]
    return matches[0] if len(matches) == 1 else None


def state_matches(
    payload: dict[str, str],
    structure: dict[str, object],
    state: str,
) -> bool:
    if state not in {"BASELINE", "FINAL"}:
        raise ValueError(f"unknown protected workflow state: {state}")
    setups = (
        CURRENT_SETUP_STEPS if state == "BASELINE" else FINAL_SETUP_STEPS
    )
    installs = (
        CURRENT_INSTALL_STEPS if state == "BASELINE" else FINAL_INSTALL_STEPS
    )
    smokes = {} if state == "BASELINE" else FINAL_SMOKE_STEPS
    body_index = 0 if state == "BASELINE" else 1
    expected_python3 = 11 if state == "BASELINE" else 0

    setup_inventory = structure["setup"]
    if set(setup_inventory) != set(setups):
        return False
    for site, literal in setups.items():
        matches = setup_inventory.get(site, [])
        if len(matches) != 1 or matches[0]["raw"] != literal:
            return False
        filename, job_name = site
        job = structure["jobs"].get(filename, {}).get(job_name)
        if job is None:
            return False
        checkout_indices = [
            step["index"]
            for step in job["steps"]
            if step_action_count(step["raw"], "actions/checkout@")
        ]
        if not checkout_indices or matches[0]["index"] != checkout_indices[-1] + 1:
            return False

    install_inventory = structure["install"]
    if set(install_inventory) != set(installs):
        return False
    for site, literal in installs.items():
        matches = install_inventory.get(site, [])
        if len(matches) != 1 or matches[0]["raw"] != literal:
            return False

    smoke_inventory = structure["smoke"]
    if set(smoke_inventory) != set(smokes):
        return False
    for site, literal in smokes.items():
        matches = smoke_inventory.get(site, [])
        if len(matches) != 1 or matches[0]["raw"] != literal:
            return False
        install = install_inventory[site][0]
        if matches[0]["index"] != install["index"] + 1:
            return False

    sweep_steps = (
        structure["jobs"]
        .get("dependabot-automerge.yml", {})
        .get("sweep", {})
        .get("steps", [])
    )
    sweep_checkouts = [
        step
        for step in sweep_steps
        if step_action_count(step["raw"], "actions/checkout@")
    ]
    expected_sweep = (
        CURRENT_SWEEP_CHECKOUT_STEP
        if state == "BASELINE"
        else FINAL_SWEEP_CHECKOUT_STEP
    )
    if len(sweep_checkouts) != 1 or sweep_checkouts[0]["raw"] != expected_sweep:
        return False

    for (filename, job_name, step_name), bodies in (
        APPROVED_PYTHON_RUN_BODIES.items()
    ):
        step = only_step_with_name(
            structure,
            filename,
            job_name,
            step_name,
        )
        if step is None or step["raw"] != bodies[body_index]:
            return False
        expected_count = bodies[2] if state == "BASELINE" else 0
        if len(re.findall(r"(?<![A-Za-z0-9_])python3(?=\s)", step["raw"])) != (
            expected_count
        ):
            return False

    expected_counts = (
        (13, 7, 0, 11) if state == "BASELINE" else (16, 7, 2, 0)
    )
    actual_counts = (
        sum(len(items) for items in setup_inventory.values()),
        sum(len(items) for items in install_inventory.values()),
        sum(len(items) for items in smoke_inventory.values()),
        structure["python3_count"],
    )
    return actual_counts == expected_counts


def apply_raw_replacements(
    text: str,
    replacements: list[tuple[int, int, str]],
) -> str:
    """Apply approved original-text spans in descending offset order."""
    nonempty = sorted(
        (start, end)
        for start, end, _ in replacements
        if start != end
    )
    for index, (start, end) in enumerate(nonempty):
        if start < 0 or end < start or end > len(text):
            raise ValueError("replacement span is outside source text")
        if index and start < nonempty[index - 1][1]:
            raise ValueError("approved workflow replacements overlap")
    for start, end, _ in replacements:
        if start == end and any(
            other_start < start < other_end
            for other_start, other_end in nonempty
        ):
            raise ValueError("approved workflow insertion overlaps a span")

    result = text
    for start, end, replacement in sorted(
        replacements,
        key=lambda item: (item[0], item[1]),
        reverse=True,
    ):
        result = result[:start] + replacement + result[end:]
    return result


def last_checkout_step(
    structure: dict[str, object],
    site: tuple[str, str],
) -> dict[str, object]:
    filename, job_name = site
    job = structure["jobs"].get(filename, {}).get(job_name)
    if job is None:
        raise ValueError(f"missing protected job: {site!r}")
    matches = [
        step
        for step in job["steps"]
        if step_action_count(step["raw"], "actions/checkout@")
    ]
    if not matches:
        raise ValueError(f"missing checkout in protected job: {site!r}")
    return matches[-1]


def normalized_protected_workflows(
    root: pathlib.Path,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    payload = protected_workflow_payload(root, overrides)
    structure = protected_workflow_structure(payload)
    current_ok = state_matches(payload, structure, "BASELINE")
    final_ok = state_matches(payload, structure, "FINAL")
    if not current_ok ^ final_ok:
        raise ValueError("protected workflows do not match one complete state")
    state = "BASELINE" if current_ok else "FINAL"

    normalized: dict[str, str] = {}
    replacements_by_file: dict[str, list[tuple[int, int, str]]] = {
        filename: [] for filename in payload
    }
    setup_literals = (
        CURRENT_SETUP_STEPS if state == "BASELINE" else FINAL_SETUP_STEPS
    )
    for site in setup_literals:
        filename, _ = site
        step = structure["setup"][site][0]
        replacements_by_file[filename].append(
            (step["start"], step["end"], TASK5_SETUP_SENTINEL)
        )

    sweep_site = ("dependabot-automerge.yml", "sweep")
    sweep_checkout = last_checkout_step(structure, sweep_site)
    sweep_replacement = CANONICAL_SWEEP_CHECKOUT_STEP
    if state == "BASELINE":
        sweep_replacement += TASK5_SETUP_SENTINEL
        for site in BASELINE_MISSING_SETUP_JOBS - {sweep_site}:
            filename, _ = site
            checkout = last_checkout_step(structure, site)
            replacements_by_file[filename].append(
                (checkout["end"], checkout["end"], TASK5_SETUP_SENTINEL)
            )
    replacements_by_file[sweep_site[0]].append(
        (
            sweep_checkout["start"],
            sweep_checkout["end"],
            sweep_replacement,
        )
    )

    install_literals = (
        CURRENT_INSTALL_STEPS if state == "BASELINE" else FINAL_INSTALL_STEPS
    )
    for site in install_literals:
        filename, _ = site
        step = structure["install"][site][0]
        replacement = TASK5_INSTALL_SENTINEL
        if state == "BASELINE" and site in FINAL_SMOKE_STEPS:
            replacement += TASK5_SMOKE_SENTINEL
        replacements_by_file[filename].append(
            (step["start"], step["end"], replacement)
        )
    if state == "FINAL":
        for site in FINAL_SMOKE_STEPS:
            filename, _ = site
            step = structure["smoke"][site][0]
            replacements_by_file[filename].append(
                (step["start"], step["end"], TASK5_SMOKE_SENTINEL)
            )

    body_index = 0 if state == "BASELINE" else 1
    for (filename, job_name, step_name), bodies in (
        APPROVED_PYTHON_RUN_BODIES.items()
    ):
        step = only_step_with_name(
            structure,
            filename,
            job_name,
            step_name,
        )
        if step is None or step["raw"] != bodies[body_index]:
            raise ValueError(f"approved Python body changed: {step_name}")
        replacements_by_file[filename].append(
            (step["start"], step["end"], bodies[1])
        )

    for filename, text in payload.items():
        normalized[filename] = apply_raw_replacements(
            text,
            replacements_by_file[filename],
        )
    return normalized


def encoded_workflow_payload(payload: dict[str, str]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def transition_protected_workflows(
    payload: dict[str, str],
    state: str,
) -> dict[str, str]:
    """Build the opposite complete state from fixed transition literals."""
    structure = protected_workflow_structure(payload)
    if not state_matches(payload, structure, state):
        raise ValueError(f"cannot transition invalid {state} fixture")
    target = "FINAL" if state == "BASELINE" else "BASELINE"
    replacements_by_file: dict[str, list[tuple[int, int, str]]] = {
        filename: [] for filename in payload
    }

    if state == "BASELINE":
        for site, target_literal in FINAL_SETUP_STEPS.items():
            filename, _ = site
            if site in BASELINE_MISSING_SETUP_JOBS:
                checkout = last_checkout_step(structure, site)
                replacements_by_file[filename].append(
                    (checkout["end"], checkout["end"], target_literal)
                )
            else:
                step = structure["setup"][site][0]
                replacements_by_file[filename].append(
                    (step["start"], step["end"], target_literal)
                )
        for site, target_literal in FINAL_INSTALL_STEPS.items():
            filename, _ = site
            step = structure["install"][site][0]
            replacement = target_literal + FINAL_SMOKE_STEPS.get(site, "")
            replacements_by_file[filename].append(
                (step["start"], step["end"], replacement)
            )
    else:
        for site, step_items in structure["setup"].items():
            filename, _ = site
            step = step_items[0]
            target_literal = CURRENT_SETUP_STEPS.get(site, "")
            replacements_by_file[filename].append(
                (step["start"], step["end"], target_literal)
            )
        for site, target_literal in CURRENT_INSTALL_STEPS.items():
            filename, _ = site
            step = structure["install"][site][0]
            replacements_by_file[filename].append(
                (step["start"], step["end"], target_literal)
            )
        for site in FINAL_SMOKE_STEPS:
            filename, _ = site
            step = structure["smoke"][site][0]
            replacements_by_file[filename].append(
                (step["start"], step["end"], "")
            )

    sweep_site = ("dependabot-automerge.yml", "sweep")
    sweep = last_checkout_step(structure, sweep_site)
    sweep_target = (
        FINAL_SWEEP_CHECKOUT_STEP
        if state == "BASELINE"
        else CURRENT_SWEEP_CHECKOUT_STEP
    )
    replacements_by_file[sweep_site[0]].append(
        (sweep["start"], sweep["end"], sweep_target)
    )

    source_body_index = 0 if state == "BASELINE" else 1
    target_body_index = 1 - source_body_index
    for (filename, job_name, step_name), bodies in (
        APPROVED_PYTHON_RUN_BODIES.items()
    ):
        step = only_step_with_name(
            structure,
            filename,
            job_name,
            step_name,
        )
        if step is None or step["raw"] != bodies[source_body_index]:
            raise ValueError(f"cannot transition Python body: {step_name}")
        replacements_by_file[filename].append(
            (step["start"], step["end"], bodies[target_body_index])
        )

    transitioned = {
        filename: apply_raw_replacements(
            text,
            replacements_by_file[filename],
        )
        for filename, text in payload.items()
    }
    transitioned_structure = protected_workflow_structure(transitioned)
    if not state_matches(transitioned, transitioned_structure, target):
        raise ValueError(f"fixed transition did not produce {target}")
    return transitioned


def replace_in_protected_job(
    payload: dict[str, str],
    site: tuple[str, str],
    old: str,
    new: str,
) -> dict[str, str]:
    filename, job_name = site
    text = payload[filename]
    jobs = raw_job_step_spans(text)
    if job_name not in jobs:
        raise AssertionError(f"missing mutation job: {site!r}")
    start = jobs[job_name]["start"]
    end = jobs[job_name]["end"]
    job_text = text[start:end]
    if job_text.count(old) != 1:
        raise AssertionError(
            f"expected one mutation literal in {site!r}, found {job_text.count(old)}"
        )
    changed = dict(payload)
    changed[filename] = (
        text[:start] + job_text.replace(old, new, 1) + text[end:]
    )
    return changed


def workflow_policy_payload(
    root: pathlib.Path,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Read every workflow by basename, with explicit in-memory overrides."""
    workflow_root = pathlib.Path(root) / ".github" / "workflows"
    paths = sorted(
        [*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml")],
        key=lambda path: path.name,
    )
    if len({path.name for path in paths}) != len(paths):
        raise ValueError("workflow basenames must be unique")
    replacements = {} if overrides is None else dict(overrides)
    known = {path.name for path in paths}
    unknown = set(replacements) - known
    if unknown:
        raise ValueError(f"unknown workflow override: {sorted(unknown)!r}")
    if any(not isinstance(value, str) for value in replacements.values()):
        raise ValueError("workflow policy overrides must be decoded text")
    return {
        path.name: replacements.get(
            path.name,
            path.read_bytes().decode("utf-8"),
        )
        for path in paths
    }


def python_interpreter_tokens(text: str) -> list[str]:
    """Return the complete raw direct-interpreter tokens in one shell body."""
    return [match.group(0) for match in PYTHON_INTERPRETER_TOKEN.finditer(text)]


def step_python_interpreter_tokens(step: str) -> list[str]:
    """Return direct-interpreter tokens from every run body in one step."""
    return [
        token
        for _, script in workflow_run_scripts(step)
        for token in python_interpreter_tokens(script)
    ]


def direct_step_uses(step: str) -> list[str]:
    """Return only direct step-level uses values, never heredoc content."""
    return re.findall(
        r"(?m)^(?:      - |        )uses:\s*(\S+)\s*$",
        step,
    )


def setup_python_actions(step: str) -> list[str]:
    """Return direct setup-python action tokens in one exact step."""
    return [
        action
        for action in direct_step_uses(step)
        if action.startswith("actions/setup-python@")
    ]


def step_uses_action_prefix(step: str, prefix: str) -> bool:
    """Return whether a direct step action starts with an exact prefix."""
    return any(action.startswith(prefix) for action in direct_step_uses(step))


def shell_command_segments(script: str) -> list[list[str]]:
    """Return direct shell command segments for bounded execution checks."""
    logical = re.sub(r"\\\r?\n[ \t]*", " ", script)
    segments: list[list[str]] = []
    for line in logical.splitlines():
        lexer = shlex.shlex(
            line,
            posix=True,
            punctuation_chars=";&|()<>",
        )
        lexer.whitespace_split = True
        lexer.commenters = "#"
        try:
            tokens = list(lexer)
        except ValueError:
            if "submission" in line:
                return [["__UNPARSEABLE_SUBMISSION_COMMAND__"]]
            continue
        segment: list[str] = []
        for token in tokens:
            if re.fullmatch(r"[;&|()]+", token):
                if segment:
                    segments.append(segment)
                    segment = []
                continue
            segment.append(token)
        if segment:
            segments.append(segment)
    return segments


def split_shell_redirections(
    command: list[str],
) -> tuple[list[str], list[str]]:
    """Remove shell redirections and return every stdin source token."""
    operators = {
        "<",
        "<<",
        "<<<",
        "<&",
        "<>",
        ">",
        ">>",
        ">&",
    }
    argv: list[str] = []
    stdin_sources: list[str] = []
    cursor = 0
    while cursor < len(command):
        token = command[cursor]
        if token not in operators:
            argv.append(token)
            cursor += 1
            continue
        if argv and argv[-1].isdigit():
            argv.pop()
        if cursor + 1 >= len(command):
            stdin_sources.append("__MISSING_REDIRECTION_SOURCE__")
            cursor += 1
            continue
        source = command[cursor + 1]
        if token.startswith("<"):
            stdin_sources.append(source)
        cursor += 2
    return argv, stdin_sources


def submission_reference(
    token: str,
    untrusted_variables: set[str],
) -> bool:
    """Return whether one shell token names the untrusted checkout."""
    candidate = token.strip().strip('"').strip("'")
    if (
        candidate == "submission"
        or candidate.endswith("/submission")
        or candidate.startswith("submission/")
        or "/submission/" in candidate
    ):
        return True
    return any(
        re.search(
            rf"\$(?:{re.escape(name)}\b|\{{{re.escape(name)}\}})(?:/|$)",
            candidate,
        )
        is not None
        for name in untrusted_variables
    )


def relative_shell_path(token: str) -> bool:
    """Return whether a shell path is resolved from the current directory."""
    candidate = token.strip().strip('"').strip("'")
    if not candidate or candidate == "-":
        return False
    return not (
        candidate.startswith("/")
        or candidate.startswith("~/")
        or candidate.startswith("$GITHUB_WORKSPACE/")
        or candidate.startswith("${GITHUB_WORKSPACE}/")
        or candidate.startswith("${{ github.workspace }}/")
    )


def explicit_relative_executable(token: str) -> bool:
    """Return whether a command explicitly executes a relative path."""
    candidate = token.strip().strip('"').strip("'")
    return candidate.startswith("./") or candidate.startswith("../")


def script_executes_submission(script: str) -> bool:
    """Detect direct execution of code from the untrusted PR checkout."""
    untrusted_variables: set[str] = set()
    untrusted_cwd = False
    assignment = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")
    wrappers = {"command", "exec", "nohup"}
    launchers = {
        "bash",
        "bun",
        "dash",
        "deno",
        "node",
        "perl",
        "php",
        "ruby",
        "sh",
        "zsh",
    }

    for raw_command in shell_command_segments(script):
        if raw_command == ["__UNPARSEABLE_SUBMISSION_COMMAND__"]:
            return True
        command, stdin_sources = split_shell_redirections(raw_command)
        cursor = 0
        while cursor < len(command):
            match = assignment.fullmatch(command[cursor])
            if match is None:
                break
            name = match.group("name")
            if submission_reference(
                match.group("value"),
                untrusted_variables,
            ):
                untrusted_variables.add(name)
            else:
                untrusted_variables.discard(name)
            cursor += 1
        if cursor >= len(command):
            continue

        if command[cursor] == "env":
            cursor += 1
            while cursor < len(command):
                if command[cursor].startswith("-"):
                    cursor += 1
                    continue
                match = assignment.fullmatch(command[cursor])
                if match is None:
                    break
                name = match.group("name")
                if submission_reference(
                    match.group("value"),
                    untrusted_variables,
                ):
                    untrusted_variables.add(name)
                cursor += 1
        while cursor < len(command) and command[cursor] in wrappers:
            cursor += 1
        if cursor >= len(command):
            continue

        executable = command[cursor]
        if submission_reference(executable, untrusted_variables):
            return True
        basename = executable.rsplit("/", 1)[-1]
        arguments = command[cursor + 1 :]
        if basename == "cd":
            target = next(
                (
                    argument
                    for argument in arguments
                    if not argument.startswith("-")
                ),
                None,
            )
            if target is None:
                untrusted_cwd = False
            elif submission_reference(target, untrusted_variables):
                untrusted_cwd = True
            elif not relative_shell_path(target):
                untrusted_cwd = False
            continue
        if untrusted_cwd and explicit_relative_executable(executable):
            return True
        if basename in {"source", "."}:
            return bool(arguments) and (
                submission_reference(
                    arguments[0],
                    untrusted_variables,
                )
                or (
                    untrusted_cwd
                    and relative_shell_path(arguments[0])
                )
            )

        is_python = re.fullmatch(
            r"python(?:3(?:\.\d+)*)?",
            basename,
        )
        if not is_python and basename not in launchers:
            continue

        code_source_kind: str | None = None
        argument_index = 0
        while argument_index < len(arguments):
            argument = arguments[argument_index]
            if argument == "--":
                argument_index += 1
                if argument_index < len(arguments):
                    code_source_kind = "trusted_path"
                    if submission_reference(
                        arguments[argument_index],
                        untrusted_variables,
                    ) or (
                        untrusted_cwd
                        and relative_shell_path(arguments[argument_index])
                    ):
                        return True
                break
            if argument == "-":
                code_source_kind = "stdin"
                break
            if is_python and argument in {"-c", "-m"}:
                payload_index = argument_index + 1
                code_source_kind = "inline"
                if payload_index < len(arguments) and submission_reference(
                    arguments[payload_index],
                    untrusted_variables,
                ):
                    return True
                break
            if (
                basename in {"bash", "dash", "sh", "zsh"}
                and argument.startswith("-")
                and "c" in argument[1:]
            ):
                payload_index = argument_index + 1
                code_source_kind = "inline"
                if payload_index < len(arguments) and submission_reference(
                    arguments[payload_index],
                    untrusted_variables,
                ):
                    return True
                break
            inline_options = {
                "bun": {"-e", "--eval"},
                "deno": {"eval"},
                "node": {"-e", "--eval", "-p", "--print"},
                "perl": {"-e"},
                "php": {"-r"},
                "ruby": {"-e"},
            }
            if argument in inline_options.get(basename, set()):
                payload_index = argument_index + 1
                code_source_kind = "inline"
                if payload_index < len(arguments) and submission_reference(
                    arguments[payload_index],
                    untrusted_variables,
                ):
                    return True
                break
            if argument.startswith("-"):
                argument_index += 1
                continue
            code_source_kind = "trusted_path"
            if submission_reference(
                argument,
                untrusted_variables,
            ) or (
                untrusted_cwd
                and relative_shell_path(argument)
            ):
                return True
            break

        stdin_is_untrusted = any(
            source == "__MISSING_REDIRECTION_SOURCE__"
            or submission_reference(source, untrusted_variables)
            or (
                untrusted_cwd
                and relative_shell_path(source)
            )
            for source in stdin_sources
        )
        if stdin_is_untrusted and code_source_kind != "trusted_path":
            return True
    return False


def require_workflow_policy(condition: bool, message: str) -> None:
    """Raise a stable fail-closed policy error instead of using assert."""
    if not condition:
        raise ValueError(message)


def enforce_pages_workflow_policy(text: str) -> None:
    """Validate the complete byte-exact, source-preserving Pages workflow."""
    try:
        require_workflow_policy(
            direct_mapping_keys(text, indent=0)
            == ["name", "on", "permissions", "concurrency", "jobs"],
            "Pages top-level keys changed",
        )
        require_workflow_policy(
            direct_mapping_value(text, "name", indent=0)
            == "Deploy frontend to GitHub Pages",
            "Pages workflow name changed",
        )

        on_block = top_level_mapping_block(text, "on")
        require_workflow_policy(
            direct_mapping_keys(on_block, indent=2)
            == ["push", "workflow_dispatch"],
            "Pages event keys changed",
        )
        push_block = mapping_block(on_block, "push", indent=2)
        require_workflow_policy(
            direct_mapping_keys(push_block, indent=4)
            == ["branches", "paths"],
            "Pages push keys changed",
        )
        require_workflow_policy(
            direct_mapping_value(push_block, "branches", indent=4) == "[main]",
            "Pages push branches changed",
        )
        require_workflow_policy(
            direct_mapping_value(push_block, "paths", indent=4)
            == '["frontend/**", "feed/schema/**", ".node-version", '
            '".github/workflows/deploy-pages.yml"]',
            "Pages push paths changed",
        )
        require_workflow_policy(
            direct_mapping_value(on_block, "workflow_dispatch", indent=2) == ""
            and mapping_block(
                on_block,
                "workflow_dispatch",
                indent=2,
            ).strip()
            == "",
            "Pages workflow_dispatch must be exactly empty",
        )
        require_workflow_policy(
            direct_mapping_value(text, "permissions", indent=0) == "{}",
            "Pages workflow permissions must be the exact empty inline mapping",
        )

        concurrency = top_level_mapping_block(text, "concurrency")
        require_workflow_policy(
            direct_mapping_keys(concurrency, indent=2)
            == ["group", "cancel-in-progress"],
            "Pages concurrency keys changed",
        )
        require_workflow_policy(
            direct_mapping_value(concurrency, "group", indent=2) == "pages"
            and direct_mapping_value(
                concurrency,
                "cancel-in-progress",
                indent=2,
            )
            == "true",
            "Pages concurrency policy changed",
        )

        jobs = top_level_mapping_block(text, "jobs")
        require_workflow_policy(
            direct_mapping_keys(jobs, indent=2) == ["build", "deploy"],
            "Pages job inventory changed",
        )
        build = mapping_block(jobs, "build", indent=2)
        deploy = mapping_block(jobs, "deploy", indent=2)
        require_workflow_policy(
            direct_mapping_keys(build, indent=4)
            == ["runs-on", "permissions", "defaults", "steps"],
            "Pages build keys changed",
        )
        require_workflow_policy(
            direct_mapping_keys(deploy, indent=4)
            == [
                "needs",
                "runs-on",
                "permissions",
                "environment",
                "steps",
            ],
            "Pages deploy keys changed",
        )
        require_workflow_policy(
            direct_mapping_value(build, "runs-on", indent=4)
            == "ubuntu-latest",
            "Pages build runner changed",
        )
        require_workflow_policy(
            direct_mapping_value(deploy, "needs", indent=4) == "build"
            and direct_mapping_value(deploy, "runs-on", indent=4)
            == "ubuntu-latest",
            "Pages deploy dependency or runner changed",
        )

        build_permissions = mapping_block(build, "permissions", indent=4)
        deploy_permissions = mapping_block(deploy, "permissions", indent=4)
        require_workflow_policy(
            direct_mapping_keys(build_permissions, indent=6) == ["contents"]
            and direct_mapping_value(
                build_permissions,
                "contents",
                indent=6,
            )
            == "read",
            "Pages build permissions changed",
        )
        require_workflow_policy(
            direct_mapping_keys(deploy_permissions, indent=6)
            == ["pages", "id-token"]
            and direct_mapping_value(
                deploy_permissions,
                "pages",
                indent=6,
            )
            == "write"
            and direct_mapping_value(
                deploy_permissions,
                "id-token",
                indent=6,
            )
            == "write",
            "Pages deploy permissions changed",
        )

        defaults = mapping_block(build, "defaults", indent=4)
        require_workflow_policy(
            direct_mapping_keys(defaults, indent=6) == ["run"],
            "Pages build defaults changed",
        )
        default_run = mapping_block(defaults, "run", indent=6)
        require_workflow_policy(
            direct_mapping_keys(default_run, indent=8)
            == ["working-directory"]
            and direct_mapping_value(
                default_run,
                "working-directory",
                indent=8,
            )
            == "frontend",
            "Pages build working directory changed",
        )
        environment = mapping_block(deploy, "environment", indent=4)
        require_workflow_policy(
            direct_mapping_keys(environment, indent=6) == ["name", "url"]
            and direct_mapping_value(environment, "name", indent=6)
            == "github-pages"
            and direct_mapping_value(environment, "url", indent=6)
            == "${{ steps.deployment.outputs.page_url }}",
            "Pages deploy environment changed",
        )

        build_steps = normalized_step_blocks(build)
        deploy_steps = normalized_step_blocks(deploy)
        expected_jobs = top_level_mapping_block(
            EXPECTED_PAGES_WORKFLOW,
            "jobs",
        )
        expected_build_steps = normalized_step_blocks(
            mapping_block(expected_jobs, "build", indent=2)
        )
        expected_deploy_steps = normalized_step_blocks(
            mapping_block(expected_jobs, "deploy", indent=2)
        )
        require_workflow_policy(
            len(build_steps) == 8 and len(deploy_steps) == 1,
            "Pages step inventory changed",
        )
        require_workflow_policy(
            [step_direct_mapping_keys(step) for step in build_steps]
            == [
                ["uses", "with"],
                ["uses", "with"],
                ["name", "run"],
                ["name", "working-directory", "run"],
                ["run"],
                ["name", "env", "run"],
                ["name", "run"],
                ["uses", "with"],
            ],
            "Pages build step direct keys changed",
        )
        require_workflow_policy(
            [step_direct_mapping_keys(step) for step in deploy_steps]
            == [["id", "uses"]],
            "Pages deploy step direct keys changed",
        )
        require_workflow_policy(
            build_steps == expected_build_steps
            and deploy_steps == expected_deploy_steps,
            "Pages exact step blocks changed",
        )

        checkout, setup_node = build_steps[:2]
        upload = build_steps[-1]
        deployment = deploy_steps[0]
        require_workflow_policy(
            step_direct_mapping_value(checkout, "uses")
            == "actions/checkout@v7",
            "Pages checkout action changed",
        )
        checkout_with = mapping_block(checkout, "with", indent=8)
        require_workflow_policy(
            direct_mapping_keys(checkout_with, indent=10)
            == ["persist-credentials"]
            and direct_mapping_value(
                checkout_with,
                "persist-credentials",
                indent=10,
            )
            == "false",
            "Pages checkout inputs changed",
        )
        require_workflow_policy(
            step_direct_mapping_value(setup_node, "uses")
            == "actions/setup-node@v7",
            "Pages setup-node action changed",
        )
        setup_with = mapping_block(setup_node, "with", indent=8)
        require_workflow_policy(
            direct_mapping_keys(setup_with, indent=10)
            == [
                "node-version-file",
                "cache",
                "cache-dependency-path",
            ]
            and direct_mapping_value(
                setup_with,
                "node-version-file",
                indent=10,
            )
            == ".node-version"
            and direct_mapping_value(setup_with, "cache", indent=10)
            == "npm"
            and direct_mapping_value(
                setup_with,
                "cache-dependency-path",
                indent=10,
            )
            == "frontend/package-lock.json",
            "Pages setup-node inputs changed",
        )
        upload_with = mapping_block(upload, "with", indent=8)
        require_workflow_policy(
            step_direct_mapping_value(upload, "uses")
            == "actions/upload-pages-artifact@v5"
            and direct_mapping_keys(upload_with, indent=10) == ["path"]
            and direct_mapping_value(upload_with, "path", indent=10)
            == "frontend/out",
            "Pages upload step changed",
        )
        require_workflow_policy(
            step_direct_mapping_value(deployment, "id") == "deployment"
            and step_direct_mapping_value(deployment, "uses")
            == "actions/deploy-pages@v5",
            "Pages deployment step changed",
        )

        build_step = build_steps[5]
        build_env = mapping_block(build_step, "env", indent=8)
        require_workflow_policy(
            direct_mapping_keys(build_env, indent=10)
            == [
                "STATIC_FEED_SOURCE",
                "NEXT_PUBLIC_BASE_PATH",
                "NEXT_PUBLIC_API_BASE",
                "NEXT_PUBLIC_EDGE_BASE",
                "NEXT_PUBLIC_FEED_BASE",
            ],
            "Pages build environment keys changed",
        )
        expected_env = {
            "STATIC_FEED_SOURCE": "${{ runner.temp }}/feed-snapshot",
            "NEXT_PUBLIC_BASE_PATH": "/${{ github.event.repository.name }}",
            "NEXT_PUBLIC_API_BASE": "${{ vars.API_BASE }}",
            "NEXT_PUBLIC_EDGE_BASE": "${{ vars.EDGE_BASE }}",
            "NEXT_PUBLIC_FEED_BASE": (
                "https://raw.githubusercontent.com/"
                "${{ github.repository }}/${{ github.ref_name }}/feed"
            ),
        }
        require_workflow_policy(
            all(
                direct_mapping_value(build_env, key, indent=10) == value
                for key, value in expected_env.items()
            ),
            "Pages build environment values changed",
        )

        snapshot_script = step_run_scripts(build_steps[3])
        build_script = step_run_scripts(build_step)
        output_script = step_run_scripts(build_steps[6])
        require_workflow_policy(
            len(snapshot_script) == len(build_script) == len(output_script) == 1,
            "Pages required run blocks changed",
        )
        snapshot_script_text = snapshot_script[0]
        build_script_text = build_script[0]
        output_script_text = output_script[0]

        source_match = re.search(
            r"(?ms)^sources=\(\n(?P<body>.*?)^\)$",
            snapshot_script_text,
        )
        require_workflow_policy(
            source_match is not None,
            "Pages snapshot source array changed",
        )
        source_entries = [
            line.strip().removeprefix("feed/")
            for line in source_match.group("body").splitlines()
            if line.strip()
        ]
        require_workflow_policy(
            source_entries == PAGES_SNAPSHOT_ENTRIES,
            "Pages snapshot entries changed",
        )
        require_workflow_policy(
            snapshot_script_text.count(
                'snapshot="$RUNNER_TEMP/feed-snapshot"'
            )
            == 1
            and 'cp -R -- "${sources[@]}" "$snapshot/"'
            in snapshot_script_text
            and 'test -e "$source"' in snapshot_script_text,
            "Pages snapshot destination or fail-closed copy changed",
        )

        entry_match = re.search(
            r"(?ms)^entries=\(\n(?P<body>.*?)^\)$",
            output_script_text,
        )
        require_workflow_policy(
            entry_match is not None,
            "Pages output entry array changed",
        )
        output_entries = [
            line.strip()
            for line in entry_match.group("body").splitlines()
            if line.strip()
        ]
        require_workflow_policy(
            output_entries == PAGES_SNAPSHOT_ENTRIES,
            "Pages output snapshot entries changed",
        )
        require_workflow_policy(
            [
                match.group("path")
                for match in re.finditer(
                    r"(?m)^test -f out/feed/(?P<path>\S+)$",
                    output_script_text,
                )
            ]
            == PAGES_CRITICAL_OUTPUTS,
            "Pages critical output checks changed",
        )

        scripts = [
            script
            for step in [*build_steps, *deploy_steps]
            for script in step_run_scripts(step)
        ]
        rm_targets = [
            match.group("target")
            for script in scripts
            for match in re.finditer(
                r"(?m)^rm -rf (?P<target>.+)$",
                script,
            )
        ]
        require_workflow_policy(
            rm_targets == ['"$snapshot"'],
            "Pages may delete only the runner-temporary snapshot",
        )
        require_workflow_policy(
            "frontend/public/feed" not in text
            and "frontend/app/api" not in text,
            "Pages workflow rewrites application source paths",
        )
        commands = [
            line.strip()
            for script in scripts
            for line in script.splitlines()
            if line.strip()
        ]
        require_workflow_policy(
            commands.count("npm ci") == 1
            and commands.count("npm run build:static") == 1
            and commands.count("npm run smoke:static") == 1,
            "Pages npm install/build/smoke command counts changed",
        )
        require_workflow_policy(
            not any(
                command == "npm run build"
                or command.startswith("npm run build:server")
                or command.startswith("npm run smoke:server")
                for command in commands
            ),
            "Pages workflow invokes a default or server profile",
        )
        require_workflow_policy(
            text.count("actions/checkout@v7") == 1
            and text.count("actions/setup-node@v7") == 1
            and text.count("actions/upload-pages-artifact@v5") == 1
            and text.count("actions/deploy-pages@v5") == 1
            and "actions/deploy-pages@v5" not in build
            and "actions/upload-pages-artifact@v5" not in deploy,
            "Pages action inventory or job ownership changed",
        )
        require_workflow_policy(
            text.encode("utf-8") == EXPECTED_PAGES_WORKFLOW.encode("utf-8"),
            "Pages workflow bytes changed",
        )
    except AssertionError as exc:
        raise ValueError(f"invalid Pages workflow structure: {exc}") from exc


def enforce_render_and_backend_quick_start(
    render_text: str,
    readme_text: str,
) -> None:
    """Validate the exact Render Blueprint and backend quick-start commands."""
    try:
        require_workflow_policy(
            direct_mapping_keys(render_text, indent=0) == ["services"],
            "Render top-level keys changed",
        )
        service_headers = [
            index
            for index, line in enumerate(render_text.splitlines())
            if re.match(r"^  - [A-Za-z0-9_-]+:", line)
        ]
        require_workflow_policy(
            len(service_headers) == 1,
            "Render must define exactly one service",
        )
        service_lines = render_text.splitlines()[service_headers[0] :]
        service_first = re.match(
            r"^  - (?P<entry>.+)$",
            service_lines[0],
        )
        require_workflow_policy(
            service_first is not None,
            "Render service header changed",
        )
        normalized_service = "\n".join(
            [f"    {service_first.group('entry')}", *service_lines[1:]]
        )
        require_workflow_policy(
            direct_mapping_keys(normalized_service, indent=4)
            == [
                "type",
                "name",
                "runtime",
                "rootDir",
                "plan",
                "buildCommand",
                "startCommand",
                "healthCheckPath",
                "autoDeploy",
                "envVars",
            ],
            "Render service keys changed",
        )
        expected_service_values = {
            "type": "web",
            "name": "stock-dashboard-api",
            "runtime": "python",
            "rootDir": "backend",
            "plan": "free",
            "buildCommand": (
                "python -m pip install --require-hashes -r requirements.txt"
            ),
            "startCommand": (
                "python -m uvicorn app.main:app "
                "--host 0.0.0.0 --port $PORT"
            ),
            "healthCheckPath": "/api/v1/health",
            "autoDeploy": "true",
        }
        require_workflow_policy(
            all(
                direct_mapping_value(
                    normalized_service,
                    key,
                    indent=4,
                )
                == value
                for key, value in expected_service_values.items()
            ),
            "Render service values changed",
        )

        env_vars = mapping_block(
            normalized_service,
            "envVars",
            indent=4,
        )
        env_lines = [line for line in env_vars.splitlines() if line.strip()]
        require_workflow_policy(
            len(env_lines) == 2,
            "Render environment variable inventory changed",
        )
        env_first = re.match(r"^      - (?P<entry>.+)$", env_lines[0])
        require_workflow_policy(
            env_first is not None,
            "Render environment variable header changed",
        )
        normalized_env = "\n".join(
            [f"        {env_first.group('entry')}", env_lines[1]]
        )
        require_workflow_policy(
            direct_mapping_keys(normalized_env, indent=8)
            == ["key", "value"]
            and direct_mapping_value(normalized_env, "key", indent=8)
            == "PYTHON_VERSION"
            and direct_mapping_value(normalized_env, "value", indent=8)
            == '"3.11.15"',
            "Render PYTHON_VERSION pin changed",
        )
        require_workflow_policy(
            len(
                re.findall(
                    r'(?m)^      - key: PYTHON_VERSION\n'
                    r'        value: "3\.11\.15"$',
                    render_text,
                )
            )
            == 1
            and len(
                re.findall(
                    r"(?m)^\s+- key: PYTHON_VERSION$",
                    render_text,
                )
            )
            == 1,
            "Render must have one adjacent PYTHON_VERSION 3.11.15 entry",
        )
        require_workflow_policy(
            render_text.encode("utf-8")
            == EXPECTED_RENDER_BLUEPRINT.encode("utf-8"),
            "Render Blueprint bytes changed",
        )

        quick_start_headings = [
            match.start()
            for match in re.finditer(r"(?m)^## 运行$", readme_text)
        ]
        require_workflow_policy(
            len(quick_start_headings) == 1,
            "backend README quick-start heading inventory changed",
        )
        section_start = quick_start_headings[0]
        next_heading = readme_text.find("\n## ", section_start + 1)
        section_end = len(readme_text) if next_heading < 0 else next_heading
        quick_start = readme_text[section_start:section_end]
        require_workflow_policy(
            quick_start == EXPECTED_BACKEND_QUICK_START,
            "backend README quick-start block changed",
        )
        fenced = re.fullmatch(
            r"## 运行\n\n```bash\n(?P<body>.*?)\n```\n",
            quick_start,
            flags=re.DOTALL,
        )
        require_workflow_policy(
            fenced is not None,
            "backend README quick-start fence changed",
        )
        commands = fenced.group("body").splitlines()
        require_workflow_policy(
            commands
            == [
                "cd backend",
                "python3.11 -m venv .venv",
                "source .venv/bin/activate",
                "python -m pip install --require-hashes -r requirements.txt",
                "python -m uvicorn app.main:app --reload --port 8000",
            ],
            "backend README quick-start command order changed",
        )
    except AssertionError as exc:
        raise ValueError(
            f"invalid Render/backend quick-start structure: {exc}"
        ) from exc


def enforce_python_workflow_policy(
    root: pathlib.Path,
    overrides: dict[str, str] | None = None,
) -> None:
    """Validate the complete final Python workflow toolchain policy."""
    payload = workflow_policy_payload(root, overrides)
    jobs_by_file: dict[str, dict[str, dict[str, object]]] = {}
    interpreter_inventory: dict[tuple[str, str], list[str]] = {}
    setup_inventory: dict[
        tuple[str, str],
        list[tuple[dict[str, object], str]],
    ] = {}
    install_inventory: dict[
        tuple[str, str],
        list[dict[str, object]],
    ] = {}
    smoke_inventory: dict[
        tuple[str, str],
        list[dict[str, object]],
    ] = {}
    raw_setup_count = 0
    parsed_setup_count = 0

    for filename, text in payload.items():
        jobs = raw_job_step_spans(text)
        jobs_by_file[filename] = jobs
        raw_setup_count += len(re.findall(r"actions/setup-python@", text))
        for job_name, job in jobs.items():
            site = (filename, job_name)
            tokens: list[str] = []
            for step in job["steps"]:
                raw = step["raw"]
                step_tokens = step_python_interpreter_tokens(raw)
                tokens.extend(step_tokens)
                actions = setup_python_actions(raw)
                parsed_setup_count += len(actions)
                for action in actions:
                    setup_inventory.setdefault(site, []).append(
                        (step, action)
                    )
                if step_has_install_command(raw):
                    install_inventory.setdefault(site, []).append(step)
                if step_is_smoke_candidate(raw):
                    smoke_inventory.setdefault(site, []).append(step)
            if tokens:
                interpreter_inventory[site] = tokens

    require_workflow_policy(
        set(interpreter_inventory) == EXPECTED_PYTHON_POLICY_JOBS,
        "direct Python interpreter job inventory changed",
    )
    for site in PRODUCTION_PYTHON_JOBS:
        tokens = interpreter_inventory.get(site, [])
        require_workflow_policy(
            bool(tokens) and all(token == "python" for token in tokens),
            f"production interpreter token is not canonical: {site!r}",
        )

    require_workflow_policy(
        raw_setup_count == parsed_setup_count == 17,
        "setup-python raw/parsed occurrence count changed",
    )
    require_workflow_policy(
        set(setup_inventory) == EXPECTED_PYTHON_POLICY_JOBS,
        "setup-python job inventory changed",
    )
    for site, entries in setup_inventory.items():
        require_workflow_policy(
            len(entries) == 1,
            f"setup-python action count changed: {site!r}",
        )
        _, action = entries[0]
        require_workflow_policy(
            action == "actions/setup-python@v6",
            f"setup-python action is not v6: {site!r}",
        )

    expected_install_sites = DEPENDENCY_JOBS | {("tests.yml", "python")}
    require_workflow_policy(
        set(install_inventory) == expected_install_sites,
        "pip install job inventory changed",
    )
    for site, (version_file, lock_path) in PRODUCTION_PYTHON_JOBS.items():
        filename, job_name = site
        job = jobs_by_file.get(filename, {}).get(job_name)
        require_workflow_policy(
            job is not None,
            f"missing production Python job: {site!r}",
        )
        setup_entries = setup_inventory.get(site, [])
        require_workflow_policy(
            len(setup_entries) == 1,
            f"missing production setup-python step: {site!r}",
        )
        setup_step = setup_entries[0][0]
        require_workflow_policy(
            setup_step["raw"] == FINAL_SETUP_STEPS[site],
            f"setup-python step does not match final literal: {site!r}",
        )

        checkouts = [
            step
            for step in job["steps"]
            if step_uses_action_prefix(step["raw"], "actions/checkout@")
        ]
        require_workflow_policy(
            bool(checkouts),
            f"production job has no checkout: {site!r}",
        )
        require_workflow_policy(
            setup_step["index"] == checkouts[-1]["index"] + 1,
            f"setup-python is not immediately after final checkout: {site!r}",
        )
        python_step_indices = [
            step["index"]
            for step in job["steps"]
            if step_python_interpreter_tokens(step["raw"])
        ]
        require_workflow_policy(
            bool(python_step_indices)
            and setup_step["index"] < min(python_step_indices),
            f"setup-python is not before the first Python command: {site!r}",
        )

        installs = install_inventory.get(site, [])
        if lock_path is None:
            require_workflow_policy(
                not installs,
                f"standard-library job installs dependencies: {site!r}",
            )
        else:
            require_workflow_policy(
                len(installs) == 1
                and installs[0]["raw"] == FINAL_INSTALL_STEPS[site],
                f"hashed install step changed: {site!r}",
            )
            require_workflow_policy(
                f"python-version-file: {version_file}"
                in setup_step["raw"],
                f"wrong Python version file: {site!r}",
            )
            require_workflow_policy(
                f"cache-dependency-path: {lock_path}"
                in setup_step["raw"],
                f"wrong Python cache lock: {site!r}",
            )

    tests_jobs = jobs_by_file["tests.yml"]
    for job_name in ("frontend", "python"):
        checkout_steps = [
            step
            for step in tests_jobs[job_name]["steps"]
            if step_uses_action_prefix(step["raw"], "actions/checkout@")
        ]
        require_workflow_policy(
            len(checkout_steps) == 1
            and checkout_steps[0]["raw"].rstrip()
            == FRONTEND_STEP_BLOCKS[0],
            f"tests.yml/{job_name} checkout exception changed",
        )
    tests_setup = setup_inventory[("tests.yml", "python")][0][0]["raw"]
    require_workflow_policy(
        tests_setup.rstrip() == PYTHON_STEP_BLOCKS[1],
        "tests.yml/python setup exception changed",
    )
    tests_install = install_inventory[("tests.yml", "python")]
    require_workflow_policy(
        len(tests_install) == 1
        and tests_install[0]["raw"].rstrip() == PYTHON_STEP_BLOCKS[2],
        "tests.yml/python install exception changed",
    )

    expected_smoke_sites = set(FINAL_SMOKE_STEPS)
    require_workflow_policy(
        set(smoke_inventory) == expected_smoke_sites,
        "automation smoke-import inventory changed",
    )
    for site, literal in FINAL_SMOKE_STEPS.items():
        smokes = smoke_inventory.get(site, [])
        require_workflow_policy(
            len(smokes) == 1 and smokes[0]["raw"] == literal,
            f"automation smoke-import step changed: {site!r}",
        )
        install = install_inventory[site][0]
        require_workflow_policy(
            smokes[0]["index"] == install["index"] + 1,
            f"automation smoke step is not immediately after install: {site!r}",
        )

    for site in PRODUCTION_PYTHON_JOBS:
        filename, job_name = site
        job = jobs_by_file[filename][job_name]
        checkouts = [
            step
            for step in job["steps"]
            if step_uses_action_prefix(step["raw"], "actions/checkout@")
        ]
        credential_values = [
            values
            for step in checkouts
            for values in [
                re.findall(
                    r"(?m)^\s+persist-credentials:\s*(\S+)\s*$",
                    step["raw"],
                )
            ]
        ]
        expected_false_count = EXPECTED_FALSE_CHECKOUT_COUNTS.get(site)
        if expected_false_count is None:
            require_workflow_policy(
                all(not values for values in credential_values),
                f"credentialed checkout policy changed: {site!r}",
            )
        else:
            require_workflow_policy(
                len(checkouts) == expected_false_count
                and credential_values
                == [["false"]] * expected_false_count,
                f"non-credentialed checkout policy changed: {site!r}",
            )

    sweep_checkout = [
        step
        for step in jobs_by_file["dependabot-automerge.yml"]["sweep"]["steps"]
        if step_uses_action_prefix(step["raw"], "actions/checkout@")
    ]
    require_workflow_policy(
        len(sweep_checkout) == 1
        and sweep_checkout[0]["raw"] == FINAL_SWEEP_CHECKOUT_STEP,
        "Dependabot sweep checkout changed",
    )
    on_pr_checkout = [
        step
        for step in jobs_by_file["dependabot-automerge.yml"]["on-pr"]["steps"]
        if step_uses_action_prefix(step["raw"], "actions/checkout@")
    ]
    require_workflow_policy(
        len(on_pr_checkout) == 1
        and on_pr_checkout[0]["raw"] == ON_PR_CHECKOUT_STEP,
        "Dependabot trusted-base checkout changed",
    )

    pr_validate = jobs_by_file["feed-validate.yml"]["pr-validate"]
    pr_checkouts = [
        step["raw"]
        for step in pr_validate["steps"]
        if step_uses_action_prefix(step["raw"], "actions/checkout@")
    ]
    require_workflow_policy(
        pr_checkouts
        == [TRUSTED_BASE_CHECKOUT_STEP, UNTRUSTED_DATA_CHECKOUT_STEP],
        "feed PR checkout trust boundary changed",
    )
    pr_scripts = [
        script
        for step in pr_validate["steps"]
        for _, script in workflow_run_scripts(step["raw"])
    ]
    require_workflow_policy(
        any(
            'python "$GITHUB_WORKSPACE/trusted/scripts/validate_feed.py"'
            in script
            for script in pr_scripts
        ),
        "trusted PR validator execution path changed",
    )
    require_workflow_policy(
        not any(script_executes_submission(script) for script in pr_scripts),
        "PR workflow executes content from submission",
    )

    dependabot_concurrency = top_level_mapping_block(
        payload["dependabot-automerge.yml"],
        "concurrency",
    )
    require_workflow_policy(
        dependabot_concurrency.splitlines() == DEPENDABOT_CONCURRENCY_LINES,
        "Dependabot concurrency policy changed",
    )


class WorkflowSecurityTests(unittest.TestCase):
    def assert_required_job_is_fail_closed(self, job: str) -> None:
        self.assertNotRegex(
            job,
            r"(?m)^\s+(?:-\s+)?"
            r"(?:continue-on-error|\"continue-on-error\"|'continue-on-error')\s*:",
        )
        self.assertNotIn("|| true", job)

    def assert_reproduction_is_exact(
        self,
        block: str,
        rows: list[tuple[str, str, str]],
    ) -> None:
        self.assertEqual(
            reproduction_lines(block, "cp "),
            [
                f'cp {committed} "$tmp/{temporary}"'
                for committed, temporary, _ in rows
            ],
        )
        compile_flags = " ".join(LOCK_COMPILE_FLAGS)
        self.assertEqual(
            reproduction_lines(block, "python -m piptools compile "),
            [
                "python -m piptools compile "
                f'{compile_flags} --output-file="$tmp/{temporary}" {direct_input}'
                for _, temporary, direct_input in rows
            ],
        )
        self.assertEqual(
            reproduction_lines(block, "cmp "),
            [
                f'cmp "$tmp/{temporary}" {committed}'
                for committed, temporary, _ in rows
            ],
        )

    def test_pages_uses_the_complete_isolated_static_profile(self) -> None:
        enforce_pages_workflow_policy(EXPECTED_PAGES_WORKFLOW)

        def mutate(old: str, new: str) -> str:
            self.assertEqual(
                EXPECTED_PAGES_WORKFLOW.count(old),
                1,
                f"mutation anchor is not unique: {old!r}",
            )
            return EXPECTED_PAGES_WORKFLOW.replace(old, new, 1)

        mutations = {
            "extra top-level key": mutate(
                "\npermissions: {}\n",
                "\nx-extra: true\n\npermissions: {}\n",
            ),
            "extra build key": mutate(
                "  build:\n    runs-on: ubuntu-latest\n",
                "  build:\n"
                "    runs-on: ubuntu-latest\n"
                "    timeout-minutes: 10\n",
            ),
            "extra deploy key": mutate(
                "  deploy:\n    needs: build\n",
                "  deploy:\n    needs: build\n    timeout-minutes: 10\n",
            ),
            "workflow dispatch inputs": mutate(
                "  workflow_dispatch:\n\npermissions: {}\n",
                "  workflow_dispatch:\n"
                "    inputs:\n"
                "      unsafe:\n"
                "        required: false\n\n"
                "permissions: {}\n",
            ),
            "checkout fetch depth": mutate(
                "          persist-credentials: false\n",
                "          persist-credentials: false\n"
                "          fetch-depth: 0\n",
            ),
            "wrong setup-node value": mutate(
                "          node-version-file: .node-version\n",
                '          node-version-file: "20"\n',
            ),
            "extra setup-node input": mutate(
                "          cache-dependency-path: frontend/package-lock.json\n",
                "          cache-dependency-path: frontend/package-lock.json\n"
                "          check-latest: true\n",
            ),
            "extra upload input": mutate(
                "          path: frontend/out\n",
                "          path: frontend/out\n"
                "          retention-days: 1\n",
            ),
            "deploy with input": mutate(
                "      - id: deployment\n"
                "        uses: actions/deploy-pages@v5\n",
                "      - id: deployment\n"
                "        uses: actions/deploy-pages@v5\n"
                "        with:\n"
                "          preview: true\n",
            ),
            "step if": mutate(
                "      - name: Verify exact Node and npm\n"
                "        run: |\n",
                "      - name: Verify exact Node and npm\n"
                "        if: always()\n"
                "        run: |\n",
            ),
            "step continue on error": mutate(
                "      - run: npm ci\n",
                "      - run: npm ci\n"
                "        continue-on-error: true\n",
            ),
            "extra build environment": mutate(
                "          NEXT_PUBLIC_API_BASE: ${{ vars.API_BASE }}\n",
                "          NEXT_PUBLIC_API_BASE: ${{ vars.API_BASE }}\n"
                "          UNDECLARED_CONTEXT: ${{ github.token }}\n",
            ),
            "substituted context": mutate(
                "          NEXT_PUBLIC_API_BASE: ${{ vars.API_BASE }}\n",
                "          NEXT_PUBLIC_API_BASE: ${{ secrets.API_BASE }}\n",
            ),
            "invalid context expression": mutate(
                "          NEXT_PUBLIC_EDGE_BASE: ${{ vars.EDGE_BASE }}\n",
                "          NEXT_PUBLIC_EDGE_BASE: $(vars.EDGE_BASE)\n",
            ),
        }
        for label, workflow in mutations.items():
            with self.subTest(mutation=label):
                with self.assertRaises(ValueError):
                    enforce_pages_workflow_policy(workflow)

        actual = (
            ROOT / ".github" / "workflows" / "deploy-pages.yml"
        ).read_text(encoding="utf-8")
        enforce_pages_workflow_policy(actual)

    def test_render_and_backend_quick_start_are_exact(self) -> None:
        enforce_render_and_backend_quick_start(
            EXPECTED_RENDER_BLUEPRINT,
            EXPECTED_BACKEND_QUICK_START,
        )

        def mutate_render(old: str, new: str) -> str:
            self.assertEqual(
                EXPECTED_RENDER_BLUEPRINT.count(old),
                1,
                f"Render mutation anchor is not unique: {old!r}",
            )
            return EXPECTED_RENDER_BLUEPRINT.replace(old, new, 1)

        render_mutations = {
            "unhashed install": mutate_render(
                "python -m pip install --require-hashes -r requirements.txt",
                "python -m pip install -r requirements.txt",
            ),
            "direct uvicorn": mutate_render(
                "startCommand: python -m uvicorn",
                "startCommand: uvicorn",
            ),
            "wrong Python version": mutate_render(
                '        value: "3.11.15"\n',
                '        value: "3.12.0"\n',
            ),
            "duplicate Python version": mutate_render(
                '        value: "3.11.15"\n',
                '        value: "3.11.15"\n'
                "      - key: PYTHON_VERSION\n"
                '        value: "3.11.15"\n',
            ),
            "non-adjacent Python version": mutate_render(
                "      - key: PYTHON_VERSION\n"
                '        value: "3.11.15"\n',
                "      - key: PYTHON_VERSION\n"
                "        sync: false\n"
                '        value: "3.11.15"\n',
            ),
            "extra service": mutate_render(
                '        value: "3.11.15"\n',
                '        value: "3.11.15"\n'
                "  - type: worker\n"
                "    name: unexpected-worker\n",
            ),
        }
        for label, render_text in render_mutations.items():
            with self.subTest(render_mutation=label):
                with self.assertRaises(ValueError):
                    enforce_render_and_backend_quick_start(
                        render_text,
                        EXPECTED_BACKEND_QUICK_START,
                    )

        def mutate_readme(old: str, new: str) -> str:
            self.assertEqual(
                EXPECTED_BACKEND_QUICK_START.count(old),
                1,
                f"README mutation anchor is not unique: {old!r}",
            )
            return EXPECTED_BACKEND_QUICK_START.replace(old, new, 1)

        readme_mutations = {
            "wrong venv interpreter": mutate_readme(
                "python3.11 -m venv .venv",
                "python3 -m venv .venv",
            ),
            "missing activation": mutate_readme(
                "source .venv/bin/activate\n",
                "",
            ),
            "unhashed install": mutate_readme(
                "python -m pip install --require-hashes -r requirements.txt",
                "python -m pip install -r requirements.txt",
            ),
            "direct uvicorn": mutate_readme(
                "python -m uvicorn",
                "uvicorn",
            ),
            "reordered activation": mutate_readme(
                "python3.11 -m venv .venv\n"
                "source .venv/bin/activate\n",
                "source .venv/bin/activate\n"
                "python3.11 -m venv .venv\n",
            ),
        }
        for label, readme_text in readme_mutations.items():
            with self.subTest(readme_mutation=label):
                with self.assertRaises(ValueError):
                    enforce_render_and_backend_quick_start(
                        EXPECTED_RENDER_BLUEPRINT,
                        readme_text,
                    )

        render_text = (ROOT / "render.yaml").read_text(encoding="utf-8")
        readme_text = (ROOT / "backend" / "README.md").read_text(
            encoding="utf-8"
        )
        enforce_render_and_backend_quick_start(render_text, readme_text)

    def protected_state_fixtures(
        self,
    ) -> tuple[dict[str, str], dict[str, str]]:
        checked_out = protected_workflow_payload(ROOT)
        structure = protected_workflow_structure(checked_out)
        current_ok = state_matches(checked_out, structure, "BASELINE")
        final_ok = state_matches(checked_out, structure, "FINAL")
        self.assertNotEqual(current_ok, final_ok)
        if current_ok:
            return (
                checked_out,
                transition_protected_workflows(checked_out, "BASELINE"),
            )
        return (
            transition_protected_workflows(checked_out, "FINAL"),
            checked_out,
        )

    def test_all_protected_workflow_behavior_is_unchanged(self) -> None:
        checked_out = protected_workflow_payload(ROOT)
        structure = protected_workflow_structure(checked_out)
        current_ok = state_matches(checked_out, structure, "BASELINE")
        final_ok = state_matches(checked_out, structure, "FINAL")
        self.assertNotEqual(current_ok, final_ok)
        state = "BASELINE" if current_ok else "FINAL"
        opposite = transition_protected_workflows(checked_out, state)

        checked_normalized = normalized_protected_workflows(ROOT)
        opposite_normalized = normalized_protected_workflows(
            ROOT,
            overrides=opposite,
        )
        self.assertEqual(checked_normalized, opposite_normalized)

        checked_source = b"".join(
            checked_normalized[filename].encode()
            for filename in sorted(checked_normalized)
        )
        opposite_source = b"".join(
            opposite_normalized[filename].encode()
            for filename in sorted(opposite_normalized)
        )
        self.assertEqual(checked_source, opposite_source)
        self.assertEqual(len(checked_source), 41_968)
        self.assertEqual(len(opposite_source), 41_968)

        checked_encoded = encoded_workflow_payload(checked_normalized)
        opposite_encoded = encoded_workflow_payload(opposite_normalized)
        self.assertEqual(checked_encoded, opposite_encoded)
        self.assertEqual(len(checked_encoded), 43_994)
        self.assertEqual(len(opposite_encoded), 43_994)
        self.assertEqual(
            hashlib.sha256(checked_encoded).hexdigest(),
            PROTECTED_WORKFLOW_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(opposite_encoded).hexdigest(),
            PROTECTED_WORKFLOW_SHA256,
        )

    def test_protected_workflow_normalizer_rejects_unapproved_variants(
        self,
    ) -> None:
        baseline, final = self.protected_state_fixtures()
        alpha = ("alpha-routine.yml", "run")
        monthly = ("monthly-studies.yml", "studies")
        chan = ("chan-stats.yml", "stats")
        digest = ("daily-digest.yml", "digest")
        hyperliquid = ("hyperliquid-monitor.yml", "monitor")
        watchdog = ("feed-watchdog.yml", "audit")
        cleanup = (
            "dependabot-automerge.yml",
            "on-pr",
            "清理旧资格并撤销 auto-merge",
        )
        funds = ("funds-13f.yml", "track", "提交 + 新披露开 Issue")

        cases: list[tuple[str, dict[str, str]]] = []
        cases.append(
            (
                "delete baseline setup",
                replace_in_protected_job(
                    baseline,
                    alpha,
                    CURRENT_SETUP_STEPS[alpha],
                    "",
                ),
            )
        )
        cases.append(
            (
                "delete final migrated setup",
                replace_in_protected_job(
                    final,
                    alpha,
                    FINAL_SETUP_STEPS[alpha],
                    "",
                ),
            )
        )
        cases.append(
            (
                "delete final-only watchdog setup",
                replace_in_protected_job(
                    final,
                    watchdog,
                    FINAL_SETUP_STEPS[watchdog],
                    "",
                ),
            )
        )
        cases.append(
            (
                "near-miss baseline setup input",
                replace_in_protected_job(
                    baseline,
                    alpha,
                    CURRENT_SETUP_STEPS[alpha],
                    CURRENT_SETUP_STEPS[alpha].replace(
                        'python-version: "3.12"',
                        'python-version: "3.12.0"',
                    ),
                ),
            )
        )
        cases.append(
            (
                "duplicate exact setup",
                replace_in_protected_job(
                    baseline,
                    alpha,
                    CURRENT_SETUP_STEPS[alpha],
                    CURRENT_SETUP_STEPS[alpha] * 2,
                ),
            )
        )
        baseline_checkout = "      - uses: actions/checkout@v7\n"
        cases.append(
            (
                "move exact setup before checkout",
                replace_in_protected_job(
                    baseline,
                    alpha,
                    baseline_checkout + CURRENT_SETUP_STEPS[alpha],
                    CURRENT_SETUP_STEPS[alpha] + baseline_checkout,
                ),
            )
        )
        cases.append(
            (
                "near-miss install name",
                replace_in_protected_job(
                    baseline,
                    alpha,
                    CURRENT_INSTALL_STEPS[alpha],
                    CURRENT_INSTALL_STEPS[alpha].replace(
                        "name: 安装依赖",
                        "name: 安装依赖变更",
                    ),
                ),
            )
        )
        cases.append(
            (
                "near-miss install command",
                replace_in_protected_job(
                    baseline,
                    chan,
                    CURRENT_INSTALL_STEPS[chan],
                    CURRENT_INSTALL_STEPS[chan].replace(
                        "backend/requirements.txt",
                        "scripts/requirements.txt",
                    ),
                ),
            )
        )
        cases.append(
            (
                "delete install",
                replace_in_protected_job(
                    baseline,
                    monthly,
                    CURRENT_INSTALL_STEPS[monthly],
                    "",
                ),
            )
        )
        cases.append(
            (
                "duplicate install",
                replace_in_protected_job(
                    baseline,
                    hyperliquid,
                    CURRENT_INSTALL_STEPS[hyperliquid],
                    CURRENT_INSTALL_STEPS[hyperliquid] * 2,
                ),
            )
        )

        shadow = dict(baseline)
        shadow["daily-digest.yml"] += (
            "\n  shadow-setup:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/setup-python@v6\n"
            "        with:\n"
            "          python-version-file: .python-version\n"
        )
        cases.append(("shadow setup job without Python command", shadow))
        cases.append(
            (
                "install added to standard-library job",
                replace_in_protected_job(
                    baseline,
                    digest,
                    CURRENT_SETUP_STEPS[digest],
                    CURRENT_SETUP_STEPS[digest]
                    + "      - run: pip install -r scripts/requirements.txt\n",
                ),
            )
        )
        cases.append(
            (
                "path-qualified Python install added to standard-library job",
                replace_in_protected_job(
                    baseline,
                    digest,
                    CURRENT_SETUP_STEPS[digest],
                    CURRENT_SETUP_STEPS[digest]
                    + "      - run: /usr/bin/python -m pip install -r scripts/requirements.txt\n",
                ),
            )
        )
        cases.append(
            (
                "quoted Python install added to standard-library job",
                replace_in_protected_job(
                    baseline,
                    digest,
                    CURRENT_SETUP_STEPS[digest],
                    CURRENT_SETUP_STEPS[digest]
                    + '      - run: \"/tmp/my env/bin/python\" -m pip install -r scripts/requirements.txt\n',
                ),
            )
        )
        cases.append(
            (
                "continued Python install added to standard-library job",
                replace_in_protected_job(
                    baseline,
                    digest,
                    CURRENT_SETUP_STEPS[digest],
                    CURRENT_SETUP_STEPS[digest]
                    + "      - run: |\n"
                    + "          python -m pip \\\n"
                    + "            install -r scripts/requirements.txt\n",
                ),
            )
        )
        cases.append(
            (
                "compound path-qualified install added to standard-library job",
                replace_in_protected_job(
                    baseline,
                    digest,
                    CURRENT_SETUP_STEPS[digest],
                    CURRENT_SETUP_STEPS[digest]
                    + "      - run: echo ready && /usr/bin/python -m pip install -r scripts/requirements.txt\n",
                ),
            )
        )

        cleanup_current, cleanup_final, _ = APPROVED_PYTHON_RUN_BODIES[cleanup]
        cases.append(
            (
                "partial multi-token body migration",
                replace_in_protected_job(
                    baseline,
                    cleanup[:2],
                    cleanup_current,
                    cleanup_current.replace("python3", "python", 1),
                ),
            )
        )
        funds_current, funds_final, _ = APPROVED_PYTHON_RUN_BODIES[funds]
        cases.append(
            (
                "one complete body migrated",
                replace_in_protected_job(
                    baseline,
                    funds[:2],
                    funds_current,
                    funds_final,
                ),
            )
        )
        cases.append(
            (
                "one complete body reversed",
                replace_in_protected_job(
                    final,
                    funds[:2],
                    funds_final,
                    funds_current,
                ),
            )
        )

        bodies_only = baseline
        for key, (current_body, final_body, _) in (
            APPROVED_PYTHON_RUN_BODIES.items()
        ):
            bodies_only = replace_in_protected_job(
                bodies_only,
                key[:2],
                current_body,
                final_body,
            )
        cases.append(
            (
                "all Python bodies final while every other category baseline",
                bodies_only,
            )
        )

        for name, mutated in cases:
            with self.subTest(name=name):
                changed = {
                    filename: text
                    for filename, text in mutated.items()
                    if text != protected_workflow_payload(ROOT)[filename]
                }
                with self.assertRaises(ValueError):
                    normalized_protected_workflows(ROOT, overrides=changed)

    def test_protected_workflow_mutations_are_detected(self) -> None:
        checked_out = protected_workflow_payload(ROOT)
        for filename, old, new, category in PROTECTED_WORKFLOW_MUTATIONS:
            with self.subTest(category=category):
                self.assertEqual(checked_out[filename].count(old), 1)
                mutated = checked_out[filename].replace(old, new, 1)
                normalized = normalized_protected_workflows(
                    ROOT,
                    overrides={filename: mutated},
                )
                self.assertNotEqual(
                    hashlib.sha256(
                        encoded_workflow_payload(normalized)
                    ).hexdigest(),
                    PROTECTED_WORKFLOW_SHA256,
                )

    def test_synthetic_final_python_workflow_policy_is_valid(self) -> None:
        _, final = self.protected_state_fixtures()
        enforce_python_workflow_policy(ROOT, overrides=final)

    def test_all_production_python_jobs_use_the_pinned_policy(self) -> None:
        enforce_python_workflow_policy(ROOT)

    def test_python_interpreter_policy_rejects_qualified_or_versioned_tokens(
        self,
    ) -> None:
        _, final = self.protected_state_fixtures()
        canonical = "python scripts/daily_digest.py"
        self.assertEqual(final["daily-digest.yml"].count(canonical), 1)
        for command in FORBIDDEN_INTERPRETER_MUTATIONS:
            with self.subTest(command=command):
                expected_token = command[: command.index(" scripts/daily_digest.py")]
                self.assertEqual(
                    python_interpreter_tokens(command),
                    [expected_token],
                )
                mutated = dict(final)
                mutated["daily-digest.yml"] = final[
                    "daily-digest.yml"
                ].replace(canonical, command, 1)
                with self.assertRaises(ValueError):
                    enforce_python_workflow_policy(ROOT, overrides=mutated)

    def test_python_setup_inventory_rejects_unapproved_actions(self) -> None:
        _, final = self.protected_state_fixtures()
        setup = FINAL_SETUP_STEPS[("daily-digest.yml", "digest")]

        shadow = dict(final)
        shadow["daily-digest.yml"] += """  shadow:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
"""

        duplicate = dict(final)
        duplicate["daily-digest.yml"] = final["daily-digest.yml"].replace(
            setup,
            setup + setup,
            1,
        )

        wrong_action = dict(final)
        wrong_action["daily-digest.yml"] = final[
            "daily-digest.yml"
        ].replace(
            "actions/setup-python@v6",
            "actions/setup-python@v5",
            1,
        )

        outside_step = dict(final)
        outside_step["daily-digest.yml"] = (
            "# actions/setup-python@v6 must not hide outside a parsed step\n"
            + final["daily-digest.yml"]
        )

        heredoc_action = dict(final)
        heredoc_action["daily-digest.yml"] += """  shadow:
    runs-on: ubuntu-latest
    steps:
      - run: |
          cat <<'EOF'
          uses: actions/setup-python@v6
          EOF
"""

        unknown_interpreter = dict(final)
        unknown_interpreter["daily-digest.yml"] += """  shadow:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/daily_digest.py
"""

        for name, mutated in (
            ("shadow setup job", shadow),
            ("duplicate setup", duplicate),
            ("wrong setup action", wrong_action),
            ("raw setup outside step", outside_step),
            ("setup action text in heredoc", heredoc_action),
            ("unknown interpreter job", unknown_interpreter),
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    enforce_python_workflow_policy(ROOT, overrides=mutated)

    def test_python_job_inventory_rejects_quoted_unknown_jobs(self) -> None:
        _, final = self.protected_state_fixtures()
        for quoted_job in ('"shadow"', "'shadow'"):
            with self.subTest(quoted_job=quoted_job):
                mutated = dict(final)
                mutated["daily-digest.yml"] += f"""  {quoted_job}:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/daily_digest.py
"""
                with self.assertRaises(ValueError):
                    enforce_python_workflow_policy(ROOT, overrides=mutated)

        duplicate = dict(final)
        duplicate["daily-digest.yml"] += """  "digest":
    runs-on: ubuntu-latest
    steps: []
"""
        with self.assertRaises(ValueError):
            enforce_python_workflow_policy(ROOT, overrides=duplicate)

    def test_feed_pr_policy_rejects_submission_execution(self) -> None:
        _, final = self.protected_state_fixtures()
        anchor = (
            '          PYTHONPATH="$GITHUB_WORKSPACE/trusted/scripts" \\\n'
            '            python "$GITHUB_WORKSPACE/trusted/scripts/'
            'validate_feed.py" \\\n'
        )
        self.assertEqual(final["feed-validate.yml"].count(anchor), 1)
        commands = (
            '          bash "$GITHUB_WORKSPACE/submission/evil.sh"\n',
            '          source "$GITHUB_WORKSPACE/submission/evil.sh"\n',
            '          . "$GITHUB_WORKSPACE/submission/evil.sh"\n',
            '          "$GITHUB_WORKSPACE/submission/evil.sh"\n',
            '          bash "$inbox/evil.sh"\n',
            '          "$inbox/evil.sh"\n',
            '          cd "$inbox" && ./evil.sh\n',
            '          cd "$inbox" && bash evil.sh\n',
            '          bash < "$inbox/evil.sh"\n',
            '          sh < "$inbox/evil.sh"\n',
            '          python < "$inbox/evil.py"\n',
            "          bash -c 'source /dev/stdin' "
            '< "$inbox/evil.sh"\n',
            "          python -c 'import sys; exec(sys.stdin.read())' "
            '< "$inbox/evil.py"\n',
        )
        for command in commands:
            with self.subTest(command=command.strip()):
                mutated = dict(final)
                mutated["feed-validate.yml"] = final[
                    "feed-validate.yml"
                ].replace(anchor, command + anchor, 1)
                with self.assertRaises(ValueError):
                    enforce_python_workflow_policy(ROOT, overrides=mutated)

    def test_feed_pr_policy_allows_submission_as_data(self) -> None:
        _, final = self.protected_state_fixtures()
        anchor = (
            '          PYTHONPATH="$GITHUB_WORKSPACE/trusted/scripts" \\\n'
            '            python "$GITHUB_WORKSPACE/trusted/scripts/'
            'validate_feed.py" \\\n'
        )
        data_read = (
            '          cat "$GITHUB_WORKSPACE/submission/feed/inbox/'
            'example.json" >/dev/null\n'
            '          python "$GITHUB_WORKSPACE/trusted/scripts/'
            'validate_feed.py" < "$GITHUB_WORKSPACE/submission/feed/'
            'inbox/example.json"\n'
        )
        mutated = dict(final)
        mutated["feed-validate.yml"] = final["feed-validate.yml"].replace(
            anchor,
            data_read + anchor,
            1,
        )
        enforce_python_workflow_policy(ROOT, overrides=mutated)

    def test_python_workflow_policy_rejects_normalized_category_mutations(
        self,
    ) -> None:
        _, final = self.protected_state_fixtures()
        cases: list[tuple[str, dict[str, str]]] = []

        daily_jobs = raw_job_step_spans(final["daily-digest.yml"])
        daily_steps = daily_jobs["digest"]["steps"]
        setup_index = next(
            index
            for index, step in enumerate(daily_steps)
            if setup_python_actions(step["raw"])
        )
        setup_raw = daily_steps[setup_index]["raw"]
        business_raw = daily_steps[setup_index + 1]["raw"]
        moved_setup = dict(final)
        moved_setup["daily-digest.yml"] = final[
            "daily-digest.yml"
        ].replace(
            setup_raw + business_raw,
            business_raw + setup_raw,
            1,
        )
        cases.append(("setup moved behind business step", moved_setup))

        wrong_version_file = dict(final)
        wrong_version_file["daily-digest.yml"] = final[
            "daily-digest.yml"
        ].replace(
            "python-version-file: .python-version",
            "python-version-file: other/.python-version",
            1,
        )
        cases.append(("wrong version file", wrong_version_file))

        extra_setup_condition = dict(final)
        extra_setup_condition["daily-digest.yml"] = final[
            "daily-digest.yml"
        ].replace(
            "          python-version-file: .python-version\n",
            "          python-version-file: .python-version\n"
            "        if: always()\n",
            1,
        )
        cases.append(("conditional setup", extra_setup_condition))

        wrong_cache = dict(final)
        wrong_cache["alpha-routine.yml"] = final[
            "alpha-routine.yml"
        ].replace(
            "cache-dependency-path: requirements/automation.txt",
            "cache-dependency-path: scripts/requirements.txt",
            1,
        )
        cases.append(("wrong cache lock", wrong_cache))

        wrong_install_name = dict(final)
        wrong_install_name["alpha-routine.yml"] = final[
            "alpha-routine.yml"
        ].replace("name: 安装依赖", "name: Install dependencies", 1)
        cases.append(("wrong named install", wrong_install_name))

        wrong_install_command = dict(final)
        wrong_install_command["chan-stats.yml"] = final[
            "chan-stats.yml"
        ].replace(
            "python -m pip install --require-hashes -r "
            "backend/requirements.txt",
            "python -m pip install -r backend/requirements.txt",
            1,
        )
        cases.append(("unhashed install", wrong_install_command))

        conditional_install = dict(final)
        conditional_install["chan-stats.yml"] = final[
            "chan-stats.yml"
        ].replace(
            "      - run: python -m pip install --require-hashes "
            "-r backend/requirements.txt\n",
            "      - run: python -m pip install --require-hashes "
            "-r backend/requirements.txt\n"
            "        continue-on-error: true\n",
            1,
        )
        cases.append(("fallible install", conditional_install))

        unexpected_install = dict(final)
        unexpected_install["daily-digest.yml"] = final[
            "daily-digest.yml"
        ].replace(
            FINAL_SETUP_STEPS[("daily-digest.yml", "digest")],
            FINAL_SETUP_STEPS[("daily-digest.yml", "digest")]
            + "      - run: python -m pip install --require-hashes "
            "-r scripts/requirements.txt\n",
            1,
        )
        cases.append(("install in standard-library job", unexpected_install))

        wrong_smoke = dict(final)
        wrong_smoke["alpha-routine.yml"] = final[
            "alpha-routine.yml"
        ].replace(
            "import factor_factory, feed_lib, run_routine, statarb",
            "import factor_factory, feed_lib, run_routine",
            1,
        )
        cases.append(("wrong smoke imports", wrong_smoke))

        sweep_true = dict(final)
        sweep_true["dependabot-automerge.yml"] = final[
            "dependabot-automerge.yml"
        ].replace(
            FINAL_SWEEP_CHECKOUT_STEP,
            FINAL_SWEEP_CHECKOUT_STEP.replace(
                "persist-credentials: false",
                "persist-credentials: true",
            ),
            1,
        )
        cases.append(("credentialed sweep", sweep_true))

        sweep_extra_input = dict(final)
        sweep_extra_input["dependabot-automerge.yml"] = final[
            "dependabot-automerge.yml"
        ].replace(
            FINAL_SWEEP_CHECKOUT_STEP,
            FINAL_SWEEP_CHECKOUT_STEP.replace(
                "          persist-credentials: false\n",
                "          persist-credentials: false\n"
                "          fetch-depth: 1\n",
            ),
            1,
        )
        self.assertNotEqual(
            sweep_extra_input["dependabot-automerge.yml"],
            final["dependabot-automerge.yml"],
        )
        cases.append(("extra sweep checkout input", sweep_extra_input))

        wrong_trusted_ref = dict(final)
        wrong_trusted_ref["feed-validate.yml"] = final[
            "feed-validate.yml"
        ].replace(
            "ref: ${{ github.event.pull_request.base.sha }}",
            "ref: ${{ github.event.pull_request.head.sha }}",
            1,
        )
        cases.append(("wrong trusted checkout ref", wrong_trusted_ref))

        unsafe_submission = dict(final)
        unsafe_submission["feed-validate.yml"] = final[
            "feed-validate.yml"
        ].replace(
            "allow-unsafe-pr-checkout: true",
            "allow-unsafe-pr-checkout: false",
            1,
        )
        cases.append(("unsafe checkout input changed", unsafe_submission))

        submission_executable = dict(final)
        submission_executable["feed-validate.yml"] = final[
            "feed-validate.yml"
        ].replace(
            'python "$GITHUB_WORKSPACE/trusted/scripts/validate_feed.py"',
            'python "$GITHUB_WORKSPACE/submission/scripts/validate_feed.py"',
            1,
        )
        cases.append(("submission executable", submission_executable))

        credentialless_publisher = dict(final)
        publish_jobs = raw_job_step_spans(
            credentialless_publisher["feed-validate.yml"]
        )
        publish_checkout = next(
            step
            for step in publish_jobs["publish"]["steps"]
            if step_uses_action_prefix(step["raw"], "actions/checkout@")
        )
        credentialless_publisher["feed-validate.yml"] = (
            credentialless_publisher["feed-validate.yml"][
                : publish_checkout["start"]
            ]
            + publish_checkout["raw"].replace(
                "      - uses: actions/checkout@v7\n",
                "      - uses: actions/checkout@v7\n"
                "        with:\n"
                "          persist-credentials: false\n",
                1,
            )
            + credentialless_publisher["feed-validate.yml"][
                publish_checkout["end"] :
            ]
        )
        cases.append(("credentialless publisher", credentialless_publisher))

        for name, mutated in cases:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    enforce_python_workflow_policy(ROOT, overrides=mutated)

    def test_python_workflow_policy_rejects_concurrency_mutations(self) -> None:
        _, final = self.protected_state_fixtures()
        original = """concurrency:
  group: dependabot-automerge-${{ github.repository }}
  queue: max
"""
        replacements = {
            "wrong queue": original.replace("queue: max", "queue: min"),
            "cancel in progress": original + "  cancel-in-progress: true\n",
            "extra key": original + "  unexpected: value\n",
        }
        self.assertEqual(
            final["dependabot-automerge.yml"].count(original),
            1,
        )
        for name, replacement in replacements.items():
            with self.subTest(name=name):
                mutated = dict(final)
                mutated["dependabot-automerge.yml"] = final[
                    "dependabot-automerge.yml"
                ].replace(original, replacement, 1)
                with self.assertRaises(ValueError):
                    enforce_python_workflow_policy(ROOT, overrides=mutated)

    def test_tests_python_setup_exception_is_owned_by_the_policy(self) -> None:
        _, final = self.protected_state_fixtures()
        tests_text = workflow_policy_payload(ROOT)["tests.yml"]
        mutation = tests_text.replace(
            "python-version: ${{ matrix.python_version }}",
            "python-version-file: .python-version",
            1,
        )
        self.assertNotEqual(mutation, tests_text)
        with self.assertRaises(ValueError):
            enforce_python_workflow_policy(
                ROOT,
                overrides={**final, "tests.yml": mutation},
            )

    def test_tests_workflow_event_policy_is_scoped_and_exact(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        events = top_level_mapping_block(text, "on")
        jobs = top_level_mapping_block(text, "jobs")
        push = mapping_block(events, "push", indent=2)
        pull_request = mapping_block(events, "pull_request", indent=2)
        paths_ignore = mapping_block(push, "paths-ignore", indent=4)
        permissions = top_level_mapping_block(text, "permissions")
        concurrency = top_level_mapping_block(text, "concurrency")

        self.assertEqual(direct_mapping_keys(text, 0), TOP_LEVEL_WORKFLOW_KEYS)
        self.assertEqual(direct_mapping_keys(jobs, 2), JOB_KEYS)
        self.assertEqual(events.splitlines(), EVENT_POLICY_LINES)
        self.assertIn("    branches: [main]", push)
        self.assertEqual(
            paths_ignore.splitlines(),
            [f'      - "{path}"' for path in GENERATED_FEED_IGNORES],
        )
        self.assertEqual(pull_request.strip(), "")
        self.assertEqual(permissions.splitlines(), ["  contents: read"])
        self.assertEqual(concurrency.splitlines(), CONCURRENCY_LINES)
        for covered_path in ("feed/inbox/**", "feed/schema/**", "feed/README.md"):
            self.assertNotIn(covered_path, paths_ignore)

    def test_tests_workflow_frontend_matrix_and_steps_are_scoped(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        jobs = top_level_mapping_block(text, "jobs")
        frontend = mapping_block(jobs, "frontend", indent=2)
        strategy = mapping_block(frontend, "strategy", indent=4)
        defaults = mapping_block(frontend, "defaults", indent=4)
        env = mapping_block(frontend, "env", indent=4)
        steps = normalized_step_blocks(frontend)

        self.assert_required_job_is_fail_closed(frontend)
        self.assertEqual(direct_mapping_keys(frontend, 4), FRONTEND_JOB_KEYS)
        self.assertEqual(strategy.splitlines(), FRONTEND_STRATEGY_LINES)
        self.assertEqual(defaults.splitlines(), FRONTEND_DEFAULTS_LINES)
        self.assertEqual(env.splitlines(), FRONTEND_ENV_LINES)
        self.assertEqual(steps, FRONTEND_STEP_BLOCKS)
        self.assertEqual(
            re.findall(
                r"(?m)^          - profile: ([^\n]+)\n"
                r"            base_path: ([^\n]+)$",
                frontend,
            ),
            [("static", "/stock-analysis"), ("server", '""')],
        )
        self.assertIn("      NEXT_PUBLIC_BASE_PATH: ${{ matrix.base_path }}", frontend)

        checkout = only_block_containing(steps, "uses: actions/checkout@v7")
        self.assertIn("persist-credentials: false", checkout)
        setup_node = only_block_containing(steps, "uses: actions/setup-node@v7")
        self.assertIn("node-version-file: .node-version", setup_node)
        self.assertIn("cache-dependency-path: frontend/package-lock.json", setup_node)

        versions = only_block_containing(steps, "name: Verify exact Node and npm")
        self.assertIn('test "$(node --version)" = "v20.20.2"', versions)
        self.assertIn('test "$(npm --version)" = "10.8.2"', versions)
        common_steps = [checkout, setup_node, versions]
        for command in (
            "npm ci",
            "npm run lint",
            "npm run typecheck",
            "npm run test:scripts",
        ):
            command_step = only_block_containing(steps, f"- run: {command}")
            self.assertRegex(
                command_step,
                rf"(?m)^      - run: {re.escape(command)}$",
            )
            common_steps.append(command_step)
        for step in common_steps:
            self.assertEqual(step_if_expressions(step), [], step)

        for profile, command in (
            ("static", "npm run build:static"),
            ("static", "npm run smoke:static"),
            ("server", "npm run build:server"),
            ("server", "npm run smoke:server"),
        ):
            profile_step = only_block_containing(steps, f"run: {command}")
            self.assertEqual(
                step_if_expressions(profile_step),
                [f"matrix.profile == '{profile}'"],
                (profile, command),
            )
            self.assertEqual(step_run_scripts(profile_step), [command])

    def test_tests_workflow_python_matrix_locks_and_entrypoints_are_scoped(
        self,
    ) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        jobs = top_level_mapping_block(text, "jobs")
        python_job = mapping_block(jobs, "python", indent=2)
        strategy = mapping_block(python_job, "strategy", indent=4)
        env = mapping_block(python_job, "env", indent=4)
        steps = normalized_step_blocks(python_job)

        self.assert_required_job_is_fail_closed(python_job)
        self.assertEqual(direct_mapping_keys(python_job, 4), PYTHON_JOB_KEYS)
        self.assertEqual(strategy.splitlines(), PYTHON_STRATEGY_LINES)
        self.assertEqual(env.splitlines(), PYTHON_ENV_LINES)
        self.assertEqual(steps, PYTHON_STEP_BLOCKS)
        python_rows = re.findall(
            r'(?m)^          - python_version: "([^"]+)"\n'
            r"            lockfile: ([^\n]+)$",
            python_job,
        )
        self.assertEqual(
            python_rows,
            [
                ("3.11.15", "requirements/ci-py311.txt"),
                ("3.12.13", "requirements/ci-py312.txt"),
            ],
        )
        checkout = only_block_containing(steps, "uses: actions/checkout@v7")
        self.assertIn("persist-credentials: false", checkout)
        setup_python = only_block_containing(steps, "uses: actions/setup-python@v6")
        self.assertIn("python-version: ${{ matrix.python_version }}", setup_python)
        install = only_block_containing(
            steps,
            'python -m pip install --require-hashes -r "${{ matrix.lockfile }}"',
        )
        self.assertNotIn("--upgrade", install)
        self.assertEqual(
            step_run_scripts(install),
            ['python -m pip install --require-hashes -r "${{ matrix.lockfile }}"'],
        )
        pip_check = only_block_containing(steps, "run: python -m pip check")
        self.assertEqual(step_run_scripts(pip_check), ["python -m pip check"])

        reproduce_311 = only_block_containing(
            steps, "name: Reproduce Python 3.11 locks from direct inputs"
        )
        reproduce_312 = only_block_containing(
            steps, "name: Reproduce Python 3.12 lock from direct inputs"
        )
        self.assertEqual(
            step_if_expressions(reproduce_311),
            ["matrix.python_version == '3.11.15'"],
        )
        self.assertEqual(
            step_if_expressions(reproduce_312),
            ["matrix.python_version == '3.12.13'"],
        )
        self.assert_reproduction_is_exact(reproduce_311, PY311_LOCK_REPRODUCTIONS)
        self.assert_reproduction_is_exact(reproduce_312, PY312_LOCK_REPRODUCTIONS)
        for block, expected_compile_count in (
            (reproduce_311, 6),
            (reproduce_312, 1),
        ):
            compile_lines = [
                line.strip()
                for line in block.splitlines()
                if "piptools compile" in line
            ]
            self.assertEqual(len(compile_lines), expected_compile_count)
            self.assertNotIn("--upgrade", block)
            self.assertLess(block.index("\n          cp "), block.index("piptools compile"))
            for compile_line in compile_lines:
                for flag in LOCK_COMPILE_FLAGS:
                    self.assertIn(flag, compile_line)

        backend_tests = only_block_containing(
            steps, "name: Backend HTTP and data-layer tests"
        )
        automation_tests = only_block_containing(
            steps, "name: Automation and feed-validation tests"
        )
        self.assertEqual(
            re.findall(
                r"(?m)^        working-directory:\s*(\S.*?)\s*$",
                backend_tests,
            ),
            ["backend"],
        )
        for step in (
            checkout,
            setup_python,
            install,
            pip_check,
            backend_tests,
            automation_tests,
        ):
            self.assertEqual(step_if_expressions(step), [], step)
        self.assertEqual(
            command_lines(backend_tests, automation_tests),
            COMMON_PYTHON_ENTRYPOINTS,
        )
        primary_locks = only_block_containing(
            steps, "name: Primary-runtime lock consistency"
        )
        self.assertEqual(
            step_if_expressions(primary_locks),
            ["matrix.python_version == '3.11.15'"],
        )
        primary_commands = command_lines(primary_locks)
        self.assertEqual(
            primary_commands,
            [
                "python scripts/tests/test_check_lock_consistency.py",
                "python scripts/check_lock_consistency.py --root .",
            ],
        )
        expanded_process_entrypoints = (
            len(python_rows)
            * len(command_lines(backend_tests, automation_tests))
            + len(primary_commands)
        )
        self.assertEqual(expanded_process_entrypoints, 22)

    def test_tests_workflow_stable_gate_requires_both_matrices(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        jobs = top_level_mapping_block(text, "jobs")
        gate = mapping_block(jobs, "gate", indent=2)
        steps = normalized_step_blocks(gate)

        self.assert_required_job_is_fail_closed(gate)
        self.assertEqual(direct_mapping_keys(gate, 4), GATE_JOB_KEYS)
        self.assertEqual(steps, GATE_STEP_BLOCKS)
        self.assertEqual(
            re.findall(r"(?m)^    name:\s*(.+)$", gate),
            ["Tests (单元测试闸门)"],
        )
        self.assertEqual(
            re.findall(r"(?m)^    if:\s*(.+)$", gate),
            ["${{ always() }}"],
        )
        self.assertEqual(
            re.findall(r"(?m)^    needs:\s*(.+)$", gate),
            ["[frontend, python]"],
        )
        requirement = only_block_containing(
            steps, "name: Require every runtime matrix to pass"
        )
        self.assertEqual(step_if_expressions(requirement), [], requirement)
        self.assertIn("FRONTEND_RESULT: ${{ needs.frontend.result }}", requirement)
        self.assertIn("PYTHON_RESULT: ${{ needs.python.result }}", requirement)
        self.assertIn('test "$FRONTEND_RESULT" = success', requirement)
        self.assertIn('test "$PYTHON_RESULT" = success', requirement)
        self.assertEqual(
            step_run_scripts(requirement),
            [
                'test "$FRONTEND_RESULT" = success\n'
                'test "$PYTHON_RESULT" = success'
            ],
        )

    def test_required_job_fail_closed_recognizes_quoted_keys(self) -> None:
        for line in (
            "    continue-on-error: false",
            '    "continue-on-error": false',
            "    'continue-on-error': false",
            '      - "continue-on-error": false',
        ):
            with self.subTest(line=line):
                with self.assertRaises(AssertionError):
                    self.assert_required_job_is_fail_closed(line)

    def test_broad_staging_detector_covers_yaml_shell_and_pathspec_variants(self) -> None:
        dangerous = {
            "inline root": "steps:\n  - run: git add feed\n",
            "block slash": "steps:\n  - run: |\n      git add ./feed/\n",
            "wildcard": "steps:\n  - run: git add feed/*\n",
            "quoted wildcard": "steps:\n  - run: git add 'feed/**'\n",
            "inline quoted": 'steps:\n  - run: "git add feed/**"\n',
            "literal comment": (
                "steps:\n  - run: | # shell\n      git add feed\n"
            ),
            "literal indent then chomp": (
                "steps:\n  - run: |2-\n      git add feed\n"
            ),
            "literal chomp then indent": (
                "steps:\n  - run: |-2\n      git add feed\n"
            ),
            "folded comment and keep": (
                "steps:\n  - run: >+ # folded shell\n      git add feed\n"
            ),
            "folded indent then chomp": (
                "steps:\n  - run: >2+\n      git add feed\n"
            ),
            "folded chomp then indent": (
                "steps:\n  - run: >-2\n      git add feed\n"
            ),
            "continuation and chdir": (
                "steps:\n  - run: |\n      git \\\n"
                "        -C . \\\n"
                "        add \\\n"
                "        ./feed/\n"
            ),
        }
        for name, workflow in dangerous.items():
            with self.subTest(name=name):
                self.assertTrue(broad_feed_adds(workflow))

        exact = "steps:\n  - run: git -C . add -A -- feed/index.json feed/reports/id.json\n"
        self.assertEqual(broad_feed_adds(exact), [])

        inline = 'steps:\n  - run: "echo inline | sed s/x/y/"\n'
        self.assertEqual(
            workflow_run_scripts(inline),
            [(2, "echo inline | sed s/x/y/")],
        )

        for header in ("|22", "|+-", ">0-", "|#not-a-comment"):
            with self.subTest(malformed_header=header):
                malformed = f"steps:\n  - run: {header}\n      git add feed\n"
                self.assertEqual(workflow_run_scripts(malformed), [(2, header)])

    def test_no_workflow_stages_feed_root_or_wildcard_pathspec(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        offenders = []
        paths = [*workflows.glob("*.yml"), *workflows.glob("*.yaml")]
        for path in paths:
            for number, pathspec in broad_feed_adds(path.read_text(encoding="utf-8")):
                offenders.append(f"{path.name}:{number}:{pathspec}")
        self.assertEqual(offenders, [])

    def test_feed_publishers_use_the_allowlist_stager(self) -> None:
        expected_counts = {
            "feed-validate.yml": 2,
            "alpha-routine.yml": 1,
            "hyperliquid-monitor.yml": 1,
            "monthly-studies.yml": 1,
            "openclaw-notes.yml": 1,
        }
        for filename, expected_count in expected_counts.items():
            text = (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
            self.assertEqual(
                text.count('python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"'),
                expected_count,
                filename,
            )

    def test_feed_publishers_fail_when_push_retries_are_exhausted(self) -> None:
        for filename in (
            "feed-validate.yml",
            "alpha-routine.yml",
            "hyperliquid-monitor.yml",
            "monthly-studies.yml",
        ):
            text = (ROOT / ".github" / "workflows" / filename).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("git pull --rebase origin main || true", text, filename)
            self.assertIn('if [ "$pushed" -ne 1 ]', text, filename)

    def test_dependabot_has_no_direct_merge_fallback(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("|| gh pr merge --merge", workflow)
        self.assertNotIn("statusCheckRollup", workflow)
        self.assertNotIn("--admin", workflow)
        self.assertIn("dependabot_merge_gate.py", workflow)
        self.assertIn("checks: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertIn("statuses: write", workflow)

    def test_dependabot_serializes_all_runs_with_a_top_level_queue(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")

        concurrency = top_level_mapping_block(workflow, "concurrency")

        self.assertIn("  group: dependabot-automerge-${{ github.repository }}", concurrency)
        self.assertIn("  queue: max", concurrency)
        self.assertNotRegex(workflow, r"(?m)^\s*cancel-in-progress:\s*true\s*$")

    def test_dependabot_sweep_reconciles_every_open_dependabot_pr(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        sweep = workflow[workflow.index("  sweep:") :]
        label = "dependencies:auto-merge-eligible"
        self.assertIn("dependabot/fetch-metadata@v3", workflow)
        self.assertIn("pull_request_target:", workflow)
        self.assertNotIn("\n  pull_request:\n", workflow)
        self.assertIn(
            "github.event.pull_request.user.login == 'dependabot[bot]'", workflow
        )
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn(f"AUTOMERGE_ELIGIBLE_LABEL: {label}", workflow)
        self.assertIn('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"', workflow)
        self.assertIn('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"', workflow)
        self.assertIn("--author 'app/dependabot' --state open", sweep)
        self.assertIn("--limit 1000", sweep)
        self.assertIn("--json number,title", sweep)
        self.assertNotIn("--label", sweep)
        self.assertNotIn("labels", sweep)
        self.assertNotIn("eligibility_label", sweep)
        self.assertNotIn("continue", sweep)
        self.assertIn("steps.eligibility.outputs.eligible == 'true'", workflow)
        self.assertNotIn("major_match", workflow)
        self.assertNotIn("re.search", workflow)
        self.assertLess(
            workflow.index('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"'),
            workflow.index("dependabot/fetch-metadata@v3"),
        )
        self.assertLess(
            workflow.index("dependabot/fetch-metadata@v3"),
            workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"'),
        )
        self.assertLess(
            workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"'),
            workflow.index('--pr "$PR_NUMBER"'),
        )

    def test_dependabot_stale_event_guards_precede_all_eligibility_writes(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        query = "--json headRefOid --jq '.headRefOid // empty'"
        mismatch = (
            'if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] '
            '|| [ "$current_head" != "$HEAD_SHA" ]; then'
        )
        self.assertEqual(workflow.count(query), 2)
        self.assertEqual(workflow.count(mismatch), 2)

        cleanup = workflow.index("- name: 清理旧资格并撤销 auto-merge")
        cleanup_guard = workflow.index(mismatch, cleanup)
        cleanup_revoke = workflow.index(
            "from dependabot_merge_gate import revoke_auto_merge",
            cleanup_guard,
        )
        cleanup_exit = workflow.index("exit 1", cleanup_revoke)
        remove_label = workflow.index('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        pending = workflow.index("-f state=pending")
        eligibility = workflow.index("- name: 根据 metadata 同步 auto-merge 资格标签")
        eligibility_guard = workflow.index(mismatch, eligibility)
        eligibility_revoke = workflow.index(
            "from dependabot_merge_gate import revoke_auto_merge",
            eligibility_guard,
        )
        eligibility_exit = workflow.index("exit 1", eligibility_revoke)
        add_label = workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        success = workflow.index("-f state=success")

        self.assertLess(cleanup, cleanup_guard)
        self.assertLess(cleanup_guard, cleanup_revoke)
        self.assertLess(cleanup_revoke, cleanup_exit)
        self.assertLess(cleanup_exit, remove_label)
        self.assertLess(cleanup_exit, pending)
        self.assertLess(eligibility, eligibility_guard)
        self.assertLess(eligibility_guard, eligibility_revoke)
        self.assertLess(eligibility_revoke, eligibility_exit)
        self.assertLess(eligibility_exit, add_label)
        self.assertLess(eligibility_exit, success)

    def test_dependabot_metadata_policy_uses_head_bound_attestation(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        required = (
            "revoke_auto_merge(",
            "-f state=pending",
            "--classify-ecosystem",
            '--add-label "$AUTOMERGE_ELIGIBLE_LABEL"',
            "-f state=success",
        )
        for marker in required:
            self.assertIn(marker, workflow)
        metadata = workflow.index("dependabot/fetch-metadata@v3")
        remove_label = workflow.index('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        revoke = workflow.index("revoke_auto_merge(", remove_label)
        pending = workflow.index("-f state=pending")
        classify = workflow.index("--classify-ecosystem")
        add_label = workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        success = workflow.index("-f state=success")

        self.assertIn(
            "AUTOMERGE_ATTESTATION_CONTEXT: dependabot/auto-merge-eligible",
            workflow,
        )
        self.assertIn("HEAD_SHA: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn(
            "PACKAGE_ECOSYSTEM: ${{ steps.meta.outputs.package-ecosystem }}",
            workflow,
        )
        self.assertIn('--classify-ecosystem "$PACKAGE_ECOSYSTEM"', workflow)
        self.assertIn("--classify-update-type", workflow)
        self.assertIn("-f state=failure", workflow)
        self.assertIn('"repos/$REPO/statuses/$HEAD_SHA"', workflow)
        self.assertLess(remove_label, revoke)
        self.assertLess(revoke, pending)
        self.assertLess(pending, metadata)
        self.assertLess(metadata, classify)
        self.assertLess(classify, add_label)
        self.assertLess(add_label, success)
        self.assertLess(success, workflow.index("--pr \"$PR_NUMBER\""))

    def test_dependabot_cleanup_revokes_active_auto_merge_fail_closed(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        gate = (ROOT / "scripts" / "dependabot_merge_gate.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("cleanup_failed=0", workflow)
        self.assertIn("from dependabot_merge_gate import revoke_auto_merge", workflow)
        self.assertIn('if [ "$cleanup_failed" -ne 0 ]; then', workflow)
        self.assertIn('"--disable-auto"', gate)
        self.assertNotIn("--admin", gate)

    def test_dependabot_gate_requires_current_clean_state_and_native_checks(
        self,
    ) -> None:
        gate = (ROOT / "scripts" / "dependabot_merge_gate.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("view_command = [", gate)
        self.assertIn('"view",', gate)
        self.assertIn('"headRefOid,mergeable,mergeStateStatus,labels"', gate)
        self.assertIn('view.get("mergeable") == "MERGEABLE"', gate)
        self.assertIn('view.get("mergeStateStatus") == "CLEAN"', gate)
        self.assertIn("statuses?per_page=100", gate)
        self.assertIn("eligibility_attested(statuses)", gate)
        self.assertIn('TRUSTED_ATTESTATION_CREATOR = "github-actions[bot]"', gate)
        self.assertIn('"--required"', gate)
        self.assertIn('"--auto"', gate)
        self.assertIn('"--match-head-commit"', gate)
        self.assertNotIn("--head-sha", gate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
