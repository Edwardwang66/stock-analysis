"use client";
// 研报模式的模块容器:折叠 + 上移/下移排序(由调用方持久化)。
// 不引第三方拖拽库:静态站点保持零重型依赖,↑↓ 按钮在移动端同样可靠。
export default function Collapse({ title, collapsed, onToggle, onUp, onDown, children }: {
  title: string;
  collapsed: boolean;
  onToggle: () => void;
  onUp?: (() => void) | null;
  onDown?: (() => void) | null;
  children: React.ReactNode;
}) {
  return (
    <div className="collapse-block">
      <div className="collapse-head">
        <button className="collapse-title" onClick={onToggle} aria-expanded={!collapsed}>
          <span className="caret">{collapsed ? "▸" : "▾"}</span> {title}
        </button>
        <span className="collapse-actions">
          {onUp && <button onClick={onUp} title="模块上移(顺序会记住)">↑</button>}
          {onDown && <button onClick={onDown} title="模块下移(顺序会记住)">↓</button>}
        </span>
      </div>
      {!collapsed && children}
    </div>
  );
}
