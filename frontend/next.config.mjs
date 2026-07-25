/** @type {import("next").NextConfig} */
const profile = process.env.NEXT_BUILD_PROFILE ?? "server";
const allowedProfiles = new Set(["static", "server"]);

if (!allowedProfiles.has(profile)) {
  throw new Error(
    `NEXT_BUILD_PROFILE must be "static" or "server", got "${profile}"`,
  );
}

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
if (basePath && (!basePath.startsWith("/") || basePath.endsWith("/"))) {
  throw new Error(
    "NEXT_PUBLIC_BASE_PATH must start with '/' and must not end with '/'",
  );
}

const nextConfig = {
  ...(profile === "static" ? { output: "export" } : {}),
  images: { unoptimized: true },
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
};

export default nextConfig;
