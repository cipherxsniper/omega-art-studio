#!/data/data/com.termux/files/usr/bin/bash
if ! pgrep -f "omega_gallery_server.py" > /dev/null 2>&1; then
    nohup python3 /data/data/com.termux/files/home/omega_gallery_server.py >> /data/data/com.termux/files/home/omega_runtime/logs/gallery_server.log 2>&1 &
fi
if ! pgrep -f "cloudflared tunnel --url http://127.0.0.1:8090" > /dev/null 2>&1; then
    nohup cloudflared tunnel --url http://127.0.0.1:8090 > /data/data/com.termux/files/home/cloudflare_gallery.log 2>&1 &
fi
