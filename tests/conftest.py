import socket
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    def blocked_connect(sock, address):
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1", "localhost"}:
            return original_connect(sock, address)
        raise AssertionError(f"tests must not access external network: {address}")

    original_connect = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
