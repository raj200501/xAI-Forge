from __future__ import annotations

import importlib

from xaiforge.compat.fastapi import TestClient


def test_health_endpoint_enabled(monkeypatch) -> None:
    monkeypatch.setenv("XAIFORGE_ENABLE_HEALTH", "1")
    monkeypatch.setenv("XAIFORGE_ENABLE_LOGGING", "0")
    monkeypatch.setenv("XAIFORGE_ENABLE_OTEL", "0")
    server = importlib.import_module("xaiforge.server")
    importlib.reload(server)
    client = TestClient(server.app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
