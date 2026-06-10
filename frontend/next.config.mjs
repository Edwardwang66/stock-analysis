/** @type {import('next').NextConfig} */
// GitHub Pages 项目站点需要 basePath = /<repo>。由 CI 注入 NEXT_PUBLIC_BASE_PATH。
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const onVercel = Boolean(process.env.VERCEL);

const nextConfig = {
  // 双目标:Vercel 跑完整 Next(app/api 边缘函数生效);GitHub Pages CI 静态导出
  //(deploy-pages.yml 构建前会移除 app/api,静态导出不含动态路由)。
  ...(onVercel ? {} : { output: "export" }),
  images: { unoptimized: true },
  basePath: basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
};

export default nextConfig;
