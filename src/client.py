"""Text-based peer-to-peer messenger client.

Run two or more terminals:
    python3 login_server.py --port 9000
    python3 client.py --id alice --listen-port 5001 --server-port 9000
    python3 client.py --id bob   --listen-port 5002 --server-port 9000

Commands inside the client:
    users              show online users from login server
    invite <user_id>   invite an online user to your messenger session
    session            show users in current session
    send <message>     send one message to all users in session
    end                end the session and notify all users
    quit               unregister and exit
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
from typing import Dict, Set

from protocol import build_message, receive_message, request

Peer = Dict[str, object]


class MessengerClient:
    def __init__(self, user_id: str, listen_host: str, listen_port: int, server_host: str, server_port: int):
        self.user_id = user_id
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.server_host = server_host
        self.server_port = server_port
        self.online_users: Dict[str, Peer] = {}
        self.session: Set[str] = set()
        self.lock = threading.Lock()
        self.running = True

    def public_ip(self) -> str:
        # For local/demo use, localhost is fine. On LAN, pass --listen-host with your LAN IP.
        return "127.0.0.1" if self.listen_host in {"0.0.0.0", ""} else self.listen_host

    def register(self) -> None:
        headers = {"User-ID": self.user_id, "IP": self.public_ip(), "Listen-Port": str(self.listen_port)}
        command, _, body = request(self.server_host, self.server_port, "REGISTER", headers)
        if command != "OK":
            raise RuntimeError(body)
        self.online_users = {row["id"]: row for row in json.loads(body)}
        print(f"[SYSTEM] Logged in as {self.user_id}. Online users loaded.")
        self.print_users()

    def unregister(self) -> None:
        try:
            request(self.server_host, self.server_port, "UNREGISTER", {"User-ID": self.user_id})
        except Exception:
            pass

    def refresh_users(self) -> None:
        command, _, body = request(self.server_host, self.server_port, "LIST", {"User-ID": self.user_id})
        if command == "OK":
            self.online_users = {row["id"]: row for row in json.loads(body)}

    def print_users(self) -> None:
        self.refresh_users()
        print("\nOnline users:")
        if not self.online_users:
            print("  nobody else online")
            return
        for user_id, info in sorted(self.online_users.items()):
            print(f"  {user_id:<15} {info['ip']}:{info['port']}")

    def print_help(self) -> None:
        print("\nCommands: users | invite <id> | session | send <text> | end | help | quit")

    def send_to_peer(self, peer_id: str, command: str, body: str = "") -> bool:
        self.refresh_users()
        peer = self.online_users.get(peer_id)
        if not peer:
            print(f"[ERROR] User '{peer_id}' is not online.")
            return False
        headers = {"From": self.user_id, "To": peer_id}
        try:
            request(str(peer["ip"]), int(peer["port"]), command, headers, body, timeout=3.0)
            return True
        except Exception as exc:
            print(f"[ERROR] Could not reach {peer_id}: {exc}")
            return False

    def invite(self, peer_id: str) -> None:
        if peer_id == self.user_id:
            print("[ERROR] Inviting yourself is spiritually concerning and technically useless.")
            return
        if self.send_to_peer(peer_id, "INVITE", f"{self.user_id} invited you to a messenger session."):
            with self.lock:
                self.session.add(peer_id)
            print(f"[SYSTEM] Invited {peer_id}. They were added to your session.")

    def send_session_message(self, text: str) -> None:
        with self.lock:
            targets = sorted(self.session)
        if not targets:
            print("[ERROR] Your session is empty. Use: invite <user_id>")
            return
        for peer_id in targets:
            self.send_to_peer(peer_id, "MESSAGE", text)
        print(f"[YOU -> session] {text}")

    def end_session(self) -> None:
        with self.lock:
            targets = sorted(self.session)
            self.session.clear()
        for peer_id in targets:
            self.send_to_peer(peer_id, "END_SESSION", f"{self.user_id} ended the messenger session.")
        print("[SYSTEM] Session ended.")

    def peer_server(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.listen_host, self.listen_port))
            server_sock.listen()
            print(f"[PEER SERVER] Listening on {self.listen_host}:{self.listen_port}")
            while self.running:
                try:
                    conn, _ = server_sock.accept()
                    threading.Thread(target=self.handle_peer, args=(conn,), daemon=True).start()
                except OSError:
                    break

    def handle_peer(self, conn: socket.socket) -> None:
        with conn:
            try:
                command, headers, body = receive_message(conn)
                sender = headers.get("From", "unknown")
                if command == "INVITE":
                    with self.lock:
                        self.session.add(sender)
                    print(f"\n[INVITE] {sender} invited you. Added to session.")
                    conn.sendall(build_message("OK", body="invite accepted"))
                elif command == "MESSAGE":
                    print(f"\n[{sender}] {body}")
                    conn.sendall(build_message("OK", body="message delivered"))
                elif command == "END_SESSION":
                    with self.lock:
                        self.session.discard(sender)
                    print(f"\n[SYSTEM] {sender} ended the session.")
                    conn.sendall(build_message("OK", body="session ended"))
                else:
                    conn.sendall(build_message("ERROR", body=f"Unknown peer command: {command}"))
                print("> ", end="", flush=True)
            except Exception as exc:
                try:
                    conn.sendall(build_message("ERROR", body=str(exc)))
                except OSError:
                    pass

    def command_loop(self) -> None:
        self.print_help()
        while self.running:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                raw = "quit"
            if not raw:
                continue

            command, _, rest = raw.partition(" ")
            command = command.lower()
            rest = rest.strip()

            if command == "users":
                self.print_users()
            elif command == "invite" and rest:
                self.invite(rest)
            elif command == "session":
                with self.lock:
                    print("Session users:", ", ".join(sorted(self.session)) or "empty")
            elif command == "send" and rest:
                self.send_session_message(rest)
            elif command == "end":
                self.end_session()
            elif command == "help":
                self.print_help()
            elif command == "quit":
                self.running = False
                self.end_session()
                self.unregister()
                print("[SYSTEM] Bye.")
                break
            else:
                print("[ERROR] Unknown or incomplete command. Type: help")

    def run(self) -> None:
        threading.Thread(target=self.peer_server, daemon=True).start()
        self.register()
        self.command_loop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Text-based P2P messenger client")
    parser.add_argument("--id", required=True, help="User ID shown to other users")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Host/IP this client listens on")
    parser.add_argument("--listen-port", type=int, required=True, help="Port this client listens on")
    parser.add_argument("--server-host", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=9000)
    args = parser.parse_args()
    MessengerClient(args.id, args.listen_host, args.listen_port, args.server_host, args.server_port).run()


if __name__ == "__main__":
    main()
