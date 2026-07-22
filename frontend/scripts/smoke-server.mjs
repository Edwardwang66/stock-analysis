import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { pathToFileURL } from "node:url";

const routes = [
  "/", "/alerts/", "/desk/", "/help/", "/intel/", "/portfolio/",
  "/reports/", "/screener/", "/sources/", "/symbol/", "/tracker/",
];
const apiChecks = [
  ["/api/quote", "symbols required"],
  ["/api/ohlcv?symbol=BAD:X", "unsupported market BAD"],
];

function errorFromExit({ code, signal }) {
  return new Error(`next start exited unexpectedly with code=${code} signal=${signal}`);
}

function parseLocalUrl(line) {
  return line.match(/\bLocal:\s*(https?:\/\/\S+)/i)?.[1];
}

function withTimeout(promise, timeoutMs, message, abort, childFailure) {
  let timer;
  const timed = new Promise((_, reject) => {
    timer = setTimeout(() => {
      abort?.abort();
      reject(new Error(message));
    }, timeoutMs);
  });
  return Promise.race([promise, timed, childFailure]).finally(() => clearTimeout(timer));
}

function defaultLaunch(port) {
  return spawn(
    process.execPath,
    ["node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", String(port)],
    {
      cwd: new URL("..", import.meta.url),
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        NEXT_BUILD_PROFILE: "server",
        NEXT_PUBLIC_BASE_PATH: "",
        NEXT_TELEMETRY_DISABLED: "1",
        NODE_ENV: "production",
      },
    },
  );
}

function drainQueuedEvents() {
  return new Promise((resolve) => setImmediate(resolve));
}

export async function runSmoke({
  launch = defaultLaunch,
  port = process.env.SMOKE_PORT === undefined ? 0 : Number(process.env.SMOKE_PORT),
  origin: configuredOrigin,
  ready = false,
  routes: smokeRoutes = routes,
  apiChecks: checks = apiChecks,
  fetchImpl = fetch,
  timeoutMs = 30_000,
  shutdownTimeoutMs = 5_000,
  output = process.stdout,
  errorOutput = process.stderr,
} = {}) {
  assert.ok(Number.isInteger(port) && port >= 0 && port < 65536, "invalid SMOKE_PORT");
  assert.ok(process.env.SMOKE_PORT === undefined || port > 0, "invalid SMOKE_PORT");
  const server = launch(port);
  let exited;
  let childError;
  let shutdownInitiated = false;
  let resolveExit;
  const exitObserved = new Promise((resolve) => { resolveExit = resolve; });
  const childFailure = new Promise((_, reject) => {
    server.once("error", (error) => {
      childError = error;
      reject(error);
    });
    server.once("exit", (code, signal) => {
      exited = { code, signal };
      resolveExit(exited);
      if (!shutdownInitiated) reject(errorFromExit(exited));
    });
  });
  // Keep the failure promise observed even after a successful smoke run.
  childFailure.catch(() => {});

  let discoveredOrigin = configuredOrigin;
  let childReady = ready;
  let startupOutput = "";
  const tee = (stream, target) => {
    if (!stream) return;
    stream.setEncoding?.("utf8");
    stream.on("data", (chunk) => {
      target?.write?.(chunk);
      const text = String(chunk);
      startupOutput += text;
      discoveredOrigin ??= parseLocalUrl(startupOutput);
      if (/\bReady\b/i.test(startupOutput)) childReady = true;
    });
  };
  tee(server.stdout, output);
  tee(server.stderr, errorOutput);

  async function waitForReady() {
    const deadline = Date.now() + timeoutMs;
    while (!(discoveredOrigin && childReady)) {
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw new Error("next start did not become ready within deadline");
      await withTimeout(delay(Math.min(25, remaining)), remaining, "next start did not become ready within deadline", undefined, childFailure);
    }
  }

  async function request(url) {
    const controller = new AbortController();
    const response = await withTimeout(
      fetchImpl(url, { signal: controller.signal }), timeoutMs, `request timed out: ${url}`, controller, childFailure,
    );
    return { response, controller };
  }

  function readBody(response, controller, url) {
    return withTimeout(
      response.text(), timeoutMs, `response body timed out: ${url}`, controller, childFailure,
    );
  }

  async function cleanup() {
    // Let an exit scheduled by the last completed probe become observable first.
    await drainQueuedEvents();
    if (exited) throw errorFromExit(exited);
    shutdownInitiated = true;
    let killError;
    try { server.kill("SIGTERM"); } catch (error) { killError = error; }
    const graceful = await Promise.race([
      exitObserved.then(() => true),
      delay(shutdownTimeoutMs).then(() => false),
    ]);
    if (!graceful && !exited) {
      try { server.kill("SIGKILL"); } catch (error) { killError ??= error; }
      const killed = await Promise.race([
        exitObserved.then(() => true),
        delay(shutdownTimeoutMs).then(() => false),
      ]);
      if (!killed && !exited) throw new Error("next start did not exit after SIGKILL", { cause: killError });
    }
    if (childError) throw childError;
    if (killError) throw killError;
  }

  let primaryError;
  try {
    await waitForReady();
    const origin = discoveredOrigin;
    for (const route of smokeRoutes) {
      const url = `${origin}${route}`;
      const { response, controller } = await request(url);
      assert.equal(response.status, 200, `${route} status`);
      assert.match(response.headers.get("content-type") || "", /^text\/html/i, `${route} content type`);
      assert.match(await readBody(response, controller, url), /<html/i, `${route} document`);
      console.log(`PASS server ${route}`);
    }
    for (const [route, expectedError] of checks) {
      const url = `${origin}${route}`;
      const { response, controller } = await request(url);
      assert.equal(response.status, 400, `${route} status`);
      const body = JSON.parse(await readBody(response, controller, url));
      assert.equal(body.error, expectedError, `${route} error`);
      console.log(`PASS server ${route}`);
    }
  } catch (error) {
    primaryError = error;
  }

  try {
    await cleanup();
  } catch (cleanupError) {
    if (primaryError) throw new AggregateError([primaryError, cleanupError], "smoke failed and cleanup failed");
    throw cleanupError;
  }
  if (primaryError) throw primaryError;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await runSmoke();
}
