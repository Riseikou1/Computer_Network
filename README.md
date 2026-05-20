# Peer-to-Peer Messenger Project

This project implements the Computer Networks design project requirements:

1. A login server stores currently online users.
2. Each online user record contains user ID, IP address, and port number.
3. The online user list is saved to a file.
4. A new client registers itself to the login server.
5. The login server returns the list of other online users.
6. Clients use that list to connect directly to each other.
7. Messages do not pass through the login server.
8. Users can invite another user, end a session, and send a message to all users in the session.
9. The message format is HTTP-like: start line, headers, blank line, body.
10. The UI is text-based and simple.

## Files

```txt
protocol.py       HTTP-like request/response protocol functions
login_server.py   login server that stores online users
client.py         peer-to-peer messenger client
```

## Run

Open three terminals in the same folder.

### Terminal 1: login server

```bash
python3 login_server.py --host 127.0.0.1 --port 9000
```

### Terminal 2: Alice

```bash
python3 client.py --id alice --listen-port 5001 --server-port 9000
```

### Terminal 3: Bob

```bash
python3 client.py --id bob --listen-port 5002 --server-port 9000
```

## Commands inside client

```txt
users              show online users
invite <user_id>   invite user to messenger session
session            show current session users
send <message>     send message to all session users
end                end current session
help               show commands
exit / quit        unregister and terminate process
```

## Example

In Alice terminal:

```txt
users
invite bob
send hello bob, this is sent directly peer-to-peer
end
exit
```

Bob should receive Alice's invite and message.

## HTTP-like message example

When Alice sends `send hello`, the actual message is formatted like this:

```http
MSG /session/message HTTP/1.0
From: alice
To: bob
Session-Mode: direct-peer-to-peer
Content-Length: 5

hello
```

This satisfies the project requirement that the message format should be similar to HTTP Request/Response messages.
