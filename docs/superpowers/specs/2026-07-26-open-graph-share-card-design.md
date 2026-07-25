# Open Graph 分享卡片设计

> **Status:** Accepted
> **Scope:** Root-site Open Graph and Twitter/X metadata, a deterministic share-card asset, and verification for the static and server profiles.
> **Last verified commit:** `ffca3728f3d9be8ebeb7f9231d618ab6f2ec9e7a`

- Date: 2026-07-26
- Approved direction: B3, “Signal Terminal — 四窗口回归”
- Review gate: written specification awaiting user confirmation before implementation planning

## 1. Decision summary

The stock-analysis root site will publish one deterministic 1200 × 630 social card for link previews. The card identifies both the author and the product:

- owner: `EDWARD WANG / INDEPENDENT RESEARCH`;
- product: `MULTI-MARKET WORKBENCH`;
- promise: `MARKETS · SIGNALS · EVIDENCE`.

The left side carries the identity and two-line product title. The right side carries a compact research chart and four small market windows. Those four windows are the primary product cue and must remain readable in a typical messaging-app preview.

The released card will be a versioned static PNG with a committed editable SVG source. The image is not generated from live data and is not rendered at request time. This keeps the exact approved pixels stable across Vercel and GitHub Pages while retaining a reviewable source asset.

Both supported runtime profiles remain first-class:

1. Vercel/server builds expose the image and absolute metadata through the production site URL.
2. GitHub Pages/static builds emit the same card and metadata under the configured repository base path.

## 2. Current state

The root layout currently publishes a title, description, manifest, and viewport settings. It does not publish `og:*` metadata, a large Twitter card, or a social image.

The frontend has two build profiles:

- `NEXT_BUILD_PROFILE=server` for Vercel or self-hosted Next.js;
- `NEXT_BUILD_PROFILE=static` for GitHub Pages and other static hosts.

Static builds may also set `NEXT_PUBLIC_BASE_PATH`, so image URLs cannot assume that the application is mounted at `/`.

The approved preview is a design artifact only. Files under `.superpowers/` are temporary brainstorming output and are not implementation inputs or commit candidates.

## 3. Goals and non-goals

### 3.1 Goals

- Make a shared root URL produce a large, intentional preview card in messaging and social clients that support Open Graph or Twitter card metadata.
- Preserve the approved B3 hierarchy at both native size and reduced preview size.
- Emit absolute, crawler-accessible metadata URLs for Vercel and GitHub Pages.
- Keep the card deterministic and independent of live market data, remote assets, fonts, or runtime image generation.
- Verify the metadata, public asset response, image dimensions, base-path behavior, and both build profiles.
- Reuse one versioned PNG for Open Graph and Twitter/X so the two previews cannot drift.

### 3.2 Non-goals

- Generating a different image for every page, symbol, report, or market.
- Showing current prices, returns, recommendations, or other claims that can become stale.
- Redesigning the dashboard itself.
- Adding a logo system, animation, share button, analytics, or social-platform SDK.
- Guaranteeing identical unfurl chrome across chat applications; each client controls the text and framing around the supplied image.
- Solving social-platform cache invalidation beyond publishing stable metadata and a versioned image URL.

## 4. Approved visual specification

### 4.1 Canvas and composition

- Canvas: exactly 1200 × 630 pixels.
- Background: near-black `#080c12`.
- Outer frame: inset on all sides with a visible safe margin; dark panel `#0d1219`, fine border `#2a3543`, and restrained rounded corners.
- Main split: approximately 55.5% identity panel and 44.5% research panel.
- All visible text and strokes remain inside the inner frame. Nothing may be clipped at 1200 × 630.
- The editable SVG uses fixed pixel coordinates and local vector primitives. The released PNG does not depend on browser layout, runtime CSS, or external assets.

### 4.2 Left identity panel

The copy is exact:

```text
EDWARD WANG / INDEPENDENT RESEARCH

MULTI-MARKET
WORKBENCH

MARKETS · SIGNALS · EVIDENCE
```

Requirements:

- `MULTI-MARKET WORKBENCH` is always exactly two lines.
- The owner line is one line at native size.
- The tagline is one line at native size.
- The title is the strongest element on the card.
- Five small market pills read `US`, `HK`, `CN`, `CRYPTO`, and `INDEX`; they are supporting detail and must not compete with the title or four windows.

### 4.3 Right research panel

The panel contains:

1. the label `RESEARCH MATRIX / 04`;
2. one decorative line chart with no axes, dates, prices, or implied live value;
3. a two-by-two set of four windows:

| Window | Label | Value | Accent |
| --- | --- | --- | --- |
| 1 | `EQUITIES` | `US / HK` | teal `#26a69a` |
| 2 | `MAINLAND` | `CN` | blue `#4c8dff` |
| 3 | `DIGITAL` | `24 / 7` | red `#ef5350` |
| 4 | `BENCHMARKS` | `INDEX` | amber `#d8a64b` |

The windows are the right panel’s visual anchor. All four must be complete, equally sized, and legible in a roughly 520-pixel-wide link preview. There is no fifth window, author watermark, footer handle, or duplicated domain inside the image.

### 4.4 Typography and accessibility

- The editable source uses `Arial`/`Helvetica`/sans-serif for the heavy title and `Menlo`/`Consolas`/monospace for compact supporting copy.
- The released PNG contains rasterized text and never fetches a font. Regeneration on a machine with different fonts requires visual reapproval before replacing the PNG.
- Contrast must remain clear against the dark background.
- Open Graph and Twitter/X images use meaningful alt text:

  `Edward Wang Multi-Market Workbench: markets, signals, and evidence across US, Hong Kong, mainland China, digital assets, and benchmarks.`

## 5. Metadata and asset architecture

### 5.1 Versioned static asset

The implementation adds:

- `frontend/design/og-card-v1.svg` as the editable, reviewable source;
- `frontend/public/og-card-v1.png` as the released 1200 × 630 crawler asset.

The PNG is the release authority. It is exported once from the approved SVG, visually reviewed, and committed. Regeneration is an explicit design-maintenance step rather than part of every application build. The asset is below 1 MiB, contains no transparency-dependent content, and uses a versioned filename so a later visual revision can publish a new URL instead of relying on social-cache invalidation.

Both Open Graph and Twitter/X metadata point to this exact file. There are no image route handlers, Edge-runtime requirements, duplicated card components, or build-time font downloads.

### 5.2 Root metadata

The existing browser title and general Chinese page description remain unchanged. The root metadata additionally publishes this share-specific contract:

- share title: `Edward Wang · Multi-Market Workbench`;
- share description: `Markets, signals and evidence across global assets.`;
- Open Graph type `website`, site name `Edward Wang · Multi-Market Workbench`, locale `zh_CN`, title, description, root URL, and the versioned image with explicit dimensions, MIME type, and alt text;
- Twitter/X card type `summary_large_image`, title, description, and the same versioned image;
- a `metadataBase` derived from the public application URL.

This confines the change to link sharing rather than silently renaming every browser tab or route.

### 5.3 Public URL resolution

One small URL resolver determines the external application root in this order:

1. explicit `NEXT_PUBLIC_SITE_URL`;
2. Vercel’s stable `VERCEL_PROJECT_PRODUCTION_URL`;
3. Vercel’s deployment `VERCEL_URL`;
4. `http://localhost:3000/`, composed with `NEXT_PUBLIC_BASE_PATH` when present, for local development and verification.

Rules:

- accepted public URLs use `http:` or `https:` only;
- release values contain no credentials, query, or fragment;
- the returned application root has one trailing slash;
- a GitHub Pages value includes the repository path, for example `https://edwardwang66.github.io/stock-analysis/`;
- `NEXT_PUBLIC_BASE_PATH` and the configured public URL must describe the same mount point;
- authorized deployed metadata must never resolve to localhost.

The GitHub Pages workflow supplies its full public application URL. Vercel may use the stable system-provided production URL unless an explicit custom domain is configured later through `NEXT_PUBLIC_SITE_URL`.

## 6. Data flow and failure behavior

At build time:

1. the URL resolver selects and validates the public application root;
2. the root layout emits Open Graph and Twitter/X text metadata;
3. the layout composes an absolute URL for `og-card-v1.png`;
4. the standard Next.js public-asset pipeline copies or serves the committed PNG;
5. both metadata families reference that same public file.

Failure rules:

- invalid explicit production URL configuration fails the build with an actionable error;
- missing Vercel system variables may fall back locally only for development or local verification;
- the application build does not regenerate or mutate the approved image;
- a missing, oversized, malformed, or wrongly dimensioned image fails the relevant smoke test;
- if a platform omits the image despite valid public HTML and PNG responses, report that as a platform cache/crawler issue rather than changing the visual contract blindly.

## 7. Verification strategy

### 7.1 Contract and configuration tests

Tests cover:

- public URL source precedence;
- URL normalization and rejection of unsafe or malformed release values;
- GitHub Pages repository base-path composition;
- Vercel production URL composition;
- exact share title, share description, card type, image alt text, image filename, MIME type, and dimensions.

### 7.2 Static-profile verification

After `build:static`:

- `out/index.html` contains the expected `og:title`, `og:description`, `og:type`, `og:url`, `og:image`, `twitter:card`, `twitter:title`, `twitter:description`, and `twitter:image` tags;
- metadata image URLs use the configured public application root and repository base path;
- `out/og-card-v1.png` exists and is below 1 MiB;
- the file has a valid PNG signature and a 1200 × 630 IHDR;
- the existing static route smoke suite still passes with an empty and a non-empty base path.

### 7.3 Server-profile verification

After `build:server`:

- the root route returns the same metadata contract;
- the image path returns status 200 and `image/png`;
- the fetched PNG is below 1 MiB and is 1200 × 630;
- existing page and API smoke checks still pass.

### 7.4 Visual verification

Render the released PNG, not the HTML brainstorm mockup, and inspect it:

- at native 1200 × 630;
- inside a roughly 520-pixel-wide messaging preview;
- with the full image visible rather than cropped by the test harness.

Acceptance requires:

- the title is exactly two lines;
- owner and tagline do not wrap;
- all four windows are present, complete, and legible;
- no panel, chart stroke, pill, or text is clipped;
- the right panel is neither compressed into a narrow strip nor reduced to empty decoration;
- there is no unexpected large empty region.

### 7.5 Production verification

After an authorized deployment:

- fetch the production root as a normal browser and as a common social crawler user agent;
- confirm status 200 and public access without authentication or challenge pages;
- resolve and fetch every emitted image URL;
- verify content type, dimensions, and cache headers;
- test at least one real messaging-client unfurl or official preview inspector;
- distinguish a stale cached unfurl from incorrect current metadata.

## 8. Planned file scope

Add:

- `frontend/design/og-card-v1.svg`;
- `frontend/public/og-card-v1.png`;
- `frontend/lib/public-site-url.mjs`;
- `frontend/scripts/tests/public-site-url.test.mjs`.

Modify:

- `frontend/app/layout.tsx`;
- `frontend/scripts/smoke-static.mjs`;
- `frontend/scripts/smoke-server.mjs`;
- `frontend/package.json` to register the focused test;
- `.github/workflows/tests.yml` to provide test public URLs for both base-path cases;
- `.github/workflows/deploy-pages.yml` to provide the GitHub Pages public application URL;
- `docs/configuration.md` to document `NEXT_PUBLIC_SITE_URL`.

No feed, market-data, analysis, backend, watchlist, or alert behavior is in scope.

## 9. Risks and safeguards

- **Source/export drift:** visually review the released PNG and assert its dimensions, size, and filename; the PNG, not an implicit runtime render, is the release authority.
- **Text clipping at preview size:** fixed copy, explicit widths, and safe margins are acceptance conditions.
- **Static base-path drift:** exercise both root and repository-path builds in tests.
- **Wrong absolute origin:** centralize URL resolution and assert that release metadata cannot point to localhost.
- **Open Graph/Twitter drift:** both metadata objects reference the same image constant.
- **Stale social cache:** the versioned asset filename limits drift, but a platform may still require a re-scrape.
- **Deployment runtime drift:** local verification uses the repository’s pinned Node/npm contract; production verification must also report the configured Vercel runtime rather than assuming parity.

## 10. Definition of done

This feature is complete only when:

1. the released PNG matches the approved B3 visual requirements;
2. Open Graph and Twitter/X metadata are present and point to the same public 1200 × 630 PNG;
3. static and server profile checks pass;
4. base-path and public-origin tests pass;
5. the current dashboard behavior is unchanged;
6. an authorized production deployment is publicly fetchable and produces a real link preview;
7. no `.superpowers/` artifact or unrelated `AGENTS.md` file is included in the feature commit.
