# Open Graph Share Card Implementation Plan

> **Status:** Accepted implementation plan
> **Scope:** Implement, test, publish, and verify the approved B3 root-site share card for both frontend build profiles.
> **Last verified commit:** `d78a04e10520904954341e737fddf40ac67f1a95`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Vercel and GitHub Pages root URLs publish the approved 1200 × 630 B3 card through complete Open Graph and Twitter/X metadata.

**Architecture:** Commit one editable SVG and one versioned PNG release asset, then point both metadata families at that same PNG. A pure public-site URL resolver owns Vercel, Pages, base-path, and local-fallback semantics; shared smoke helpers verify the emitted HTML and PNG in static and server builds.

**Tech Stack:** Next.js 14.2.35 App Router metadata, React 18.3.1, Node 20.20.2, npm 10.8.2, native `node:test`, static SVG/PNG assets, headless Google Chrome for one-time raster export, GitHub Actions, Vercel, and GitHub Pages.

**Source specification:** [`../specs/2026-07-26-open-graph-share-card-design.md`](../specs/2026-07-26-open-graph-share-card-design.md)

## Global Constraints

- Start execution on `codex/open-graph-share-card` in an isolated worktree created with `superpowers:using-git-worktrees`; do not implement in the dirty main checkout.
- Preserve the existing browser title `多市场股票数据看板`, Chinese page description, manifest path, routes, and dashboard behavior.
- Share title is exactly `Edward Wang · Multi-Market Workbench`.
- Share description is exactly `Markets, signals and evidence across global assets.`.
- Card owner line is exactly `EDWARD WANG / INDEPENDENT RESEARCH`.
- Card title is exactly two lines: `MULTI-MARKET` and `WORKBENCH`.
- Card tagline is exactly `MARKETS · SIGNALS · EVIDENCE`.
- The right panel contains exactly four equally sized windows: `EQUITIES / US / HK`, `MAINLAND / CN`, `DIGITAL / 24 / 7`, and `BENCHMARKS / INDEX`.
- The card is exactly 1200 × 630, below 1 MiB, self-contained, and independent of live data, remote images, runtime fonts, and request-time rendering.
- `frontend/public/og-card-v1.png` is the release authority; `frontend/design/og-card-v1.svg` is the editable source.
- Open Graph and Twitter/X reuse one image URL and one alt string.
- Static-root, static Pages base-path, and server-root builds are equal CI targets.
- Add no npm or Python dependency; `frontend/package-lock.json` must remain byte-identical.
- Use only `http:` or `https:` public roots. Deployed CI/Vercel metadata may not use localhost, credentials, query strings, or fragments.
- Never stage `.superpowers/` or the user-owned untracked `AGENTS.md`.
- Do not push, deploy, change Vercel project settings, or trigger a remote refresh without explicit user authorization.

---

### Task 1: Define and test the public-site URL contract

**Files:**

- Create: `frontend/lib/public-site-url.mjs`
- Create: `frontend/scripts/tests/public-site-url.test.mjs`
- Modify: `frontend/package.json:18`

**Interfaces:**

- Consumes: `NEXT_PUBLIC_SITE_URL`, `VERCEL_PROJECT_PRODUCTION_URL`, `VERCEL_URL`, `NEXT_PUBLIC_BASE_PATH`, `CI`, `GITHUB_ACTIONS`, and `VERCEL`.
- Produces: `resolvePublicSiteUrl(env: Record<string, string | undefined> = process.env) -> URL`.
- Preserves: the base-path validation already enforced by `frontend/next.config.mjs`.

- [ ] **Step 1: Write the failing URL-resolution tests**

Create `frontend/scripts/tests/public-site-url.test.mjs`:

```js
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
```

Append the test to the explicit `test:scripts` list:

```json
"test:scripts": "node --test scripts/tests/build-profile-publication.test.mjs scripts/tests/public-site-url.test.mjs scripts/tests/smoke-server.test.mjs"
```

- [ ] **Step 2: Run the focused test and verify the red state**

Run:

```bash
cd frontend
node --test scripts/tests/public-site-url.test.mjs
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `lib/public-site-url.mjs`.

- [ ] **Step 3: Implement the minimal pure resolver**

Create `frontend/lib/public-site-url.mjs`:

```js
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

function localHostname(hostname) {
  return hostname === "localhost"
    || hostname.endsWith(".localhost")
    || hostname === "127.0.0.1"
    || hostname === "[::1]";
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
    if (deploymentEnvironment(env) && localHostname(result.hostname)) {
      throw new Error(`${name} must not resolve to localhost when deployed`);
    }
    return result;
  }

  if (deploymentEnvironment(env)) {
    throw new Error("a public site URL is required in deployment environments");
  }
  return new URL(`http://localhost:3000${expectedPath}`);
}
```

- [ ] **Step 4: Run focused tests, typecheck, and the existing script suite**

Run:

```bash
cd frontend
node --test scripts/tests/public-site-url.test.mjs
npm run typecheck
npm run test:scripts
```

Expected: all URL cases PASS; typecheck and the complete script suite exit 0.

- [ ] **Step 5: Commit Task 1**

```bash
git add frontend/lib/public-site-url.mjs \
  frontend/scripts/tests/public-site-url.test.mjs \
  frontend/package.json
git commit -m "test(frontend): define public site URL contract"
```

Before committing, assert `git diff --cached --name-only` contains exactly those three paths.

---

### Task 2: Add and mechanically validate the approved B3 asset

**Files:**

- Create: `frontend/design/og-card-v1.svg`
- Create: `frontend/public/og-card-v1.png`
- Create: `frontend/scripts/tests/og-card-asset.test.mjs`
- Modify: `frontend/package.json:18`

**Interfaces:**

- Produces: `/og-card-v1.png`, a versioned 1200 × 630 RGB PNG below 1 MiB.
- Produces: four `data-market-window` groups and five `data-market-pill` groups in the editable SVG.
- Consumes: the exact visual copy and colors from the approved design specification.

- [ ] **Step 1: Write the failing asset contract**

Create `frontend/scripts/tests/og-card-asset.test.mjs`:

```js
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const svgUrl = new URL("../../design/og-card-v1.svg", import.meta.url);
const pngUrl = new URL("../../public/og-card-v1.png", import.meta.url);
const requiredCopy = [
  "EDWARD WANG / INDEPENDENT RESEARCH",
  "MULTI-MARKET",
  "WORKBENCH",
  "MARKETS · SIGNALS · EVIDENCE",
  "RESEARCH MATRIX / 04",
  "EQUITIES",
  "US / HK",
  "MAINLAND",
  "CN",
  "DIGITAL",
  "24 / 7",
  "BENCHMARKS",
  "INDEX",
];

function pngChunks(buffer) {
  const names = [];
  for (let offset = 8; offset + 12 <= buffer.length;) {
    const length = buffer.readUInt32BE(offset);
    const name = buffer.toString("ascii", offset + 4, offset + 8);
    names.push(name);
    offset += 12 + length;
    if (name === "IEND") {
      assert.equal(offset, buffer.length);
      break;
    }
  }
  return names;
}

test("editable SVG preserves the approved structure and copy", async () => {
  const svg = await readFile(svgUrl, "utf8");
  assert.match(
    svg,
    /<svg[^>]*width="1200"[^>]*height="630"[^>]*viewBox="0 0 1200 630"/,
  );
  for (const text of requiredCopy) assert.ok(svg.includes(text), text);
  assert.equal((svg.match(/data-market-window=/g) || []).length, 4);
  assert.equal((svg.match(/data-market-pill=/g) || []).length, 5);
  assert.doesNotMatch(
    svg,
    /<(?:image|foreignObject|script)\b|(?:xlink:)?href=|@font-face|@import|url\(\s*https?:/i,
  );
});

test("released PNG is complete and crawler-sized", async () => {
  const png = await readFile(pngUrl);
  assert.ok(png.length < 1_048_576);
  assert.deepEqual(
    [...png.subarray(0, 8)],
    [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a],
  );
  assert.equal(png.readUInt32BE(8), 13);
  assert.equal(png.toString("ascii", 12, 16), "IHDR");
  assert.equal(png.readUInt32BE(16), 1200);
  assert.equal(png.readUInt32BE(20), 630);
  assert.equal(png[24], 8);
  assert.ok([2, 6].includes(png[25]), "PNG must be RGB or RGBA");
  const chunks = pngChunks(png);
  assert.equal(chunks.at(-1), "IEND");
});
```

Append the asset test to `test:scripts`:

```json
"test:scripts": "node --test scripts/tests/build-profile-publication.test.mjs scripts/tests/og-card-asset.test.mjs scripts/tests/public-site-url.test.mjs scripts/tests/smoke-server.test.mjs"
```

- [ ] **Step 2: Run the asset test and verify the red state**

Run:

```bash
cd frontend
node --test scripts/tests/og-card-asset.test.mjs
```

Expected: FAIL with `ENOENT` for `design/og-card-v1.svg` and/or `public/og-card-v1.png`.

- [ ] **Step 3: Create the complete editable SVG**

Create `frontend/design/og-card-v1.svg` with this fixed structure. The approved copy contains no ampersand; do not introduce entity substitutions or replace the visible strings.

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"
  viewBox="0 0 1200 630" role="img"
  aria-label="Edward Wang Multi-Market Workbench share card">
  <defs>
    <radialGradient id="glow" cx="78%" cy="43%" r="42%">
      <stop offset="0" stop-color="#4c8dff" stop-opacity=".14"/>
      <stop offset="1" stop-color="#080c12" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="signal" x1="0" x2="1">
      <stop offset="0" stop-color="#26a69a"/>
      <stop offset=".52" stop-color="#4c8dff"/>
      <stop offset="1" stop-color="#4c8dff"/>
    </linearGradient>
    <pattern id="grid" width="54" height="54" patternUnits="userSpaceOnUse">
      <path d="M54 0H0V54" fill="none" stroke="#26313e"
        stroke-opacity=".25" stroke-width="1"/>
    </pattern>
    <clipPath id="frame-clip">
      <rect x="44.5" y="44.5" width="1111" height="541" rx="18"/>
    </clipPath>
  </defs>

  <rect width="1200" height="630" fill="#080c12"/>
  <rect width="1200" height="630" fill="url(#glow)"/>

  <g clip-path="url(#frame-clip)">
    <rect x="44.5" y="44.5" width="617" height="541" fill="#0d1219"/>
    <rect x="661.5" y="44.5" width="494" height="541" fill="#0a0f15"/>
    <rect x="661.5" y="44.5" width="494" height="541" fill="url(#grid)"/>
  </g>
  <rect x="44.5" y="44.5" width="1111" height="541" rx="18"
    fill="none" stroke="#2a3543"/>
  <line x1="661.5" y1="44.5" x2="661.5" y2="585.5"
    stroke="#2a3543"/>

  <g font-family="Menlo, Consolas, monospace">
    <text x="96" y="108" fill="#26a69a" font-size="14"
      font-weight="700" letter-spacing="2.2">
      EDWARD WANG / INDEPENDENT RESEARCH
    </text>
    <text x="96" y="225" fill="#f5f7f9"
      font-family="Arial, Helvetica, sans-serif" font-size="68"
      font-weight="800" letter-spacing="-3">
      <tspan x="96" dy="0">MULTI-MARKET</tspan>
      <tspan x="96" dy="64">WORKBENCH</tspan>
    </text>
    <text x="96" y="350" fill="#919dab" font-size="17"
      font-weight="700" letter-spacing="1.7">
      MARKETS · SIGNALS · EVIDENCE
    </text>

    <g data-market-pill="us" transform="translate(96 512)">
      <rect width="54" height="30" rx="15" fill="none" stroke="#344150"/>
      <text x="27" y="20" text-anchor="middle" fill="#7d8997"
        font-size="11" font-weight="700">US</text>
    </g>
    <g data-market-pill="hk" transform="translate(162 512)">
      <rect width="54" height="30" rx="15" fill="none" stroke="#344150"/>
      <text x="27" y="20" text-anchor="middle" fill="#7d8997"
        font-size="11" font-weight="700">HK</text>
    </g>
    <g data-market-pill="cn" transform="translate(228 512)">
      <rect width="54" height="30" rx="15" fill="none" stroke="#344150"/>
      <text x="27" y="20" text-anchor="middle" fill="#7d8997"
        font-size="11" font-weight="700">CN</text>
    </g>
    <g data-market-pill="crypto" transform="translate(294 512)">
      <rect width="88" height="30" rx="15" fill="none" stroke="#344150"/>
      <text x="44" y="20" text-anchor="middle" fill="#7d8997"
        font-size="11" font-weight="700">CRYPTO</text>
    </g>
    <g data-market-pill="index" transform="translate(394 512)">
      <rect width="78" height="30" rx="15" fill="none" stroke="#344150"/>
      <text x="39" y="20" text-anchor="middle" fill="#7d8997"
        font-size="11" font-weight="700">INDEX</text>
    </g>

    <text x="699.5" y="91" fill="#6f7c8c" font-size="13"
      font-weight="700" letter-spacing="2">RESEARCH MATRIX / 04</text>
    <path d="M699.5 111.5V274.5H1119" fill="none"
      stroke="#2a3543" stroke-width="1"/>
    <path d="M699.5 220 L742 202 L784 211 L829 172 L874 185
      L920 146 L967 160 L1015 119 L1066 137 L1119 110"
      fill="none" stroke="url(#signal)" stroke-width="4"
      stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="1015" cy="119" r="6" fill="#26a69a"/>

    <g data-market-window="equities" transform="translate(699.5 299.5)">
      <rect width="203.5" height="118.5" rx="12" fill="#080c12"
        fill-opacity=".94" stroke="#26a69a" stroke-opacity=".55"/>
      <circle cx="22" cy="28" r="4" fill="#26a69a"/>
      <text x="34" y="33" fill="#26a69a" font-size="12"
        font-weight="700" letter-spacing="1.5">EQUITIES</text>
      <text x="20" y="82" fill="#26a69a" font-size="22"
        font-weight="700">US / HK</text>
    </g>
    <g data-market-window="mainland" transform="translate(915.5 299.5)">
      <rect width="203.5" height="118.5" rx="12" fill="#080c12"
        fill-opacity=".94" stroke="#4c8dff" stroke-opacity=".55"/>
      <circle cx="22" cy="28" r="4" fill="#4c8dff"/>
      <text x="34" y="33" fill="#4c8dff" font-size="12"
        font-weight="700" letter-spacing="1.5">MAINLAND</text>
      <text x="20" y="82" fill="#4c8dff" font-size="22"
        font-weight="700">CN</text>
    </g>
    <g data-market-window="digital" transform="translate(699.5 430.5)">
      <rect width="203.5" height="118.5" rx="12" fill="#080c12"
        fill-opacity=".94" stroke="#ef5350" stroke-opacity=".52"/>
      <circle cx="22" cy="28" r="4" fill="#ef5350"/>
      <text x="34" y="33" fill="#ef5350" font-size="12"
        font-weight="700" letter-spacing="1.5">DIGITAL</text>
      <text x="20" y="82" fill="#ef5350" font-size="22"
        font-weight="700">24 / 7</text>
    </g>
    <g data-market-window="benchmarks" transform="translate(915.5 430.5)">
      <rect width="203.5" height="118.5" rx="12" fill="#080c12"
        fill-opacity=".94" stroke="#d8a64b" stroke-opacity=".55"/>
      <circle cx="22" cy="28" r="4" fill="#d8a64b"/>
      <text x="34" y="33" fill="#d8a64b" font-size="12"
        font-weight="700" letter-spacing="1.5">BENCHMARKS</text>
      <text x="20" y="82" fill="#d8a64b" font-size="22"
        font-weight="700">INDEX</text>
    </g>
  </g>
</svg>
```

- [ ] **Step 4: Export the PNG with an isolated local Chrome profile**

From the active worktree root, set the exact paths:

```bash
repo_root="$(git rev-parse --show-toplevel)"
profile_dir="$(mktemp -d /private/tmp/stock-analysis-og-chrome.XXXXXX)"
```

Run the local-only export. If the managed sandbox blocks Chrome output, request scoped approval for this command; do not add `--no-sandbox`.

```bash
'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --headless=new \
  --disable-background-networking \
  --disable-component-update \
  --disable-extensions \
  --no-first-run \
  --no-default-browser-check \
  --hide-scrollbars \
  --force-device-scale-factor=1 \
  --window-size=1200,630 \
  --user-data-dir="$profile_dir" \
  --screenshot="$repo_root/frontend/public/og-card-v1.png" \
  "file://$repo_root/frontend/design/og-card-v1.svg"
```

Expected: Chrome writes `frontend/public/og-card-v1.png` without contacting a remote origin.

- [ ] **Step 5: Run mechanical asset checks**

```bash
cd frontend
node --test scripts/tests/og-card-asset.test.mjs
file public/og-card-v1.png
sips -g pixelWidth -g pixelHeight -g hasAlpha -g format \
  public/og-card-v1.png
git diff --exit-code -- package-lock.json
```

Expected: test PASS; PNG 1200 × 630 with a fully painted background and below 1 MiB; lockfile unchanged. An RGBA encoding is acceptable only because the SVG paints the complete canvas and visual review confirms no transparency-dependent region.

- [ ] **Step 6: Inspect native and messaging-preview sizes**

Create a temporary scaled preview:

```bash
sips --resampleWidth 520 \
  frontend/public/og-card-v1.png \
  --out /private/tmp/stock-analysis-og-card-v1-520.png
```

Inspect both PNGs at original detail. Confirm:

- title is exactly two lines;
- owner and tagline are one line;
- all four windows are complete, equally sized, and legible;
- the right panel is a real visual anchor;
- no text, chart, pill, border, or window is clipped;
- no fifth window, watermark, duplicated domain, or unexpectedly empty region exists.

If any visual condition fails, change the SVG, regenerate the PNG, rerun the asset test, and repeat both inspections before proceeding.

- [ ] **Step 7: Commit Task 2**

```bash
git add frontend/design/og-card-v1.svg \
  frontend/public/og-card-v1.png \
  frontend/scripts/tests/og-card-asset.test.mjs \
  frontend/package.json
git commit -m "feat(frontend): add B3 share card asset"
```

Before committing, assert the staged set contains exactly those four paths and `frontend/package-lock.json` is unchanged.

---

### Task 3: Publish metadata and enforce it in both smoke profiles

**Files:**

- Create: `frontend/scripts/social-card-smoke.mjs`
- Create: `frontend/scripts/tests/social-card-smoke.test.mjs`
- Modify: `frontend/scripts/tests/smoke-server.test.mjs`
- Modify: `frontend/scripts/smoke-static.mjs:1-33`
- Modify: `frontend/scripts/smoke-server.mjs:1-189`
- Modify: `frontend/app/layout.tsx:1-26`
- Modify: `frontend/package.json:18`

**Interfaces:**

- Consumes: `resolvePublicSiteUrl()` from Task 1 and `/og-card-v1.png` from Task 2.
- Produces: `assertSocialMetadata(html: string, publicRoot: URL) -> URL`.
- Produces: `assertShareCardPng(value: Buffer | ArrayBuffer) -> Buffer`.
- Changes: `runSmoke({ shareCard?: { publicRoot: URL }, ... })`; omitted `shareCard` preserves the existing lifecycle-test surface.
- Publishes: one Open Graph and one Twitter/X metadata contract, both referencing `new URL("og-card-v1.png", PUBLIC_SITE_URL)`.

- [ ] **Step 1: Write focused failing tests for metadata parsing and PNG validation**

Create `frontend/scripts/tests/social-card-smoke.test.mjs`:

```js
import assert from "node:assert/strict";
import test from "node:test";
import {
  assertShareCardPng,
  assertSocialMetadata,
} from "../social-card-smoke.mjs";

const root = new URL("https://example.test/stock-analysis/");
const title = "Edward Wang · Multi-Market Workbench";
const description = "Markets, signals and evidence across global assets.";
const alt = "Edward Wang Multi-Market Workbench: markets, signals, and evidence across US, Hong Kong, mainland China, digital assets, and benchmarks.";

const metas = {
  "og:title": title,
  "og:description": description,
  "og:type": "website",
  "og:url": root.href,
  "og:site_name": title,
  "og:locale": "zh_CN",
  "og:image": new URL("og-card-v1.png", root).href,
  "og:image:width": "1200",
  "og:image:height": "630",
  "og:image:type": "image/png",
  "og:image:alt": alt,
  "twitter:card": "summary_large_image",
  "twitter:title": title,
  "twitter:description": description,
  "twitter:image": new URL("og-card-v1.png", root).href,
  "twitter:image:alt": alt,
};

function html(overrides = {}) {
  return Object.entries({ ...metas, ...overrides })
    .map(([key, value], index) => index % 2
      ? `<meta content="${value}" name="${key}">`
      : `<meta property="${key}" content="${value}">`)
    .join("");
}

function png(width = 1200, height = 630) {
  const value = Buffer.alloc(45);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
    .copy(value, 0);
  value.writeUInt32BE(13, 8);
  value.write("IHDR", 12, "ascii");
  value.writeUInt32BE(width, 16);
  value.writeUInt32BE(height, 20);
  value.writeUInt8(8, 24);
  value.writeUInt8(2, 25);
  value.writeUInt32BE(0, 33);
  value.write("IEND", 37, "ascii");
  return value;
}

test("complete metadata returns the public image URL", () => {
  assert.equal(
    assertSocialMetadata(html(), root).href,
    "https://example.test/stock-analysis/og-card-v1.png",
  );
});

test("missing, duplicate, or wrong metadata is rejected", () => {
  assert.throws(() => assertSocialMetadata("", root), /og:title/);
  assert.throws(
    () => assertSocialMetadata(`${html()}<meta property="og:title" content="${title}">`, root),
    /exactly once/,
  );
  assert.throws(
    () => assertSocialMetadata(html({ "og:image:width": "600" }), root),
    /og:image:width/,
  );
});

test("PNG dimensions are enforced", () => {
  assert.equal(assertShareCardPng(png()).readUInt32BE(16), 1200);
  assert.throws(() => assertShareCardPng(png(600, 315)), /1200/);
});
```

Append the focused test to `test:scripts`:

```json
"test:scripts": "node --test scripts/tests/build-profile-publication.test.mjs scripts/tests/og-card-asset.test.mjs scripts/tests/public-site-url.test.mjs scripts/tests/social-card-smoke.test.mjs scripts/tests/smoke-server.test.mjs"
```

- [ ] **Step 2: Run the focused test and verify the red state**

```bash
cd frontend
node --test scripts/tests/social-card-smoke.test.mjs
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `scripts/social-card-smoke.mjs`.

- [ ] **Step 3: Implement the shared smoke assertions**

Create `frontend/scripts/social-card-smoke.mjs`. Parse every `<meta>` tag by attribute name rather than attribute order, and assert each required key occurs exactly once:

```js
import assert from "node:assert/strict";

export const SHARE_TITLE = "Edward Wang · Multi-Market Workbench";
export const SHARE_DESCRIPTION =
  "Markets, signals and evidence across global assets.";
export const SHARE_IMAGE_ALT =
  "Edward Wang Multi-Market Workbench: markets, signals, and evidence across US, Hong Kong, mainland China, digital assets, and benchmarks.";

function attributes(tag) {
  return Object.fromEntries(
    [...tag.matchAll(/([A-Za-z_:][A-Za-z0-9_:.-]*)=(["'])(.*?)\2/g)]
      .map((match) => [match[1], match[3]]),
  );
}

function metaValues(html, key) {
  return [...html.matchAll(/<meta\b[^>]*>/gi)]
    .map((match) => attributes(match[0]))
    .filter((value) => value.property === key || value.name === key)
    .map((value) => value.content);
}

function requireMeta(html, key, expected) {
  const values = metaValues(html, key);
  assert.equal(values.length, 1, `${key} must appear exactly once`);
  assert.equal(values[0], expected, `${key} content`);
}

export function assertSocialMetadata(html, publicRoot) {
  const root = publicRoot instanceof URL ? publicRoot : new URL(publicRoot);
  const image = new URL("og-card-v1.png", root);
  const expected = {
    "og:title": SHARE_TITLE,
    "og:description": SHARE_DESCRIPTION,
    "og:type": "website",
    "og:url": root.href,
    "og:site_name": SHARE_TITLE,
    "og:locale": "zh_CN",
    "og:image": image.href,
    "og:image:width": "1200",
    "og:image:height": "630",
    "og:image:type": "image/png",
    "og:image:alt": SHARE_IMAGE_ALT,
    "twitter:card": "summary_large_image",
    "twitter:title": SHARE_TITLE,
    "twitter:description": SHARE_DESCRIPTION,
    "twitter:image": image.href,
    "twitter:image:alt": SHARE_IMAGE_ALT,
  };
  for (const [key, value] of Object.entries(expected)) {
    requireMeta(html, key, value);
  }
  return image;
}

export function assertShareCardPng(value) {
  const buffer = Buffer.isBuffer(value) ? value : Buffer.from(value);
  assert.ok(buffer.length < 1_048_576, "share card must be below 1 MiB");
  assert.deepEqual(
    [...buffer.subarray(0, 8)],
    [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a],
    "share card PNG signature",
  );
  assert.equal(buffer.readUInt32BE(8), 13, "share card IHDR length");
  assert.equal(buffer.toString("ascii", 12, 16), "IHDR");
  assert.equal(buffer.readUInt32BE(16), 1200, "share card width");
  assert.equal(buffer.readUInt32BE(20), 630, "share card height");
  return buffer;
}
```

- [ ] **Step 4: Run the focused test and verify it passes**

```bash
cd frontend
node --test scripts/tests/social-card-smoke.test.mjs
```

Expected: all metadata and PNG helper tests PASS.

- [ ] **Step 5: Extend static and server smoke checks before adding metadata**

In `frontend/scripts/smoke-static.mjs`:

- import `resolvePublicSiteUrl`, `assertShareCardPng`, and `assertSocialMetadata`;
- keep the existing 12-route and `basePath/_next` assertions;
- resolve the expected public root independently;
- run `assertSocialMetadata(index, publicRoot)`;
- read `out/og-card-v1.png` and run `assertShareCardPng`.

Use:

```js
const publicRoot = resolvePublicSiteUrl();
assertSocialMetadata(index, publicRoot);
const card = await readFile(new URL("../out/og-card-v1.png", import.meta.url));
assertShareCardPng(card);
```

In `frontend/scripts/smoke-server.mjs`:

- add `shareCard` to `runSmoke()` options, defaulting to `undefined`;
- retain the `/` response body while iterating routes;
- when `shareCard` is present, assert metadata in that body;
- remap the public image pathname to the discovered local origin;
- fetch it with the existing timeout and child-failure race;
- read it through `response.arrayBuffer()`;
- assert status 200, `image/png`, and `assertShareCardPng`;
- enable the contract only in the CLI entry:

```js
await runSmoke({
  shareCard: { publicRoot: resolvePublicSiteUrl() },
});
```

Add two focused cases to `frontend/scripts/tests/smoke-server.test.mjs`:

1. a local fixture serving complete meta HTML and a synthetic 1200 × 630 PNG header passes with `shareCard` enabled;
2. a fixture with missing `og:title` or a 600 × 315 IHDR rejects, and cleanup still reaps the child.

Do not enable `shareCard` by default inside `runSmoke`; the existing lifecycle fixtures intentionally serve minimal HTML.

- [ ] **Step 6: Run the build smoke and verify it fails for missing metadata**

```bash
cd frontend
NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/stock-analysis/ \
  npm run build:static
NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/stock-analysis/ \
  npm run smoke:static
```

Expected: build succeeds, then smoke FAILS on the first missing `og:*` key.

- [ ] **Step 7: Add the root metadata without changing browser title semantics**

Update `frontend/app/layout.tsx`:

```tsx
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
  description:
    "美股 · 港股 · A股 · 加密 · 指数 实时行情,主力资金 / 筹码 / 缠论等非 LLM 技术分析,价格提醒,零成本静态部署",
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
```

Keep the existing `viewport` and `RootLayout` bodies unchanged.

- [ ] **Step 8: Run all focused and dual-profile checks**

```bash
cd frontend
npm run lint
npm run typecheck
npm run test:scripts

NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run build:static
NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run smoke:static

NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/stock-analysis/ \
  npm run build:static
NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/stock-analysis/ \
  npm run smoke:static

NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run build:server
NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run smoke:server
```

Expected: lint, typecheck, scripts, both static variants, and server build/smoke all exit 0. Static output retains `out/og-card-v1.png`; server smoke fetches the local image path while asserting the absolute public metadata URL.

- [ ] **Step 9: Commit Task 3**

```bash
git add frontend/scripts/social-card-smoke.mjs \
  frontend/scripts/tests/social-card-smoke.test.mjs \
  frontend/scripts/tests/smoke-server.test.mjs \
  frontend/scripts/smoke-static.mjs \
  frontend/scripts/smoke-server.mjs \
  frontend/app/layout.tsx \
  frontend/package.json
git commit -m "feat(frontend): publish social share metadata"
```

Assert those seven paths are the complete staged set and `frontend/package-lock.json` is unchanged.

---

### Task 4: Lock CI, Pages, configuration, and workflow documentation together

**Files:**

- Modify: `scripts/tests/test_workflow_security.py`
- Modify: `.github/workflows/tests.yml:30-72`
- Modify: `.github/workflows/deploy-pages.yml:63-72`
- Modify: `docs/configuration.md`
- Modify: `docs/operations/workflows.md`
- Modify: `docs/verification.json`

**Interfaces:**

- Consumes: `NEXT_PUBLIC_SITE_URL` and the three verified frontend build cases.
- Produces: exact CI matrix rows `static-root`, `static-pages`, and `server-root`.
- Produces: GitHub Pages application root `https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/`.
- Documents: Vercel system inputs `VERCEL_PROJECT_PRODUCTION_URL` and `VERCEL_URL`.

- [ ] **Step 1: Update the exact workflow tests first**

In `scripts/tests/test_workflow_security.py`, change `FRONTEND_STRATEGY_LINES` to:

```python
FRONTEND_STRATEGY_LINES = [
    "      fail-fast: false",
    "      matrix:",
    "        include:",
    "          - case: static-root",
    "            profile: static",
    '            base_path: ""',
    "            site_url: https://stock-analysis.example.test/",
    "          - case: static-pages",
    "            profile: static",
    "            base_path: /stock-analysis",
    "            site_url: https://stock-analysis.example.test/stock-analysis/",
    "          - case: server-root",
    "            profile: server",
    '            base_path: ""',
    "            site_url: https://stock-analysis.example.test/",
]
```

Change `FRONTEND_ENV_LINES` to include:

```python
"      NEXT_PUBLIC_SITE_URL: ${{ matrix.site_url }}",
```

Update `EXPECTED_PAGES_WORKFLOW` and the structural Pages policy so the build-step environment contains, in this order:

```yaml
STATIC_FEED_SOURCE: ${{ runner.temp }}/feed-snapshot
NEXT_PUBLIC_BASE_PATH: /${{ github.event.repository.name }}
NEXT_PUBLIC_SITE_URL: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/
NEXT_PUBLIC_API_BASE: ${{ vars.API_BASE }}
NEXT_PUBLIC_EDGE_BASE: ${{ vars.EDGE_BASE }}
NEXT_PUBLIC_FEED_BASE: https://raw.githubusercontent.com/${{ github.repository }}/${{ github.ref_name }}/feed
```

Update `test_tests_workflow_frontend_matrix_and_steps_are_scoped` to parse `case`, `profile`, `base_path`, and `site_url` together and expect:

```python
[
    (
        "static-root",
        "static",
        '""',
        "https://stock-analysis.example.test/",
    ),
    (
        "static-pages",
        "static",
        "/stock-analysis",
        "https://stock-analysis.example.test/stock-analysis/",
    ),
    (
        "server-root",
        "server",
        '""',
        "https://stock-analysis.example.test/",
    ),
]
```

Also assert:

```python
self.assertIn(
    "      NEXT_PUBLIC_SITE_URL: ${{ matrix.site_url }}",
    frontend,
)
```

The existing exact-policy mutation framework must reject deletion, localhost replacement, or a base-path-mismatched replacement of either workflow’s site URL.

- [ ] **Step 2: Run the workflow tests and verify the red state**

Run with the repository’s pinned Python 3.11 path:

```bash
scripts/run-python311 python scripts/tests/test_workflow_security.py
```

Expected: FAIL because `.github/workflows/tests.yml` and `deploy-pages.yml` still have the old matrix/environment contract.

- [ ] **Step 3: Update the CI matrix**

In `.github/workflows/tests.yml`, use:

```yaml
frontend:
  name: Frontend (${{ matrix.case }})
  runs-on: ubuntu-latest
  strategy:
    fail-fast: false
    matrix:
      include:
        - case: static-root
          profile: static
          base_path: ""
          site_url: https://stock-analysis.example.test/
        - case: static-pages
          profile: static
          base_path: /stock-analysis
          site_url: https://stock-analysis.example.test/stock-analysis/
        - case: server-root
          profile: server
          base_path: ""
          site_url: https://stock-analysis.example.test/
```

Add to the existing frontend job environment:

```yaml
NEXT_PUBLIC_SITE_URL: ${{ matrix.site_url }}
```

Leave the current profile-specific build/smoke `if` conditions unchanged.

- [ ] **Step 4: Supply the real Pages public root**

Add this next to `NEXT_PUBLIC_BASE_PATH` in the Pages build/smoke step:

```yaml
NEXT_PUBLIC_SITE_URL: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/
```

Do not change permissions, checkout credentials, feed snapshot behavior, artifact upload, deployment job, or concurrency.

- [ ] **Step 5: Update configuration and workflow authorities**

In `docs/configuration.md`:

- add `NEXT_PUBLIC_SITE_URL` to the frontend table as the complete public application root, including a repository path and trailing slash when applicable;
- state that explicit config wins, then `VERCEL_PROJECT_PRODUCTION_URL`, then `VERCEL_URL`, then local fallback;
- state that CI, GitHub Actions, and Vercel builds fail without a non-local public root;
- add `CI`, `GITHUB_ACTIONS`, `VERCEL`, `VERCEL_PROJECT_PRODUCTION_URL`, and `VERCEL_URL` to the platform-provided table, including the exact deployment-flag values used by the resolver;
- update the static example:

```bash
NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://edwardwang66.github.io/stock-analysis/ \
STATIC_FEED_SOURCE=/absolute/path/to/feed-snapshot \
  npm run build:static
```

In `docs/operations/workflows.md`:

- add the computed Pages public site URL to the `deploy-pages.yml` configuration cell;
- state that the frontend CI matrix covers static root, static repository path, and server root with non-local test origins.

In `docs/verification.json`, add these platform-provided names:

```json
"CI",
"GITHUB_ACTIONS",
"VERCEL",
"VERCEL_PROJECT_PRODUCTION_URL",
"VERCEL_URL"
```

Stamp only the two modified maintained Markdown authorities to the current pre-Task-4 HEAD:

```bash
scripts/run-python311 python scripts/check_docs.py \
  --stamp-current \
  --document docs/configuration.md \
  --document docs/operations/workflows.md
```

- [ ] **Step 6: Run workflow and documentation gates**

```bash
scripts/run-python311 python scripts/tests/test_workflow_security.py
scripts/run-python311 python scripts/tests/test_check_docs.py
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: workflow security PASS; documentation tests report 72/72; documentation checker passes with all discovered environment names documented; diff check is empty.

- [ ] **Step 7: Commit Task 4**

```bash
git add scripts/tests/test_workflow_security.py \
  .github/workflows/tests.yml \
  .github/workflows/deploy-pages.yml \
  docs/configuration.md \
  docs/operations/workflows.md \
  docs/verification.json
git commit -m "ci(frontend): verify social metadata across profiles"
```

Assert those six paths are the complete staged set.

---

### Task 5: Run the complete local acceptance gate

**Files:**

- Verify only; no planned file changes.

**Interfaces:**

- Consumes: Tasks 1–4.
- Produces: exact local evidence for code, asset, both static mounts, server runtime, workflows, docs, and repository cleanliness.

- [ ] **Step 1: Verify the isolated worktree and runtime**

```bash
test "$(node --version)" = "v20.20.2"
test "$(npm --version)" = "10.8.2"
test "$(python --version 2>&1)" = "Python 3.11.15"
git status --short --branch
```

If the host runtimes do not match, run the repository’s controlled Node/Python gates in their approved containers. Any network-capable `npm ci` or image pull with private source mounted requires the explicit approval flow; do not substitute a different runtime and call it equivalent.

- [ ] **Step 2: Run the full frontend gate**

From `frontend/`:

```bash
npm ci
npm run lint
npm run typecheck
npm run test:scripts
```

Then run all three build cases:

```bash
NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run build:static
NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run smoke:static

NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/stock-analysis/ \
  npm run build:static
NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/stock-analysis/ \
  npm run smoke:static

NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run build:server
NEXT_PUBLIC_BASE_PATH= \
NEXT_PUBLIC_SITE_URL=https://stock-analysis.example.test/ \
  npm run smoke:server
```

Expected: every command exits 0; both static cases report 12 rendered routes and valid share metadata; server reports 11 UI routes, two expected API 400 checks, complete social metadata, and a valid local PNG response.

- [ ] **Step 3: Run repository workflow and documentation gates**

From the repository root:

```bash
scripts/run-python311 python scripts/tests/test_workflow_security.py
scripts/run-python311 python scripts/tests/test_check_docs.py
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: workflow security passes, documentation tests report 72/72, documentation checker passes, and no whitespace errors exist.

- [ ] **Step 4: Repeat native and 520-pixel visual inspection**

Inspect:

- `frontend/public/og-card-v1.png` at original size;
- `/private/tmp/stock-analysis-og-card-v1-520.png` at original size.

Apply every visual acceptance point from Task 2. Do not infer visual correctness from metadata tests.

- [ ] **Step 5: Audit final diff and commits**

```bash
git status --short --branch
git log --oneline --decorate -5
git diff "$(git merge-base HEAD main)"..HEAD --stat
git diff "$(git merge-base HEAD main)"..HEAD --check
git diff --exit-code -- frontend/package-lock.json
```

Expected: only planned commits/files exist; no `.superpowers/`, `AGENTS.md`, generated `frontend/out`, `.next`, temporary preview, or lockfile change is tracked.

Stop and report any failed gate. Do not commit a “verification fix” without returning to the owning task’s red/green cycle.

---

### Task 6: Integrate, publish, and verify both live URLs after explicit authorization

**Files:**

- No planned repository changes.

**Interfaces:**

- Consumes: a green Task 5 and explicit user approval to push/deploy.
- Produces: verified Vercel and GitHub Pages root metadata, public PNG responses, deployment evidence, and one real unfurl observation.

- [ ] **Step 1: Present the exact publication scope and request approval**

Report:

- branch and commit list;
- exact changed-file list;
- all Task 5 results;
- cached versus live `origin/main` ancestry;
- Vercel’s configured Node runtime separately from the repository’s Node 20.20.2 contract.

Ask for explicit approval to fast-forward the tested feature branch into local `main` and push `main`. Do not treat plan approval, test approval, or a previous merge instruction as current publication authority.

- [ ] **Step 2: Reconcile the live remote and fast-forward local main only after approval**

```bash
git fetch origin main
git rev-list --left-right --count \
  origin/main...codex/open-graph-share-card
git log --oneline --decorate \
  origin/main..codex/open-graph-share-card
git -C /Users/edwardwang/Documents/stock-analysis \
  status --short --branch
git -C /Users/edwardwang/Documents/stock-analysis \
  merge --ff-only codex/open-graph-share-card
```

Expected: live ancestry is understood; the main checkout has no tracked edits; `.superpowers/` and `AGENTS.md` remain untouched; local `main` fast-forwards to the exact tested feature tip. If `origin/main` has advanced outside that ancestry, stop and reconcile explicitly rather than force-pushing or silently creating a merge.

- [ ] **Step 3: Push the exact tested main tip**

```bash
git -C /Users/edwardwang/Documents/stock-analysis push origin main
```

Expected: push succeeds without force and the remote main SHA equals the tested local main SHA.

- [ ] **Step 4: Wait for both deployment paths**

- Inspect the Vercel deployment created from the pushed commit and wait for terminal `READY` or an actionable failure.
- Inspect the GitHub Pages workflow run created from the same commit and wait for the build and deploy jobs.
- Do not change Vercel project settings, aliases, Node version, or environment variables as an implicit repair. Report any runtime mismatch or failed workflow first.

- [ ] **Step 5: Verify Vercel and GitHub Pages as public crawlers**

For each live root:

- `https://stock-analysis-ten-phi.vercel.app/`
- `https://edwardwang66.github.io/stock-analysis/`

Fetch with a normal browser user agent and at least:

```text
facebookexternalhit/1.1
Twitterbot/1.0
```

Verify:

- root status 200;
- no authentication, challenge, or bot-block page;
- the complete Open Graph and Twitter/X contract from Task 3;
- `og:url` matches that deployment’s configured public root;
- `og:image` and `twitter:image` are identical absolute HTTPS URLs;
- the image response is status 200 and `image/png`;
- the live image is below 1 MiB and 1200 × 630;
- cache headers are present and do not prevent crawler retrieval.

- [ ] **Step 6: Verify one real unfurl and separate cache behavior**

Paste a live root URL into one real messaging-client or official preview inspector. If an old card is cached:

1. verify current HTML and PNG first;
2. request a platform re-scrape when supported;
3. test a query-distinct share URL such as `?og=v1` without changing the canonical metadata;
4. report the stale cache separately from current deployment correctness.

Expected: the preview uses the B3 image, title `Edward Wang · Multi-Market Workbench`, and description `Markets, signals and evidence across global assets.`.

- [ ] **Step 7: Report the final publication evidence**

Report the pushed commit, Vercel deployment/alias, Pages workflow/run, both live metadata/image checks, the real unfurl result, cache caveats, and the observed Vercel Node runtime. Do not call the feature fully live if either hosting path or the real unfurl remains unverified.
