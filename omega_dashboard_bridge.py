#!/usr/bin/env python3
"""
OMEGA DASHBOARD BRIDGE
A small local server that proxies MEXC price data and OpenRouter chat
completions, so the browser dashboard never has to make cross-origin
calls directly (which both MEXC and OpenRouter block).

Run this on Phone 1. The dashboard (running anywhere — your phone's
browser, Netlify, wherever) points at this server's address instead
of calling MEXC/OpenRouter directly.

No card logic, no trading execution, no ledger writes — purely a
read-through proxy for prices and chat.
"""
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 5050

MEXC_TICKER_URL = "https://api.mexc.com/api/v3/ticker/24hr"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYMBOLS = ["XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "HBARUSDT", "XLMUSDT", "LINKUSDT"]


def cors_headers(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


def respond_json(handler, code, data):
    body = json.dumps(data).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    cors_headers(handler)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # quiet logs

    def do_OPTIONS(self):
        self.send_response(200)
        cors_headers(self)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            respond_json(self, 200, {"status": "online", "service": "omega-dashboard-bridge"})
            return

        if path == "/prices":
            try:
                req = urllib.request.Request(
                    MEXC_TICKER_URL,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())

                out = {}
                rows_by_symbol = {row["symbol"]: row for row in data if isinstance(row, dict)}
                for sym in SYMBOLS:
                    row = rows_by_symbol.get(sym)
                    if row:
                        out[sym] = {
                            "price": float(row["lastPrice"]),
                            "change_pct": float(row["priceChangePercent"]),
                        }
                respond_json(self, 200, {"prices": out})
            except Exception as e:
                respond_json(self, 502, {"error": f"MEXC fetch failed: {e}"})
            return

        respond_json(self, 404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/chat":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode())

                api_key = payload.get("api_key", "").strip()
                messages = payload.get("messages", [])
                model = payload.get("model", "openai/gpt-4o-mini")

                if not api_key:
                    respond_json(self, 400, {"error": "Missing api_key"})
                    return
                if not messages:
                    respond_json(self, 400, {"error": "Missing messages"})
                    return

                body = json.dumps({"model": model, "messages": messages}).encode()
                req = urllib.request.Request(
                    OPENROUTER_URL,
                    data=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        result = json.loads(resp.read().decode())
                    respond_json(self, 200, result)
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode()
                    respond_json(self, e.code, {"error": err_body})
            except Exception as e:
                respond_json(self, 500, {"error": str(e)})
            return

        respond_json(self, 404, {"error": "not found"})


if __name__ == "__main__":
    print(f"Omega Dashboard Bridge — http://0.0.0.0:{PORT}")
    print(f"  GET  /health  — health check")
    print(f"  GET  /prices  — live MEXC prices for {len(SYMBOLS)} symbols")
    print(f"  POST /chat    — proxies OpenRouter chat completions")
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    server.serve_forever()
