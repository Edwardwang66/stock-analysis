import type { Metadata, Viewport } from "next";
import "./globals.css";
import HotKeys from "@/components/HotKeys";
import ErrorCollector from "@/components/ErrorCollector";
import { Analytics } from "@vercel/analytics/next";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const metadata: Metadata = {
  title: "多市场股票数据看板",
  description: "美股 · 港股 · A股 · 加密 · 指数 实时行情,主力资金 / 筹码 / 缠论等非 LLM 技术分析,价格提醒,零成本静态部署",
  manifest: `${BASE_PATH}/manifest.json`,
};

export const viewport: Viewport = {
  themeColor: "#0b0e14",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body><HotKeys /><ErrorCollector />{children}<Analytics /></body>
    </html>
  );
}
