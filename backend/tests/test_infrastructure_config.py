"""
Unit tests for configuration loading, saving, and env-var overrides.

Subject: infrastructure/config.py — load_config, save_config
Scope:   YAML I/O, defaults, parse-error handling, and DOCASSIST_* env var overrides.
Out of scope:
  - Default config values verified by existing tests  → test_config.py
  - LLM factory fast-model fallback                   → test_config.py
Setup:   Temporary files for YAML round-tripping; monkeypatch for env vars.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from infrastructure.config import AppConfig, load_config, save_config


# ---------------------------------------------------------------------------
# load_config — YAML parse errors
# ---------------------------------------------------------------------------


def test_load_config_raises_on_invalid_yaml():
    """A malformed YAML file must propagate the parser error (yaml.YAMLError)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("ollama: [not_valid: yaml: content")
        tmp_path = Path(f.name)

    try:
        with pytest.raises(yaml.YAMLError):
            load_config(tmp_path)
    finally:
        tmp_path.unlink()


# ---------------------------------------------------------------------------
# save_config + load_config round-trip
# ---------------------------------------------------------------------------


def test_save_config_writes_readable_yaml():
    """save_config() must produce a file that load_config() can read back."""
    original = AppConfig(
        llm_provider="ollama",
        ollama={"base_url": "http://other:11434", "generation_model": "qwen2.5", "timeout": 120},
        chunking={"max_tokens": 256, "overlap_tokens": 64},
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        tmp_path = Path(f.name)

    try:
        save_config(original, tmp_path)
        assert tmp_path.exists()

        reloaded = load_config(tmp_path)
        assert reloaded.llm_provider == "ollama"
        assert reloaded.ollama.base_url == "http://other:11434"
        assert reloaded.ollama.generation_model == "qwen2.5"
        assert reloaded.ollama.timeout == 120
        assert reloaded.chunking.max_tokens == 256
        assert reloaded.chunking.overlap_tokens == 64
    finally:
        tmp_path.unlink()


def test_save_config_omits_empty_api_keys():
    """save_config() must not write API keys into the YAML file."""
    config = AppConfig(groq={"api_key": "secret"})

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        tmp_path = Path(f.name)

    try:
        save_config(config, tmp_path)
        raw = tmp_path.read_text()
        assert "secret" not in raw
    finally:
        tmp_path.unlink()


def test_save_config_preserves_optional_fast_model():
    """When a fast_model is set, save_config must include it in the output."""
    config = AppConfig(ollama={"fast_model": "orca-mini:3b"})

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        tmp_path = Path(f.name)

    try:
        save_config(config, tmp_path)
        data = yaml.safe_load(tmp_path.read_text())
        assert data["ollama"]["fast_model"] == "orca-mini:3b"
    finally:
        tmp_path.unlink()


def test_save_config_skips_none_fast_model():
    """When fast_model is None, save_config must omit the key from the output."""
    config = AppConfig()
    config.ollama.fast_model = None

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        tmp_path = Path(f.name)

    try:
        save_config(config, tmp_path)
        data = yaml.safe_load(tmp_path.read_text())
        assert "fast_model" not in data.get("ollama", {})
    finally:
        tmp_path.unlink()


# ---------------------------------------------------------------------------
# Env var overrides
# ---------------------------------------------------------------------------


def test_env_override_nested_ollama(monkeypatch):
    """DOCASSIST_OLLAMA__BASE_URL must override the default ollama base_url."""
    monkeypatch.setenv("DOCASSIST_OLLAMA__BASE_URL", "http://override:11434")
    config = load_config(Path("/nonexistent/config.yml"))
    assert config.ollama.base_url == "http://override:11434"


def test_env_override_deeply_nested(monkeypatch):
    """DOCASSIST_CHUNKING__MAX_TOKENS must override the chunking max_tokens default."""
    monkeypatch.setenv("DOCASSIST_CHUNKING__MAX_TOKENS", "1024")
    config = load_config(Path("/nonexistent/config.yml"))
    assert config.chunking.max_tokens == 1024


def test_env_override_wins_over_yaml(monkeypatch):
    """An env var must take precedence over a value present in the YAML file."""
    data = {"llm_provider": "groq", "ollama": {"base_url": "http://yaml:11434"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(data, f)
        tmp_path = Path(f.name)

    monkeypatch.setenv("DOCASSIST_OLLAMA__BASE_URL", "http://env:11434")

    try:
        config = load_config(tmp_path)
        assert config.ollama.base_url == "http://env:11434"
        assert config.llm_provider == "groq"
    finally:
        tmp_path.unlink()


def test_env_override_creates_missing_intermediate_nodes(monkeypatch):
    """An env var for a nested key must create intermediate dicts if they don't exist."""
    monkeypatch.setenv("DOCASSIST_EXAM__COOLDOWN_AFTER_FAIL_HOURS", "4")
    config = load_config(Path("/nonexistent/config.yml"))
    assert config.exam.cooldown_after_fail_hours == 4


def test_env_prefix_is_case_sensitive(monkeypatch):
    """Variables without the DOCASSIST_ prefix must not affect configuration."""
    monkeypatch.setenv("OTHER_PREFIX__FOO", "bar")
    config = load_config(Path("/nonexistent/config.yml"))
    # Should use defaults without crashing
    assert isinstance(config, AppConfig)
    assert config.llm_provider == "groq"
