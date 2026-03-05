const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const { SidecarManager } = require("./sidecar");

let mainWindow = null;
let sidecar = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "Cowork",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Dev mode: load from Vite dev server; Prod: load built files
  const isDev = process.env.NODE_ENV !== "production" || !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// --- IPC Handlers ---

ipcMain.handle("start-task", async (_event, goal, files) => {
  if (!sidecar || !sidecar.isRunning()) {
    return { error: "Sidecar not running. Check your Python installation." };
  }
  return sidecar.sendRequest("start_task", { goal, files: files || [] });
});

ipcMain.handle("get-config", async () => {
  if (!sidecar || !sidecar.isRunning()) {
    return { error: "Sidecar not running" };
  }
  return sidecar.sendRequest("get_config", {});
});

ipcMain.handle("set-config", async (_event, key, value) => {
  if (!sidecar || !sidecar.isRunning()) {
    return { error: "Sidecar not running" };
  }
  return sidecar.sendRequest("set_config", { key, value });
});

ipcMain.handle("list-tools", async () => {
  if (!sidecar || !sidecar.isRunning()) {
    return { error: "Sidecar not running" };
  }
  return sidecar.sendRequest("list_tools", {});
});

ipcMain.handle("ping-sidecar", async () => {
  if (!sidecar || !sidecar.isRunning()) {
    return { ok: false, error: "Sidecar not running" };
  }
  try {
    const result = await sidecar.sendRequest("ping", {});
    return { ok: true, ...result };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
  });
  if (result.canceled) return null;
  return result.filePaths[0];
});

ipcMain.handle("select-files", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile", "multiSelections"],
  });
  if (result.canceled) return [];
  return result.filePaths;
});

// --- App Lifecycle ---

app.whenReady().then(async () => {
  // Start sidecar FIRST so it's ready before the page loads
  sidecar = new SidecarManager((event) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("sidecar-event", event);
    }
  });

  try {
    await sidecar.start();
    console.log("Sidecar started successfully");
  } catch (err) {
    console.error("Failed to start sidecar:", err.message);
  }

  // Now create window — page loads after sidecar is ready
  createWindow();
});

app.on("window-all-closed", () => {
  if (sidecar) sidecar.stop();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on("before-quit", () => {
  if (sidecar) sidecar.stop();
});
