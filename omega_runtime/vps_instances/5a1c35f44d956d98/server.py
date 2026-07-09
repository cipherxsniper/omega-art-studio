#!/usr/bin/env python3
import socket, threading, logging
PORT=6000
INSTANCE_ID="5a1c35f44d956d98"
TIER="lite"
STORAGE_GB=1
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vps")
def handle_conn(conn, addr):
    try:
        raw = conn.recv(4096)
        conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"status":"healthy","instance":"'+INSTANCE_ID[:8].encode()+b'","tier":"'+TIER.encode()+b'"}')
    except Exception as e:
        log.warning(f"Conn error: {e}")
    finally:
        conn.close()
def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", PORT))
    sock.listen(32)
    log.info(f"Omega VPS Instance {INSTANCE_ID[:8]} ONLINE on {PORT}")
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()
if __name__ == "__main__":
    run()
