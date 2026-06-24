#!/usr/bin/env python3
"""OMEGA CLOUD — Customer Node Instance 5a1c35f44d956d98"""
import socket, threading, json, os, logging, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.expanduser("~/omega_runtime"))
from omega_auth import OmegaAuth
from omega_storage import OmegaStorage as _BaseStorage

INSTANCE_ID  = "5a1c35f44d956d98"
OWNER_ID     = "5a1c35f44d956d98"
PORT         = 6000
STORAGE_DIR  = "/data/data/com.termux/files/home/omega_runtime/vps_instances/5a1c35f44d956d98/storage"
META_DIR     = "/data/data/com.termux/files/home/omega_runtime/vps_instances/5a1c35f44d956d98/storage_meta"
LOG_FILE     = "/data/data/com.termux/files/home/omega_runtime/vps_instances/5a1c35f44d956d98/logs/server.log"
TIER         = "lite"
STORAGE_GB   = 1
MAX_OBJECTS  = 1000

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(META_DIR,    exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger(f"omega.vps.{INSTANCE_ID[:8]}")

def parse_request(raw):
    try:
        header_section, _, body = raw.partition(b"\r\n\r\n")
        lines = header_section.decode("utf-8", errors="replace").split("\r\n")
        method, path, _ = lines[0].split(" ", 2)
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()
        return {"method": method.upper(), "path": path,
                "headers": headers, "body": body}
    except:
        return {}

def resp(status, body):
    phrases = {200:"OK",201:"Created",400:"Bad Request",
               401:"Unauthorized",403:"Forbidden",
               404:"Not Found",500:"Internal Server Error"}
    payload = json.dumps(body).encode()
    headers = "\r\n".join([
        f"HTTP/1.1 {status} {phrases.get(status,'Unknown')}",
        "Content-Type: application/json",
        f"Content-Length: {len(payload)}",
        f"X-Omega-Instance: {INSTANCE_ID[:8]}",
        f"X-Omega-Tier: {TIER}",
        "Connection: close",
    ])
    return headers.encode() + b"\r\n\r\n" + payload

def bearer(req):
    auth = req.get("headers", {}). get("authorization", "")
    if not auth.startswith("Bearer "):
        return None, None
    return OmegaAuth.verify_bearer(auth[7:].strip())

def perm(perms, required):
    return perms and (required in perms or "admin:all" in perms)

ROUTES = {}
def route(m, p):
    def d(fn):
        ROUTES[(m.upper(), p)] = fn
        return fn
    return d

def dispatch(req):
    if not req:
        return resp(400, {"error": "bad request"})
    key     = (req["method"], req["path"].split("?")[0])
    handler = ROUTES.get(key)
    if handler:
        try:
            return handler(req)
        except Exception as e:
            log.error(f"Handler error: {e}")
            return resp(500, {"error": "internal error"})
    return resp(404, {"error": "not found"})

@route("GET", "/")
def index(req):
    return resp(200, {
        "instance": INSTANCE_ID[:8],
        "tier": TIER,
        "status": "online",
        "time": datetime.now(timezone.utc).isoformat(),
    })

@route("GET", "/health")
def health(req):
    return resp(200, {
        "status": "healthy",
        "instance": INSTANCE_ID[:8],
        "tier": TIER,
        "time": datetime.now(timezone.utc).isoformat(),
    })

@route("POST", "/v1/storage/upload")
def upload(req):
    owner_id, perms = bearer(req)
    if not owner_id: return resp(401, {"error": "unauthorized"})
    if not perm(perms, "storage:write"):
        return resp(403, {"error": "forbidden"})
    try:
        # Check storage quota
        used = sum(
            os.path.getsize(os.path.join(STORAGE_DIR, f))
            for f in os.listdir(STORAGE_DIR)
            if os.path.isfile(os.path.join(STORAGE_DIR, f))
        ) / (1024**3)
        if used >= STORAGE_GB:
            return resp(403, {"error": f"Storage quota exceeded ({STORAGE_GB}GB)"})

        body    = json.loads(req["body"].decode())
        name    = body.get("object_name")
        content = body.get("content", "").encode()
        ctype   = body.get("content_type", "application/octet-stream")
        if not name or not content:
            return resp(400, {"error": "object_name and content required"})

        # Use base storage with instance dirs
        import hashlib, secrets as _sec
        object_id  = _sec.token_hex(16)
        import hmac as _hmac
        master_key = hashlib.sha256(b"omega_master_CHANGE_IN_PROD").digest()
        key        = _hmac.new(master_key, object_id.encode(), hashlib.sha256).digest()
        import struct
        def crypt(data, k):
            out = bytearray()
            bs  = 32
            for i in range(0, len(data), bs):
                nonce   = b"\x00" * 16
                ctr     = struct.pack(">Q", i // bs)
                ks      = hashlib.sha256(k + nonce + ctr).digest()
                chunk   = data[i:i+bs]
                out.extend(a ^ b for a, b in zip(chunk, ks))
            return bytes(out)

        nonce     = _sec.token_bytes(16)
        encrypted = crypt(content, key)
        checksum  = hashlib.sha256(encrypted).hexdigest()

        with open(os.path.join(STORAGE_DIR, object_id), "wb") as f:
            f.write(nonce + encrypted)

        import json as _j
        from datetime import datetime as _dt, timezone as _tz
        meta = {
            "object_id":    object_id,
            "owner_id":     owner_id,
            "object_name":  name,
            "content_type": ctype,
            "size_bytes":   len(content),
            "checksum":     checksum,
            "created_at":   _dt.now(_tz.utc).isoformat(),
            "instance":     INSTANCE_ID[:8],
            "tier":         TIER,
        }
        with open(os.path.join(META_DIR, f"{object_id}.json"), "w") as f:
            _j.dump(meta, f)

        return resp(201, {"success": True, "object": meta})
    except Exception as e:
        return resp(500, {"error": str(e)})

@route("GET", "/v1/storage/list")
def list_objects(req):
    owner_id, perms = bearer(req)
    if not owner_id: return resp(401, {"error": "unauthorized"})
    if not perm(perms, "storage:read"):
        return resp(403, {"error": "forbidden"})
    try:
        import json as _j
        objects = []
        for fname in os.listdir(META_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(META_DIR, fname)) as f:
                    objects.append(_j.load(f))
        objects.sort(key=lambda x: x["created_at"], reverse=True)
        return resp(200, {"success": True,
                          "objects": objects,
                          "count": len(objects)})
    except Exception as e:
        return resp(500, {"error": str(e)})

@route("GET", "/v1/quota")
def quota(req):
    owner_id, perms = bearer(req)
    if not owner_id: return resp(401, {"error": "unauthorized"})
    try:
        used_bytes = sum(
            os.path.getsize(os.path.join(STORAGE_DIR, f))
            for f in os.listdir(STORAGE_DIR)
            if os.path.isfile(os.path.join(STORAGE_DIR, f))
        )
        used_gb  = used_bytes / (1024**3)
        total_gb = STORAGE_GB
        pct      = (used_gb / total_gb * 100) if total_gb > 0 else 0
        return resp(200, {
            "success":    True,
            "used_bytes": used_bytes,
            "used_gb":    round(used_gb, 4),
            "total_gb":   total_gb,
            "percent":    round(pct, 2),
            "tier":       TIER,
        })
    except Exception as e:
        return resp(500, {"error": str(e)})

def handle_conn(conn, addr):
    try:
        raw = b""
        conn.settimeout(10)
        while True:
            chunk = conn.recv(4096)
            if not chunk: break
            raw += chunk
            if b"\r\n\r\n" in raw: break
        if raw:
            req = parse_request(raw)
            res = dispatch(req)
            conn.sendall(res)
            log.info(f"{addr[0]} {req.get('method','?')} {req.get('path','?')}")
    except Exception as e:
        log.warning(f"Conn error: {e}")
    finally:
        conn.close()

def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", PORT))
    sock.listen(32)
    log.info(f"Omega VPS Instance {INSTANCE_ID[:8]} ONLINE")
    log.info(f"Tier: {TIER} | Port: {PORT} | Storage: {STORAGE_GB}GB")
    while True:
        try:
            conn, addr = sock.accept()
            threading.Thread(target=handle_conn,
                           args=(conn, addr), daemon=True).start()
        except Exception as e:
            log.error(f"Accept error: {e}")

if __name__ == "__main__":
    run()
