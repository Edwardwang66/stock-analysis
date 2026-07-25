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
