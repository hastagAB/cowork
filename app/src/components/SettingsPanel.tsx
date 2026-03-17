import { useState, useEffect } from "react";
import { useAppStore } from "../store";

export function SettingsPanel() {
  const { config, setConfig } = useAppStore();
  const [apiKey, setApiKey] = useState("");
  const [provider, setProvider] = useState(config?.llm.provider || "openai");
  const [model, setModel] = useState(config?.llm.model || "gpt-4o");
  const [baseUrl, setBaseUrl] = useState(config?.llm.base_url || "");
  const [endpoint, setEndpoint] = useState(config?.llm.endpoint || "");
  const [deployment, setDeployment] = useState(config?.llm.deployment || "");
  const [apiVersion, setApiVersion] = useState(config?.llm.api_version || "2024-12-01-preview");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config) {
      setProvider(config.llm.provider);
      setModel(config.llm.model);
      setBaseUrl(config.llm.base_url || "");
      setEndpoint(config.llm.endpoint || "");
      setDeployment(config.llm.deployment || "");
      setApiVersion(config.llm.api_version || "");
    }
  }, [config]);

  const saveField = async (key: string, value: string) => {
    if (!window.cowork) return;
    try {
      await window.cowork.setConfig(key, value);
      const updated = await window.cowork.getConfig();
      if (updated && !("error" in updated)) setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Failed to save config:", err);
    }
  };

  const saveAll = async () => {
    if (!window.cowork) return;
    try {
      const save = async (key: string, value: string) => {
        const res = await window.cowork.setConfig(key, value);
        if (res && "error" in res) throw new Error(String(res.error));
      };
      await save("llm.provider", provider);
      await save("llm.model", model);
      if (apiKey) await save("llm.api_key", apiKey);
      if (provider === "azure_openai") {
        await save("llm.endpoint", endpoint);
        await save("llm.deployment", deployment);
        await save("llm.api_version", apiVersion);
      }
      if (provider === "ollama") {
        await save("llm.base_url", baseUrl);
      }
      const updated = await window.cowork.getConfig();
      if (updated && !("error" in updated)) setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Failed to save config:", err);
      alert("Failed to save settings. Check if the agent is connected.");
    }
  };

  return (
    <div className="settings-panel">
      <h2>Settings</h2>

      {saved && (
        <div
          style={{
            padding: "8px 14px",
            background: "rgba(52, 211, 153, 0.15)",
            color: "var(--success)",
            borderRadius: "var(--radius)",
            fontSize: "13px",
            marginBottom: "16px",
          }}
        >
          ✓ Settings saved
        </div>
      )}

      <div className="settings-group">
        <h3>LLM Provider</h3>

        <div className="setting-row">
          <span className="setting-label">Provider</span>
          <select
            className="setting-select"
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value);
              saveField("llm.provider", e.target.value);
            }}
          >
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="openai">OpenAI (GPT)</option>
            <option value="azure_openai">Azure OpenAI</option>
            <option value="ollama">Ollama (Local)</option>
          </select>
        </div>

        <div className="setting-row">
          <span className="setting-label">Model</span>
          <input
            className="setting-input"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            onBlur={() => saveField("llm.model", model)}
            placeholder="claude-sonnet-4-20250514"
          />
        </div>

        <div className="setting-row">
          <span className="setting-label">API Key</span>
          <input
            className="setting-input"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onBlur={() => {
              if (apiKey) saveField("llm.api_key", apiKey);
            }}
            placeholder={config?.llm.has_api_key ? "••••••••••• (set)" : "Enter API key"}
          />
        </div>

        {provider === "ollama" && (
          <div className="setting-row">
            <span className="setting-label">Base URL</span>
            <input
              className="setting-input"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              onBlur={() => saveField("llm.base_url", baseUrl)}
              placeholder="http://localhost:11434/v1"
            />
          </div>
        )}

        {provider === "azure_openai" && (
          <>
            <div className="setting-row">
              <span className="setting-label">Endpoint</span>
              <input
                className="setting-input"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                onBlur={() => saveField("llm.endpoint", endpoint)}
                placeholder="https://your-resource.openai.azure.com"
              />
            </div>
            <div className="setting-row">
              <span className="setting-label">Deployment</span>
              <input
                className="setting-input"
                value={deployment}
                onChange={(e) => setDeployment(e.target.value)}
                onBlur={() => saveField("llm.deployment", deployment)}
                placeholder="gpt-4o"
              />
            </div>
            <div className="setting-row">
              <span className="setting-label">API Version</span>
              <input
                className="setting-input"
                value={apiVersion}
                onChange={(e) => setApiVersion(e.target.value)}
                onBlur={() => saveField("llm.api_version", apiVersion)}
                placeholder="2024-12-01-preview"
              />
            </div>
          </>
        )}

        <div style={{ marginTop: "12px" }}>
          <button
            className="goal-submit"
            onClick={saveAll}
            style={{ width: "100%" }}
          >
            Save LLM Settings
          </button>
        </div>
      </div>

      <div className="settings-group">
        <h3>Permissions</h3>

        <div className="setting-row">
          <span className="setting-label">Confirm destructive operations</span>
          <select
            className="setting-select"
            value={config?.permissions.confirm_destructive ? "true" : "false"}
            onChange={(e) => saveField("permissions.confirm_destructive", e.target.value)}
          >
            <option value="true">Yes (recommended)</option>
            <option value="false">No</option>
          </select>
        </div>

        <div className="setting-row">
          <span className="setting-label">Dry-run mode</span>
          <select
            className="setting-select"
            value={config?.permissions.dry_run ? "true" : "false"}
            onChange={(e) => saveField("permissions.dry_run", e.target.value)}
          >
            <option value="false">Off — execute tasks normally</option>
            <option value="true">On — plan only, don't execute</option>
          </select>
        </div>
      </div>

      <div className="settings-group">
        <h3>Agent</h3>

        <div className="setting-row">
          <span className="setting-label">Max steps per task</span>
          <input
            className="setting-input"
            type="number"
            value={config?.agent.max_steps_per_task || 50}
            onChange={(e) => saveField("agent.max_steps_per_task", e.target.value)}
            min={1}
            max={200}
          />
        </div>

        <div className="setting-row">
          <span className="setting-label">Max re-plans</span>
          <input
            className="setting-input"
            type="number"
            value={config?.agent.max_replans || 3}
            onChange={(e) => saveField("agent.max_replans", e.target.value)}
            min={0}
            max={10}
          />
        </div>
      </div>

      <div className="settings-group">
        <h3>About</h3>
        <div style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.8 }}>
          <div>Cowork v0.1.0</div>
          <div>Local-first AI desktop agent for knowledge work</div>
          <div>Data stored in ~/.cowork/</div>
        </div>
      </div>
    </div>
  );
}
