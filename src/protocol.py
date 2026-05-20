"""Small HTTP-like text protocol for the messenger project."""
from __future__ import annotations

import socket
from typing import Dict, Tuple

ENCODING = "utf-8"
SEPARATOR = "\r\n\r\n"


def build_message(command: str, headers: Dict[str, str] | None = None, body: str = "") -> bytes:
    headers = dict(headers or {})
    body_bytes = body.encode(ENCODING)
    headers["Command"] = command
    headers["Content-Length"] = str(len(body_bytes))
    header_text = "\r\n".join(f"{key}: {value}" for key, value in headers.items())
    return (header_text + SEPARATOR).encode(ENCODING) + body_bytes


def _recv_until(sock: socket.socket, marker: bytes) -> bytes:
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Connection closed before headers were complete")
        data += chunk
    return data


def receive_message(sock: socket.socket) -> Tuple[str, Dict[str, str], str]:
    raw = _recv_until(sock, SEPARATOR.encode(ENCODING))
    header_raw, body_start = raw.split(SEPARATOR.encode(ENCODING), 1)
    headers: Dict[str, str] = {}

    for line in header_raw.decode(ENCODING).split("\r\n"):
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"Bad header line: {line}")
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()

    length = int(headers.get("Content-Length", "0"))
    body = body_start
    while len(body) < length:
        chunk = sock.recv(length - len(body))
        if not chunk:
            raise ConnectionError("Connection closed before body was complete")
        body += chunk

    command = headers.get("Command", "")
    return command, headers, body[:length].decode(ENCODING)


def request(host: str, port: int, command: str, headers: Dict[str, str] | None = None, body: str = "", timeout: float = 5.0):
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(build_message(command, headers, body))
        return receive_message(sock)
