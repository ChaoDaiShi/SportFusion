import asyncio
import socket

import pytest

import conftest as project_conftest

COLLECTION_GUARD_WAS_ACTIVE = bool(
    getattr(socket.socket.connect, "__sportfusion_network_guard__", False)
)
assert COLLECTION_GUARD_WAS_ACTIVE, "network guard must be installed before collection"
assert getattr(
    asyncio.BaseEventLoop.create_connection,
    "__sportfusion_network_guard__",
    False,
), "asyncio network guard must be installed before collection"


class _NeverNetworkSocket:
    """A socket-shaped object that makes accidental real I/O impossible."""


@pytest.mark.parametrize(
    ("method_name", "address"),
    [
        ("connect", ("198.51.100.1", 443)),
        ("connect_ex", ("198.51.100.1", 443)),
        ("connect", ("2001:db8::1", 443, 0, 0)),
        ("connect_ex", ("2001:db8::1", 443, 0, 0)),
    ],
)
def test_tcp_guard_rejects_non_loopback_destinations(method_name, address):
    with pytest.raises(RuntimeError, match="tests must not access external network"):
        getattr(socket.socket, method_name)(_NeverNetworkSocket(), address)


@pytest.mark.parametrize(
    ("method_name", "host"),
    [
        ("getaddrinfo", "example.com"),
        ("gethostbyname", "example.com"),
        ("gethostbyname_ex", "example.com"),
        ("gethostbyaddr", "198.51.100.1"),
    ],
)
def test_dns_guard_rejects_external_hosts(method_name, host):
    arguments = (host, 443) if method_name == "getaddrinfo" else (host,)
    with pytest.raises(RuntimeError, match="tests must not access external network"):
        getattr(socket, method_name)(*arguments)


def test_getnameinfo_guard_rejects_external_addresses():
    with pytest.raises(RuntimeError, match="tests must not access external network"):
        socket.getnameinfo(("198.51.100.1", 443), 0)


@pytest.mark.parametrize("with_flags", [False, True])
def test_udp_sendto_guard_rejects_external_destinations(with_flags):
    arguments = (b"payload", 0, ("198.51.100.1", 53)) if with_flags else (
        b"payload",
        ("198.51.100.1", 53),
    )
    with pytest.raises(RuntimeError, match="tests must not access external network"):
        socket.socket.sendto(_NeverNetworkSocket(), *arguments)


@pytest.mark.skipif(not hasattr(socket.socket, "sendmsg"), reason="sendmsg unavailable")
def test_udp_sendmsg_guard_rejects_external_destinations():
    with pytest.raises(RuntimeError, match="tests must not access external network"):
        socket.socket.sendmsg(
            _NeverNetworkSocket(),
            [b"payload"],
            [],
            0,
            ("198.51.100.1", 53),
        )


def test_allowed_destinations_delegate_without_real_network(monkeypatch):
    calls = []
    expected_operations = {
        "connect",
        "connect_ex",
        "sendto",
        "getaddrinfo",
        "gethostbyname",
        "gethostbyname_ex",
        "gethostbyaddr",
        "getnameinfo",
    }
    if hasattr(socket.socket, "sendmsg"):
        expected_operations.add("sendmsg")

    def spy(operation):
        def record(*args, **kwargs):
            calls.append((operation, args, kwargs))
            return operation

        return record

    for operation in expected_operations:
        monkeypatch.setitem(
            project_conftest._NETWORK_ORIGINALS,
            operation,
            spy(operation),
        )

    sock = _NeverNetworkSocket()
    assert socket.socket.connect(sock, ("127.0.0.1", 8000)) == "connect"
    assert socket.socket.connect_ex(sock, ("::1", 8000, 0, 0)) == "connect_ex"
    assert socket.socket.connect(sock, "/tmp/sportfusion-test.sock") == "connect"
    assert socket.socket.sendto(sock, b"payload", ("localhost", 53)) == "sendto"
    assert socket.socket.sendto(sock, b"payload", 0, ("127.0.0.1", 53)) == "sendto"
    assert socket.getaddrinfo("localhost", 8000) == "getaddrinfo"
    assert socket.gethostbyname("127.0.0.1") == "gethostbyname"
    assert socket.gethostbyname_ex("localhost") == "gethostbyname_ex"
    assert socket.gethostbyaddr("::1") == "gethostbyaddr"
    assert socket.getnameinfo(("::1", 8000, 0, 0), 0) == "getnameinfo"

    if hasattr(socket.socket, "sendmsg"):
        assert (
            socket.socket.sendmsg(sock, [b"payload"], [], 0, ("::1", 53, 0, 0))
            == "sendmsg"
        )

    assert {operation for operation, _, _ in calls} == expected_operations


@pytest.mark.parametrize(
    "address",
    [
        ("127.0.0.1", 8000),
        ("::1", 8000, 0, 0),
        ("::1%1", 8000, 0, 1),
        ("localhost", 8000),
        "/tmp/sportfusion-test.sock",
    ],
)
def test_loopback_and_local_socket_destinations_are_allowed(address):
    assert project_conftest._is_loopback_destination(address)


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("::ffff:127.0.0.1", True),
        ("::ffff:127.23.45.67", True),
        ("::ffff:198.51.100.1", False),
    ],
)
def test_ipv4_mapped_ipv6_uses_mapped_ipv4_loopback_status(host, expected):
    assert project_conftest._is_loopback_host(host) is expected


@pytest.mark.parametrize(
    "host",
    ["example.com", "198.51.100.1", "2001:db8::1", "::ffff:198.51.100.1"],
)
def test_asyncio_create_connection_rejects_external_hosts(host):
    async def exercise():
        await asyncio.BaseEventLoop.create_connection(
            object(),
            lambda: None,
            host=host,
            port=443,
        )

    with pytest.raises(RuntimeError, match="tests must not access external network"):
        asyncio.run(exercise())


@pytest.mark.parametrize(
    "host",
    ["example.com", "198.51.100.1", "2001:db8::1", "::ffff:198.51.100.1"],
)
def test_asyncio_create_datagram_endpoint_rejects_external_hosts(host):
    async def exercise():
        await asyncio.BaseEventLoop.create_datagram_endpoint(
            object(),
            lambda: None,
            remote_addr=(host, 53),
        )

    with pytest.raises(RuntimeError, match="tests must not access external network"):
        asyncio.run(exercise())


def test_asyncio_high_level_guard_delegates_none_and_loopback(monkeypatch):
    calls = []

    async def connection_spy(*args, **kwargs):
        calls.append(("asyncio_create_connection", args, kwargs))
        return "connection"

    async def datagram_spy(*args, **kwargs):
        calls.append(("asyncio_create_datagram_endpoint", args, kwargs))
        return "datagram"

    monkeypatch.setitem(
        project_conftest._NETWORK_ORIGINALS,
        "asyncio_create_connection",
        connection_spy,
    )
    monkeypatch.setitem(
        project_conftest._NETWORK_ORIGINALS,
        "asyncio_create_datagram_endpoint",
        datagram_spy,
    )

    async def exercise():
        loop = object()
        assert (
            await asyncio.BaseEventLoop.create_connection(
                loop,
                lambda: None,
                host=None,
                port=None,
                sock=object(),
            )
            == "connection"
        )
        assert (
            await asyncio.BaseEventLoop.create_connection(
                loop,
                lambda: None,
                host="::ffff:127.0.0.1",
                port=8000,
            )
            == "connection"
        )
        assert (
            await asyncio.BaseEventLoop.create_datagram_endpoint(
                loop,
                lambda: None,
                remote_addr=None,
            )
            == "datagram"
        )
        assert (
            await asyncio.BaseEventLoop.create_datagram_endpoint(
                loop,
                lambda: None,
                remote_addr=("::1", 53),
            )
            == "datagram"
        )

    asyncio.run(exercise())
    assert [operation for operation, _, _ in calls] == [
        "asyncio_create_connection",
        "asyncio_create_connection",
        "asyncio_create_datagram_endpoint",
        "asyncio_create_datagram_endpoint",
    ]


@pytest.mark.skipif(
    not hasattr(asyncio, "ProactorEventLoop"),
    reason="Windows ProactorEventLoop unavailable",
)
@pytest.mark.parametrize(
    ("method_name", "arguments"),
    [
        ("sock_connect", (object(), ("example.com", 443))),
        ("sock_connect", (object(), ("198.51.100.1", 443))),
        ("sock_connect", (object(), ("2001:db8::1", 443, 0, 0))),
        ("sock_connect", (object(), ("::ffff:198.51.100.1", 443, 0, 0))),
        ("sock_sendto", (object(), b"payload", ("example.com", 53))),
        ("sock_sendto", (object(), b"payload", ("198.51.100.1", 53))),
        ("sock_sendto", (object(), b"payload", ("2001:db8::1", 53, 0, 0))),
        (
            "sock_sendto",
            (object(), b"payload", ("::ffff:198.51.100.1", 53, 0, 0)),
        ),
    ],
)
def test_proactor_guard_rejects_external_numeric_addresses(method_name, arguments):
    async def exercise():
        await getattr(asyncio.ProactorEventLoop, method_name)(object(), *arguments)

    with pytest.raises(RuntimeError, match="tests must not access external network"):
        asyncio.run(exercise())


@pytest.mark.skipif(
    not hasattr(asyncio, "ProactorEventLoop"),
    reason="Windows ProactorEventLoop unavailable",
)
def test_proactor_guard_delegates_loopback_without_real_network(monkeypatch):
    calls = []

    async def connect_spy(*args, **kwargs):
        calls.append(("proactor_sock_connect", args, kwargs))
        return "connect"

    async def sendto_spy(*args, **kwargs):
        calls.append(("proactor_sock_sendto", args, kwargs))
        return "sendto"

    monkeypatch.setitem(
        project_conftest._NETWORK_ORIGINALS,
        "proactor_sock_connect",
        connect_spy,
    )
    monkeypatch.setitem(
        project_conftest._NETWORK_ORIGINALS,
        "proactor_sock_sendto",
        sendto_spy,
    )

    async def exercise():
        loop = object()
        sock = object()
        assert (
            await asyncio.ProactorEventLoop.sock_connect(
                loop,
                sock,
                ("::ffff:127.0.0.1", 8000),
            )
            == "connect"
        )
        assert (
            await asyncio.ProactorEventLoop.sock_sendto(
                loop,
                sock,
                b"payload",
                ("::1", 53, 0, 0),
            )
            == "sendto"
        )

    asyncio.run(exercise())
    assert [operation for operation, _, _ in calls] == [
        "proactor_sock_connect",
        "proactor_sock_sendto",
    ]


def test_network_guard_install_and_restore_are_idempotent():
    active_patch = project_conftest._NETWORK_MONKEYPATCH
    original_connect = project_conftest._NETWORK_ORIGINALS["connect"]

    project_conftest._install_network_guard()
    assert project_conftest._NETWORK_MONKEYPATCH is active_patch

    try:
        project_conftest._restore_network_guard()
        assert project_conftest._NETWORK_MONKEYPATCH is None
        assert socket.socket.connect is original_connect
        project_conftest._restore_network_guard()
    finally:
        project_conftest._install_network_guard()

    assert getattr(socket.socket.connect, "__sportfusion_network_guard__", False)
