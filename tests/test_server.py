from xaiforge.compat.fastapi import TestClient
from xaiforge.server import app


def test_api_metadata_endpoints() -> None:
    client = TestClient(app)
    tools = client.get("/api/tools")
    assert tools.status_code == 200
    assert isinstance(tools.json(), list)

    providers = client.get("/api/providers")
    assert providers.status_code == 200
    assert "heuristic" in providers.json()

    schema = client.get("/api/schema/events")
    assert schema.status_code == 200
    assert "oneOf" in schema.json() or "$defs" in schema.json()
