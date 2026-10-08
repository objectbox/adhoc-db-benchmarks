#!/bin/bash
# Grosser Lauf, ein Befehl:  ./lauf_gross.sh [N] [M] [K] [Engines] [Ausgabedatei]
#   N = Stores je Engine (Standard 100000), M = zufaellige Stores je Oeffnen-Lauf (10000),
#   K = gleichzeitig offene Stores (1000). Braucht root fuer den kalten Lauf (drop_caches).
# Je Engine zwei Einstellungen: standard, und mallopt (eine Allokator-Zeile im Messprogramm).
# Je Einstellung: anlegen, 3x oeffnen warm, 3x oeffnen kalt (Seitencache vorher geleert), halten.
N=${1:-100000}; M=${2:-10000}; K=${3:-1000}; ENGINES=${4:-"obx sqlite turso libsql"}; OUT=${5:-ergebnisse_gross.jsonl}
cd "$(dirname "$0")"; export OBX_LIB=${OBX_LIB:-obxc/lib/libobjectbox.so}; export MESS_ROOT=${MESS_ROOT:-data_gross}
log() { echo "$(date -u +%H:%M:%S) $*"; }
run() { python3 messung_gross.py "$@" | sed "s/^{/{$TAG /" >> "$OUT" || log "FEHLER bei $*"; }
for E in $ENGINES; do
  for MODE in standard mallopt; do
    if [ $MODE = mallopt ]; then export MESS_MALLOPT=1; else unset MESS_MALLOPT; fi
    rm -rf "$MESS_ROOT/$E"; sync
    log "$E $MODE anlegen $N"; TAG="\"lauf\": 1,"; run $E anlegen $N
    for L in 1 2 3; do
      log "$E $MODE oeffnen warm $L"; TAG="\"lauf\": $L, \"cache\": \"warm\","; run $E oeffnen $N $M $L
    done
    for L in 1 2 3; do
      sync; echo 3 > /proc/sys/vm/drop_caches
      log "$E $MODE oeffnen kalt $L"; TAG="\"lauf\": $L, \"cache\": \"kalt\","; run $E oeffnen $N $M $((L+10))
    done
    log "$E $MODE halten $K"; TAG="\"lauf\": 1,"; run $E halten $N $K 1
  done
done
log "fertig"
