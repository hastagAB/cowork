const { contextBridge, ipcRenderer } = require("electron");

// Expose a safe API to the renderer process
contextBridge.exposeInMainWorld("cowork", {
  // Task operations
  startTask: (goal, files) => ipcRenderer.invoke("start-task", goal, files),
  
  // Config
  getConfig: () => ipcRenderer.invoke("get-config"),
  setConfig: (key, value) => ipcRenderer.invoke("set-config", key, value),

  // Tools
  listTools: () => ipcRenderer.invoke("list-tools"),

  // Health
  pingSidecar: () => ipcRenderer.invoke("ping-sidecar"),

  // File dialogs
  selectFolder: () => ipcRenderer.invoke("select-folder"),
  selectFiles: () => ipcRenderer.invoke("select-files"),

  // Sidecar events (from Python agent)
  onSidecarEvent: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on("sidecar-event", handler);
    // Return cleanup function
    return () => ipcRenderer.removeListener("sidecar-event", handler);
  },
});
