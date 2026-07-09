import hmac, hashlib, time, json, os
import urllib.request

def get_env(key):
    for line in open('/data/data/com.termux/files/home/.env').readlines():
        if line.startswith(key + '='):
            return line.split('=', 1)[1].strip()
    return ''

HMAC_KEY = get_env('OMEGA_HMAC_KEY')
HMAC_SECRET = get_env('OMEGA_HMAC_SECRET')

def hmac_sign(method, path, body=""):
    timestamp = str(int(time.time()))
    msg = f"{timestamp}{method}{path}{body}"
    sig = hmac.new(HMAC_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return timestamp, sig

def register_node(node_id, endpoint, node_type="cloud_node"):
    body = json.dumps({"node_id": node_id, "node_type": node_type, "endpoint": endpoint})
    path = "/v1/nodes/register"
    timestamp, sig = hmac_sign("POST", path, body)
    req = urllib.request.Request(
        f"http://localhost:5000{path}",
        data=body.encode(),
        headers={
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Signature": sig,
            "X-API-Key": HMAC_KEY,
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.read().decode())

register_node("omega-node-003", "http://localhost:9000", "cloud_node")
print("Node 003 registered")
