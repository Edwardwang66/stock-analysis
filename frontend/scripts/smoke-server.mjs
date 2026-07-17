import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { setTimeout as delay } from "node:timers/promises";

const port = Number(process.env.SMOKE_PORT || "3100");
assert.ok(Number.isInteger(port) && port > 0 && port < 65536, "invalid SMOKE_PORT");

const origin = `http://127.0.0.1:${port}`;
const routes = [
  "/",
  "/alerts/",
  "/desk/",
  "/help/",
  "/intel/",
  "/portfolio/",
  "/reports/",
  "/screener/",
  "/sources/",
  "/symbol/",
  "/tracker/",
];

const server = spawn(
  process.execPath,
  [
    "node_modules/next/dist/bin/next",
    "start",
    "--hostname",
    "127.0.0.1",
    "--port",
    String(port),
  ],
  {
    cwd: new URL("..", import.meta.url),
    stdio: "inherit",
    env: {
      ...process.env,
      NEXT_BUILD_PROFILE: "server",
      NEXT_PUBLIC_BASE_PATH: "",
      NEXT_TELEMETRY_DISABLED: "1",
      NODE_ENV: "production",
    },
  },
);

async function waitUntilReady() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (server.exitCode !== null) {
      throw new Error(`next start exited early with ${server.exitCode}`);
    }
    try {
      const response = await fetch(origin);
      if (response.status === 200) return;
    } catch {
      // The local server is still starting.
    }
    await delay(250);
  }
  throw new Error("next start did not become ready within 30 seconds");
}

async function stopServer() {
  if (server.exitCode !== null) return;
  const exited = once(server, "exit");
  server.kill("SIGTERM");
  const stoppedGracefully = await Promise.race([
    exited.then(() => true),
    delay(5_000).then(() => false),
  ]);
  if (!stoppedGracefully && server.exitCode === null) {
    server.kill("SIGKILL");
    await exited;
  }
}

try {
  await waitUntilReady();
  for (const route of routes) {
    const response = await fetch(`${origin}${route}`);
    assert.equal(response.status, 200, `${route} status`);
    assert.match(
      response.headers.get("content-type") || "",
      /^text\/html/i,
      `${route} content type`,
    );
    assert.match(await response.text(), /<html/i, `${route} document`);
    console.log(`PASS server ${route}`);
  }
  for (const [route, expectedError] of [
    ["/api/quote", "symbols required"],
    ["/api/ohlcv?symbol=BAD:X", "unsupported market BAD"],
  ]) {
    const response = await fetch(`${origin}${route}`);
    assert.equal(response.status, 400, `${route} status`);
    const body = await response.json();
    assert.equal(body.error, expectedError, `${route} error`);
    console.log(`PASS server ${route}`);
  }
} finally {
  await stopServer();
}
