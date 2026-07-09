PATH = "/data/data/com.termux/files/home/omega_tunnel_daemon.sh"
with open(PATH) as f:
    src = f.read()

src = src.replace(
    "-o ServerAliveInterval=10 \\\n      -o ServerAliveCountMax=3 \\",
    "-o ServerAliveInterval=30 \\\n      -o ServerAliveCountMax=6 \\\n      -o TCPKeepAlive=yes \\"
)
with open(PATH, "w") as f:
    f.write(src)
print("Fixed")
