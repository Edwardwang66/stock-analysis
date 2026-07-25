import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";

const pages = [
  "index.html",
  "alerts/index.html",
  "desk/index.html",
  "help/index.html",
  "intel/index.html",
  "portfolio/index.html",
  "reports/index.html",
  "screener/index.html",
  "sources/index.html",
  "symbol/index.html",
  "tracker/index.html",
  "404.html",
];

for (const page of pages) {
  const file = new URL(`../out/${page}`, import.meta.url);
  await stat(file);
  const html = await readFile(file, "utf8");
  assert.match(html, /^<!DOCTYPE html>/i, `${page} must be rendered HTML`);
}

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const index = await readFile(new URL("../out/index.html", import.meta.url), "utf8");
assert.ok(
  index.includes(`${basePath}/_next/`),
  `exported assets must use basePath "${basePath}"`,
);

console.log(`static smoke: ${pages.length} routes OK`);
