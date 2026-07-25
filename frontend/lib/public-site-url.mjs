import { isIP } from "node:net";

const SOURCES = [
  ["NEXT_PUBLIC_SITE_URL", false],
  ["VERCEL_PROJECT_PRODUCTION_URL", true],
  ["VERCEL_URL", true],
];

function deploymentEnvironment(env) {
  return env.CI === "true"
    || env.GITHUB_ACTIONS === "true"
    || env.VERCEL === "1";
}

function basePathFrom(env) {
  const basePath = env.NEXT_PUBLIC_BASE_PATH || "";
  if (
    typeof basePath !== "string"
    || (basePath
      && (!basePath.startsWith("/") || basePath.endsWith("/")))
  ) {
    throw new Error(
      "NEXT_PUBLIC_BASE_PATH must start with '/' and must not end with '/'",
    );
  }
  return basePath;
}

function candidateUrl(name, value, vercelHost) {
  if (typeof value !== "string" || value.trim() !== value) {
    throw new Error(`${name} must not contain surrounding whitespace`);
  }
  const input = vercelHost && !value.includes("://")
    ? `https://${value}`
    : value;
  let result;
  try {
    result = new URL(input);
  } catch {
    throw new Error(`${name} must be a valid absolute URL`);
  }
  if (!["http:", "https:"].includes(result.protocol)) {
    throw new Error(`${name} must use http or https`);
  }
  if (result.username || result.password || result.search || result.hash) {
    throw new Error(`${name} must not contain credentials, query, or fragment`);
  }
  return result;
}

function canonicalHostname(hostname) {
  let result = hostname.toLowerCase();
  while (result.endsWith(".")) result = result.slice(0, -1);
  return result;
}

function unbracketIpv6(hostname) {
  return hostname.startsWith("[") && hostname.endsWith("]")
    ? hostname.slice(1, -1)
    : hostname;
}

function nonPublicDeploymentHostname(hostname) {
  const canonical = canonicalHostname(hostname);
  return canonical === "localhost"
    || canonical.endsWith(".localhost")
    || isIP(unbracketIpv6(canonical)) !== 0;
}

export function resolvePublicSiteUrl(env = process.env) {
  const basePath = basePathFrom(env);
  const expectedPath = basePath ? `${basePath}/` : "/";

  for (const [name, vercelHost] of SOURCES) {
    const value = env[name];
    if (value === undefined || value === "") continue;
    const result = candidateUrl(name, value, vercelHost);
    result.pathname = result.pathname.endsWith("/")
      ? result.pathname
      : `${result.pathname}/`;
    if (result.pathname !== expectedPath) {
      throw new Error(
        `${name} pathname must match NEXT_PUBLIC_BASE_PATH "${basePath}"`,
      );
    }
    if (deploymentEnvironment(env) && nonPublicDeploymentHostname(result.hostname)) {
      throw new Error(`${name} must use a public hostname when deployed`);
    }
    return result;
  }

  if (deploymentEnvironment(env)) {
    throw new Error("a public site URL is required in deployment environments");
  }
  return new URL(`http://localhost:3000${expectedPath}`);
}
