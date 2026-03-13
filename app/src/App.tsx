import { useEffect } from "react";
import { useAppStore } from "./store";
import { Sidebar } from "./components/Sidebar";
import { GoalInput } from "./components/GoalInput";
import { TaskView } from "./components/TaskView";
import { SettingsPanel } from "./components/SettingsPanel";

export function App() {
  const { view, sidecarConnected, setSidecarConnected, handleSidecarEvent, setConfig } =
    useAppStore();

  useEffect(() => {
    // Listen for sidecar events
    let cleanup: (() => void) | undefined;
    if (window.cowork) {
      cleanup = window.cowork.onSidecarEvent((event) => {
        handleSidecarEvent(event);
      });

      // Check connection with retry
      const pingWithRetry = async (retries = 5, delay = 1000) => {
        for (let i = 0; i < retries; i++) {
          try {
            const res = await window.cowork.pingSidecar();
            if (res.ok) {
              setSidecarConnected(true);
              return;
            }
          } catch {
            // ignore
          }
          await new Promise((r) => setTimeout(r, delay));
        }
        setSidecarConnected(false);
      };
      pingWithRetry();

      // Load config
      window.cowork
        .getConfig()
        .then((config) => {
          if (config && !("error" in config)) setConfig(config);
        })
        .catch(() => {});
    }

    return () => {
      if (cleanup) cleanup();
    };
  }, [handleSidecarEvent, setSidecarConnected, setConfig]);

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        {view === "home" && <GoalInput />}
        {view === "task" && <TaskView />}
        {view === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
}
