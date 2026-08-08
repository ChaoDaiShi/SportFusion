import ipaddress
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _is_loopback_destination(address):
    if not isinstance(address, tuple) or not address:
        return True

    host = address[0]
    if host == "localhost":
        return True

    try:
        return ipaddress.ip_address(host).is_loopback
    except (TypeError, ValueError):
        return False


@pytest.fixture(scope="session", autouse=True)
def block_external_network():
    monkeypatch = pytest.MonkeyPatch()
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def blocked_connect(sock, address):
        if _is_loopback_destination(address):
            return original_connect(sock, address)
        raise RuntimeError(f"tests must not access external network: {address}")

    def blocked_connect_ex(sock, address):
        if _is_loopback_destination(address):
            return original_connect_ex(sock, address)
        raise RuntimeError(f"tests must not access external network: {address}")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked_connect_ex)
    yield
    monkeypatch.undo()
