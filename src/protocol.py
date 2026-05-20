"""HTTP-like protocol utilities for the messenger project.

The assignment asks for a message format similar to HTTP Request/Response:
- start line
- headers
- blank line
- body

Examples:
    MSG /peer HTTP/1.0
    From: alice
    To: bob
    Content-Length: 5

    hello

    HTTP/1.0 200 OK
    Content-Length: 8

    accepted
"""
from __future__ import annotations

import socket
from typing import Dict, Tuple

ENCODING = "utf-8"
CRLF = "\r\n"
HEADER_END = b"\r\n\r\n"


Request = Tuple[str, str, Dict[str, str], str]
Response = Tuple[int, str, Dict[str, str], str]


def _body_bytes(body: str) -> bytes:
    return body.encode(ENCODING)


def build_request(method: str, path: str = "/", headers: Dict[str, str] | None = None, body: str = "") -> bytes:
    """Build an HTTP-like request message."""
    headers = dict(headers or {})
    body_raw = _body_bytes(body)
    headers["Content-Length"] = str(len(body_raw))

    start_line = f"{method.upper()} {path} HTTP/1.0"
    header_lines = [f"{key}: {value}" for key, value in headers.items()]
    head = CRLF.join([start_line] + header_lines) + CRLF + CRLF
    return head.encode(ENCODING) + body_raw


def build_response(status_code: int = 200, reason: str = "OK", headers: Dict[str, str] | None = None, body: str = "") -> bytes:
    """Build an HTTP-like response message."""
    headers = dict(headers or {})
    body_raw = _body_bytes(body)
    headers["Content-Length"] = str(len(body_raw))

    start_line = f"HTTP/1.0 {status_code} {reason}"
    header_lines = [f"{key}: {value}" for key, value in headers.items()]
    head = CRLF.join([start_line] + header_lines) + CRLF + CRLF
    return head.encode(ENCODING) + body_raw


def format_request_for_display(method: str, path: str = "/", headers: Dict[str, str] | None = None, body: str = "") -> str:
    """Return a pretty printable HTTP-like request block."""
    raw = build_request(method, path, headers, body).decode(ENCODING, errors="replace")
    return raw.replace("\r\n", "\n")


def _recv_until(sock: socket.socket, marker: bytes) -> bytes:
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("connection closed before headers were complete")
        data += chunk
    return data


def _read_head_and_body(sock: socket.socket) -> tuple[str, bytes]:
    raw = _recv_until(sock, HEADER_END)
    head_raw, body_start = raw.split(HEADER_END, 1)
    head_text = head_raw.decode(ENCODING)

    headers = parse_headers(head_text.split(CRLF)[1:])
    content_length = int(headers.get("Content-Length", "0"))

    body = body_start
    while len(body) < content_length:
        chunk = sock.recv(content_length - len(body))
        if not chunk:
            raise ConnectionError("connection closed before body was complete")
        body += chunk

    return head_text, body[:content_length]


def parse_headers(lines: list[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"bad header line: {line}")
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def receive_request(sock: socket.socket) -> Request:
    """Receive and parse an HTTP-like request."""
    head_text, body_raw = _read_head_and_body(sock)
    lines = head_text.split(CRLF)
    start_parts = lines[0].split()

    if len(start_parts) != 3 or not start_parts[2].startswith("HTTP/"):
        raise ValueError(f"bad request start line: {lines[0]}")

    method, path, _version = start_parts
    headers = parse_headers(lines[1:])
    body = body_raw.decode(ENCODING)
    return method.upper(), path, headers, body


def receive_response(sock: socket.socket) -> Response:
    """Receive and parse an HTTP-like response."""
    head_text, body_raw = _read_head_and_body(sock)
    lines = head_text.split(CRLF)
    start_parts = lines[0].split(maxsplit=2)

    if len(start_parts) < 2 or not start_parts[0].startswith("HTTP/"):
        raise ValueError(f"bad response start line: {lines[0]}")

    status_code = int(start_parts[1])
    reason = start_parts[2] if len(start_parts) == 3 else ""
    headers = parse_headers(lines[1:])
    body = body_raw.decode(ENCODING)
    return status_code, reason, headers, body


def request(host: str, port: int, method: str, path: str = "/", headers: Dict[str, str] | None = None,
            body: str = "", timeout: float = 5.0) -> Response:
    """Send one request and wait for one response."""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(build_request(method, path, headers, body))
        return receive_response(sock)
