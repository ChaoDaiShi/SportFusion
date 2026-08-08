import ipaddress
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


_NETWORK_MONKEYPATCH = None
_NETWORK_ORIGINALS = {}


def _is_loopback_host(host):
    if host is None:
        return True
    if isinstance(host, bytes):
        try:
            host = host.decode("ascii")
        except UnicodeDecodeError:
            return False
    if not isinstance(host, str):
        return False

    normalized = host.rstrip(".").casefold()
    if normalized == "localhost":
        return True

    numeric_host = normalized.partition("%")[0]
    try:
        return ipaddress.ip_address(numeric_host).is_loopback
    except ValueError:
        return False


def _is_loopback_destination(address):
    if not isinstance(address, tuple) or not address:
        return True
    return _is_loopback_host(address[0])


def _reject_external(operation, destination):
    if not _is_loopback_destination(destination):
        raise RuntimeError(
            f"tests must not access external network via {operation}: {destination!r}"
        )


def _reject_external_host(operation, host):
    if not _is_loopback_host(host):
        raise RuntimeError(
            f"tests must not access external network via {operation}: {host!r}"
        )


def _guard_wrapper(function):
    function.__sportfusion_network_guard__ = True
    return function


@_guard_wrapper
def _blocked_connect(sock, address):
    _reject_external("connect", address)
    return _NETWORK_ORIGINALS["connect"](sock, address)


@_guard_wrapper
def _blocked_connect_ex(sock, address):
    _reject_external("connect_ex", address)
    return _NETWORK_ORIGINALS["connect_ex"](sock, address)


@_guard_wrapper
def _blocked_sendto(sock, data, *args, **kwargs):
    destination = kwargs.get("address", args[-1] if args else None)
    _reject_external("sendto", destination)
    return _NETWORK_ORIGINALS["sendto"](sock, data, *args, **kwargs)


@_guard_wrapper
def _blocked_sendmsg(sock, buffers, *args, **kwargs):
    destination = kwargs.get("address")
    if destination is None and len(args) >= 3:
        destination = args[-1]
    _reject_external("sendmsg", destination)
    return _NETWORK_ORIGINALS["sendmsg"](sock, buffers, *args, **kwargs)


@_guard_wrapper
def _blocked_getaddrinfo(host, *args, **kwargs):
    _reject_external_host("getaddrinfo", host)
    return _NETWORK_ORIGINALS["getaddrinfo"](host, *args, **kwargs)


@_guard_wrapper
def _blocked_gethostbyname(host):
    _reject_external_host("gethostbyname", host)
    return _NETWORK_ORIGINALS["gethostbyname"](host)


@_guard_wrapper
def _blocked_gethostbyname_ex(host):
    _reject_external_host("gethostbyname_ex", host)
    return _NETWORK_ORIGINALS["gethostbyname_ex"](host)


@_guard_wrapper
def _blocked_gethostbyaddr(host):
    _reject_external_host("gethostbyaddr", host)
    return _NETWORK_ORIGINALS["gethostbyaddr"](host)


@_guard_wrapper
def _blocked_getnameinfo(address, flags):
    _reject_external("getnameinfo", address)
    return _NETWORK_ORIGINALS["getnameinfo"](address, flags)


def _install_network_guard():
    global _NETWORK_MONKEYPATCH

    if _NETWORK_MONKEYPATCH is not None:
        return

    targets = {
        "connect": (socket.socket, "connect", _blocked_connect),
        "connect_ex": (socket.socket, "connect_ex", _blocked_connect_ex),
        "sendto": (socket.socket, "sendto", _blocked_sendto),
        "getaddrinfo": (socket, "getaddrinfo", _blocked_getaddrinfo),
        "gethostbyname": (socket, "gethostbyname", _blocked_gethostbyname),
        "gethostbyname_ex": (socket, "gethostbyname_ex", _blocked_gethostbyname_ex),
        "gethostbyaddr": (socket, "gethostbyaddr", _blocked_gethostbyaddr),
        "getnameinfo": (socket, "getnameinfo", _blocked_getnameinfo),
    }
    if hasattr(socket.socket, "sendmsg"):
        targets["sendmsg"] = (socket.socket, "sendmsg", _blocked_sendmsg)

    monkeypatch = pytest.MonkeyPatch()
    try:
        for operation, (owner, name, wrapper) in targets.items():
            _NETWORK_ORIGINALS[operation] = getattr(owner, name)
            monkeypatch.setattr(owner, name, wrapper)
    except Exception:
        monkeypatch.undo()
        _NETWORK_ORIGINALS.clear()
        raise
    _NETWORK_MONKEYPATCH = monkeypatch


def _restore_network_guard():
    global _NETWORK_MONKEYPATCH

    monkeypatch = _NETWORK_MONKEYPATCH
    if monkeypatch is None:
        return
    try:
        monkeypatch.undo()
    finally:
        _NETWORK_MONKEYPATCH = None
        _NETWORK_ORIGINALS.clear()


def pytest_sessionstart(session):
    _install_network_guard()


def pytest_sessionfinish(session, exitstatus):
    _restore_network_guard()
