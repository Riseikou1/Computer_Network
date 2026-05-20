"""Text-based peer-to-peer messenger client.

Professor requirement covered here:
1. Client registers ID, IP address, and port number to the login server.
2. Client receives and displays currently online users.
3. Client invites users into a messenger session.
4. Client sends messages directly to other clients, not through login server.
5. Client can end the session.
6. Message format is HTTP-like: start line + headers + blank line + body.

Run examples:
    python3 login_server.py --port 9000
    python3 client.py --id alice --listen-port 5001 --server-port 9000
    python3 client.py --id bob   --listen-port 5002 --server-port 9000
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
from datetime import datetime
from typing import Dict, Set

from protocol import build_response, format_request_for_display, receive_request, request

Peer = Dict[str, object]


class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def line(width: int = 72) -> str:
    return "─" * width


def box(title: str, lines: list[str], width: int = 72) -> str:
    width = max(width, len(title) + 6, *(len(x) + 6 for x in lines))
    top = "╭" + "─" * (width - 2) + "╮"
    sep = "├" + "─" * (width - 2) + "┤"
    bottom = "╰" + "─" * (width - 2) + "╯"
    title_line = f"│ {Style.BOLD}{title.center(width - 4)}{Style.RESET} │"
    body = [f"│ {text.ljust(width - 4)} │" for text in lines]
    return "\n".join([top, title_line, sep, *body, bottom])


def tag(text: str, color: str) -> str:
    return f"{color}{Style.BOLD}{text}{Style.RESET}"


class MessengerClient:
    def __init__(self, user_id: str, listen_host: str, listen_port: int, server_host: str, server_port: int,
                 show_packets: bool):
        self.user_id = user_id
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.server_host = server_host
        self.server_port = server_port
        self.show_packets = show_packets
        self.online_users: Dict[str, Peer] = {}
        self.session: Set[str] = set()
        self.lock = threading.Lock()
        self.running = True

    def public_ip(self) -> str:
        # For local/demo use, localhost is fine. On LAN, pass --listen-host with your LAN IP.
        return "127.0.0.1" if self.listen_host in {"0.0.0.0", ""} else self.listen_host

    def system(self, text: str) -> None:
        print(f"{Style.DIM}[{now()}]{Style.RESET} {tag('SYSTEM', Style.CYAN)} {text}")

    def error(self, text: str) -> None:
        print(f"{Style.DIM}[{now()}]{Style.RESET} {tag('ERROR ', Style.RED)} {text}")

    def success(self, text: str) -> None:
        print(f"{Style.DIM}[{now()}]{Style.RESET} {tag('OK    ', Style.GREEN)} {text}")

    def print_welcome(self) -> None:
        print(Style.CYAN + box(f"Welcome, {self.user_id}", [
            "This is a simple peer-to-peer messenger for the network project.",
            "The login server stores only online users: ID, IP address, and port.",
            "Actual chat messages are sent directly between clients.",
            "Type 'help' to show commands again.",
            "Type 'exit' or 'quit' to terminate this process safely.",
        ]) + Style.RESET)

    def print_help(self) -> None:
        print(box("COMMANDS", [
            "users              refresh and show online users",
            "invite <user_id>   invite a user to the current messenger session",
            "session            show users in your current session",
            "send <message>     send one HTTP-like message to all session users",
            "end                end current messenger session",
            "help               show this command menu",
            "exit / quit        unregister and terminate this process",
        ]))

    def print_http_packet(self, method: str, path: str, headers: Dict[str, str], body: str) -> None:
        if not self.show_packets and method != "MSG":
            return
        packet = format_request_for_display(method, path, headers, body)
        print(Style.MAGENTA + "\n╭─ HTTP-like outgoing message " + "─" * 38)
        for packet_line in packet.splitlines():
            print("│ " + packet_line)
        print("╰" + "─" * 69 + Style.RESET)

    def register(self) -> None:
        headers = {
            "User-ID": self.user_id,
            "IP": self.public_ip(),
            "Listen-Port": str(self.listen_port),
        }
        status, reason, _headers, body = request(self.server_host, self.server_port, "REGISTER", "/login", headers)
        if status != 200:
            raise RuntimeError(f"login failed: {status} {reason} {body}")
        self.online_users = {row["id"]: row for row in json.loads(body)}
        self.success(f"Logged in as {self.user_id} at {self.public_ip()}:{self.listen_port}")

    def unregister(self) -> None:
        try:
            request(self.server_host, self.server_port, "UNREGISTER", "/logout", {"User-ID": self.user_id})
        except Exception:
            pass

    def refresh_users(self) -> None:
        status, _reason, _headers, body = request(
            self.server_host,
            self.server_port,
            "LIST",
            "/users",
            {"User-ID": self.user_id},
        )
        if status == 200:
            self.online_users = {row["id"]: row for row in json.loads(body)}

    def print_users(self) -> None:
        self.refresh_users()
        print("\n" + tag("ONLINE USERS", Style.BLUE))
        print(line())
        if not self.online_users:
            print("  nobody else online. tragic, but technically correct.")
            print(line())
            return
        print(f"  {'ID':<18} {'IP ADDRESS':<18} {'PORT':<8}")
        print(f"  {'-' * 18} {'-' * 18} {'-' * 8}")
        for user_id, info in sorted(self.online_users.items()):
            print(f"  {user_id:<18} {str(info['ip']):<18} {str(info['port']):<8}")
        print(line())

    def send_to_peer(self, peer_id: str, method: str, body: str = "") -> bool:
        self.refresh_users()
        peer = self.online_users.get(peer_id)
        if not peer:
            self.error(f"User '{peer_id}' is not online. Use 'users' to check available users.")
            return False

        headers = {
            "From": self.user_id,
            "To": peer_id,
            "Session-Mode": "direct-peer-to-peer",
        }

        path = "/session/message" if method == "MSG" else "/session/control"
        self.print_http_packet(method, path, headers, body)

        try:
            status, reason, _headers, response_body = request(
                str(peer["ip"]), int(peer["port"]), method, path, headers, body, timeout=3.0
            )
            if status != 200:
                self.error(f"{peer_id} returned {status} {reason}: {response_body}")
                return False
            return True
        except Exception as exc:
            self.error(f"Could not reach {peer_id}: {exc}")
            return False

    def invite(self, peer_id: str) -> None:
        if peer_id == self.user_id:
            self.error("Inviting yourself is not networking. It is just loneliness with extra steps.")
            return
        body = f"{self.user_id} invited you to a messenger session."
        if self.send_to_peer(peer_id, "INVITE", body):
            with self.lock:
                self.session.add(peer_id)
            self.success(f"Invited {peer_id}. They were added to your session.")

    def send_session_message(self, text: str) -> None:
        with self.lock:
            targets = sorted(self.session)
        if not targets:
            self.error("Your session is empty. Use: invite <user_id>")
            return

        delivered = 0
        for peer_id in targets:
            if self.send_to_peer(peer_id, "MSG", text):
                delivered += 1
        print(f"{Style.DIM}[{now()}]{Style.RESET} {tag('YOU   ', Style.GREEN)} sent to {delivered}/{len(targets)} session user(s): {text}")

    def end_session(self) -> None:
        with self.lock:
            targets = sorted(self.session)
            self.session.clear()
        for peer_id in targets:
            self.send_to_peer(peer_id, "END", f"{self.user_id} ended the messenger session.")
        self.system("Session ended.")

    def print_session(self) -> None:
        with self.lock:
            users = sorted(self.session)
        print("\n" + tag("CURRENT SESSION", Style.YELLOW))
        print(line())
        if not users:
            print("  empty. Invite someone before sending messages.")
        else:
            for user_id in users:
                print(f"  • {user_id}")
        print(line())

    def peer_server(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.listen_host, self.listen_port))
            server_sock.listen()
            self.system(f"Peer listener running on {self.listen_host}:{self.listen_port}")
            while self.running:
                try:
                    conn, _addr = server_sock.accept()
                    threading.Thread(target=self.handle_peer, args=(conn,), daemon=True).start()
                except OSError:
                    break

    def handle_peer(self, conn: socket.socket) -> None:
        with conn:
            try:
                method, _path, headers, body = receive_request(conn)
                sender = headers.get("From", "unknown")

                if method == "INVITE":
                    with self.lock:
                        self.session.add(sender)
                    print(f"\n{Style.DIM}[{now()}]{Style.RESET} {tag('INVITE', Style.YELLOW)} {sender} invited you. Added to session.")
                    conn.sendall(build_response(200, "OK", body="invite accepted"))

                elif method == "MSG":
                    print(f"\n{Style.DIM}[{now()}]{Style.RESET} {tag(sender[:6].ljust(6), Style.MAGENTA)} {body}")
                    conn.sendall(build_response(200, "OK", body="message delivered"))

                elif method == "END":
                    with self.lock:
                        self.session.discard(sender)
                    print(f"\n{Style.DIM}[{now()}]{Style.RESET} {tag('END   ', Style.YELLOW)} {sender} ended the session.")
                    conn.sendall(build_response(200, "OK", body="session ended"))

                else:
                    conn.sendall(build_response(404, "Not Found", body=f"Unknown peer method: {method}"))

                print("› ", end="", flush=True)
            except Exception as exc:
                try:
                    conn.sendall(build_response(500, "Peer Error", body=str(exc)))
                except OSError:
                    pass

    def command_loop(self) -> None:
        self.print_welcome()
        self.print_help()
        self.print_users()

        while self.running:
            try:
                raw = input("› ").strip()
            except (EOFError, KeyboardInterrupt):
                raw = "exit"

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
                self.print_session()
            elif command == "send" and rest:
                self.send_session_message(rest)
            elif command == "end":
                self.end_session()
            elif command == "help":
                self.print_help()
            elif command in {"exit", "quit"}:
                self.running = False
                self.end_session()
                self.unregister()
                self.system("Unregistered from login server. Process terminated cleanly.")
                break
            else:
                self.error("Unknown or incomplete command. Type 'help'.")

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
    parser.add_argument(
        "--show-packets",
        action="store_true",
        help="Show all outgoing HTTP-like requests. By default, only chat messages are displayed.",
    )
    args = parser.parse_args()
    MessengerClient(
        args.id,
        args.listen_host,
        args.listen_port,
        args.server_host,
        args.server_port,
        args.show_packets,
    ).run()


if __name__ == "__main__":
    main()
