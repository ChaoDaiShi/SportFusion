import socket

import pytest

from conftest import _is_loopback_destination


class _NeverConnectSocket:
    """A socket-shaped object that makes an accidental real connect impossible."""


@pytest.mark.parametrize(
    ("method_name", "address"),
    [
        ("connect", ("198.51.100.1", 443)),
        ("connect_ex", ("198.51.100.1", 443)),
        ("connect", ("2001:db8::1", 443, 0, 0)),
        ("connect_ex", ("2001:db8::1", 443, 0, 0)),
    ],
)
def test_backend_tests_block_non_loopback_destinations_before_connecting(method_name, address):
    with pytest.raises(RuntimeError, match="tests must not access external network"):
        getattr(socket.socket, method_name)(_NeverConnectSocket(), address)


def test_network_guard_is_session_scoped(request):
    assert request._fixture_defs["block_external_network"].scope == "session"


@pytest.mark.parametrize("address", [("127.0.0.1", 8000), ("::1", 8000, 0, 0)])
def test_loopback_destinations_remain_allowed(address):
    assert _is_loopback_destination(address)
