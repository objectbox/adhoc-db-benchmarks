#!/bin/bash
# One complete measurement run across all engines. Usage: ./lauf.sh <run number> [N] [M] [K]
# Results as JSON lines in ergebnisse.jsonl. Needs root for the cold run (drop_caches).
L=${1:-1}; N=${2:-10000}; M=${3:-2000}; K=${4:-1000}
cd "$(dirname "$0")"; export OBX_LIB=${OBX_LIB:-obxc/lib/libobjectbox.so}
for E in obx sqlite turso libsql; do
  rm -rf data/$E
  python3 messung.py $E create $N | sed "s/^{/{\"run\": $L, /" >> ergebnisse.jsonl
  python3 messung.py $E open $M | sed "s/^{/{\"run\": $L, \"cache\": \"warm\", /" >> ergebnisse.jsonl
  sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null && \
  python3 messung.py $E open $M | sed "s/^{/{\"run\": $L, \"cache\": \"cold\", /" >> ergebnisse.jsonl
  python3 messung.py $E hold $K | sed "s/^{/{\"run\": $L, /" >> ergebnisse.jsonl
done
