import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "多市场股票数据看板",
  description: "美股 + 加密 实时行情与非 LLM 技术分析(MVP)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
