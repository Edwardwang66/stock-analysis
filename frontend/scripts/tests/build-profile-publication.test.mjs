import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import {
  mkdir,
  link,
  mkdtemp,
  readFile,
  readdir,
  rename,
  rm,
  stat,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";

const buildModuleUrl = new URL("../build-profile.mjs", import.meta.url);

async function loadBuildModule() {
  return import(`${buildModuleUrl.href}?test=${Date.now()}-${Math.random()}`);
}

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "build-publication-"));
  const frontendRoot = join(root, "frontend");
  const sourceOut = join(root, "source-out");
  await mkdir(frontendRoot);
  await mkdir(sourceOut);
  await writeFile(join(sourceOut, "marker.txt"), "new");
  return {
    frontendRoot,
    sourceOut,
    async oldOut(marker = "old") {
      await mkdir(join(frontendRoot, "out"));
      await writeFile(join(frontendRoot, "out", "marker.txt"), marker);
    },
    async marker() {
      return readFile(join(frontendRoot, "out", "marker.txt"), "utf8");
    },
    async dispose() {
      await rm(root, { recursive: true, force: true });
    },
  };
}

async function publicationResidue(frontendRoot) {
  return (await readdir(frontendRoot)).filter((name) =>
    name.startsWith(".out-stage-") ||
    name.startsWith(".out-backup-") ||
    name.startsWith(".out-publish.lock"),
  );
}

async function waitFor(path, timeoutMs = 2_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      await stat(path);
      return;
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error(`timed out waiting for ${path}`);
}

async function waitForExit(child, timeoutMs = 2_000) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return [child.exitCode, child.signalCode];
  }
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      clearTimeout(timeout);
      child.off("exit", onExit);
      child.off("error", onError);
    };
    const onExit = (code, signal) => {
      cleanup();
      resolve([code, signal]);
    };
    const onError = (error) => {
      cleanup();
      reject(error);
    };
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error("timed out waiting for child exit"));
    }, timeoutMs);
    timeout.unref?.();
    child.once("exit", onExit);
    child.once("error", onError);
  });
}

async function killAndReap(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  const exited = waitForExit(child);
  child.kill("SIGKILL");
  await exited;
}

async function assertMissing(path) {
  await assert.rejects(() => stat(path), { code: "ENOENT" });
}

async function writeSentinelDirectory(path, sentinel) {
  await mkdir(path);
  await writeFile(join(path, "sentinel.txt"), sentinel);
}

async function sentinelDirectorySnapshot(path) {
  try {
    return {
      entries: (await readdir(path)).sort(),
      sentinel: await readFile(join(path, "sentinel.txt"), "utf8"),
    };
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

async function installDeadLock(target, txId = "dead-owner", pid = deadPid(), createDefaultStage = true) {
  const lock = join(target.frontendRoot, ".out-publish.lock");
  const recordDir = join(target.frontendRoot, `.out-publish.lock.tx-${txId}`);
  const ownerPath = join(recordDir, "owner.json");
  const statePath = join(recordDir, "state.json");
  await mkdir(recordDir);
  await writeFile(statePath, JSON.stringify({
    version: 1,
    txId,
    phase: "staged",
    hadOut: true,
    stagePath: join(target.frontendRoot, `.out-stage-${txId}`), backupPath: join(target.frontendRoot, `.out-backup-${txId}`),
  }));
  await writeFile(ownerPath, JSON.stringify({ version: 1, txId, pid, recordDir, ownerPath, statePath }));
  if (createDefaultStage) await mkdir(join(target.frontendRoot, `.out-stage-${txId}`));
  await link(ownerPath, lock);
  return { lock, recordDir, ownerPath, statePath };
}

async function installDeadSuccessor(target, predecessor, txId = "dead-successor", pid = deadPid()) {
  const recordDir = join(target.frontendRoot, `.out-publish.lock.tx-${txId}`);
  const ownerPath = join(recordDir, "owner.json");
  const statePath = join(recordDir, "state.json");
  await mkdir(recordDir);
  await writeFile(statePath, JSON.stringify({
    version: 1,
    txId,
    phase: "created",
    hadOut: null,
    stagePath: join(target.frontendRoot, `.out-stage-${txId}`),
    backupPath: join(target.frontendRoot, `.out-backup-${txId}`),
  }));
  await writeFile(ownerPath, JSON.stringify({
    version: 1,
    txId,
    pid,
    recordDir,
    ownerPath,
    statePath,
  }));
  await link(ownerPath, join(predecessor.recordDir, "successor"));
  return { recordDir, ownerPath, statePath };
}

function deadPid() {
  return 999_999_999;
}

test("importing the module has no CLI or build side effects", async () => {
  const module = await loadBuildModule();
  assert.equal(typeof module.publishStaticOutput, "function");
});

test("publication atomically replaces the old out tree and cleans all transaction residue", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  try {
    await target.oldOut();
    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await target.dispose();
  }
});

test("ordinary failure after moving old out restores the old tree and cleans its own residue", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  try {
    await target.oldOut();
    await assert.rejects(
      () => publishStaticOutput({
        frontendRoot: target.frontendRoot,
        sourceOut: target.sourceOut,
        hooks: { afterOldOutMoved() { throw new Error("injected publish failure"); } },
      }),
      /injected publish failure/,
    );
    assert.equal(await target.marker(), "old");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await target.dispose();
  }
});

test("a live owner blocks a concurrent publisher and its canonical lock remains untouched", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const txId = "live-owner";
  try {
    await target.oldOut();
    const { ownerPath } = await installDeadLock(target, txId, process.pid);
    const before = await readFile(join(target.frontendRoot, ".out-publish.lock"), "utf8");
    await assert.rejects(
      () => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }),
      /already active/,
    );
    assert.equal(await readFile(join(target.frontendRoot, ".out-publish.lock"), "utf8"), before);
    assert.equal(await target.marker(), "old");
  } finally {
    await target.dispose();
  }
});

test("corrupt or unsafe metadata fails closed without touching out or an outside sentinel", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  for (const metadata of ["not-json", "unsafe-state"]) {
    await t.test(metadata, async () => {
      const target = await fixture();
      const outside = join(dirname(target.frontendRoot), "outside-sentinel");
      try {
        await target.oldOut("sentinel-out");
        await mkdir(outside);
        await writeFile(join(outside, "sentinel.txt"), "outside");
        if (metadata === "not-json") {
          await writeFile(join(target.frontendRoot, ".out-publish.lock"), "this is not JSON");
        } else {
          const { statePath } = await installDeadLock(target, "unsafe-owner", deadPid(), false);
          await writeFile(statePath, JSON.stringify({
            version: 1, txId: "unsafe-owner",
            phase: "old-at-backup",
            hadOut: true,
            stagePath: outside,
            backupPath: join(target.frontendRoot, ".out-backup-unsafe-owner"),
          }));
        }
        await assert.rejects(
          () => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }),
          /metadata|unsafe|corrupt/i,
        );
        assert.equal(await target.marker(), "sentinel-out");
        assert.equal(await readFile(join(outside, "sentinel.txt"), "utf8"), "outside");
      } finally {
        await target.dispose();
      }
    });
  }
});

test("SIGKILL between old-out backup and staging promotion is recovered by the next publisher", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const ready = join(dirname(target.frontendRoot), "child-paused");
  const childPath = join(dirname(target.frontendRoot), "publisher-child.mjs");
  try {
    await target.oldOut();
    await writeFile(childPath, `
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      import { writeFile } from "node:fs/promises";
      await publishStaticOutput({
        frontendRoot: process.argv[2],
        sourceOut: process.argv[3],
        hooks: { async afterOldOutMoved() {
          await writeFile(process.argv[4], "paused");
          await new Promise(() => setInterval(() => {}, 1_000));
        } },
      });
    `);
    const child = spawn(process.execPath, [childPath, target.frontendRoot, target.sourceOut, ready], {
      stdio: "inherit",
    });
    await waitFor(ready);
    assert.equal(child.kill("SIGKILL"), true);
    const [code, signal] = await once(child, "exit");
    assert.equal(code, null);
    assert.equal(signal, "SIGKILL");
    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await target.dispose();
  }
});

test("a delayed stale reader cannot rename a newly installed live canonical owner", async () => {
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const script = join(base, "race-publisher.mjs");
  const firstRead = join(base, "first-read");
  const liveSecond = join(base, "live-second");
  const releaseFirst = join(base, "release-first");
  const releaseSecond = join(base, "release-second");
  let first;
  let second;
  try {
    await target.oldOut();
    await installDeadLock(target);
    await writeFile(script, `
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      import { stat, writeFile } from "node:fs/promises";
      const waitFor = async (path) => { while (true) { try { await stat(path); return; } catch (error) { if (error.code !== "ENOENT") throw error; await new Promise((resolve) => setTimeout(resolve, 5)); } } };
      const [root, source, role, read, live, releaseA, releaseB] = process.argv.slice(2);
      const hooks = role === "first" ? {
        async afterDeadLockRead() { await writeFile(read, "read"); await waitFor(releaseA); },
      } : {
        async afterSuccessorLinked() { await writeFile(live, "live"); await waitFor(releaseB); },
      };
      await publishStaticOutput({ frontendRoot: root, sourceOut: source, hooks });
    `);
    first = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "first", firstRead, liveSecond, releaseFirst, releaseSecond], { stdio: "ignore" });
    await waitFor(firstRead);
    second = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "second", firstRead, liveSecond, releaseFirst, releaseSecond], { stdio: "ignore" });
    await waitFor(liveSecond);
    const liveOwner = JSON.parse(await readFile(join(target.frontendRoot, ".out-publish.lock"), "utf8"));
    assert.equal(liveOwner.pid, deadPid());
    await writeFile(releaseFirst, "release");
    const [firstCode] = await waitForExit(first);
    assert.notEqual(firstCode, 0);
    assert.deepEqual(JSON.parse(await readFile(join(target.frontendRoot, ".out-publish.lock"), "utf8")), liveOwner);
    await writeFile(releaseSecond, "release");
    const [secondCode] = await waitForExit(second);
    assert.equal(secondCode, 0);
    assert.equal(await target.marker(), "new");
  } finally {
    first?.kill("SIGKILL");
    second?.kill("SIGKILL");
    await target.dispose();
  }
});

test("failure after staging promotion restores the previous out tree before discarding residue", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  try {
    await target.oldOut();
    await assert.rejects(
      () => publishStaticOutput({
        frontendRoot: target.frontendRoot,
        sourceOut: target.sourceOut,
        hooks: { beforePromotedState() { throw new Error("promoted state write failed"); } },
      }),
      /promoted state write failed/,
    );
    assert.equal(await target.marker(), "old");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await target.dispose();
  }
});

test("rollback cleanup failure preserves dead-child metadata for a later publisher to recover", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const script = join(base, "rollback-failure-child.mjs");
  let child;
  try {
    await target.oldOut();
    await writeFile(script, `
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      try {
        await publishStaticOutput({
          frontendRoot: process.argv[2], sourceOut: process.argv[3],
          hooks: {
            afterOldOutMoved() { throw new Error("primary publish failure"); },
            beforeRollback() { throw new Error("rollback cleanup failure"); },
          },
        });
      } catch { process.exit(17); }
    `);
    child = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut], { stdio: "ignore" });
    const [code] = await waitForExit(child);
    assert.equal(code, 17);
    await stat(join(target.frontendRoot, ".out-publish.lock"));
    await stat((await readdir(target.frontendRoot)).map((name) => join(target.frontendRoot, name)).find((path) => path.startsWith(join(target.frontendRoot, ".out-publish.lock.tx-"))));
    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    child?.kill("SIGKILL");
    await target.dispose();
  }
});

test("SIGKILL after a complete transaction record but before canonical install is cleaned by the next publisher", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const ready = join(base, "record-ready");
  const script = join(base, "record-crash-child.mjs");
  let child;
  try {
    await writeFile(script, `
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      import { writeFile } from "node:fs/promises";
      await publishStaticOutput({ frontendRoot: process.argv[2], sourceOut: process.argv[3], hooks: {
        async afterRecordCreated() { await writeFile(process.argv[4], "ready"); await new Promise(() => setInterval(() => {}, 1_000)); },
      }});
    `);
    child = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, ready], { stdio: "ignore" });
    await waitFor(ready);
    child.kill("SIGKILL");
    await waitForExit(child);
    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally { child?.kill("SIGKILL"); await target.dispose(); }
});

test("a live successor claim is append-only and cannot be stolen by a later recovery contender", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const deadReady = join(base, "dead-ready");
  const successorReady = join(base, "successor-ready");
  const release = join(base, "release-successor");
  const script = join(base, "successor-child.mjs");
  let dead;
  let successor;
  try {
    await target.oldOut();
    await writeFile(script, `
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      import { stat, writeFile } from "node:fs/promises";
      const wait = async (path) => { while (true) { try { await stat(path); return; } catch (error) { if (error.code !== "ENOENT") throw error; await new Promise((resolve) => setTimeout(resolve, 5)); } } };
      const role = process.argv[4];
      await publishStaticOutput({ frontendRoot: process.argv[2], sourceOut: process.argv[3], hooks: role === "dead" ? {
        async afterOldOutMoved() { await writeFile(process.argv[5], "dead"); await new Promise(() => setInterval(() => {}, 1_000)); },
      } : {
        async afterSuccessorLinked() { await writeFile(process.argv[5], "successor"); await wait(process.argv[6]); },
      }});
    `);
    dead = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "dead", deadReady], { stdio: "ignore" });
    await waitFor(deadReady);
    dead.kill("SIGKILL");
    await waitForExit(dead);
    successor = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "successor", successorReady, release], { stdio: "ignore" });
    await waitFor(successorReady);
    await assert.rejects(() => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }), /recovery|active/);
    await writeFile(release, "go");
    const [code] = await waitForExit(successor);
    assert.equal(code, 0);
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally { dead?.kill("SIGKILL"); successor?.kill("SIGKILL"); await target.dispose(); }
});

test("recovery survives SIGKILL both before and after retiring dead canonical A", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  for (const point of ["afterRecoveredBeforeRelease", "afterCanonicalReleased"]) {
    await t.test(point, async () => {
      const target = await fixture();
      const base = dirname(target.frontendRoot);
      const deadReady = join(base, `dead-${point}`);
      const recoveryReady = join(base, `recovery-${point}`);
      const script = join(base, `recovery-${point}.mjs`);
      let dead;
      let recovery;
      try {
        await target.oldOut();
        await writeFile(script, `
          import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
          import { writeFile } from "node:fs/promises";
          const role = process.argv[4];
          await publishStaticOutput({ frontendRoot: process.argv[2], sourceOut: process.argv[3], hooks: role === "dead" ? {
            async afterOldOutMoved() { await writeFile(process.argv[5], "dead"); await new Promise(() => setInterval(() => {}, 1_000)); },
          } : {
            async ${point}() { await writeFile(process.argv[5], "recovery"); await new Promise(() => setInterval(() => {}, 1_000)); },
          }});
        `);
        dead = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "dead", deadReady], { stdio: "ignore" });
        await waitFor(deadReady);
        dead.kill("SIGKILL");
        await waitForExit(dead);
        recovery = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "recovery", recoveryReady], { stdio: "ignore" });
        await waitFor(recoveryReady);
        recovery.kill("SIGKILL");
        await waitForExit(recovery);
        await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
        assert.equal(await target.marker(), "new");
        assert.deepEqual(await publicationResidue(target.frontendRoot), []);
      } finally { dead?.kill("SIGKILL"); recovery?.kill("SIGKILL"); await target.dispose(); }
    });
  }
});

test("rollback pre-phase recovery handles both sides of moving rejected new out back to staging", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  for (const point of ["beforeRollbackNewOutRename", "afterRollbackNewOutRename"]) {
    await t.test(point, async () => {
      const target = await fixture();
      const base = dirname(target.frontendRoot);
      const ready = join(base, `rollback-${point}`);
      const script = join(base, `rollback-${point}.mjs`);
      let child;
      try {
        await target.oldOut();
        await writeFile(script, `
          import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
          import { writeFile } from "node:fs/promises";
          await publishStaticOutput({ frontendRoot: process.argv[2], sourceOut: process.argv[3], hooks: {
            beforePromotedState() { throw new Error("force rollback"); },
            async ${point}() { await writeFile(process.argv[4], "pause"); await new Promise(() => setInterval(() => {}, 1_000)); },
          }}).catch(() => {});
        `);
        child = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, ready], { stdio: "ignore" });
        await waitFor(ready);
        child.kill("SIGKILL");
        await waitForExit(child);
        await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
        assert.equal(await target.marker(), "new");
        assert.deepEqual(await publicationResidue(target.frontendRoot), []);
      } finally { child?.kill("SIGKILL"); await target.dispose(); }
    });
  }
});

test("created records, valid unsafe paths, and transaction temp residue are cleaned or fail closed correctly", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  await t.test("created record and temp are cleaned", async () => {
    const target = await fixture();
    try {
      const temporary = join(target.frontendRoot, ".out-publish.lock.tx-tmp-999999999-dead");
      await mkdir(temporary);
      await writeFile(join(temporary, "state.json.tmp-dead"), "partial");
      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally { await target.dispose(); }
  });
  await t.test("unsafe path reaches path validation with valid schema", async () => {
    const { publishStaticOutput } = await loadBuildModule();
    const target = await fixture();
    const outside = join(dirname(target.frontendRoot), "outside-valid-schema");
    try {
      await target.oldOut("old");
      await mkdir(outside);
      await writeFile(join(outside, "sentinel"), "keep");
      const { lock, statePath } = await installDeadLock(target, "unsafe-valid", deadPid(), false);
      await writeFile(statePath, JSON.stringify({ version: 1, txId: "unsafe-valid", phase: "staged", hadOut: true, stagePath: outside, backupPath: join(target.frontendRoot, ".out-backup-unsafe-valid") }));
      await assert.rejects(() => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }), /unsafe path/);
      assert.equal(await readFile(join(outside, "sentinel"), "utf8"), "keep");
      await stat(lock);
    } finally { await target.dispose(); }
  });
});

test("review-3 cleanup safety: live temp, symlink record, failed initial cleanup, live terminal, and relink loser", async (t) => {
  await t.test("live temporary record is skipped then cleaned after child death", async () => {
    const { publishStaticOutput } = await loadBuildModule();
    const target = await fixture();
    const base = dirname(target.frontendRoot);
    const ready = join(base, "tmp-live");
    const script = join(base, "tmp-live.mjs");
    let child;
    try {
      await writeFile(script, `
        import { mkdir, writeFile } from "node:fs/promises";
        import { join } from "node:path";
        const temporary = join(process.argv[2], ".out-publish.lock.tx-tmp-" + process.pid + "-live");
        await mkdir(temporary);
        await writeFile(process.argv[3], "ready");
        await new Promise(() => setInterval(() => {}, 1_000));
      `);
      child = spawn(process.execPath, [script, target.frontendRoot, ready], { stdio: "ignore" });
      await waitFor(ready);
      const temporary = join(
        target.frontendRoot,
        (await readdir(target.frontendRoot)).find((name) => name.startsWith(".out-publish.lock.tx-tmp-")),
      );
      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      await stat(temporary);
      child.kill("SIGKILL");
      await waitForExit(child);
      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally {
      child?.kill("SIGKILL");
      await target.dispose();
    }
  });
  await t.test("symlinked record fails closed without touching outside", async () => {
    const { publishStaticOutput } = await loadBuildModule();
    const target = await fixture();
    const outside = join(dirname(target.frontendRoot), "outside-record");
    try {
      await mkdir(outside);
      await writeFile(join(outside, "owner.json"), "{}");
      await writeFile(join(outside, "state.json"), "{}");
      await writeFile(join(outside, "sentinel"), "keep");
      await symlink(outside, join(target.frontendRoot, ".out-publish.lock.tx-999999999-symlink"));
      await assert.rejects(() => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }), /transaction record is unsafe/);
      assert.equal(await readFile(join(outside, "sentinel"), "utf8"), "keep");
    } finally {
      await target.dispose();
    }
  });
  await t.test("post-link corrupt orphan retires candidate canonical before removal", async () => {
    const { publishStaticOutput } = await loadBuildModule();
    const target = await fixture();
    try {
      const corrupt = join(target.frontendRoot, ".out-publish.lock.tx-999999999-corrupt");
      await mkdir(corrupt);
      await writeFile(join(corrupt, "owner.json"), "bad");
      await assert.rejects(() => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }));
      await assert.rejects(() => stat(join(target.frontendRoot, ".out-publish.lock")), { code: "ENOENT" });
    } finally {
      await target.dispose();
    }
  });
  await t.test("live terminal previous record is skipped after canonical unlink", async () => {
    const target = await fixture();
    const base = dirname(target.frontendRoot);
    const ready = join(base, "terminal-ready");
    const release = join(base, "terminal-release");
    const script = join(base, "terminal.mjs");
    let child;
    try {
      await writeFile(script, `
        import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
        import { stat, writeFile } from "node:fs/promises";
        const wait = async (path) => {
          while (true) {
            try { await stat(path); return; }
            catch (error) {
              if (error.code !== "ENOENT") throw error;
              await new Promise((resolve) => setTimeout(resolve, 5));
            }
          }
        };
        await publishStaticOutput({
          frontendRoot: process.argv[2], sourceOut: process.argv[3],
          hooks: { async afterCanonicalReleased() { await writeFile(process.argv[4], "ready"); await wait(process.argv[5]); } },
        });
      `);
      child = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, ready, release], { stdio: "ignore" });
      await waitFor(ready);
      const { publishStaticOutput } = await loadBuildModule();
      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      await writeFile(release, "go");
      const [code] = await waitForExit(child);
      assert.equal(code, 0);
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally {
      child?.kill("SIGKILL");
      await target.dispose();
    }
  });
  await t.test("successor B loses normal re-link to C and only B is discarded", async () => {
    const { publishStaticOutput } = await loadBuildModule();
    const target = await fixture();
    const base = dirname(target.frontendRoot);
    const deadReady = join(base, "e-dead");
    const bReady = join(base, "e-b");
    const release = join(base, "e-release");
    const script = join(base, "e.mjs");
    let dead;
    let b;
    try {
      await target.oldOut();
      await writeFile(script, `
        import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
        import { stat, writeFile } from "node:fs/promises";
        const wait = async (path) => {
          while (true) {
            try { await stat(path); return; }
            catch (error) {
              if (error.code !== "ENOENT") throw error;
              await new Promise((resolve) => setTimeout(resolve, 5));
            }
          }
        };
        const role = process.argv[4];
        await publishStaticOutput({
          frontendRoot: process.argv[2], sourceOut: process.argv[3],
          hooks: role === "dead"
            ? { async afterOldOutMoved() { await writeFile(process.argv[5], "d"); await new Promise(() => setInterval(() => {}, 1_000)); } }
            : { async beforeSuccessorCanonicalInstall() { await writeFile(process.argv[5], "b"); await wait(process.argv[6]); } },
        });
      `);
      dead = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "dead", deadReady], { stdio: "ignore" });
      await waitFor(deadReady);
      dead.kill("SIGKILL");
      await waitForExit(dead);
      b = spawn(process.execPath, [script, target.frontendRoot, target.sourceOut, "b", bReady, release], { stdio: "ignore" });
      await waitFor(bReady);
      await publishStaticOutput({
        frontendRoot: target.frontendRoot,
        sourceOut: target.sourceOut,
        hooks: {
          async afterLockAcquired() {
            setTimeout(() => writeFile(release, "go"), 10);
            await new Promise((resolve) => setTimeout(resolve, 100));
          },
        },
      });
      b.kill("SIGKILL");
      if (b.exitCode === null) await waitForExit(b);
      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally {
      dead?.kill("SIGKILL");
      b?.kill("SIGKILL");
      await target.dispose();
    }
  });
});

test("a deep dead successor chain discards only B when C wins B's normal canonical re-link", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const bReady = join(base, "deep-b-ready");
  const bRecord = join(base, "deep-b-record");
  const bRelease = join(base, "deep-b-release");
  const cReady = join(base, "deep-c-ready");
  const cRelease = join(base, "deep-c-release");
  const bScript = join(base, "deep-b.mjs");
  const cScript = join(base, "deep-c.mjs");
  let b;
  let c;
  try {
    await target.oldOut();
    const a = await installDeadLock(target, "dead-a");
    await installDeadSuccessor(target, a, "dead-x");
    await writeFile(bScript, `
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      import { stat, writeFile } from "node:fs/promises";
      const wait = async (path) => {
        while (true) {
          try { await stat(path); return; }
          catch (error) {
            if (error.code !== "ENOENT") throw error;
            await new Promise((resolve) => setTimeout(resolve, 5));
          }
        }
      };
      await publishStaticOutput({
        frontendRoot: process.argv[2], sourceOut: process.argv[3],
        hooks: {
          async afterSuccessorLinked(transaction) { await writeFile(process.argv[4], transaction.paths.recordDir); },
          async beforeSuccessorCanonicalInstall() { await writeFile(process.argv[5], "paused"); await wait(process.argv[6]); },
        },
      });
    `);
    await writeFile(cScript, `
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      import { stat, writeFile } from "node:fs/promises";
      const wait = async (path) => {
        while (true) {
          try { await stat(path); return; }
          catch (error) {
            if (error.code !== "ENOENT") throw error;
            await new Promise((resolve) => setTimeout(resolve, 5));
          }
        }
      };
      await publishStaticOutput({
        frontendRoot: process.argv[2], sourceOut: process.argv[3],
        hooks: { async afterLockAcquired() { await writeFile(process.argv[4], String(process.pid)); await wait(process.argv[5]); } },
      });
    `);
    b = spawn(process.execPath, [bScript, target.frontendRoot, target.sourceOut, bRecord, bReady, bRelease], { stdio: "ignore" });
    await waitFor(bReady);
    const bRecordDir = await readFile(bRecord, "utf8");
    c = spawn(process.execPath, [cScript, target.frontendRoot, target.sourceOut, cReady, cRelease], { stdio: "ignore" });
    await waitFor(cReady);
    const cPid = Number(await readFile(cReady, "utf8"));
    const cOwner = JSON.parse(await readFile(join(target.frontendRoot, ".out-publish.lock"), "utf8"));
    assert.equal(cOwner.pid, cPid);
    assert.equal(await target.marker(), "old");
    await writeFile(bRelease, "resume");
    const [bCode] = await waitForExit(b);
    assert.notEqual(bCode, 0);
    await assert.rejects(() => stat(bRecordDir), { code: "ENOENT" });
    assert.equal(JSON.parse(await readFile(join(target.frontendRoot, ".out-publish.lock"), "utf8")).pid, cPid);
    assert.equal(await target.marker(), "old");
    await writeFile(cRelease, "release");
    const [cCode] = await waitForExit(c);
    assert.equal(cCode, 0);
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    b?.kill("SIGKILL");
    c?.kill("SIGKILL");
    await target.dispose();
  }
});

test("SIGKILL during a durably declared stage copy is recovered without changing old out", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const ready = join(base, "copy-crash-ready");
  const script = join(base, "copy-crash.mjs");
  let child;
  try {
    await target.oldOut();
    await writeFile(script, `
      import { mkdir, writeFile } from "node:fs/promises";
      import { join } from "node:path";
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      await publishStaticOutput({
        frontendRoot: process.argv[2],
        sourceOut: process.argv[3],
        hooks: {
          async afterCopyingState(paths) {
            await mkdir(paths.stagePath);
            await writeFile(join(paths.stagePath, "partial.txt"), "partial");
            await writeFile(process.argv[4], "ready");
            await new Promise(() => setInterval(() => {}, 1_000));
          },
        },
      });
    `);
    child = spawn(
      process.execPath,
      [script, target.frontendRoot, target.sourceOut, ready],
      { stdio: "ignore" },
    );
    await waitFor(ready);
    const recordName = (await readdir(target.frontendRoot)).find((name) =>
      name.startsWith(".out-publish.lock.tx-") &&
      !name.startsWith(".out-publish.lock.tx-tmp-"),
    );
    const state = JSON.parse(await readFile(join(target.frontendRoot, recordName, "state.json"), "utf8"));
    assert.equal(state.phase, "copying-stage");
    assert.equal(state.hadOut, true);
    assert.equal(await target.marker(), "old");

    const exited = waitForExit(child);
    assert.equal(child.kill("SIGKILL"), true);
    const [code, signal] = await exited;
    assert.equal(code, null);
    assert.equal(signal, "SIGKILL");

    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await killAndReap(child);
    await target.dispose();
  }
});

test("ordinary copy-start failure retires its canonical transaction and allows retry", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  for (const hadOut of [true, false]) {
    await t.test(hadOut ? "with an existing out tree" : "without an existing out tree", async () => {
      const target = await fixture();
      try {
        if (hadOut) await target.oldOut();
        await assert.rejects(
          () => publishStaticOutput({
            frontendRoot: target.frontendRoot,
            sourceOut: target.sourceOut,
            hooks: {
              async afterCopyingState(paths) {
                const state = JSON.parse(await readFile(paths.statePath, "utf8"));
                assert.equal(state.phase, "copying-stage");
                assert.equal(state.hadOut, hadOut);
                throw new Error("injected copy-start failure");
              },
            },
          }),
          /injected copy-start failure/,
        );
        if (hadOut) assert.equal(await target.marker(), "old");
        else await assertMissing(join(target.frontendRoot, "out"));
        assert.deepEqual(await publicationResidue(target.frontendRoot), []);

        await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
        assert.equal(await target.marker(), "new");
        assert.deepEqual(await publicationResidue(target.frontendRoot), []);
      } finally {
        await target.dispose();
      }
    });
  }
});

test("an error after linking a successor retires only that exact claim and candidate record", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  let candidate;
  try {
    await target.oldOut();
    const predecessor = await installDeadLock(target, "post-claim-a");
    const canonicalBefore = await stat(predecessor.lock);
    const contentsBefore = await readFile(predecessor.lock, "utf8");
    await assert.rejects(
      () => publishStaticOutput({
        frontendRoot: target.frontendRoot,
        sourceOut: target.sourceOut,
        hooks: {
          afterSuccessorLinked(transaction) {
            candidate = transaction;
            throw new Error("injected post-claim failure");
          },
        },
      }),
      /injected post-claim failure/,
    );
    assert.ok(candidate);
    const canonicalAfter = await stat(predecessor.lock);
    assert.equal(canonicalAfter.dev, canonicalBefore.dev);
    assert.equal(canonicalAfter.ino, canonicalBefore.ino);
    assert.equal(await readFile(predecessor.lock, "utf8"), contentsBefore);
    await assertMissing(join(predecessor.recordDir, "successor"));
    await assertMissing(candidate.paths.recordDir);

    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await target.dispose();
  }
});

test("successor post-canonical failures unwind its canonical, claim, and record", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  await t.test("afterLockAcquired hook failure", async () => {
    const target = await fixture();
    let candidate;
    try {
      await target.oldOut();
      const predecessor = await installDeadLock(target, "post-canonical-hook-a");
      await assert.rejects(
        () => publishStaticOutput({
          frontendRoot: target.frontendRoot,
          sourceOut: target.sourceOut,
          hooks: {
            afterSuccessorLinked(transaction) { candidate = transaction; },
            afterLockAcquired() { throw new Error("injected post-canonical hook failure"); },
          },
        }),
        /injected post-canonical hook failure/,
      );
      assert.ok(candidate);
      await assertMissing(join(target.frontendRoot, ".out-publish.lock"));
      await assertMissing(join(predecessor.recordDir, "successor"));
      await assertMissing(candidate.paths.recordDir);

      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      assert.equal(await target.marker(), "new");
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally {
      await target.dispose();
    }
  });

  await t.test("corrupt orphan cleanup failure", async () => {
    const target = await fixture();
    let candidate;
    try {
      await target.oldOut();
      const predecessor = await installDeadLock(target, "post-canonical-cleanup-a");
      const corrupt = join(target.frontendRoot, ".out-publish.lock.tx-999999999-corrupt-post-canonical");
      await mkdir(corrupt);
      await writeFile(join(corrupt, "owner.json"), "not-json");
      await assert.rejects(
        () => publishStaticOutput({
          frontendRoot: target.frontendRoot,
          sourceOut: target.sourceOut,
          hooks: { afterSuccessorLinked(transaction) { candidate = transaction; } },
        }),
        /metadata|corrupt/i,
      );
      assert.ok(candidate);
      await assertMissing(join(target.frontendRoot, ".out-publish.lock"));
      await assertMissing(join(predecessor.recordDir, "successor"));
      await assertMissing(candidate.paths.recordDir);

      await rm(corrupt, { recursive: true, force: true });
      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      assert.equal(await target.marker(), "new");
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally {
      await target.dispose();
    }
  });
});

test("recovered-created remains a valid idempotent terminal state across repeated recovery", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const ready = join(base, "recovered-created-ready");
  const script = join(base, "recovered-created.mjs");
  let child;
  try {
    const predecessor = await installDeadLock(target, "recovered-created-a", deadPid(), false);
    await writeFile(predecessor.statePath, JSON.stringify({
      version: 1,
      txId: "recovered-created-a",
      phase: "recovered-created",
      hadOut: null,
      stagePath: join(target.frontendRoot, ".out-stage-recovered-created-a"),
      backupPath: join(target.frontendRoot, ".out-backup-recovered-created-a"),
    }));
    await writeFile(script, `
      import { writeFile } from "node:fs/promises";
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      await publishStaticOutput({
        frontendRoot: process.argv[2],
        sourceOut: process.argv[3],
        hooks: {
          async afterRecoveredBeforeRelease() {
            await writeFile(process.argv[4], "ready");
            await new Promise(() => setInterval(() => {}, 1_000));
          },
        },
      });
    `);
    child = spawn(
      process.execPath,
      [script, target.frontendRoot, target.sourceOut, ready],
      { stdio: "ignore" },
    );
    await waitFor(ready);
    const durable = JSON.parse(await readFile(predecessor.statePath, "utf8"));
    assert.equal(durable.phase, "recovered-created");
    assert.equal(durable.hadOut, null);

    const exited = waitForExit(child);
    assert.equal(child.kill("SIGKILL"), true);
    const [code, signal] = await exited;
    assert.equal(code, null);
    assert.equal(signal, "SIGKILL");

    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await killAndReap(child);
    await target.dispose();
  }
});

test("record retirement is atomic and tombstone cleanup is symlink-safe", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  await t.test("a partial retired tombstone is inert and removed without following internal symlinks", async () => {
    const target = await fixture();
    const base = dirname(target.frontendRoot);
    const ready = join(base, "record-retired-ready");
    const script = join(base, "record-retired.mjs");
    const outside = join(base, "record-retired-outside");
    let child;
    try {
      await mkdir(outside);
      await writeFile(join(outside, "sentinel"), "keep");
      await writeFile(script, `
        import { writeFile } from "node:fs/promises";
        import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
        await publishStaticOutput({
          frontendRoot: process.argv[2],
          sourceOut: process.argv[3],
          hooks: {
            async afterRecordRetired(retiredPath) {
              await writeFile(process.argv[4], retiredPath);
              await new Promise(() => setInterval(() => {}, 1_000));
            },
          },
        });
      `);
      child = spawn(
        process.execPath,
        [script, target.frontendRoot, target.sourceOut, ready],
        { stdio: "ignore" },
      );
      await waitFor(ready);
      const retiredPath = await readFile(ready, "utf8");
      await assertMissing(join(target.frontendRoot, ".out-publish.lock"));
      await stat(retiredPath);
      await rm(join(retiredPath, "state.json"), { force: false });
      await symlink(outside, join(retiredPath, "outside-link"));

      const exited = waitForExit(child);
      assert.equal(child.kill("SIGKILL"), true);
      const [code, signal] = await exited;
      assert.equal(code, null);
      assert.equal(signal, "SIGKILL");

      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      assert.equal(await readFile(join(outside, "sentinel"), "utf8"), "keep");
      assert.equal(await target.marker(), "new");
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally {
      await killAndReap(child);
      await target.dispose();
    }
  });

  await t.test("a top-level retired tombstone symlink fails closed", async () => {
    const target = await fixture();
    const outside = join(dirname(target.frontendRoot), "top-level-tombstone-outside");
    const tombstoneName = ".out-publish.lock.retired-999999999-dead-00000000-0000-4000-8000-000000000000";
    const tombstone = join(target.frontendRoot, tombstoneName);
    try {
      await mkdir(outside);
      await writeFile(join(outside, "sentinel"), "keep");
      await symlink(outside, tombstone);
      await assert.rejects(
        () => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }),
        /retired|tombstone|unsafe/i,
      );
      assert.equal(await readFile(join(outside, "sentinel"), "utf8"), "keep");
      assert.deepEqual(await publicationResidue(target.frontendRoot), [tombstoneName]);

      await rm(tombstone, { force: false });
      await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
      assert.equal(await target.marker(), "new");
      assert.deepEqual(await publicationResidue(target.frontendRoot), []);
    } finally {
      await target.dispose();
    }
  });
});

test("a failed first copying-stage state write unwinds with authoritative hadOut and permits retry", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  for (const hadOut of [true, false]) {
    await t.test(hadOut ? "with an existing out tree" : "without an existing out tree", async () => {
      const target = await fixture();
      let injected = false;
      try {
        if (hadOut) await target.oldOut();
        await assert.rejects(
          () => publishStaticOutput({
            frontendRoot: target.frontendRoot,
            sourceOut: target.sourceOut,
            hooks: {
              async afterStateTempWritten(temporaryStatePath) {
                const state = JSON.parse(await readFile(temporaryStatePath, "utf8"));
                if (!injected && state.phase === "copying-stage") {
                  injected = true;
                  throw new Error("injected copying-stage state write failure");
                }
              },
            },
          }),
          /injected copying-stage state write failure/,
        );
        assert.equal(injected, true);
        if (hadOut) assert.equal(await target.marker(), "old");
        else await assertMissing(join(target.frontendRoot, "out"));
        assert.deepEqual(await publicationResidue(target.frontendRoot), []);

        await writeFile(join(target.sourceOut, "marker.txt"), "retry");
        await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
        assert.equal(await target.marker(), "retry");
        assert.deepEqual(await publicationResidue(target.frontendRoot), []);
      } finally {
        await target.dispose();
      }
    });
  }
});

test("a failed complete state write retains promoted output but releases all publication ownership", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  let injected = false;
  try {
    await target.oldOut();
    await assert.rejects(
      () => publishStaticOutput({
        frontendRoot: target.frontendRoot,
        sourceOut: target.sourceOut,
        hooks: {
          async afterStateTempWritten(temporaryStatePath) {
            const state = JSON.parse(await readFile(temporaryStatePath, "utf8"));
            if (!injected && state.phase === "complete") {
              injected = true;
              throw new Error("injected complete state write failure");
            }
          },
        },
      }),
      /injected complete state write failure/,
    );
    assert.equal(injected, true);
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);

    await writeFile(join(target.sourceOut, "marker.txt"), "retry-after-complete");
    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "retry-after-complete");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);

    await writeFile(join(target.sourceOut, "marker.txt"), "aggregate-after-complete");
    let aggregate;
    try {
      await publishStaticOutput({
        frontendRoot: target.frontendRoot,
        sourceOut: target.sourceOut,
        hooks: {
          async afterStateTempWritten(temporaryStatePath) {
            const state = JSON.parse(await readFile(temporaryStatePath, "utf8"));
            if (state.phase === "complete") throw new Error("primary complete write failure");
          },
          afterCanonicalReleased() {
            throw new Error("secondary canonical cleanup failure");
          },
        },
      });
      assert.fail("expected complete-state and cleanup failures");
    } catch (error) {
      aggregate = error;
    }
    assert.ok(aggregate instanceof AggregateError);
    assert.equal(aggregate.message, "primary complete write failure");
    assert.equal(aggregate.cause?.message, "primary complete write failure");
    assert.deepEqual(
      aggregate.errors.map((error) => error.message),
      ["primary complete write failure", "secondary canonical cleanup failure"],
    );
    assert.equal(await target.marker(), "aggregate-after-complete");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await target.dispose();
  }
});

test("invalid recovery phase shapes fail closed before mutating canonical or artifact sentinels", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  const cases = [
    { name: "moving old with neither out nor backup", phase: "moving-old-to-backup", stage: true, out: false, backup: false },
    { name: "rollback restore with neither out nor backup", phase: "rolling-back-backup-to-out", stage: true, out: false, backup: false },
    { name: "rollback new out without backup", phase: "rolling-back-new-out", stage: false, out: true, backup: false },
    { name: "old at backup with both out and backup", phase: "old-at-backup", stage: true, out: true, backup: true },
    { name: "restoring backup with both out and backup", phase: "restoring-backup", stage: true, out: true, backup: true },
  ];

  for (const [index, recoveryCase] of cases.entries()) {
    await t.test(recoveryCase.name, async () => {
      const target = await fixture();
      const txId = `invalid-shape-${index}`;
      try {
        const dead = await installDeadLock(target, txId, deadPid(), false);
        const paths = {
          stage: join(target.frontendRoot, `.out-stage-${txId}`),
          out: join(target.frontendRoot, "out"),
          backup: join(target.frontendRoot, `.out-backup-${txId}`),
        };
        await writeFile(dead.statePath, JSON.stringify({
          version: 1,
          txId,
          phase: recoveryCase.phase,
          hadOut: true,
          stagePath: paths.stage,
          backupPath: paths.backup,
        }));
        for (const [artifact, present] of Object.entries({
          stage: recoveryCase.stage,
          out: recoveryCase.out,
          backup: recoveryCase.backup,
        })) {
          if (present) await writeSentinelDirectory(paths[artifact], `${txId}-${artifact}`);
        }

        const canonicalBefore = await stat(dead.lock);
        const canonicalContentsBefore = await readFile(dead.lock, "utf8");
        const stateBefore = await readFile(dead.statePath, "utf8");
        const recordEntriesBefore = (await readdir(dead.recordDir)).sort();
        const artifactsBefore = Object.fromEntries(await Promise.all(
          Object.entries(paths).map(async ([name, path]) => [name, await sentinelDirectorySnapshot(path)]),
        ));

        await assert.rejects(
          () => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }),
          /ambiguous|shape|recovery|rollback/i,
        );

        const canonicalAfter = await stat(dead.lock);
        assert.equal(canonicalAfter.dev, canonicalBefore.dev);
        assert.equal(canonicalAfter.ino, canonicalBefore.ino);
        assert.equal(await readFile(dead.lock, "utf8"), canonicalContentsBefore);
        assert.equal(await readFile(dead.statePath, "utf8"), stateBefore);
        assert.deepEqual((await readdir(dead.recordDir)).sort(), recordEntriesBefore);
        const artifactsAfter = Object.fromEntries(await Promise.all(
          Object.entries(paths).map(async ([name, path]) => [name, await sentinelDirectorySnapshot(path)]),
        ));
        assert.deepEqual(artifactsAfter, artifactsBefore);
      } finally {
        await target.dispose();
      }
    });
  }
});

test("created terminal phases reject boolean hadOut without mutating canonical or artifacts", async (t) => {
  const { publishStaticOutput } = await loadBuildModule();
  for (const phase of ["created", "recovered-created"]) {
    for (const hadOut of [true, false]) {
      await t.test(`${phase}/${hadOut}`, async () => {
        const target = await fixture();
        const txId = `invalid-null-state-${phase}-${hadOut}`;
        try {
          const dead = await installDeadLock(target, txId, deadPid(), false);
          const paths = {
            stage: join(target.frontendRoot, `.out-stage-${txId}`),
            out: join(target.frontendRoot, "out"),
            backup: join(target.frontendRoot, `.out-backup-${txId}`),
          };
          await writeFile(dead.statePath, JSON.stringify({
            version: 1,
            txId,
            phase,
            hadOut,
            stagePath: paths.stage,
            backupPath: paths.backup,
          }));
          await writeSentinelDirectory(paths.out, `${txId}-out`);

          const canonicalBefore = await stat(dead.lock);
          const canonicalContentsBefore = await readFile(dead.lock, "utf8");
          const stateBefore = await readFile(dead.statePath, "utf8");
          const recordEntriesBefore = (await readdir(dead.recordDir)).sort();
          const artifactsBefore = Object.fromEntries(await Promise.all(
            Object.entries(paths).map(async ([name, path]) => [name, await sentinelDirectorySnapshot(path)]),
          ));

          await assert.rejects(
            () => publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut }),
            /state|metadata|corrupt|hadOut/i,
          );

          const canonicalAfter = await stat(dead.lock);
          assert.equal(canonicalAfter.dev, canonicalBefore.dev);
          assert.equal(canonicalAfter.ino, canonicalBefore.ino);
          assert.equal(await readFile(dead.lock, "utf8"), canonicalContentsBefore);
          assert.equal(await readFile(dead.statePath, "utf8"), stateBefore);
          assert.deepEqual((await readdir(dead.recordDir)).sort(), recordEntriesBefore);
          const artifactsAfter = Object.fromEntries(await Promise.all(
            Object.entries(paths).map(async ([name, path]) => [name, await sentinelDirectorySnapshot(path)]),
          ));
          assert.deepEqual(artifactsAfter, artifactsBefore);
        } finally {
          await target.dispose();
        }
      });
    }
  }
});

const invalidTerminalOrphanCases = [
  { phase: "created", hadOut: null, stage: true, backup: false },
  { phase: "recovered-created", hadOut: null, stage: false, backup: true },
  { phase: "recovered", hadOut: false, stage: false, backup: true },
  { phase: "complete", hadOut: true, stage: true, backup: false },
];

for (const orphanCase of invalidTerminalOrphanCases) {
  test(`dead non-canonical ${orphanCase.phase}/${orphanCase.hadOut} orphan validates shape before retirement`, async () => {
    const { publishStaticOutput } = await loadBuildModule();
    const target = await fixture();
    const txId = `invalid-terminal-orphan-${orphanCase.phase}`;
    try {
      const orphan = await installDeadLock(target, txId, deadPid(), false);
      await rm(orphan.lock, { force: false });
      const paths = {
        stage: join(target.frontendRoot, `.out-stage-${txId}`),
        backup: join(target.frontendRoot, `.out-backup-${txId}`),
        out: join(target.frontendRoot, "out"),
      };
      await writeFile(orphan.statePath, JSON.stringify({
        version: 1,
        txId,
        phase: orphanCase.phase,
        hadOut: orphanCase.hadOut,
        stagePath: paths.stage,
        backupPath: paths.backup,
      }));
      if (orphanCase.stage) await writeSentinelDirectory(paths.stage, `${txId}-stage`);
      if (orphanCase.backup) await writeSentinelDirectory(paths.backup, `${txId}-backup`);
      await writeSentinelDirectory(paths.out, `${txId}-out`);

      const unrelated = join(target.frontendRoot, `.out-stage-unrelated-${orphanCase.phase}`);
      await writeSentinelDirectory(unrelated, `${txId}-unrelated`);
      const ownerBefore = await readFile(orphan.ownerPath);
      const stateBefore = await readFile(orphan.statePath);
      const recordEntriesBefore = (await readdir(orphan.recordDir)).sort();
      const artifactsBefore = Object.fromEntries(await Promise.all(
        Object.entries(paths).map(async ([name, path]) => [name, await sentinelDirectorySnapshot(path)]),
      ));
      const unrelatedBefore = await sentinelDirectorySnapshot(unrelated);
      let candidate;

      await assert.rejects(
        () => publishStaticOutput({
          frontendRoot: target.frontendRoot,
          sourceOut: target.sourceOut,
          hooks: { afterRecordCreated(transaction) { candidate = transaction; } },
        }),
        /ambiguous|shape/i,
      );

      assert.ok(candidate);
      await assertMissing(orphan.lock);
      await assertMissing(candidate.paths.recordDir);
      assert.deepEqual(await readFile(orphan.ownerPath), ownerBefore);
      assert.deepEqual(await readFile(orphan.statePath), stateBefore);
      assert.deepEqual((await readdir(orphan.recordDir)).sort(), recordEntriesBefore);
      const artifactsAfter = Object.fromEntries(await Promise.all(
        Object.entries(paths).map(async ([name, path]) => [name, await sentinelDirectorySnapshot(path)]),
      ));
      assert.deepEqual(artifactsAfter, artifactsBefore);
      assert.deepEqual(await sentinelDirectorySnapshot(unrelated), unrelatedBefore);
    } finally {
      await target.dispose();
    }
  });
}

test("SIGKILL after durable recovery-cleanup is resumed idempotently by the next publisher", async () => {
  const { publishStaticOutput } = await loadBuildModule();
  const target = await fixture();
  const base = dirname(target.frontendRoot);
  const ready = join(base, "recovery-cleanup-ready");
  const script = join(base, "recovery-cleanup-child.mjs");
  const txId = "recovery-cleanup-a";
  let child;
  try {
    const dead = await installDeadLock(target, txId, deadPid(), false);
    const stagePath = join(target.frontendRoot, `.out-stage-${txId}`);
    const backupPath = join(target.frontendRoot, `.out-backup-${txId}`);
    await writeFile(dead.statePath, JSON.stringify({
      version: 1,
      txId,
      phase: "old-at-backup",
      hadOut: true,
      stagePath,
      backupPath,
    }));
    await writeSentinelDirectory(stagePath, "rejected-new-stage");
    await writeSentinelDirectory(backupPath, "old");
    await rename(join(backupPath, "sentinel.txt"), join(backupPath, "marker.txt"));
    await writeFile(script, `
      import { writeFile } from "node:fs/promises";
      import { publishStaticOutput } from ${JSON.stringify(buildModuleUrl.href)};
      await publishStaticOutput({
        frontendRoot: process.argv[2],
        sourceOut: process.argv[3],
        hooks: {
          async afterRecoveringCleanupState() {
            await writeFile(process.argv[4], "ready");
            await new Promise(() => setInterval(() => {}, 1_000));
          },
        },
      });
    `);
    child = spawn(
      process.execPath,
      [script, target.frontendRoot, target.sourceOut, ready],
      { stdio: "ignore" },
    );
    await waitFor(ready);
    const durable = JSON.parse(await readFile(dead.statePath, "utf8"));
    assert.equal(durable.phase, "recovering-cleanup");
    assert.equal(durable.hadOut, true);
    assert.equal(await target.marker(), "old");
    await stat(stagePath);
    await assertMissing(backupPath);

    const exited = waitForExit(child);
    assert.equal(child.kill("SIGKILL"), true);
    const [code, signal] = await exited;
    assert.equal(code, null);
    assert.equal(signal, "SIGKILL");

    await publishStaticOutput({ frontendRoot: target.frontendRoot, sourceOut: target.sourceOut });
    assert.equal(await target.marker(), "new");
    assert.deepEqual(await publicationResidue(target.frontendRoot), []);
  } finally {
    await killAndReap(child);
    await target.dispose();
  }
});
