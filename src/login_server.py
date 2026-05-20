"""Login server for the Computer Networks messenger design project.

Professor requirement covered here:
1. The login server stores online users.
2. For each user, it stores ID, IP address, and port number.
3. The user list is saved into a file.
4. New clients register themselves and receive the list of other online users.

Run:
    python3 login_server.py --host 0.0.0.0 --port 9000
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict

from protocol import build_response, receive_request

UserTable = Dict[str, Dict[str, str]]


class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RED = "\033[31m"


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def box(title: str, lines: list[str]) -> str:
    width = max([len(title)] + [len(line) for line in lines]) + 4
    top = "╭" + "─" * width + "╮"
    bottom = "╰" + "─" * width + "╯"
    title_line = f"│  {title.center(width - 4)}  │"
    body = [f"│  {line.ljust(width - 4)}  │" for line in lines]
    return "\n".join([top, title_line, "├" + "─" * width + "┤", *body, bottom])


class LoginServer:
    def __init__(self, host: str, port: int, db_path: str, keep_old_users: bool = False):
        self.host = host
        self.port = port
        self.db_path = Path(db_path)
        self.users: UserTable = {}
        self.lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Important: the file stores CURRENTLY online users.
        # If the server restarts, old clients are no longer guaranteed to be online,
        # so we clear stale entries by default. This prevents ghosts like bob/temuujin
        # appearing before they actually run their client.
        if keep_old_users:
            self._load()
        else:
            self._save()

    def _load(self) -> None:
        if self.db_path.exists():
            try:
                self.users = json.loads(self.db_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.users = {}

    def _save(self) -> None:
        self.db_path.write_text(json.dumps(self.users, indent=2), encoding="utf-8")

    def _online_users_json(self, exclude_id: str | None = None) -> str:
        rows = []
        for user_id, info in sorted(self.users.items()):
            if user_id == exclude_id:
                continue
            rows.append({"id": user_id, "ip": info["ip"], "port": int(info["port"])})
        return json.dumps(rows, indent=2)

    def log(self, message: str, color: str = Style.CYAN) -> None:
        print(f"{Style.DIM}[{now()}]{Style.RESET} {color}{message}{Style.RESET}")

    def handle_client(self, conn: socket.socket, addr) -> None:
        with conn:
            try:
                method, path, headers, _body = receive_request(conn)
                user_id = headers.get("User-ID", "").strip()

                if method == "REGISTER" and path == "/login":
                    listen_port = headers.get("Listen-Port", "").strip()
                    if not user_id or not listen_port.isdigit():
                        response = build_response(400, "Bad Request", body="Missing User-ID or Listen-Port")
                    else:
                        client_ip = headers.get("IP", addr[0]).strip() or addr[0]
                        with self.lock:
                            self.users[user_id] = {"ip": client_ip, "port": listen_port}
                            self._save()
                            users_json = self._online_users_json(exclude_id=user_id)
                        self.log(f"REGISTER {user_id} at {client_ip}:{listen_port}", Style.GREEN)
                        response = build_response(200, "OK", {"Content-Type": "application/json"}, users_json)

                elif method == "LIST" and path == "/users":
                    with self.lock:
                        users_json = self._online_users_json(exclude_id=user_id or None)
                    self.log(f"LIST requested by {user_id or 'unknown'}", Style.BLUE)
                    response = build_response(200, "OK", {"Content-Type": "application/json"}, users_json)

                elif method == "UNREGISTER" and path == "/logout":
                    with self.lock:
                        existed = self.users.pop(user_id, None) is not None
                        self._save()
                    if existed:
                        self.log(f"UNREGISTER {user_id}", Style.YELLOW)
                    response = build_response(200, "OK", body="unregistered")

                else:
                    response = build_response(404, "Not Found", body=f"Unknown request: {method} {path}")

                conn.sendall(response)
            except Exception as exc:
                self.log(f"ERROR {exc}", Style.RED)
                try:
                    conn.sendall(build_response(500, "Server Error", body=str(exc)))
                except OSError:
                    pass

    def serve_forever(self) -> None:
        print(Style.CYAN + box("LOGIN SERVER", [
            f"Listening : {self.host}:{self.port}",
            f"User file : {self.db_path}",
            "Purpose   : store online user ID/IP/port only",
            "Messages  : sent directly between user clients",
        ]) + Style.RESET)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen()
            while True:
                conn, addr = server_sock.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Login server for messenger project")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--db", default="../data/online_users.json")
    parser.add_argument(
        "--keep-old-users",
        action="store_true",
        help="Load users from the previous online-users file. Usually do NOT use this for demo/testing.",
    )
    args = parser.parse_args()
    LoginServer(args.host, args.port, args.db, keep_old_users=args.keep_old_users).serve_forever()


if __name__ == "__main__":
    main()
