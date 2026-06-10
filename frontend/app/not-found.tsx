import Link from "next/link";

export default function NotFound() {
  return (
    <div className="container" style={{ textAlign: "center", paddingTop: 80 }}>
      <h1 style={{ fontSize: 40, margin: 0 }}>404</h1>
      <p style={{ color: "var(--muted)" }}>页面不存在,常用入口:</p>
      <p style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
        <Link className="btn" href="/">📈 看板</Link>
        <Link className="btn" href="/desk/">📋 总览</Link>
        <Link className="btn" href="/reports/">📜 报告</Link>
        <Link className="btn" href="/tracker/">🎯 追踪</Link>
        <Link className="btn" href="/help/">❓ 功能地图</Link>
      </p>
    </div>
  );
}
