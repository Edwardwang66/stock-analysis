import assert from "node:assert/strict";
import test from "node:test";
import { resolvePublicSiteUrl } from "../../lib/public-site-url.mjs";

test("explicit site URL wins and is normalized", () => {
  const result = resolvePublicSiteUrl({
    NEXT_PUBLIC_SITE_URL: "https://example.com/stock-analysis",
    VERCEL_PROJECT_PRODUCTION_URL: "stable.vercel.app",
    VERCEL_URL: "preview.vercel.app",
    NEXT_PUBLIC_BASE_PATH: "/stock-analysis",
  });
  assert.ok(result instanceof URL);
  assert.equal(result.href, "https://example.com/stock-analysis/");
});

test("stable Vercel URL wins over deployment URL", () => {
  assert.equal(
    resolvePublicSiteUrl({
      VERCEL_PROJECT_PRODUCTION_URL: "stable.vercel.app",
      VERCEL_URL: "preview.vercel.app",
    }).href,
    "https://stable.vercel.app/",
  );
});

test("deployment Vercel URL is accepted when stable URL is absent", () => {
  assert.equal(
    resolvePublicSiteUrl({ VERCEL_URL: "preview.vercel.app" }).href,
    "https://preview.vercel.app/",
  );
});

test("local fallback composes the base path", () => {
  assert.equal(resolvePublicSiteUrl({}).href, "http://localhost:3000/");
  assert.equal(
    resolvePublicSiteUrl({ NEXT_PUBLIC_BASE_PATH: "/stock-analysis" }).href,
    "http://localhost:3000/stock-analysis/",
  );
});

test("GitHub Pages root must match the configured base path", () => {
  assert.equal(
    resolvePublicSiteUrl({
      NEXT_PUBLIC_SITE_URL:
        "https://edwardwang66.github.io/stock-analysis",
      NEXT_PUBLIC_BASE_PATH: "/stock-analysis",
    }).href,
    "https://edwardwang66.github.io/stock-analysis/",
  );
  assert.throws(
    () => resolvePublicSiteUrl({
      NEXT_PUBLIC_SITE_URL: "https://edwardwang66.github.io/",
      NEXT_PUBLIC_BASE_PATH: "/stock-analysis",
    }),
    /pathname.*NEXT_PUBLIC_BASE_PATH/,
  );
  assert.throws(
    () => resolvePublicSiteUrl({
      NEXT_PUBLIC_SITE_URL:
        "https://edwardwang66.github.io/stock-analysis/",
      NEXT_PUBLIC_BASE_PATH: "",
    }),
    /pathname.*NEXT_PUBLIC_BASE_PATH/,
  );
});

test("invalid explicit URLs fail closed", () => {
  for (const value of [
    "ftp://example.com/",
    "https://user:pass@example.com/",
    "https://example.com/?query=1",
    "https://example.com/#fragment",
    "not a url",
    " https://example.com/",
    "https://example.com/ ",
  ]) {
    assert.throws(
      () => resolvePublicSiteUrl({ NEXT_PUBLIC_SITE_URL: value }),
      /NEXT_PUBLIC_SITE_URL/,
      value,
    );
  }
});

test("invalid base paths fail closed", () => {
  for (const value of ["stock-analysis", "/stock-analysis/"]) {
    assert.throws(
      () => resolvePublicSiteUrl({ NEXT_PUBLIC_BASE_PATH: value }),
      /NEXT_PUBLIC_BASE_PATH/,
      value,
    );
  }
});

test("deployment environments require a non-local public URL", () => {
  for (const flag of [
    { CI: "true" },
    { GITHUB_ACTIONS: "true" },
    { VERCEL: "1" },
  ]) {
    assert.throws(() => resolvePublicSiteUrl(flag), /public site URL/i);
  }
  for (const hostname of ["localhost", "app.localhost", "127.0.0.1", "[::1]"]) {
    assert.throws(
      () => resolvePublicSiteUrl({
        CI: "true",
        NEXT_PUBLIC_SITE_URL: `http://${hostname}/`,
      }),
      /localhost/i,
    );
  }
});
