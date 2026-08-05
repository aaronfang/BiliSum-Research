import { spawnSync } from "node:child_process";
import process from "node:process";

const DEV_PORTS = [3000, 3838];
const repoRoot = process.cwd();

function listeningPids(port) {
  if (process.platform === "win32") {
    const result = spawnSync("netstat", ["-ano", "-p", "tcp"], {
      encoding: "utf8",
      windowsHide: true,
    });
    const pids = new Set();
    for (const line of String(result.stdout || "").split(/\r?\n/)) {
      const fields = line.trim().split(/\s+/);
      if (fields.length < 5 || fields[0] !== "TCP") {
        continue;
      }
      const localAddress = fields[1] || "";
      const state = fields[3] || "";
      if (state !== "LISTENING" || !localAddress.endsWith(`:${port}`)) {
        continue;
      }
      const pid = Number(fields[4]);
      if (Number.isInteger(pid) && pid > 0 && pid !== process.pid) {
        pids.add(pid);
      }
    }
    return [...pids];
  }

  const result = spawnSync("sh", ["-c", `lsof -tiTCP:${port} -sTCP:LISTEN 2>/dev/null`], {
    encoding: "utf8",
  });
  return String(result.stdout || "")
    .split(/\r?\n/)
    .map((value) => Number(value.trim()))
    .filter((pid) => Number.isInteger(pid) && pid > 0 && pid !== process.pid);
}

function killTree(pid) {
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/F", "/T", "/PID", String(pid)], {
      stdio: "ignore",
      windowsHide: true,
    });
    return;
  }
  try {
    process.kill(pid, "SIGTERM");
  } catch {
    // The process may have exited between discovery and cleanup.
  }
}

const stalePids = new Set(DEV_PORTS.flatMap(listeningPids));
for (const pid of stalePids) {
  console.log(`[dev-cleanup] stopping stale process ${pid} on a dev port`);
  killTree(pid);
}

if (stalePids.size > 0) {
  spawnSync(process.platform === "win32" ? "powershell" : "sleep", process.platform === "win32"
    ? ["-NoProfile", "-Command", "Start-Sleep -Milliseconds 500"]
    : ["0.5"], { stdio: "ignore", windowsHide: true });
}

console.log(`[dev-cleanup] ready: ${repoRoot}`);
