import { spawn } from "node:child_process";
import { cp, mkdtemp, rm, stat, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(scriptsDir, "..");
const nextBin = join(frontendRoot, "node_modules", "next", "dist", "bin", "next");

function runNextBuild(cwd, profile) {
  return new Promise((resolveBuild, rejectBuild) => {
    const child = spawn(process.execPath, [nextBin, "build"], {
      cwd,
      stdio: "inherit",
      env: {
        ...process.env,
        NEXT_BUILD_PROFILE: profile,
        NEXT_TELEMETRY_DISABLED: "1",
      },
    });

    child.once("error", rejectBuild);
    child.once("exit", (code, signal) => {
      if (code === 0) {
        resolveBuild();
        return;
      }
      rejectBuild(
        new Error(`next build failed with code=${code} signal=${signal ?? "none"}`),
      );
    });
  });
}

async function buildStatic() {
  const temporaryParent = await mkdtemp(join(tmpdir(), "stock-analysis-static-"));
  const temporaryRoot = join(temporaryParent, "frontend");
  const excludedRoots = new Set(["node_modules", ".next", "out"]);

  try {
    await cp(frontendRoot, temporaryRoot, {
      recursive: true,
      filter(source) {
        const pathWithinFrontend = relative(frontendRoot, source);
        const rootName = pathWithinFrontend.split(sep)[0];
        return !excludedRoots.has(rootName);
      },
    });
    await rm(join(temporaryRoot, "app", "api"), {
      recursive: true,
      force: true,
    });

    const feedSourceValue = process.env.STATIC_FEED_SOURCE;
    if (feedSourceValue) {
      const feedSource = resolve(feedSourceValue);
      const feedSourceStat = await stat(feedSource);
      if (!feedSourceStat.isDirectory()) {
        throw new Error("STATIC_FEED_SOURCE must name a directory");
      }
      const bundledFeed = join(temporaryRoot, "public", "feed");
      await rm(bundledFeed, { recursive: true, force: true });
      await cp(feedSource, bundledFeed, { recursive: true });
    }

    await symlink(
      join(frontendRoot, "node_modules"),
      join(temporaryRoot, "node_modules"),
      process.platform === "win32" ? "junction" : "dir",
    );

    await runNextBuild(temporaryRoot, "static");
    await rm(join(frontendRoot, "out"), { recursive: true, force: true });
    await cp(join(temporaryRoot, "out"), join(frontendRoot, "out"), {
      recursive: true,
    });
  } finally {
    await rm(temporaryParent, { recursive: true, force: true });
  }
}

async function main() {
  const profile = process.argv[2];
  if (!new Set(["static", "server"]).has(profile)) {
    throw new Error("usage: node scripts/build-profile.mjs <static|server>");
  }

  if (profile === "server") {
    await runNextBuild(frontendRoot, "server");
    return;
  }

  await buildStatic();
}

await main();
