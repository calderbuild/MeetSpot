from pathlib import Path

import pytest

from app.config import Config


def _default_llm(monkeypatch: pytest.MonkeyPatch, config_path: Path):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_BASE", raising=False)
    monkeypatch.setattr(Config, "_get_config_path", staticmethod(lambda: config_path))
    # Bypass the singleton so each test resolves the config from scratch.
    cfg = object.__new__(Config)
    cfg._config = None
    cfg._load_initial_config()
    return cfg.llm["default"]


def test_missing_config_falls_back_to_deepseek(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _default_llm(monkeypatch, tmp_path / "config.toml")

    assert llm.model == "deepseek-flash"
    assert llm.base_url == "https://api.deepseek.com"


def test_malformed_config_falls_back_to_deepseek(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[llm\nmodel =", encoding="utf-8")

    llm = _default_llm(monkeypatch, config_path)

    assert llm.model == "deepseek-flash"
    assert llm.base_url == "https://api.deepseek.com"
