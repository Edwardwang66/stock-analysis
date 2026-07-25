import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";
import test from "node:test";

const smokeModuleUrl = new URL("../smoke-server.mjs", import.meta.url);

async function loadSmoke() {
  return import(`${smokeModuleUrl.href}?test=${Date.now()}-${Math.random()}`);
}

async function fixture(source) {
  const dir = await mkdtemp(join(tmpdir(), "smoke-server-"));
  const path = join(dir, "fixture.mjs");
  await writeFile(path, source);
  return { dir, path, async dispose() { await rm(dir, { recursive: true, force: true }); } };
}

function launch(path) {
  return (port) => spawn(process.execPath, [path], {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, SMOKE_PORT: String(port) },
  });
}

async function listen(server) {
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  return server.address().port;
}

function errorHas(error, pattern) {
  return pattern.test(error.message) || (error.errors || []).some((entry) => errorHas(entry, pattern));
}

const shareRoot = new URL("https://example.test/stock-analysis/");
const shareTitle = "Edward Wang · Multi-Market Workbench";
const shareDescription = "Markets, signals and evidence across global assets.";
const shareAlt = "Edward Wang Multi-Market Workbench: markets, signals, and evidence across US, Hong Kong, mainland China, digital assets, and benchmarks.";

function shareHtml({ includeTitle = true } = {}) {
  return [
    includeTitle && `<meta property="og:title" content="${shareTitle}">`,
    `<meta property="og:description" content="${shareDescription}">`,
    '<meta property="og:type" content="website">',
    `<meta property="og:url" content="${shareRoot.href}">`,
    `<meta property="og:site_name" content="${shareTitle}">`,
    '<meta property="og:locale" content="zh_CN">',
    `<meta property="og:image" content="${new URL("og-card-v1.png", shareRoot).href}">`,
    '<meta property="og:image:width" content="1200">',
    '<meta property="og:image:height" content="630">',
    '<meta property="og:image:type" content="image/png">',
    `<meta property="og:image:alt" content="${shareAlt}">`,
    '<meta name="twitter:card" content="summary_large_image">',
    `<meta name="twitter:title" content="${shareTitle}">`,
    `<meta name="twitter:description" content="${shareDescription}">`,
    `<meta name="twitter:image" content="${new URL("og-card-v1.png", shareRoot).href}">`,
    `<meta name="twitter:image:alt" content="${shareAlt}">`,
  ].filter(Boolean).join("");
}

function shareServer({ html = shareHtml(), width = 1200, height = 630 } = {}) {
  return `
    import { createServer } from 'node:http';
    const html = ${JSON.stringify(`<html><head>${html}</head><body>ok</body></html>`)};
    const png = Buffer.alloc(45);
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png, 0);
    png.writeUInt32BE(13, 8);
    png.write('IHDR', 12, 'ascii');
    png.writeUInt32BE(${width}, 16);
    png.writeUInt32BE(${height}, 20);
    png.writeUInt8(8, 24);
    png.writeUInt8(2, 25);
    png.writeUInt32BE(0, 33);
    png.write('IEND', 37, 'ascii');
    const server = createServer((request, response) => {
      if (request.url === '/stock-analysis/og-card-v1.png') {
        response.writeHead(200, { 'content-type': 'image/png' });
        response.end(png);
        return;
      }
      response.writeHead(200, { 'content-type': 'text/html' });
      response.end(html);
    });
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      console.log('Local: http://127.0.0.1:' + port);
      console.log('Ready');
    });
    process.on('SIGTERM', () => server.close(() => process.exit(0)));
  `;
}

const htmlServer = `
  import { createServer } from 'node:http';
  const server = createServer((_, response) => { response.setHeader('content-type', 'text/html'); response.end('<html>ok</html>'); });
  server.listen(0, '127.0.0.1', () => {
    const port = server.address().port;
    console.log('  - Local:        http://127.0.0.1:' + port);
    console.log(' ✓ Ready in 1ms');
  });
  process.on('SIGTERM', () => server.close(() => process.exit(0)));
`;

test("child-owned port-0 waits for this child's Local and Ready markers", async () => {
  const { runSmoke } = await loadSmoke();
  const child = await fixture(htmlServer);
  const ports = [];
  try {
    const start = launch(child.path);
    await runSmoke({ launch: (port) => { ports.push(port); return start(port); }, routes: ["/"], apiChecks: [], timeoutMs: 1_000, shutdownTimeoutMs: 1_000 });
    assert.deepEqual(ports, [0]);
  } finally { await child.dispose(); }
});

test("occupied explicit port fails its child without touching the foreign server", async () => {
  const { runSmoke } = await loadSmoke();
  let requests = 0;
  const foreign = createServer((_, response) => { requests += 1; response.end("foreign"); });
  const port = await listen(foreign);
  const child = await fixture(`
    import { createServer } from 'node:http';
    const port = Number(process.env.SMOKE_PORT);
    const server = createServer();
    server.once('error', () => process.exit(1));
    server.listen(port, '127.0.0.1');
  `);
  try {
    await assert.rejects(() => runSmoke({ launch: launch(child.path), port, routes: ["/"], apiChecks: [], timeoutMs: 500, shutdownTimeoutMs: 500 }));
    assert.equal(requests, 0);
  } finally { foreign.close(); await child.dispose(); }
});

test("Local without Ready followed by exit never probes a foreign server", async () => {
  const { runSmoke } = await loadSmoke();
  let requests = 0;
  const foreign = createServer((_, response) => { requests += 1; response.end("foreign"); });
  const port = await listen(foreign);
  const child = await fixture(`console.log('  - Local: http://127.0.0.1:${port}'); process.exit(1);`);
  try {
    await assert.rejects(() => runSmoke({ launch: launch(child.path), routes: ["/"], apiChecks: [], timeoutMs: 500, shutdownTimeoutMs: 500 }));
    assert.equal(requests, 0);
  } finally { foreign.close(); await child.dispose(); }
});

test("black-hole response body times out and reaps the child", async () => {
  const { runSmoke } = await loadSmoke();
  const child = await fixture(`
    import { createServer } from 'node:http';
    const server = createServer((_, response) => { response.writeHead(200, { 'content-type': 'text/html' }); response.write('<html>'); });
    server.listen(0, '127.0.0.1', () => { const p = server.address().port; console.log('Local: http://127.0.0.1:' + p); console.log('Ready'); });
    process.on('SIGTERM', () => server.close(() => process.exit(0)));
  `);
  let spawned;
  try {
    await assert.rejects(() => runSmoke({ launch: () => (spawned = launch(child.path)()), routes: ["/"], apiChecks: [], timeoutMs: 120, shutdownTimeoutMs: 1_000 }));
    if (spawned.exitCode === null && spawned.signalCode === null) await once(spawned, "exit");
  } finally { await child.dispose(); }
});

test("spawn error is reported without an unhandled child lifecycle", async () => {
  const { runSmoke } = await loadSmoke();
  const child = { stdout: null, stderr: null, once(event, listener) { if (event === "error") queueMicrotask(() => listener(new Error("spawn denied"))); this[event] = listener; return this; }, kill(signal) { if (signal === "SIGKILL") queueMicrotask(() => this.exit(null, "SIGKILL")); return true; } };
  await assert.rejects(() => runSmoke({ launch: () => child, origin: "http://fixture", ready: true, routes: [], apiChecks: [], timeoutMs: 20, shutdownTimeoutMs: 20 }), (error) => errorHas(error, /spawn denied/));
});

test("child exit during an in-flight fetch fails promptly", async () => {
  const { runSmoke } = await loadSmoke();
  const child = await fixture(`
    import { createServer } from 'node:http';
    const server = createServer(() => setTimeout(() => {}, 10_000));
    server.listen(0, '127.0.0.1', () => { const p = server.address().port; console.log('Local: http://127.0.0.1:' + p); console.log('Ready'); setTimeout(() => process.exit(7), 80); });
  `);
  try {
    await assert.rejects(() => runSmoke({ launch: launch(child.path), routes: ["/"], apiChecks: [], timeoutMs: 1_000, shutdownTimeoutMs: 500 }), (error) => errorHas(error, /exited unexpectedly/));
  } finally { await child.dispose(); }
});

test("SIGTERM kill error is not an exit and cleanup escalates to SIGKILL", async () => {
  const { runSmoke } = await loadSmoke();
  const events = new Map(); let killed = [];
  const child = { stdout: null, stderr: null, once(event, listener) { events.set(event, listener); return this; }, kill(signal) { killed.push(signal); if (signal === "SIGKILL") queueMicrotask(() => events.get("exit")(null, "SIGKILL")); throw new Error("kill denied"); } };
  await assert.rejects(() => runSmoke({ launch: () => child, origin: "http://fixture", ready: true, routes: [], apiChecks: [], timeoutMs: 10, shutdownTimeoutMs: 20 }), /kill denied/);
  assert.deepEqual(killed, ["SIGTERM", "SIGKILL"]);
});

test("pre-cleanup SIGKILL is unexpected", async () => {
  const { runSmoke } = await loadSmoke();
  const events = new Map(); let killed = false;
  const child = { stdout: null, stderr: null, once(event, listener) { events.set(event, listener); return this; }, kill() { killed = true; return true; } };
  const fetchImpl = async () => { queueMicrotask(() => events.get("exit")(null, "SIGKILL")); return new Response("<html>ok</html>", { headers: { "content-type": "text/html" } }); };
  await assert.rejects(() => runSmoke({ launch: () => child, origin: "http://fixture", ready: true, routes: ["/"], apiChecks: [], fetchImpl, timeoutMs: 100, shutdownTimeoutMs: 100 }), (error) => errorHas(error, /exited unexpectedly/));
  assert.equal(killed, false);
});

test("code-0 exit queued by the final probe is unexpected before cleanup", async () => {
  const { runSmoke } = await loadSmoke();
  const events = new Map(); let killed = false;
  const child = { stdout: null, stderr: null, once(event, listener) { events.set(event, listener); return this; }, kill() { killed = true; return true; } };
  const fetchImpl = async () => { queueMicrotask(() => events.get("exit")(0, null)); return new Response("<html>ok</html>", { headers: { "content-type": "text/html" } }); };
  await assert.rejects(() => runSmoke({ launch: () => child, origin: "http://fixture", ready: true, routes: ["/"], apiChecks: [], fetchImpl, timeoutMs: 100, shutdownTimeoutMs: 100 }), (error) => errorHas(error, /exited unexpectedly/));
  assert.equal(killed, false);
});

test("share-card smoke accepts complete metadata and a 1200 by 630 local PNG", async () => {
  const { runSmoke } = await loadSmoke();
  const child = await fixture(shareServer());
  try {
    await runSmoke({
      launch: launch(child.path),
      routes: ["/"],
      apiChecks: [],
      shareCard: { publicRoot: shareRoot },
      timeoutMs: 1_000,
      shutdownTimeoutMs: 1_000,
    });
  } finally { await child.dispose(); }
});

test("share-card smoke rejects invalid metadata or PNG dimensions and reaps the child", async () => {
  const { runSmoke } = await loadSmoke();
  const cases = [
    shareServer({ html: shareHtml({ includeTitle: false }) }),
    shareServer({ width: 600, height: 315 }),
  ];
  for (const source of cases) {
    const child = await fixture(source);
    let spawned;
    try {
      await assert.rejects(() => runSmoke({
        launch: () => (spawned = launch(child.path)()),
        routes: ["/"],
        apiChecks: [],
        shareCard: { publicRoot: shareRoot },
        timeoutMs: 1_000,
        shutdownTimeoutMs: 1_000,
      }));
      if (spawned.exitCode === null && spawned.signalCode === null) await once(spawned, "exit");
      assert.notEqual(spawned.exitCode, null);
    } finally { await child.dispose(); }
  }
});
