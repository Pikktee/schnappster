"""127.0.0.1:front → 127.0.0.1:back (TCP).

Ersatz für mitmdump, wenn der Quick-Tunnel dieselbe URL behalten soll.
"""

from __future__ import annotations

import socket
import sys
import threading


def _pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass


def _relay(client: socket.socket, back_host: str, back_port: int) -> None:
    upstream = socket.create_connection((back_host, back_port))
    t1 = threading.Thread(target=_pipe, args=(client, upstream), daemon=True)
    t2 = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    client.close()
    upstream.close()


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: tunnel_front_tcp.py FRONT_PORT BACK_PORT", file=sys.stderr)
        sys.exit(2)
    front, back = int(sys.argv[1]), int(sys.argv[2])
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", front))
    srv.listen(128)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=_relay, args=(c, "127.0.0.1", back), daemon=True).start()


if __name__ == "__main__":
    main()
