"""Tests pour KIVA-CLI rootx_client."""

from src.rootx_client import RootxClient, RootxClientConfig, build_rootx_client


def test_build_rootx_client() -> None:
    client = build_rootx_client()
    assert isinstance(client, RootxClient)


def test_rootx_client_health() -> None:
    client = build_rootx_client(RootxClientConfig(endpoint="http://localhost:8795"))
    health = client.health()
    assert health["status"] == "ok"
    assert health["endpoint"] == "http://localhost:8795"


def test_rootx_client_query() -> None:
    client = build_rootx_client()
    result = client.query("root-1", {"key": "value"})
    assert result["root_id"] == "root-1"
    assert result["status"] == "accepted"
