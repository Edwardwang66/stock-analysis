import type { Metadata, Viewport } from "next";
import { resolvePublicSiteUrl } from "@/lib/public-site-url.mjs";
import "./globals.css";
import HotKeys from "@/components/HotKeys";
import ErrorCollector from "@/components/ErrorCollector";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";
const PUBLIC_SITE_URL = resolvePublicSiteUrl();
const SHARE_TITLE = "Edward Wang · Multi-Market Workbench";
const SHARE_DESCRIPTION =
  "Markets, signals and evidence across global assets.";
const SHARE_IMAGE_ALT =
  "Edward Wang Multi-Market Workbench: markets, signals, and evidence across US, Hong Kong, mainland China, digital assets, and benchmarks.";
const SHARE_IMAGE = {
  url: new URL("og-card-v1.png", PUBLIC_SITE_URL),
  width: 1200,
  height: 630,
  type: "image/png",
  alt: SHARE_IMAGE_ALT,
};

export const metadata: Metadata = {
  title: "多市场股票数据看板",
  description: "美股 · 港股 · A股 · 加密 · 指数 实时行情,主力资金 / 筹码 / 缠论等非 LLM 技术分析,价格提醒,零成本静态部署",
  manifest: `${BASE_PATH}/manifest.json`,
  metadataBase: PUBLIC_SITE_URL,
  openGraph: {
    type: "website",
    siteName: SHARE_TITLE,
    locale: "zh_CN",
    title: SHARE_TITLE,
    description: SHARE_DESCRIPTION,
    url: PUBLIC_SITE_URL,
    images: [SHARE_IMAGE],
  },
  twitter: {
    card: "summary_large_image",
    title: SHARE_TITLE,
    description: SHARE_DESCRIPTION,
    images: [SHARE_IMAGE],
  },
};

export const viewport: Viewport = {
  themeColor: "#0b0e14",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body><HotKeys /><ErrorCollector />{children}</body>
    </html>
  );
}
