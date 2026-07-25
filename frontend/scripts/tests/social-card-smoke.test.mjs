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
