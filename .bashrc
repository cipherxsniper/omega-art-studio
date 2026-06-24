alias score='export PGPASSWORD=omega && python3 ~/omega_oracle_v2.py score'
alias omega="bash /data/data/com.termux/files/home/omega_start.sh"

# Phone 2 remote commands — run from Phone 1
alias p2="ssh -i /data/data/com.termux/files/home/.ssh/omega_bridge -o StrictHostKeyChecking=no u0_a253@192.168.11.163 -p 8022"
alias p2pg="psql -h 127.0.0.1 -p 5432 -U postgres -d omega_bank"
alias p2status="ssh -i /data/data/com.termux/files/home/.ssh/omega_bridge -o StrictHostKeyChecking=no u0_a253@192.168.11.163 -p 8022 'pgrep -f omega_consensus && echo CONSENSUS:UP || echo CONSENSUS:DEAD; pg_ctl status -D \$PREFIX/var/lib/postgresql | head -1'"
alias p2boot='p2 "cd ~/Omega-Production/omega_bank && setsid python3 omega_consensus.py >> ~/omega_runtime/logs/consensus.log 2>&1 </dev/null & setsid python3 omega_node_manager.py >> ~/omega_runtime/logs/node_manager.log 2>&1 </dev/null & sleep 5 && pgrep -f omega_consensus && echo CONSENSUS:UP"'

# OMEGA MASTER BOOT — one command, entire system
alias omega-full='omega && p2boot'
