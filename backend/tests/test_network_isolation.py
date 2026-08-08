import socket

import pytest

from conftest import _is_loopback_destination


class _NeverConnectSocket:
    """A socket-shaped object that makes an accidental real connect impossible."""


def test_backend_tests_block_non_loopback_destinations_before_connecting():
    with pytest.raises(RuntimeError, match=r"tests must not access external network: \('198\.51\.100\.1', 443\)"):
        socket.socket.connect(_NeverConnectSocket(), ("198.51.100.1", 443))


@pytest.mark.parametrize("address", [("127.0.0.1", 8000), ("::1", 8000, 0, 0)])
def test_loopback_destinations_remain_allowed(address):
    assert _is_loopback_destination(address)
