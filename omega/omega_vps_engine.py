#!/usr/bin/env python3
"""
OMEGA VPS ENGINE — Sovereign Cloud Provisioning
Provisions isolated node instances for customers.
Each instance gets: port, storage, TLS cert, Bearer token, guardian.
"""
import os
import json
import secrets
import hashlib
import shutil
import subprocess
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
sys.path.insert(0, os.path.expanduser("~/omega_runtime"))
from omega_auth import OmegaAuth
from omega_storage import OmegaStorage

# ── CONFIG ────────────────────────────────────────────────────
HOME         = Path(os.path.expanduser("~"))
VPS_DIR      = HOME / "omega_runtime" / "vps_instances"
CERTS_DIR    = HOME / "omega_runtime" / "certs"
LOGS_DIR     = HOME / "omega_runtime" / "logs"
REGISTRY     = HOME / "omega_runtime" / "vps_registry.json"

VPS_DIR.mkdir(parents=True, exist_ok=True)

# Port range for customer nodes
PORT_START   = 6000
PORT_END     = 6999

# Tier definitions
TIERS = {
    "lite": {
        "name":        "Lite",
        "price":       29,
        "storage_gb":  1,
        "max_objects": 1000,
        "api_calls":   10000,
        "consensus":   False,
        "description": "Observer node — read ledger, verify transactions",
        "permissions": ["storage:read", "ledger:read"],
    },
    "pro": {
        "name":        "Pro",
        "price":       97,
        "storage_gb":  10,
        "max_objects": 10000,
        "api_calls":   100000,
        "consensus":   True,
        "description": "Full node — storage + ledger + API + consensus",
        "permissions": ["storage:read", "storage:write", "storage:delete",
                        "ledger:read", "ledger:write"],
    },
    "sovereign": {
        "name":        "Sovereign",
        "price":       297,
        "storage_gb":  100,
        "max_objects": -1,
        "api_calls":   -1,
        "consensus":   True,
        "description": "Mirror node — full replica, ISO 20022, white-label",
        "permissions": ["storage:read", "storage:write", "storage:delete",
                        "storage:replicate", "ledger:read", "ledger:write",
                        "admin:all"],
    },
}

# ── REGISTRY ──────────────────────────────────────────────────
def load_registry() -> dict:
    if REGISTRY.exists():
        with open(REGISTRY) as f:
            return json.load(f)
    return {"instances": {}, "port_assignments": {}}

def save_registry(reg: dict):
    with open(REGISTRY, "w") as f:
        json.dump(reg, f, indent=2)
    os.chmod(REGISTRY, 0o600)

# ── PORT ALLOCATOR ────────────────────────────────────────────
def allocate_port() -> int:
    reg = load_registry()
    # Only count ports from ACTIVE instances
    used = set(
        inst["port"] for inst in reg["instances"].values()
        if inst["status"] == "ACTIVE"
    )
    for port in range(PORT_START, PORT_END):
        if port not in used:
            # Verify port is actually free
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
    raise RuntimeError("No available ports in range 6000-6999")

# ── TLS CERT ISSUER ───────────────────────────────────────────
def issue_node_cert(instance_id: str, subdomain: str) -> tuple:
    """Issue TLS cert for customer node signed by Omega CA."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        import datetime as dt

        # Load Omega CA
        with open(CERTS_DIR / "omega_ca.key", "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(CERTS_DIR / "omega_ca.crt", "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())

        # Generate node key
        node_key = ec.generate_private_key(ec.SECP384R1())
        now = dt.datetime.now(dt.timezone.utc)

        node_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME,      "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Omega Cloud"),
            x509.NameAttribute(NameOID.COMMON_NAME,       f"{subdomain}.omegacloud.net"),
        ])

        node_cert = (
            x509.CertificateBuilder()
            .subject_name(node_name)
            .issuer_name(ca_cert.subject)
            .public_key(node_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + dt.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(f"{subdomain}.omegacloud.net"),
                    x509.DNSName("localhost"),
                ]), critical=False
            )
            .sign(ca_key, hashes.SHA256())
        )

        # Save to instance dir
        inst_dir = VPS_DIR / instance_id / "certs"
        inst_dir.mkdir(parents=True, exist_ok=True)

        key_path  = inst_dir / "node.key"
        cert_path = inst_dir / "node.crt"
        ca_path   = inst_dir / "omega_ca.crt"

        with open(key_path, "wb") as f:
            f.write(node_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()
            ))
        with open(cert_path, "wb") as f:
            f.write(node_cert.public_bytes(serialization.Encoding.PEM))
        shutil.copy(CERTS_DIR / "omega_ca.crt", ca_path)

        os.chmod(key_path, 0o600)
        return str(cert_path), str(key_path), str(ca_path)

    except Exception as e:
        print(f"[WARN] TLS cert generation failed: {e} — using shared cert")
        return (str(CERTS_DIR / "node3.crt"),
                str(CERTS_DIR / "node3.key"),
                str(CERTS_DIR / "omega_ca.crt"))

# ── INSTANCE PROVISIONER ──────────────────────────────────────
def provision(
    owner_email: str,
    owner_name:  str,
    tier:        str,
    stripe_payment_id: str = None,
) -> dict:
    """
    Provision a new VPS instance.
    Returns full credentials dict.
    """
    if tier not in TIERS:
        raise ValueError(f"Invalid tier: {tier}. Choose: {list(TIERS.keys())}")

    tier_cfg     = TIERS[tier]
    instance_id  = secrets.token_hex(8)
    subdomain    = f"{owner_name.lower().replace(' ','')}-{instance_id[:6]}"
    port         = allocate_port()
    now          = datetime.now(timezone.utc).isoformat()
    expires      = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    print(f"\n[PROVISION] Starting instance {instance_id}")
    print(f"[PROVISION] Owner: {owner_name} | Tier: {tier} | Port: {port}")

    # ── 1. Create directory structure ─────────────────────────
    inst_dir = VPS_DIR / instance_id
    (inst_dir / "storage").mkdir(parents=True, exist_ok=True)
    (inst_dir / "storage_meta").mkdir(parents=True, exist_ok=True)
    (inst_dir / "logs").mkdir(parents=True, exist_ok=True)
    (inst_dir / "auth").mkdir(parents=True, exist_ok=True)
    print(f"[PROVISION] ✅ Directories created")

    # ── 2. Issue TLS certificate ──────────────────────────────
    cert_path, key_path, ca_path = issue_node_cert(instance_id, subdomain)
    print(f"[PROVISION] ✅ TLS cert issued")

    # ── 3. Generate API credentials ───────────────────────────
    bearer = OmegaAuth.generate_bearer(
        owner_id    = instance_id,
        alias       = f"{tier}_bearer",
        permissions = tier_cfg["permissions"],
        expires_days= 30,
    )
    print(f"[PROVISION] ✅ Bearer token generated")

    # ── 4. Write instance config ──────────────────────────────
    config = {
        "instance_id":       instance_id,
        "owner_email":       owner_email,
        "owner_name":        owner_name,
        "tier":              tier,
        "tier_name":         tier_cfg["name"],
        "port":              port,
        "subdomain":         subdomain,
        "endpoint":          f"https://{subdomain}.omegacloud.net:{port}",
        "storage_gb":        tier_cfg["storage_gb"],
        "max_objects":       tier_cfg["max_objects"],
        "consensus":         tier_cfg["consensus"],
        "permissions":       tier_cfg["permissions"],
        "stripe_payment_id": stripe_payment_id,
        "status":            "ACTIVE",
        "created_at":        now,
        "expires_at":        expires,
        "cert_path":         cert_path,
        "key_path":          key_path,
        "ca_path":           ca_path,
        "key_id":            bearer["key_id"],
        "api_key":           bearer["api_key"],
        "directories": {
            "storage":      str(inst_dir / "storage"),
            "storage_meta": str(inst_dir / "storage_meta"),
            "logs":         str(inst_dir / "logs"),
            "auth":         str(inst_dir / "auth"),
        }
    }

    config_path = inst_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(config_path, 0o600)
    print(f"[PROVISION] ✅ Config written")

    # ── 5. Write instance HTTP server ─────────────────────────
    server_code = f'''#!/usr/bin/env python3
"""OMEGA CLOUD — Customer Node Instance {instance_id}"""
import socket, threading, json, os, logging, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.expanduser("~/omega_runtime"))
from omega_auth import OmegaAuth
from omega_storage import OmegaStorage as _BaseStorage

INSTANCE_ID  = "{instance_id}"
OWNER_ID     = "{instance_id}"
PORT         = {port}
STORAGE_DIR  = "{inst_dir}/storage"
META_DIR     = "{inst_dir}/storage_meta"
LOG_FILE     = "{inst_dir}/logs/server.log"
TIER         = "{tier}"
STORAGE_GB   = {tier_cfg["storage_gb"]}
MAX_OBJECTS  = {tier_cfg["max_objects"]}

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(META_DIR,    exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger(f"omega.vps.{{INSTANCE_ID[:8]}}")

def parse_request(raw):
    try:
        header_section, _, body = raw.partition(b"\\r\\n\\r\\n")
        lines = header_section.decode("utf-8", errors="replace").split("\\r\\n")
        method, path, _ = lines[0].split(" ", 2)
        headers = {{}}
        for line in lines[1:]:
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()
        return {{"method": method.upper(), "path": path,
                "headers": headers, "body": body}}
    except:
        return {{}}

def resp(status, body):
    phrases = {{200:"OK",201:"Created",400:"Bad Request",
               401:"Unauthorized",403:"Forbidden",
               404:"Not Found",500:"Internal Server Error"}}
    payload = json.dumps(body).encode()
    headers = "\\r\\n".join([
        f"HTTP/1.1 {{status}} {{phrases.get(status,'Unknown')}}",
        "Content-Type: application/json",
        f"Content-Length: {{len(payload)}}",
        f"X-Omega-Instance: {{INSTANCE_ID[:8]}}",
        f"X-Omega-Tier: {{TIER}}",
        "Connection: close",
    ])
    return headers.encode() + b"\\r\\n\\r\\n" + payload

def bearer(req):
    auth = req.get("headers", {{}}). get("authorization", "")
    if not auth.startswith("Bearer "):
        return None, None
    return OmegaAuth.verify_bearer(auth[7:].strip())

def perm(perms, required):
    return perms and (required in perms or "admin:all" in perms)

ROUTES = {{}}
def route(m, p):
    def d(fn):
        ROUTES[(m.upper(), p)] = fn
        return fn
    return d

def dispatch(req):
    if not req:
        return resp(400, {{"error": "bad request"}})
    key     = (req["method"], req["path"].split("?")[0])
    handler = ROUTES.get(key)
    if handler:
        try:
            return handler(req)
        except Exception as e:
            log.error(f"Handler error: {{e}}")
            return resp(500, {{"error": "internal error"}})
    return resp(404, {{"error": "not found"}})

@route("GET", "/")
def index(req):
    return resp(200, {{
        "instance": INSTANCE_ID[:8],
        "tier": TIER,
        "status": "online",
        "time": datetime.now(timezone.utc).isoformat(),
    }})

@route("GET", "/health")
def health(req):
    return resp(200, {{
        "status": "healthy",
        "instance": INSTANCE_ID[:8],
        "tier": TIER,
        "time": datetime.now(timezone.utc).isoformat(),
    }})

@route("POST", "/v1/storage/upload")
def upload(req):
    owner_id, perms = bearer(req)
    if not owner_id: return resp(401, {{"error": "unauthorized"}})
    if not perm(perms, "storage:write"):
        return resp(403, {{"error": "forbidden"}})
    try:
        # Check storage quota
        used = sum(
            os.path.getsize(os.path.join(STORAGE_DIR, f))
            for f in os.listdir(STORAGE_DIR)
            if os.path.isfile(os.path.join(STORAGE_DIR, f))
        ) / (1024**3)
        if used >= STORAGE_GB:
            return resp(403, {{"error": f"Storage quota exceeded ({{STORAGE_GB}}GB)"}})

        body    = json.loads(req["body"].decode())
        name    = body.get("object_name")
        content = body.get("content", "").encode()
        ctype   = body.get("content_type", "application/octet-stream")
        if not name or not content:
            return resp(400, {{"error": "object_name and content required"}})

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
                nonce   = b"\\x00" * 16
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
        meta = {{
            "object_id":    object_id,
            "owner_id":     owner_id,
            "object_name":  name,
            "content_type": ctype,
            "size_bytes":   len(content),
            "checksum":     checksum,
            "created_at":   _dt.now(_tz.utc).isoformat(),
            "instance":     INSTANCE_ID[:8],
            "tier":         TIER,
        }}
        with open(os.path.join(META_DIR, f"{{object_id}}.json"), "w") as f:
            _j.dump(meta, f)

        return resp(201, {{"success": True, "object": meta}})
    except Exception as e:
        return resp(500, {{"error": str(e)}})

@route("GET", "/v1/storage/list")
def list_objects(req):
    owner_id, perms = bearer(req)
    if not owner_id: return resp(401, {{"error": "unauthorized"}})
    if not perm(perms, "storage:read"):
        return resp(403, {{"error": "forbidden"}})
    try:
        import json as _j
        objects = []
        for fname in os.listdir(META_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(META_DIR, fname)) as f:
                    objects.append(_j.load(f))
        objects.sort(key=lambda x: x["created_at"], reverse=True)
        return resp(200, {{"success": True,
                          "objects": objects,
                          "count": len(objects)}})
    except Exception as e:
        return resp(500, {{"error": str(e)}})

@route("GET", "/v1/quota")
def quota(req):
    owner_id, perms = bearer(req)
    if not owner_id: return resp(401, {{"error": "unauthorized"}})
    try:
        used_bytes = sum(
            os.path.getsize(os.path.join(STORAGE_DIR, f))
            for f in os.listdir(STORAGE_DIR)
            if os.path.isfile(os.path.join(STORAGE_DIR, f))
        )
        used_gb  = used_bytes / (1024**3)
        total_gb = STORAGE_GB
        pct      = (used_gb / total_gb * 100) if total_gb > 0 else 0
        return resp(200, {{
            "success":    True,
            "used_bytes": used_bytes,
            "used_gb":    round(used_gb, 4),
            "total_gb":   total_gb,
            "percent":    round(pct, 2),
            "tier":       TIER,
        }})
    except Exception as e:
        return resp(500, {{"error": str(e)}})

def handle_conn(conn, addr):
    try:
        raw = b""
        conn.settimeout(10)
        while True:
            chunk = conn.recv(4096)
            if not chunk: break
            raw += chunk
            if b"\\r\\n\\r\\n" in raw: break
        if raw:
            req = parse_request(raw)
            res = dispatch(req)
            conn.sendall(res)
            log.info(f"{{addr[0]}} {{req.get('method','?')}} {{req.get('path','?')}}")
    except Exception as e:
        log.warning(f"Conn error: {{e}}")
    finally:
        conn.close()

def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", PORT))
    sock.listen(32)
    log.info(f"Omega VPS Instance {{INSTANCE_ID[:8]}} ONLINE")
    log.info(f"Tier: {{TIER}} | Port: {{PORT}} | Storage: {{STORAGE_GB}}GB")
    while True:
        try:
            conn, addr = sock.accept()
            threading.Thread(target=handle_conn,
                           args=(conn, addr), daemon=True).start()
        except Exception as e:
            log.error(f"Accept error: {{e}}")

if __name__ == "__main__":
    run()
'''

    server_path = inst_dir / "server.py"
    with open(server_path, "w") as f:
        f.write(server_code)
    os.chmod(server_path, 0o755)
    print(f"[PROVISION] ✅ Instance server written")

    # ── 6. Write guardian script ──────────────────────────────
    guardian_code = f'''#!/data/data/com.termux/files/usr/bin/bash
# Guardian for instance {instance_id[:8]}
LOG="{inst_dir}/logs/guardian.log"
if ! pgrep -f "server.py.*{port}" > /dev/null 2>&1; then
    nohup python3 "{inst_dir}/server.py" >> "$LOG" 2>&1 &
    echo "[$(date -u)] RESTARTED instance {instance_id[:8]}" >> "$LOG"
fi
'''
    guardian_path = inst_dir / "guardian.sh"
    with open(guardian_path, "w") as f:
        f.write(guardian_code)
    os.chmod(guardian_path, 0o755)
    print(f"[PROVISION] ✅ Guardian written")

    # ── 7. Register in registry ───────────────────────────────
    reg = load_registry()
    reg["instances"][instance_id] = {
        "instance_id":  instance_id,
        "owner_email":  owner_email,
        "owner_name":   owner_name,
        "tier":         tier,
        "port":         port,
        "subdomain":    subdomain,
        "status":       "ACTIVE",
        "created_at":   now,
        "expires_at":   expires,
        "stripe_id":    stripe_payment_id,
        "key_id":       bearer["key_id"],
    }
    reg["port_assignments"][instance_id] = port
    save_registry(reg)
    print(f"[PROVISION] ✅ Registered in registry")

    # ── 8. Add to cron ────────────────────────────────────────
    cron_line = (f"*/1 * * * * bash {inst_dir}/guardian.sh "
                 f">> {inst_dir}/logs/guardian.log 2>&1")
    os.system(f'(crontab -l 2>/dev/null; echo "{cron_line}") | crontab -')
    print(f"[PROVISION] ✅ Guardian added to cron (every 1 min)")

    # ── 9. Start instance immediately ─────────────────────────
    subprocess.Popen(
        ["python3", str(server_path)],
        stdout=open(f"{inst_dir}/logs/server.log", "a"),
        stderr=subprocess.STDOUT,
    )
    print(f"[PROVISION] ✅ Instance started on port {port}")

    # ── 10. Build credentials package ─────────────────────────
    credentials = {
        "instance_id":   instance_id,
        "subdomain":     subdomain,
        "endpoint":      f"https://{subdomain}.omegacloud.net:{port}",
        "local_port":    port,
        "tier":          tier_cfg["name"],
        "storage_gb":    tier_cfg["storage_gb"],
        "api_key":       bearer["api_key"],
        "key_id":        bearer["key_id"],
        "ca_cert":       ca_path,
        "expires_at":    expires,
        "created_at":    now,
        "install_cmd":   f"curl -sSL https://omegaledgernode.netlify.app/install.sh | OMEGA_KEY={bearer['api_key']} OMEGA_PORT={port} bash",
        "health_check":  f"curl http://127.0.0.1:{port}/health",
        "permissions":   tier_cfg["permissions"],
    }

    print(f"\n{'='*60}")
    print(f"  OMEGA VPS — INSTANCE PROVISIONED")
    print(f"{'='*60}")
    print(f"  Instance  : {instance_id[:8]}")
    print(f"  Owner     : {owner_name} <{owner_email}>")
    print(f"  Tier      : {tier_cfg['name']} (${tier_cfg['price']}/mo)")
    print(f"  Port      : {port}")
    print(f"  Subdomain : {subdomain}.omegacloud.net")
    print(f"  Storage   : {tier_cfg['storage_gb']}GB")
    print(f"  Expires   : {expires[:10]}")
    print(f"{'='*60}")
    print(f"  API Key   : {bearer['api_key']}")
    print(f"{'='*60}")
    print(f"  Health    : curl http://127.0.0.1:{port}/health")
    print(f"{'='*60}\n")

    return credentials


# ── INSTANCE MANAGER ──────────────────────────────────────────
def list_instances() -> list:
    reg = load_registry()
    return list(reg["instances"].values())

def get_instance(instance_id: str) -> dict:
    reg = load_registry()
    return reg["instances"].get(instance_id)

def terminate(instance_id: str) -> bool:
    reg = load_registry()
    if instance_id not in reg["instances"]:
        return False
    inst = reg["instances"][instance_id]
    port = inst["port"]
    # Kill process
    os.system(f"pkill -f 'server.py.*{port}' 2>/dev/null")
    # Mark terminated
    reg["instances"][instance_id]["status"] = "TERMINATED"
    reg["instances"][instance_id]["terminated_at"] = datetime.now(timezone.utc).isoformat()
    del reg["port_assignments"][instance_id]
    save_registry(reg)
    print(f"[TERMINATE] Instance {instance_id[:8]} terminated")
    return True

def status_all() -> dict:
    reg      = load_registry()
    active   = sum(1 for i in reg["instances"].values() if i["status"] == "ACTIVE")
    total    = len(reg["instances"])
    ports    = list(reg["port_assignments"].values())
    return {
        "total_instances": total,
        "active":          active,
        "terminated":      total - active,
        "ports_in_use":    ports,
        "next_port":       max(ports) + 1 if ports else PORT_START,
    }


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "provision":
        # python3 omega_vps_engine.py provision email name tier
        email = sys.argv[2] if len(sys.argv) > 2 else "test@omega.ai"
        name  = sys.argv[3] if len(sys.argv) > 3 else "TestUser"
        tier  = sys.argv[4] if len(sys.argv) > 4 else "lite"
        provision(email, name, tier)

    elif cmd == "list":
        instances = list_instances()
        if not instances:
            print("No instances provisioned yet.")
        else:
            print(f"\n{'='*60}")
            print(f"  OMEGA VPS — {len(instances)} INSTANCE(S)")
            print(f"{'='*60}")
            for inst in instances:
                status_icon = "🟢" if inst["status"] == "ACTIVE" else "🔴"
                print(f"  {status_icon} {inst['instance_id'][:8]} | "
                      f"{inst['tier']:10} | "
                      f"port {inst['port']} | "
                      f"{inst['owner_email']}")
            print(f"{'='*60}\n")

    elif cmd == "status":
        s = status_all()
        print(f"\n{'='*60}")
        print(f"  OMEGA VPS ENGINE STATUS")
        print(f"{'='*60}")
        print(f"  Total instances : {s['total_instances']}")
        print(f"  Active          : {s['active']}")
        print(f"  Terminated      : {s['terminated']}")
        print(f"  Ports in use    : {s['ports_in_use']}")
        print(f"  Next port       : {s['next_port']}")
        print(f"{'='*60}\n")

    elif cmd == "terminate":
        iid = sys.argv[2] if len(sys.argv) > 2 else None
        if not iid:
            print("Usage: omega_vps_engine.py terminate <instance_id>")
        else:
            terminate(iid)

    elif cmd == "tiers":
        print(f"\n{'='*60}")
        print(f"  OMEGA VPS — PRICING TIERS")
        print(f"{'='*60}")
        for tid, t in TIERS.items():
            print(f"\n  {t['name']} — ${t['price']}/mo [{tid}]")
            print(f"    {t['description']}")
            print(f"    Storage  : {t['storage_gb']}GB")
            print(f"    Consensus: {'Yes' if t['consensus'] else 'No'}")
            print(f"    Perms    : {', '.join(t['permissions'])}")
        print(f"\n{'='*60}\n")

    else:
        print("""
OMEGA VPS ENGINE — Commands:
  provision <email> <name> <tier>  — provision new instance
  list                             — list all instances
  status                           — engine status
  terminate <instance_id>          — terminate instance
  tiers                            — show pricing tiers
        """)
