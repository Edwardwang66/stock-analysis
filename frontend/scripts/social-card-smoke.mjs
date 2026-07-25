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
