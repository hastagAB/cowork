"""Configuration manager — reads/writes ~/.cowork/config.toml."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

from cowork.models import AppConfig

COWORK_DIR = Path.home() / ".cowork"
CONFIG_PATH = COWORK_DIR / "config.toml"

DEFAULT_CONFIG_TOML = """\
[llm]
provider = "azure_openai"
model = "gpt-5.2-2025-12-11"
base_url = ""
endpoint = "https://openai-aiattack-msa-001600-swedencentral-tandiexperiments-00.openai.azure.com"
deployment = "gpt-5.2-2025-12-11"
api_version = "2024-12-01-preview"
max_tokens = 4096
temperature = 0.3

[permissions]
allowed_paths = []
confirm_destructive = true
dry_run = false

[agent]
max_steps_per_task = 50
max_replans = 3
task_timeout_seconds = 600
"""


def ensure_cowork_dir() -> Path:
    """Create ~/.cowork/ and subdirectories if they don't exist."""
    for subdir in ["", "cache", "logs", "undo", "vectors", "templates"]:
        (COWORK_DIR / subdir).mkdir(parents=True, exist_ok=True)
    return COWORK_DIR


def load_config() -> AppConfig:
    """Load config from ~/.cowork/config.toml. Create default if missing."""
    ensure_cowork_dir()

    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")

    raw = CONFIG_PATH.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    return AppConfig(**data)


def _strip_none(d: dict) -> dict:
    """Recursively remove None values (TOML can't serialize None)."""
    cleaned = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, dict):
            cleaned[k] = _strip_none(v)
        else:
            cleaned[k] = v
    return cleaned


def save_config(config: AppConfig) -> None:
    """Save config to ~/.cowork/config.toml."""
    ensure_cowork_dir()
    data = _strip_none(config.model_dump())
    CONFIG_PATH.write_bytes(tomli_w.dumps(data).encode("utf-8"))


def get_config_value(key: str) -> str | None:
    """Get a dot-separated config value. e.g. 'llm.provider'."""
    config = load_config()
    parts = key.split(".")
    obj = config.model_dump()
    for part in parts:
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return None
    return str(obj)


def set_config_value(key: str, value: str) -> None:
    """Set a dot-separated config value. e.g. 'llm.model' = 'gpt-4o'."""
    config = load_config()
    data = config.model_dump()
    parts = key.split(".")
    obj = data
    for part in parts[:-1]:
        obj = obj[part]

    # Type coercion
    current = obj.get(parts[-1])
    if isinstance(current, bool):
        value = value.lower() in ("true", "1", "yes")
    elif isinstance(current, int):
        value = int(value)
    elif isinstance(current, float):
        value = float(value)

    obj[parts[-1]] = value
    save_config(AppConfig(**data))
