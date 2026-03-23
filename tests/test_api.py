"""API smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from masc_ahu_dwg2excel_api.api import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
