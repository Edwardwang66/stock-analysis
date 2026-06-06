/** @type {import('next').NextConfig} */
// GitHub Pages 项目站点需要 basePath = /<repo>。由 CI 注入 NEXT_PUBLIC_BASE_PATH。
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig = {
  output: "export", // 静态导出 -> out/ ,可直接放 GitHub Pages
  images: { unoptimized: true },
  basePath: basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
};

export default nextConfig;
