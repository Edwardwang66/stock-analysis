import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import {
  cp,
  link,
  lstat,
  mkdir,
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
import { basename, dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(scriptsDir, "..");
const nextBin = join(frontendRoot, "node_modules", "next", "dist", "bin", "next");
const lockName = ".out-publish.lock";
const retiredNamePattern = /^\.out-publish\.lock\.retired-[A-Za-z0-9-]+-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const phases = new Set([
  "created", "copying-stage", "staged", "moving-old-to-backup", "old-at-backup", "promoting-stage", "promoted",
  "rolling-back-new-out", "rolling-back-backup-to-out", "restoring-backup", "recovering-cleanup", "recovered", "recovered-created", "complete",
]);

function transactionId() { return `${process.pid}-${randomUUID()}`; }
function isTransactionId(value) { return typeof value === "string" && /^[A-Za-z0-9-]+$/.test(value); }

function pathsFor(root, txId) {
  const recordDir = join(root, `${lockName}.tx-${txId}`);
  return {
    root, txId, recordDir, temporaryRecordDir: join(root, `${lockName}.tx-tmp-${txId}`),
    ownerPath: join(recordDir, "owner.json"), statePath: join(recordDir, "state.json"), successorPath: join(recordDir, "successor"),
    lockPath: join(root, lockName), stagePath: join(root, `.out-stage-${txId}`), backupPath: join(root, `.out-backup-${txId}`), outPath: join(root, "out"),
  };
}

async function entry(path) {
  try { return await lstat(path); } catch (error) { if (error.code === "ENOENT") return null; throw error; }
}

async function assertRegular(path, label) {
  const value = await entry(path);
  if (!value || !value.isFile() || value.isSymbolicLink()) throw new Error(`publication ${label} metadata is missing, corrupt, or unsafe`);
}

async function assertDirectory(path, label) {
  const value = await entry(path);
  if (value && (!value.isDirectory() || value.isSymbolicLink())) throw new Error(`publication ${label} is unsafe`);
  return value;
}

function assertExact(candidate, expected) {
  if (typeof candidate !== "string" || resolve(candidate) !== expected) throw new Error("publication metadata contains an unsafe path");
}

async function readJson(path, label) {
  await assertRegular(path, label);
  try { return JSON.parse(await readFile(path, "utf8")); } catch { throw new Error(`publication ${label} metadata is corrupt`); }
}

async function writeAtomic(path, value, hooks) {
  const temporary = `${path}.tmp-${randomUUID()}`;
  try {
    await writeFile(temporary, `${JSON.stringify(value)}\n`, { flag: "wx" });
    await hooks?.afterStateTempWritten?.(temporary);
    await rename(temporary, path);
  } finally { await rm(temporary, { force: true }); }
}

function validateOwner(root, owner) {
  if (!owner || owner.version !== 1 || !isTransactionId(owner.txId) || !Number.isSafeInteger(owner.pid) || owner.pid <= 0) throw new Error("publication lock metadata is corrupt");
  const paths = pathsFor(root, owner.txId);
  assertExact(owner.recordDir, paths.recordDir);
  assertExact(owner.ownerPath, paths.ownerPath);
  assertExact(owner.statePath, paths.statePath);
  return paths;
}

function validateState(paths, state) {
  if (!state || state.version !== 1 || state.txId !== paths.txId || !phases.has(state.phase) || ![null, true, false].includes(state.hadOut)) throw new Error("publication state metadata is corrupt");
  assertExact(state.stagePath, paths.stagePath);
  assertExact(state.backupPath, paths.backupPath);
  const isCreatedPhase = ["created", "recovered-created"].includes(state.phase);
  if ((isCreatedPhase && state.hadOut !== null) || (!isCreatedPhase && typeof state.hadOut !== "boolean")) throw new Error("publication state metadata is corrupt");
  return state;
}

async function readTransactionByOwner(root, ownerPath, label = "lock") {
  const hintedRecord = dirname(ownerPath);
  if (basename(ownerPath) === "owner.json" && basename(hintedRecord).startsWith(`${lockName}.tx-`)) {
    const value = await entry(hintedRecord);
    if (!value || !value.isDirectory() || value.isSymbolicLink() || dirname(hintedRecord) !== root) throw new Error("publication transaction record is unsafe");
  }
  const owner = await readJson(ownerPath, label);
  const paths = validateOwner(root, owner);
  const record = await entry(paths.recordDir);
  if (!record || !record.isDirectory() || record.isSymbolicLink() || dirname(paths.recordDir) !== root) throw new Error("publication transaction record is unsafe");
  const state = validateState(paths, await readJson(paths.statePath, "state"));
  return { owner, paths, state };
}

async function readCanonical(root) {
  const transaction = await readTransactionByOwner(root, join(root, lockName));
  if (!(await sameInode(join(root, lockName), transaction.paths.ownerPath))) throw new Error("publication canonical token is unsafe");
  return transaction;
}

async function sameInode(left, right) {
  const [first, second] = await Promise.all([stat(left), stat(right)]);
  return first.dev === second.dev && first.ino === second.ino;
}

function alive(pid) {
  try { process.kill(pid, 0); return true; } catch (error) {
    if (error.code === "ESRCH") return false;
    if (error.code === "EPERM") return true;
    throw new Error(`cannot safely determine publication owner liveness: ${error.code ?? error.message}`);
  }
}

function stateFor(paths, phase, hadOut) {
  return { version: 1, txId: paths.txId, phase, hadOut, stagePath: paths.stagePath, backupPath: paths.backupPath };
}

async function updateState(transaction, phase, hadOut, hooks) {
  const state = stateFor(transaction.paths, phase, hadOut);
  await writeAtomic(transaction.paths.statePath, state, hooks);
  transaction.state = state;
}

async function createRecord(root) {
  const paths = pathsFor(root, transactionId());
  await mkdir(paths.temporaryRecordDir);
  const temporaryOwner = join(paths.temporaryRecordDir, "owner.json");
  const temporaryState = join(paths.temporaryRecordDir, "state.json");
  const owner = { version: 1, txId: paths.txId, pid: process.pid, recordDir: paths.recordDir, ownerPath: paths.ownerPath, statePath: paths.statePath };
  const state = stateFor(paths, "created", null);
  try {
    await writeFile(temporaryState, `${JSON.stringify(state)}\n`, { flag: "wx" });
    await writeFile(temporaryOwner, `${JSON.stringify(owner)}\n`, { flag: "wx" });
    await rename(paths.temporaryRecordDir, paths.recordDir);
    return { owner, paths, state };
  } catch (error) {
    await rm(paths.temporaryRecordDir, { recursive: true, force: true });
    throw error;
  }
}

async function installCanonical(transaction) {
  await link(transaction.paths.ownerPath, transaction.paths.lockPath);
}

async function removeDirectory(path) {
  await assertDirectory(path, basename(path));
  await rm(path, { recursive: true, force: true });
}

async function clearStateTemps(paths) {
  const names = await readdir(paths.recordDir);
  for (const name of names.filter((value) => value.startsWith("state.json.tmp-"))) await rm(join(paths.recordDir, name), { force: true });
}

async function removeArtifacts(paths) {
  await removeDirectory(paths.stagePath);
  await removeDirectory(paths.backupPath);
  await clearStateTemps(paths);
}

async function publicationShape(paths) {
  const stage = await assertDirectory(paths.stagePath, "staging path");
  const backup = await assertDirectory(paths.backupPath, "backup path");
  const out = await assertDirectory(paths.outPath, "out path");
  return { stage: Boolean(stage), backup: Boolean(backup), out: Boolean(out) };
}

function validateRecoveryShape(state, shape) {
  const { stage, backup, out } = shape;
  const exactlyOne = (left, right) => left !== right;
  let valid = false;
  switch (state.phase) {
    case "created":
    case "recovered-created":
      valid = !stage && !backup;
      break;
    case "copying-stage":
      valid = !backup && out === state.hadOut;
      break;
    case "staged":
      valid = stage && !backup && out === state.hadOut;
      break;
    case "moving-old-to-backup":
      valid = state.hadOut === true && stage && exactlyOne(out, backup);
      break;
    case "old-at-backup":
      valid = state.hadOut === true && stage && !out && backup;
      break;
    case "promoting-stage":
      valid = state.hadOut
        ? ((!out && backup && stage) || (out && backup && !stage))
        : ((!out && !backup && stage) || (out && !backup && !stage));
      break;
    case "promoted":
      valid = state.hadOut
        ? out && !stage
        : out && !stage && !backup;
      break;
    case "rolling-back-new-out":
      valid = state.hadOut === true && backup && exactlyOne(out, stage);
      break;
    case "rolling-back-backup-to-out":
    case "restoring-backup":
      valid = state.hadOut === true && stage && exactlyOne(out, backup);
      break;
    case "recovering-cleanup":
      valid = state.hadOut === false || out;
      break;
    case "recovered":
    case "complete":
      valid = !stage && !backup && (state.hadOut === false || out);
      break;
  }
  if (!valid) throw new Error(`publication ${state.phase} metadata shape is ambiguous`);
}

async function finishRecoveryCleanup(transaction, hadOut, hooks, alreadyDurable = false) {
  if (!alreadyDurable) {
    const resolved = await publicationShape(transaction.paths);
    if (hadOut && !resolved.out) throw new Error("publication cleanup metadata shape is ambiguous");
    await updateState(transaction, "recovering-cleanup", hadOut, hooks);
  }
  await hooks.afterRecoveringCleanupState?.(transaction.paths);
  await removeArtifacts(transaction.paths);
  await updateState(transaction, "recovered", hadOut, hooks);
}

async function recoverTransaction(transaction, hooks) {
  const { paths, state } = transaction;
  const shape = await publicationShape(paths);
  validateRecoveryShape(state, shape);

  if (state.phase === "created") {
    await updateState(transaction, "recovered-created", null, hooks);
    await clearStateTemps(paths);
    return;
  }
  if (state.phase === "recovered-created") {
    await clearStateTemps(paths);
    return;
  }
  if (["recovered", "complete"].includes(state.phase)) {
    await clearStateTemps(paths);
    return;
  }
  if (state.phase === "recovering-cleanup") {
    await finishRecoveryCleanup(transaction, state.hadOut, hooks, true);
    return;
  }

  if (state.phase === "moving-old-to-backup" || state.phase === "old-at-backup") {
    if (shape.backup) {
      await updateState(transaction, "restoring-backup", true, hooks);
      await rename(paths.backupPath, paths.outPath);
    }
  } else if (state.phase === "promoting-stage" && state.hadOut && !shape.out) {
    await updateState(transaction, "restoring-backup", true, hooks);
    await rename(paths.backupPath, paths.outPath);
  } else if (state.phase === "rolling-back-new-out") {
    if (shape.out) {
      await rename(paths.outPath, paths.stagePath);
      await updateState(transaction, "rolling-back-backup-to-out", true, hooks);
      await rename(paths.backupPath, paths.outPath);
    } else {
      await updateState(transaction, "rolling-back-backup-to-out", true, hooks);
      await rename(paths.backupPath, paths.outPath);
    }
  } else if (["rolling-back-backup-to-out", "restoring-backup"].includes(state.phase) && shape.backup) {
    await rename(paths.backupPath, paths.outPath);
  }

  await finishRecoveryCleanup(transaction, state.hadOut, hooks);
}

async function removeRecord(transaction, hooks) {
  const { paths } = transaction;
  const record = await entry(paths.recordDir);
  if (!record) return;
  if (!record.isDirectory() || record.isSymbolicLink() || dirname(paths.recordDir) !== paths.root) throw new Error("publication transaction record is unsafe");
  const owner = await entry(paths.ownerPath);
  if (!owner || !owner.isFile() || owner.isSymbolicLink()) throw new Error("publication owner metadata is missing, corrupt, or unsafe");
  if (owner.nlink !== 1) throw new Error("publication transaction record is still linked");
  const retiredPath = join(paths.root, `${lockName}.retired-${paths.txId}-${randomUUID()}`);
  await rename(paths.recordDir, retiredPath);
  await hooks?.afterRecordRetired?.(retiredPath, transaction);
  await rm(retiredPath, { recursive: true, force: true });
}

async function cleanupRetiredRecords(root) {
  const names = await readdir(root);
  for (const name of names.filter((value) => value.startsWith(`${lockName}.retired-`))) {
    const retiredPath = join(root, name);
    const retired = await entry(retiredPath);
    if (!retiredNamePattern.test(name) || !retired || !retired.isDirectory() || retired.isSymbolicLink() || dirname(retiredPath) !== root) {
      throw new Error("publication retired tombstone is unsafe");
    }
    await rm(retiredPath, { recursive: true, force: true });
  }
}

async function cleanupOrphans(root, holder, hooks) {
  const canonicalTransaction = await readCanonical(root);
  if (!sameToken(canonicalTransaction, holder)) throw new Error("publication orphan scan lost canonical ownership");
  await cleanupRetiredRecords(root);
  const names = await readdir(root);
  for (const name of names.filter((value) => value.startsWith(`${lockName}.tx-tmp-`))) {
    const match = new RegExp(`^\\${lockName}\\.tx-tmp-(\\d+)-[A-Za-z0-9-]+$`).exec(name);
    const temporary = join(root, name);
    const value = await entry(temporary);
    if (!match || !value || !value.isDirectory() || value.isSymbolicLink() || dirname(temporary) !== root) throw new Error("publication temporary transaction record is unsafe");
    if (!alive(Number(match[1]))) await rm(temporary, { recursive: true, force: false });
  }
  const pending = new Set(names.filter((value) => value.startsWith(`${lockName}.tx-`) && !value.startsWith(`${lockName}.tx-tmp-`)));
  let progressed;
  do {
    progressed = false;
    for (const name of [...pending]) {
      const recordDir = join(root, name);
      if (!(await entry(recordDir))) {
        pending.delete(name);
        continue;
      }
      const transaction = await readTransactionByOwner(root, join(recordDir, "owner.json"), "transaction record");
      if (transaction.paths.txId === holder.paths.txId || alive(transaction.owner.pid)) {
        pending.delete(name);
        continue;
      }
      if (!["created", "recovered-created", "recovered", "complete"].includes(transaction.state.phase)) throw new Error("publication orphan metadata is not recoverable without canonical ownership");
      const owner = await entry(transaction.paths.ownerPath);
      if (!owner || !owner.isFile() || owner.isSymbolicLink()) throw new Error("publication owner metadata is missing, corrupt, or unsafe");
      if (owner.nlink > 1) continue;
      if (owner.nlink !== 1) throw new Error("publication transaction record link count is unsafe");
      const shape = await publicationShape(transaction.paths);
      validateRecoveryShape(transaction.state, shape);
      await removeRecord(transaction, hooks);
      pending.delete(name);
      progressed = true;
    }
  } while (progressed && pending.size);
}

function withCleanupErrors(primary, cleanupErrors) {
  if (!cleanupErrors.length) return primary;
  return new AggregateError([primary, ...cleanupErrors], primary.message, { cause: primary });
}

async function retireSuccessorClaim(claim) {
  const successorPath = claim.predecessor.paths.successorPath;
  const linked = await entry(successorPath);
  if (!linked) return;
  if (!linked.isFile() || linked.isSymbolicLink()) throw new Error("publication successor token is unsafe");
  const owner = await entry(claim.candidate.paths.ownerPath);
  if (!owner || !owner.isFile() || owner.isSymbolicLink()) throw new Error("publication successor owner token is unsafe");
  if (linked.dev !== owner.dev || linked.ino !== owner.ino) throw new Error("publication successor ownership changed unexpectedly");
  try {
    await rm(successorPath, { force: false });
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

function sameToken(left, right) { return left.owner.txId === right.owner.txId && left.owner.ownerPath === right.owner.ownerPath; }

async function claimSuccessor(root, leaf, candidate) {
  try {
    await link(candidate.paths.ownerPath, leaf.paths.successorPath);
    return { candidate, predecessor: leaf };
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  const successor = await readTransactionByOwner(root, leaf.paths.successorPath, "successor claim");
  if (!(await sameInode(leaf.paths.successorPath, successor.paths.ownerPath))) throw new Error("publication successor token is unsafe");
  if (alive(successor.owner.pid)) throw new Error(`static publication recovery already active (pid ${successor.owner.pid})`);
  return claimSuccessor(root, successor, candidate);
}

async function unlinkCanonical(transaction) {
  const verified = await readCanonical(transaction.paths.root);
  if (!sameToken(transaction, verified)) throw new Error("publication canonical ownership changed unexpectedly");
  await rm(transaction.paths.lockPath, { force: false });
}

async function cleanupCandidate(candidate, claim, hooks, canonicalInstalled) {
  const errors = [];
  let canonicalUnlinked = !canonicalInstalled;
  if (canonicalInstalled) {
    try {
      await unlinkCanonical(candidate);
      canonicalUnlinked = true;
    } catch (error) {
      errors.push(error);
    }
    if (canonicalUnlinked) {
      try { await hooks.afterCanonicalReleased?.(candidate); } catch (error) { errors.push(error); }
    }
  }
  if (claim) {
    try { await retireSuccessorClaim(claim); } catch (error) { errors.push(error); }
  }
  if (canonicalUnlinked) {
    try { await removeRecord(candidate, hooks); } catch (error) { errors.push(error); }
  }
  return errors;
}

async function failCandidate(primary, candidate, claim, hooks, canonicalInstalled) {
  const cleanupErrors = await cleanupCandidate(candidate, claim, hooks, canonicalInstalled);
  throw withCleanupErrors(primary, cleanupErrors);
}

async function finalizeInstalledCandidate(root, candidate, claim, hooks) {
  try {
    await cleanupOrphans(root, candidate, hooks);
    await hooks.afterLockAcquired?.(candidate);
    return candidate;
  } catch (error) {
    await failCandidate(error, candidate, claim, hooks, true);
  }
}

async function acquirePublication(root, hooks) {
  const candidate = await createRecord(root);
  try {
    await hooks.afterRecordCreated?.(candidate);
  } catch (error) {
    await failCandidate(error, candidate, null, hooks, false);
  }
  try {
    await installCanonical(candidate);
  } catch (error) {
    if (error.code !== "EEXIST") await failCandidate(error, candidate, null, hooks, false);
    if (error.code === "EEXIST") {
      let claim;
      try {
        const stale = await readCanonical(root);
        if (alive(stale.owner.pid)) throw new Error(`static publication already active (pid ${stale.owner.pid})`);
        await hooks.afterDeadLockRead?.(stale);
        claim = await claimSuccessor(root, stale, candidate);
        if (claim.candidate.paths.txId !== candidate.paths.txId) throw new Error("publication successor protocol lost candidate ownership");
        await hooks.afterSuccessorLinked?.(candidate);
        const verified = await readCanonical(root);
        if (!sameToken(stale, verified)) throw new Error("publication canonical owner changed while recovering");
        await recoverTransaction(stale, hooks);
        await hooks.afterRecoveredBeforeRelease?.(stale);
        await unlinkCanonical(stale);
        await hooks.afterCanonicalReleased?.(stale);
        await hooks.beforeSuccessorCanonicalInstall?.(candidate);
      } catch (recoveryError) {
        await failCandidate(recoveryError, candidate, claim, hooks, false);
      }
      try {
        await installCanonical(candidate);
      } catch (installError) {
        const primary = installError.code === "EEXIST"
          ? new Error("publication canonical owner changed while installing successor")
          : installError;
        await failCandidate(primary, candidate, claim, hooks, false);
      }
      return finalizeInstalledCandidate(root, candidate, claim, hooks);
    }
  }
  return finalizeInstalledCandidate(root, candidate, null, hooks);
}

async function releasePublication(transaction, hadOut, hooks) {
  try {
    await updateState(transaction, "complete", hadOut, hooks);
    await cleanupOrphans(transaction.paths.root, transaction, hooks);
  } catch (error) {
    await failCandidate(error, transaction, null, hooks, true);
  }
  const cleanupErrors = await cleanupCandidate(transaction, null, hooks, true);
  if (cleanupErrors.length === 1) throw cleanupErrors[0];
  if (cleanupErrors.length > 1) throw new AggregateError(cleanupErrors, "static publication release failed");
}

async function rollbackPublication(transaction, hadOut, promoted, hooks) {
  const { paths } = transaction;
  await hooks.beforeRollback?.(paths);
  const shape = await publicationShape(paths);
  validateRecoveryShape(transaction.state, shape);
  if (typeof transaction.state.hadOut === "boolean" && transaction.state.hadOut !== hadOut) {
    throw new Error("publication rollback metadata disagrees with authoritative output state");
  }
  if (hadOut && promoted && shape.out && shape.backup) {
    await updateState(transaction, "rolling-back-new-out", true, hooks);
    await hooks.beforeRollbackNewOutRename?.(paths);
    await rename(paths.outPath, paths.stagePath);
    await hooks.afterRollbackNewOutRename?.(paths);
    await updateState(transaction, "rolling-back-backup-to-out", true, hooks);
    await rename(paths.backupPath, paths.outPath);
  } else if (hadOut && !shape.out && shape.backup) {
    await updateState(transaction, "restoring-backup", true, hooks);
    await rename(paths.backupPath, paths.outPath);
  }
  await finishRecoveryCleanup(transaction, hadOut, hooks);
}

export async function publishStaticOutput({ frontendRoot: configuredRoot, sourceOut, hooks = {} }) {
  const root = resolve(configuredRoot);
  if (!(await stat(resolve(sourceOut))).isDirectory()) throw new Error("static publication source must be a directory");
  const transaction = await acquirePublication(root, hooks);
  let hadOut = null;
  let promoted = false;
  let primary;
  try {
    const oldOut = await entry(transaction.paths.outPath);
    if (oldOut && (!oldOut.isDirectory() || oldOut.isSymbolicLink())) throw new Error("publication out path is unsafe");
    hadOut = Boolean(oldOut);
    await updateState(transaction, "copying-stage", hadOut, hooks);
    await hooks.afterCopyingState?.(transaction.paths);
    await cp(resolve(sourceOut), transaction.paths.stagePath, { recursive: true });
    await updateState(transaction, "staged", hadOut, hooks);
    if (hadOut) {
      await updateState(transaction, "moving-old-to-backup", hadOut, hooks);
      await rename(transaction.paths.outPath, transaction.paths.backupPath);
      await updateState(transaction, "old-at-backup", hadOut, hooks);
      await hooks.afterOldOutMoved?.(transaction.paths);
    }
    await updateState(transaction, "promoting-stage", hadOut, hooks);
    await rename(transaction.paths.stagePath, transaction.paths.outPath);
    promoted = true;
    await hooks.beforePromotedState?.(transaction.paths);
    await updateState(transaction, "promoted", hadOut, hooks);
  } catch (error) { primary = error; }
  if (primary && typeof hadOut !== "boolean") await failCandidate(primary, transaction, null, hooks, true);
  const cleanup = [];
  try { if (primary) await rollbackPublication(transaction, hadOut, promoted, hooks); else await removeDirectory(transaction.paths.backupPath); } catch (error) { cleanup.push(error); }
  if (!cleanup.length) { try { await releasePublication(transaction, hadOut, hooks); } catch (error) { cleanup.push(error); } }
  if (primary && cleanup.length) throw withCleanupErrors(primary, cleanup);
  if (primary) throw primary;
  if (cleanup.length === 1) throw cleanup[0];
  if (cleanup.length > 1) throw new AggregateError(cleanup, "static publication cleanup failed");
}

function runNextBuild(cwd, profile) {
  return new Promise((resolveBuild, rejectBuild) => {
    const child = spawn(process.execPath, [nextBin, "build"], { cwd, stdio: "inherit", env: { ...process.env, NEXT_BUILD_PROFILE: profile, NEXT_TELEMETRY_DISABLED: "1" } });
    child.once("error", rejectBuild);
    child.once("exit", (code, signal) => code === 0 ? resolveBuild() : rejectBuild(new Error(`next build failed with code=${code} signal=${signal ?? "none"}`)));
  });
}

async function buildStatic() {
  const temporaryParent = await mkdtemp(join(tmpdir(), "stock-analysis-static-"));
  const temporaryRoot = join(temporaryParent, "frontend");
  const excludedRoots = new Set(["node_modules", ".next", "out"]);
  try {
    await cp(frontendRoot, temporaryRoot, { recursive: true, filter(source) { return !excludedRoots.has(relative(frontendRoot, source).split(sep)[0]); } });
    await rm(join(temporaryRoot, "app", "api"), { recursive: true, force: true });
    if (process.env.STATIC_FEED_SOURCE) {
      const feedSource = resolve(process.env.STATIC_FEED_SOURCE);
      if (!(await stat(feedSource)).isDirectory()) throw new Error("STATIC_FEED_SOURCE must name a directory");
      await rm(join(temporaryRoot, "public", "feed"), { recursive: true, force: true });
      await cp(feedSource, join(temporaryRoot, "public", "feed"), { recursive: true });
    }
    await symlink(join(frontendRoot, "node_modules"), join(temporaryRoot, "node_modules"), process.platform === "win32" ? "junction" : "dir");
    await runNextBuild(temporaryRoot, "static");
    await publishStaticOutput({ frontendRoot, sourceOut: join(temporaryRoot, "out") });
  } finally { await rm(temporaryParent, { recursive: true, force: true }); }
}

async function main() {
  const profile = process.argv[2];
  if (!new Set(["static", "server"]).has(profile)) throw new Error("usage: node scripts/build-profile.mjs <static|server>");
  return profile === "server" ? runNextBuild(frontendRoot, "server") : buildStatic();
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
