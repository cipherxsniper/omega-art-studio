#!/usr/bin/env python3
"""
OMEGA CLOUD — SOVEREIGN TLS SERVER
Pure Python. No nginx. No gunicorn. Raw socket + ssl module.
"""
import ssl
import socket
import threading
import json
import hashlib
import hmac
import os
import logging
from datetime import datetime, timezone

CERT_DIR = os.path.expanduser("~/omega_runtime/certs")
HOST     = "0.0.0.0"
PORT     = 5003
LOG      = os.path.expanduser("~/omega_runtime/logs/node3.log")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(LOG),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("omega.node3")

# ── TLS CONTEXT ───────────────────────────────────────────────
def make_tls_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(
        certfile=f"{CERT_DIR}/node3.crt",
        keyfile=f"{CERT_DIR}/node3.key"
    )
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers("ECDH+AESGCM:ECDH+CHACHA20:!aNULL:!MD5")
    return ctx

# ── HTTP PARSER ───────────────────────────────────────────────
def parse_request(raw: bytes) -> dict:
    try:
        header_section, _, body = raw.partition(b"\r\n\r\n")
        lines = header_section.decode("utf-8", errors="replace").split("\r\n")
        method, path, _ = lines[0].split(" ", 2)
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()
        return {
            "method":  method.upper(),
            "path":    path,
            "headers": headers,
            "body":    body,
        }
    except Exception as e:
        log.warning(f"Parse error: {e}")
        return {}

# ── HTTP RESPONSE BUILDER ─────────────────────────────────────
def make_response(status: int, body: dict, extra_headers: dict = None) -> bytes:
    status_map = {
        200: "OK", 201: "Created", 400: "Bad Request",
        401: "Unauthorized", 403: "Forbidden",
        404: "Not Found", 500: "Internal Server Error"
    }
    phrase  = status_map.get(status, "Unknown")
    payload = json.dumps(body).encode()
    headers = [
        f"HTTP/1.1 {status} {phrase}",
        f"Content-Type: application/json",
        f"Content-Length: {len(payload)}",
        f"X-Omega-Node: node3",
        f"X-Omega-Version: 1.0",
        "Connection: close",
    ]
    if extra_headers:
        for k, v in extra_headers.items():
            headers.append(f"{k}: {v}")
    return "\r\n".join(headers).encode() + b"\r\n\r\n" + payload

# ── ROUTER ────────────────────────────────────────────────────
ROUTES = {}

def route(method, path):
    def decorator(fn):
        ROUTES[(method.upper(), path)] = fn
        return fn
    return decorator

def dispatch(req: dict) -> bytes:
    if not req:
        return make_response(400, {"error": "bad request"})
    key = (req["method"], req["path"].split("?")[0])
    handler = ROUTES.get(key)
    if handler:
        try:
            return handler(req)
        except Exception as e:
            log.error(f"Handler error: {e}")
            return make_response(500, {"error": "internal error"})
    return make_response(404, {"error": "not found", "path": req["path"]})

# ── ROUTES ────────────────────────────────────────────────────
@route("GET", "/")
def index(req):
    return make_response(200, {
        "node":    "omega-node3",
        "status":  "online",
        "version": "1.0",
        "time":    datetime.now(timezone.utc).isoformat(),
    })

@route("GET", "/health")
def health(req):
    return make_response(200, {
        "status":  "healthy",
        "node":    "node3",
        "time":    datetime.now(timezone.utc).isoformat(),
    })

@route("GET", "/v1/info")
def info(req):
    return make_response(200, {
        "node":        "omega-node3",
        "description": "Omega Cloud Sovereign Node",
        "endpoints":   ["/", "/health", "/v1/info"],
    })

# ── CONNECTION HANDLER ────────────────────────────────────────
def handle_conn(conn, addr):
    try:
        raw = b""
        conn.settimeout(10)
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
            if b"\r\n\r\n" in raw:
                break
        if raw:
            req  = parse_request(raw)
            resp = dispatch(req)
            conn.sendall(resp)
            log.info(f"{addr[0]} {req.get('method','?')} {req.get('path','?')}")
    except Exception as e:
        log.warning(f"Connection error from {addr}: {e}")
    finally:
        conn.close()

# ── MAIN SERVER LOOP ──────────────────────────────────────────
def run():
    ctx = make_tls_context()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(64)
    tls_sock = ctx.wrap_socket(sock, server_side=True)
    log.info(f"🔐 Omega Cloud Node 3 ONLINE — https://{HOST}:{PORT}")
    log.info(f"🌐 Public: https://omega-node3.duckdns.org:{PORT}")
    while True:
        try:
            conn, addr = tls_sock.accept()
            t = threading.Thread(target=handle_conn, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            log.error(f"Accept error: {e}")

if __name__ == "__main__":
    run()
