#!/bin/bash
# Ein kompletter Messlauf ueber alle Engines. Aufruf: ./lauf.sh <Laufnummer> [N] [M] [K]
# Ergebnisse als JSON-Zeilen in ergebnisse.jsonl. Braucht root fuer den kalten Lauf (drop_caches).
L=${1:-1}; N=${2:-10000}; M=${3:-2000}; K=${4:-1000}
cd "$(dirname "$0")"; export OBX_LIB=${OBX_LIB:-obxc/lib/libobjectbox.so}
for E in obx sqlite turso libsql; do
  rm -rf data/$E
  python3 messung.py $E anlegen $N | sed "s/^{/{\"lauf\": $L, /" >> ergebnisse.jsonl
  python3 messung.py $E oeffnen $M | sed "s/^{/{\"lauf\": $L, \"cache\": \"warm\", /" >> ergebnisse.jsonl
  sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null && \
  python3 messung.py $E oeffnen $M | sed "s/^{/{\"lauf\": $L, \"cache\": \"kalt\", /" >> ergebnisse.jsonl
  python3 messung.py $E halten $K | sed "s/^{/{\"lauf\": $L, /" >> ergebnisse.jsonl
done
