"use client";
// ⑨ 深度研究简报:消费 feed/research/(scripts/deep_research.py 产出)。
// 引擎是确定性逻辑,不调用任何 LLM;本面板只如实转述简报里已有的字段。
// 关键约定:被反驳(refuted)与未验证(unverified)的论断不删除、照旧展示 —— 面板存在的意义就是让反驳可见。
import { useEffect, useState } from "react";
import {
  getResearchBrief, getResearchIndex,
  type ResearchBrief, type ResearchClaim, type ResearchIndex,
} from "@/lib/feed";

const UP = "#26a69a", DOWN = "#ef5350", WARN = "#f7b500", MUT = "#787b86";
const LVL: Record<string, string> = { info: MUT, warning: WARN, critical: DOWN };
const VERDICT: Record<string, { c: string; t: string }> = {
  confirmed: { c: UP, t: "已确认" }, refuted: { c: DOWN, t: "被反驳" }, unverified: { c: WARN, t: "未验证" },
};
// boolean 必须显式转字符串:React 不渲染 true/false,直接 return v 会让布尔取值凭空消失。
const fmt = (v?: number | string | boolean | null) =>
  v == null ? "—"
    : typeof v === "boolean" ? (v ? "true" : "false")
      : typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(4)) : v;
// "none" 是引擎的哨兵值(无方向/无单位),不是数据,不展示。
const real = (v?: string | null) => (v && v !== "none" ? v : "");

export default function ResearchBriefs() {
  const [idx, setIdx] = useState<ResearchIndex | null>(null);
  const [brief, setBrief] = useState<ResearchBrief | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [openClaim, setOpenClaim] = useState<string | null>(null);

  // 只拉索引(小文件);整份简报等用户展开时再懒加载,避免 /intel 的 5 分钟轮询把简报全文拖下来。
  // 与 /intel 其它面板同频刷新索引(5 分钟)。
  useEffect(() => {
    const load = () => { getResearchIndex().then(setIdx).catch(() => {}); };
    load();
    const timer = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, []);

  const latest = idx?.briefs?.[0];
  const latestId = latest?.id;
  const path = latest?.path;

  // 简报全文跟着「当前最新简报」取:轮询换了简报就重取。
  // 不能只在 brief 为空时取 —— 那样头部会显示新 id 与新计数,展开区却还是上一份简报的内容。
  // alive 守卫避免卸载后 setState;取数失败解析为 null,不抛异常。
  useEffect(() => {
    if (!open || !path) return;
    let alive = true;
    setBusy(true);
    setFailed(false);
    setOpenClaim(null);            // 结论 id 是位序(c01…),换简报后旧展开项指向的已是另一条
    getResearchBrief(path).then((doc) => {
      if (!alive) return;
      setBrief(doc);
      setFailed(doc == null);      // 否则面板会永远停在「加载简报中…」
      setBusy(false);
    });
    return () => { alive = false; };
  }, [open, latestId, path]);

  if (!idx || !latest) return null;

  const rejected = brief?.refuted ?? [];

  return (
    <div className="section">
      <h2>⑨ 深度研究简报(确定性引擎 · 对抗验证)
        <span className="src" style={{ marginLeft: 10 }}>
          {latest.id} · 数据截至 {latest.asof_data || "—"} · 简报累计 {idx.stats?.total_briefs ?? idx.briefs?.length ?? 0} 份
          {idx.stats?.last_7d != null && ` · 近 7 天 ${idx.stats.last_7d} 份`}
        </span>
      </h2>

      {/* 裁决计数(来自索引摘要,展开前就可见) */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(140px,1fr))" }}>
        <Chip label="已确认 confirmed" value={latest.confirmed ?? 0} color={UP} />
        <Chip label="被反驳 refuted" value={latest.refuted ?? 0} color={DOWN} />
        <Chip label="未验证 unverified" value={latest.unverified ?? 0} color={WARN} />
        <Chip label="立题数" value={latest.n_questions ?? 0} />
        <Chip label="发现数(仅确认)" value={latest.n_findings ?? 0} />
        <Chip label="告警" value={latest.n_alerts ?? 0} color={(latest.n_alerts ?? 0) > 0 ? WARN : MUT} />
      </div>

      {latest.headline && <p className="src" style={{ marginTop: 10, lineHeight: 1.6 }}>{latest.headline}</p>}

      <button className="btn" style={{ marginTop: 10 }} onClick={() => setOpen((v) => !v)}>
        {open ? "收起取证明细" : "展开取证明细(含被反驳论断)"}
      </button>

      {open && (failed && !brief ? (
        <div className="err" style={{ marginTop: 10 }}>
          无法加载简报 <code>{path}</code>(远端与捆绑快照均失败)。
          <button className="btn" style={{ marginLeft: 8 }} onClick={() => { setOpen(false); setFailed(false); }}>
            收起重试
          </button>
        </div>
      ) : busy || !brief ? (
        <p className="loading" style={{ marginTop: 10 }}>加载简报中…</p>
      ) : (
        <div style={{ marginTop: 12, display: "grid", gap: 14 }}>
          {/* 已确认发现:点行展开证据链 */}
          <div>
            <div className="src" style={{ fontWeight: 600, marginBottom: 6, color: UP }}>
              已确认发现({brief.findings?.length ?? 0})—— 点行展开证据(artifact · field · value · asof)
            </div>
            <div className="signal-list">
              {(brief.findings ?? []).length === 0 && <p className="src">本次没有通过对抗验证的论断。</p>}
              {(brief.findings ?? []).map((c) => (
                <ClaimRow key={c.id} c={c} open={openClaim === c.id}
                  onClick={() => setOpenClaim(openClaim === c.id ? null : c.id)} />
              ))}
            </div>
          </div>

          {/* 被反驳 / 未验证:刻意弱化但绝不删除 */}
          <div style={{ borderTop: "1px dashed var(--border)", paddingTop: 10, opacity: 0.72 }}>
            <div className="src" style={{ fontWeight: 600, marginBottom: 6, color: MUT }}>
              被反驳 / 未验证({rejected.length})—— red-team 反驳器判定,保留在简报中供审计,不作为结论
            </div>
            {rejected.length === 0 && <p className="src">无。</p>}
            {rejected.map((c) => (
              <div key={c.id} className="src" style={{ lineHeight: 1.7 }}>
                <span className="badge" style={{ marginRight: 6, borderColor: VERDICT[c.verdict || "unverified"]?.c, color: VERDICT[c.verdict || "unverified"]?.c }}>
                  {VERDICT[c.verdict || "unverified"]?.t ?? c.verdict}
                </span>
                <span style={{ textDecoration: c.verdict === "refuted" ? "line-through" : "none" }}>{c.statement}</span>
                {(c.refutations ?? []).map((r, i) => (
                  <span key={i} className="badge" style={{ marginLeft: 6, borderColor: MUT, color: MUT }} title={r.message}>{r.code}</span>
                ))}
              </div>
            ))}
          </div>

          {/* 开放问题:缺输入而降级,不静默丢弃 */}
          {(brief.open_questions ?? []).length > 0 && (
            <div>
              <div className="src" style={{ fontWeight: 600, marginBottom: 6, color: WARN }}>
                开放问题({brief.open_questions?.length})—— 缺输入即降级为 open_question,不静默丢弃
              </div>
              {(brief.open_questions ?? []).map((q) => (
                <div key={q.id} className="src" style={{ lineHeight: 1.7 }}>
                  · {q.title}
                  <span className="badge" style={{ marginLeft: 6, borderColor: WARN, color: WARN }}>{q.reason}</span>
                  {(q.missing ?? []).length > 0 && <span style={{ color: MUT }}> 缺:{(q.missing ?? []).join(" / ")}</span>}
                </div>
              ))}
            </div>
          )}

          {/* 下一步动作 */}
          {(brief.next_actions ?? []).length > 0 && (
            <div>
              <div className="src" style={{ fontWeight: 600, marginBottom: 6 }}>下一步动作({brief.next_actions?.length})</div>
              <table>
                <thead><tr><th>优先级</th><th>动作</th><th>依据</th></tr></thead>
                <tbody>
                  {(brief.next_actions ?? []).map((a, i) => (
                    <tr key={i}>
                      <td><span className="badge" style={{ borderColor: LVL[a.priority === "high" ? "critical" : a.priority === "medium" ? "warning" : "info"], color: LVL[a.priority === "high" ? "critical" : a.priority === "medium" ? "warning" : "info"] }}>{a.priority}</span></td>
                      <td>{a.action}</td>
                      <td className="src">{a.because}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 覆盖账本:每个 artifact 读到了没有 */}
          {(brief.coverage?.artifacts ?? []).length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {(brief.coverage?.artifacts ?? []).map((a) => (
                <span key={a.key} className="badge" title={`${a.path}${a.asof ? ` · ${a.asof}` : ""}`}
                  style={{ borderColor: a.exists ? "var(--border)" : DOWN, color: a.exists ? MUT : DOWN }}>
                  {a.key} {!a.exists ? "缺失" : a.age_days != null ? `${a.age_days.toFixed(1)}d` : "✓"}
                </span>
              ))}
            </div>
          )}

          {brief.notes && <p className="src" style={{ color: MUT, lineHeight: 1.6 }}>{brief.notes}</p>}
          {brief.run && (
            <p className="src" style={{ color: MUT }}>
              运行:并发 {brief.run.workers ?? "—"} · 角色 {(brief.run.roles ?? []).join("/") || "—"} · 立题 {brief.run.questions_derived ?? "—"}
              · 取证 {brief.run.lenses_run ?? "—"}(失败 {brief.run.lenses_failed ?? 0})· 扫描报告 {brief.run.reports_scanned ?? "—"} 份
              · 耗时 {brief.run.duration_ms ?? "—"}ms
            </p>
          )}
        </div>
      ))}

      <p className="src" style={{ marginTop: 10, color: MUT, lineHeight: 1.6 }}>
        {idx.note || "深度研究简报由 scripts/deep_research.py 产出。"} 引擎为确定性逻辑,<strong>不调用任何 LLM</strong>,
        也不访问网络 —— 它只描述本仓库 <code>feed/</code> 里已有的数据(LLM 是研究放大器,不决策(R6))。
        schema 校验通过 ≠ 分析结论获批:简报<strong>不是投资建议,也不等于策略获批</strong>。
      </p>
    </div>
  );
}

function Chip({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="card">
      <div className="src">{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4, color: color || "var(--text)" }}>{value}</div>
    </div>
  );
}

function ClaimRow({ c, open, onClick }: { c: ResearchClaim; open: boolean; onClick: () => void }) {
  return (
    <div className="signal" style={{ flexDirection: "column", alignItems: "stretch", gap: 4, cursor: "pointer",
      background: open ? "rgba(76,141,255,.08)" : undefined }} onClick={onClick}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <span>
          <span className="badge" style={{ marginRight: 6, borderColor: LVL[c.severity || "info"], color: LVL[c.severity || "info"] }}>
            {c.severity || "info"}
          </span>
          {c.statement}
        </span>
        <span className="src" style={{ whiteSpace: "nowrap" }}>{c.role}</span>
      </div>
      <span className="src">
        {c.metric || "—"} = {fmt(c.value)}{real(c.unit) ? ` ${real(c.unit)}` : ""}
        {real(c.direction) ? ` · 方向 ${real(c.direction)}` : ""}{c.n != null ? ` · n=${c.n}` : ""}
        {(c.cites ?? []).length > 0 ? ` · 依据 ${(c.cites ?? []).join("/")}` : ""}
      </span>
      {open && (
        <div style={{ display: "grid", gap: 3, marginTop: 4 }}>
          {(c.evidence ?? []).length === 0 && <span className="src" style={{ color: MUT }}>无证据条目。</span>}
          {(c.evidence ?? []).map((e, i) => (
            <span key={i} className="src" style={{ color: MUT }}>
              🔎 <code>{e.artifact}</code> · {e.field} = {fmt(e.value)}{e.asof ? ` · asof ${e.asof}` : ""}
            </span>
          ))}
          <span className="src" style={{ color: MUT }}>立题 {c.question} · 论断 {c.id}</span>
        </div>
      )}
    </div>
  );
}
