import asyncio

import api.index


def test_amap_config_does_not_leak_web_key(monkeypatch):
    monkeypatch.setattr(api.index, "AMAP_JS_API_KEY", "")
    monkeypatch.setattr(api.index, "AMAP_SECURITY_JS_CODE", "sec-code")
    monkeypatch.setattr(api.index, "AMAP_API_KEY", "web-secret")
    monkeypatch.setattr(api.index, "config", None)

    result = asyncio.run(api.index.get_amap_config())

    assert result["api_key"] == ""
    assert "web-secret" not in result.values()
    assert result["security_js_code"] == "sec-code"


def test_amap_config_returns_js_key_when_configured(monkeypatch):
    monkeypatch.setattr(api.index, "AMAP_JS_API_KEY", "js-key")
    monkeypatch.setattr(api.index, "AMAP_API_KEY", "web-secret")
    monkeypatch.setattr(api.index, "config", None)

    result = asyncio.run(api.index.get_amap_config())

    assert result["api_key"] == "js-key"
