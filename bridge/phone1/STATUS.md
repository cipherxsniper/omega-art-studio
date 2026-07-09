# OMEGA PHONE 1 — LIVE STATUS
**Generated:** Wed Jun 24 04:28:38 UTC 2026

## Oracle Score
  OMEGA ORACLE v2 — SYSTEM SCORE: 99/100
  Grade: C  |  No change detected — system identical to prior state
  Hash:  6333638747b9316f  (prev: 6333638747b9316f)

## Running Processes
17408 autossh /data/data/com.termux/files/usr/bin/autossh -M 0 -i /data/data/com.termux/files/home/.ssh/omega_bridge -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -o ExitOnForwardFailure=yes -o TCPKeepAlive=yes -L 5432:127.0.0.1:5432 u0_a253@192.168.11.2 -p 8022 -N
17410 /data/data/com.termux/files/usr/bin/ssh /data/data/com.termux/files/usr/bin/ssh -i /data/data/com.termux/files/home/.ssh/omega_bridge -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -o ExitOnForwardFailure=yes -o TCPKeepAlive=yes -L 5432:127.0.0.1:5432 u0_a253@192.168.11.2 -p 8022 -N
18870 bash /data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/omega_bridge_sync.sh
18884 bash /data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/omega_bridge_sync.sh
18892 bash /data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/omega_bridge_sync.sh

## Tunnel URLs


## Disk Usage Phone 1
2.0G	/data/data/com.termux/files/home/sd15-fp16.safetensors
452M	/data/data/com.termux/files/home/misc
425M	/data/data/com.termux/files/home/sdcpp_project
111M	/data/data/com.termux/files/home/paracosm
107M	/data/data/com.termux/files/home/monolith
107M	/data/data/com.termux/files/home/echoes_of_eternity
98M	/data/data/com.termux/files/home/somnium
41M	/data/data/com.termux/files/home/omega_runtime
25M	/data/data/com.termux/files/home/omega-fintech
12M	/data/data/com.termux/files/home/omega
11M	/data/data/com.termux/files/home/omega_ledger_3.db
11M	/data/data/com.termux/files/home/ngrok.tgz
10M	/data/data/com.termux/files/home/phaser.js.map
8.5M	/data/data/com.termux/files/home/lightningcss.android-arm64.node
8.2M	/data/data/com.termux/files/home/control_plane_1.log

## Guardian Log (last 20)
[Tue Jun 23 14:19:21 PDT 2026] RESTART: spawn_engine
[Tue Jun 23 17:57:14 PDT 2026] Guardian started (PID 30099)
[Tue Jun 23 17:57:14 PDT 2026] RESTART: spawn_engine
[Tue Jun 23 17:57:14 PDT 2026] RESTART: node3 http_server
[Tue Jun 23 17:57:17 PDT 2026] RESTART: node3 localhost.run tunnel
[Tue Jun 23 18:05:02 PDT 2026] RESTART: companion_server
[Tue Jun 23 18:05:02 PDT 2026] RESTART: node3_bridge
[Tue Jun 23 18:05:02 PDT 2026] RESTART: dashboard_bridge
[Tue Jun 23 18:07:08 PDT 2026] RESTART: provenance_api
[Tue Jun 23 18:07:08 PDT 2026] RESTART: tunnel_daemon
[Tue Jun 23 19:00:45 PDT 2026] Guardian started (PID 13010)
[Tue Jun 23 19:01:41 PDT 2026] Guardian started (PID 14022)
[Tue Jun 23 19:04:45 PDT 2026] RESTART: gallery cloudflared tunnel
[Tue Jun 23 19:59:24 PDT 2026] Guardian started (PID 3390)
[Tue Jun 23 19:59:54 PDT 2026] RESTART: API cloudflared tunnel
[Tue Jun 23 20:07:00 PDT 2026] Guardian started (PID 10890)
[Tue Jun 23 21:10:30 PDT 2026] RESTART: consensus
[Tue Jun 23 21:11:06 PDT 2026] RESTART: omega_v10.py
[Tue Jun 23 21:11:18 PDT 2026] RESTART: sentinel
[Tue Jun 23 21:11:22 PDT 2026] RESTART: node_manager

## Spawn Log (last 10)
[2026-06-23 20:15:49] Node registry failed: connection to server at "127.0.0.1", port 5432 failed: timeout expired

[2026-06-23 20:15:54] Ledger count failed: connection to server at "127.0.0.1", port 5432 failed: timeout expired

[2026-06-23 20:32:27] Ledger count failed: connection to server at "127.0.0.1", port 5432 failed: timeout expired

[2026-06-23 20:32:32] Node registry failed: connection to server at "127.0.0.1", port 5432 failed: timeout expired

[2026-06-23 20:32:37] Ledger count failed: connection to server at "127.0.0.1", port 5432 failed: timeout expired

## NFT Registry Summary
     collection     | total | sold | for_sale 
--------------------+-------+------+----------
 Echoes of Eternity |   100 |    1 |       86
 Monolith           |   100 |    0 |       87
 Paracosm           |   100 |    0 |       87
 Somnium            |   100 |    0 |       87
(4 rows)

## Recent Sales
 token_id | title  |     collection     | rarity |            sold_at            
----------+--------+--------------------+--------+-------------------------------
        1 | Unique | Echoes of Eternity | Common | 2026-06-23 17:24:25.220261-07
(1 row)

## Wallet Balances
           owner_name           | settled_balance 
--------------------------------+-----------------
 Omega Primary Reserve          |    756150695.17
 Omega Debit Layer              |     59696107.52
 Omega Credit Layer             |     59696107.52
 Omega Investment Pool          |     44782080.64
 Omega Treasury Reserve Account |     26372091.76
(5 rows)
