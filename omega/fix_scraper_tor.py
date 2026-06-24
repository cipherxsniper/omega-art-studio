PATH = "/data/data/com.termux/files/home/omega_scraper_v4.py"
with open(PATH) as f:
    src = f.read()

OLD = """def tor_opener():
    proxy = ur.ProxyHandler({
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    })
    return ur.build_opener(proxy)"""

NEW = """def tor_opener():
    import socks, socket
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
    socket.socket = socks.socksocket
    return ur.build_opener()"""

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("✅ Tor routing fixed")
else:
    print("❌ NOT FOUND")

with open(PATH, "w") as f:
    f.write(src)
