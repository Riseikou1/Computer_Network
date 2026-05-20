"""Login server for the Computer Networks messenger design project.

Run:
    python3 login_server.py --host 0.0.0.0 --port 9000
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
from pathlib import Path
from typing import Dict

from protocol import build_message, receive_message

UserTable = Dict[str, Dict[str, str]]


class LoginServer:
    def __init__(self, host: str, port: int, db_path: str):
        self.host = host
        self.port = port
        self.db_path = Path(db_path)
        self.users: UserTable = {}
        self.lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

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

    def handle_client(self, conn: socket.socket, addr) -> None:
        with conn:
            try:
                command, headers, body = receive_message(conn)
                user_id = headers.get("User-ID", "").strip()

                if command == "REGISTER":
                    listen_port = headers.get("Listen-Port", "").strip()
                    if not user_id or not listen_port.isdigit():
                        response = build_message("ERROR", body="Missing User-ID or Listen-Port")
                    else:
                        client_ip = headers.get("IP", addr[0]).strip() or addr[0]
                        with self.lock:
                            self.users[user_id] = {"ip": client_ip, "port": listen_port}
                            self._save()
                            users_json = self._online_users_json(exclude_id=user_id)
                        response = build_message("OK", {"Content-Type": "application/json"}, users_json)

                elif command == "LIST":
                    with self.lock:
                        users_json = self._online_users_json(exclude_id=user_id or None)
                    response = build_message("OK", {"Content-Type": "application/json"}, users_json)

                elif command == "UNREGISTER":
                    with self.lock:
                        if user_id in self.users:
                            del self.users[user_id]
                            self._save()
                    response = build_message("OK", body="unregistered")

                else:
                    response = build_message("ERROR", body=f"Unknown command: {command}")

                conn.sendall(response)
            except Exception as exc:
                try:
                    conn.sendall(build_message("ERROR", body=str(exc)))
                except OSError:
                    pass

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen()
            print(f"[LOGIN SERVER] Listening on {self.host}:{self.port}")
            print(f"[LOGIN SERVER] User table: {self.db_path}")
            while True:
                conn, addr = server_sock.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Login server for messenger project")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--db", default="../data/online_users.json")
    args = parser.parse_args()
    LoginServer(args.host, args.port, args.db).serve_forever()


if __name__ == "__main__":
    main()
