"""Tests for configuration management."""

import pytest

from cowork.models import AppConfig
from cowork.storage.config import load_config, save_config


def test_default_config():
    config = AppConfig()
    assert config.llm.provider == "azure_openai"
    assert config.llm.temperature == 0.3
    assert config.permissions.confirm_destructive is True
    assert config.agent.max_steps_per_task == 50


def test_config_round_trip(tmp_path, monkeypatch):
    # Point config to a temp dir
    import cowork.storage.config as cfg
    monkeypatch.setattr(cfg, "COWORK_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_PATH", tmp_path / "config.toml")

    config = AppConfig()
    config.llm.provider = "ollama"
    config.llm.model = "llama3"
    config.agent.max_steps_per_task = 100

    save_config(config)
    loaded = load_config()

    assert loaded.llm.provider == "ollama"
    assert loaded.llm.model == "llama3"
    assert loaded.agent.max_steps_per_task == 100
