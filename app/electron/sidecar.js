const { spawn } = require("child_process");
const path = require("path");
const readline = require("readline");

class SidecarManager {
  constructor(onEvent) {
    this.process = null;
    this.onEvent = onEvent || (() => {});
    this._requestId = 0;
    this._pendingRequests = new Map();
    this._ready = false;
    this._readyPromise = null;
    this._readyResolve = null;
  }

  async start() {
    const sidecarDir = path.resolve(__dirname, "..", "..", "sidecar");

    // Try to find Python in the sidecar's venv first, then system Python
    const venvPython = process.platform === "win32"
      ? path.join(sidecarDir, ".venv", "Scripts", "python.exe")
      : path.join(sidecarDir, ".venv", "bin", "python");

    let pythonPath;
    const fs = require("fs");
    if (fs.existsSync(venvPython)) {
      pythonPath = venvPython;
    } else {
      pythonPath = "python";
    }

    this._readyPromise = new Promise((resolve) => {
      this._readyResolve = resolve;
    });

    console.log(`Starting sidecar: ${pythonPath} -m cowork`);

    this.process = spawn(pythonPath, ["-m", "cowork"], {
      cwd: sidecarDir,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    // Read stdout line by line (JSON-RPC messages)
    const rl = readline.createInterface({ input: this.process.stdout });
    rl.on("line", (line) => {
      this._handleLine(line);
    });

    // Log stderr
    this.process.stderr.on("data", (data) => {
      console.error(`[sidecar stderr] ${data.toString().trim()}`);
    });

    this.process.on("exit", (code) => {
      console.log(`Sidecar exited with code ${code}`);
      this._ready = false;
      // Reject any pending requests
      for (const [id, { reject }] of this._pendingRequests) {
        reject(new Error("Sidecar process exited"));
      }
      this._pendingRequests.clear();
      // Notify renderer that sidecar disconnected
      this.onEvent({ type: "sidecar_disconnected", code });
    });

    this.process.on("error", (err) => {
      console.error("Sidecar spawn error:", err.message);
    });

    // Wait for the "ready" signal from the sidecar
    const timeout = new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Sidecar startup timed out (10s)")), 10000)
    );

    await Promise.race([this._readyPromise, timeout]);
    this._ready = true;
    console.log("Sidecar is ready");
  }

  stop() {
    if (this.process) {
      this.process.kill();
      this.process = null;
      this._ready = false;
    }
  }

  isRunning() {
    return this._ready && this.process && !this.process.killed;
  }

  sendRequest(method, params) {
    return new Promise((resolve, reject) => {
      if (!this.isRunning()) {
        return reject(new Error("Sidecar is not running"));
      }

      const id = ++this._requestId;
      const request = {
        jsonrpc: "2.0",
        method,
        params,
        id,
      };

      this._pendingRequests.set(id, { resolve, reject });

      // Set a timeout for the request (5 minutes for long tasks)
      const timer = setTimeout(() => {
        if (this._pendingRequests.has(id)) {
          this._pendingRequests.delete(id);
          reject(new Error(`Request ${method} timed out after 5 minutes`));
        }
      }, 300000);

      this._pendingRequests.set(id, { resolve, reject, timer });

      const line = JSON.stringify(request) + "\n";
      this.process.stdin.write(line);
    });
  }

  _handleLine(line) {
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      console.warn("[sidecar] Non-JSON output:", line);
      return;
    }

    // Notification/event (no id)
    if (msg.method && msg.id === undefined) {
      if (msg.method === "ready") {
        if (this._readyResolve) this._readyResolve();
        return;
      }
      // Forward agent events to the renderer
      this.onEvent(msg.params || {});
      return;
    }

    // Response to a request
    if (msg.id !== undefined && msg.id !== null) {
      const pending = this._pendingRequests.get(msg.id);
      if (pending) {
        clearTimeout(pending.timer);
        this._pendingRequests.delete(msg.id);
        if (msg.error) {
          pending.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
        } else {
          pending.resolve(msg.result);
        }
      }
    }
  }
}

module.exports = { SidecarManager };
