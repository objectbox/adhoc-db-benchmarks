#!/bin/bash
# Large run, one command:  ./run_large.sh [N] [M] [K] [engines] [output file]
#   N = stores per engine (default 100000), M = random stores per open run (10000),
#   K = stores open at the same time (1000). Needs root for the cold run (drop_caches).
# Per engine two settings: standard, and mallopt (one allocator line in the benchmark program).
# Per setting: create, 3x open warm, 3x open cold (page cache dropped before), hold.
N=${1:-100000}; M=${2:-10000}; K=${3:-1000}; ENGINES=${4:-"obx sqlite turso libsql"}; OUT=${5:-results_large.jsonl}
cd "$(dirname "$0")"; export BENCH_ROOT=${BENCH_ROOT:-data_large}
PYTHON=${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}
log() { echo "$(date -u +%H:%M:%S) $*"; }
run() { "$PYTHON" measure_large.py "$@" | sed "s/^{/{$TAG /" >> "$OUT" || log "ERROR in $*"; }
for E in $ENGINES; do
  for MODE in standard mallopt; do
    if [ $MODE = mallopt ]; then export BENCH_MALLOPT=1; else unset BENCH_MALLOPT; fi
    rm -rf "$BENCH_ROOT/$E"; sync
    log "$E $MODE create $N"; TAG="\"run\": 1,"; run $E create $N
    for L in 1 2 3; do
      log "$E $MODE open warm $L"; TAG="\"run\": $L, \"cache\": \"warm\","; run $E open $N $M $L
    done
    for L in 1 2 3; do
      sync; echo 3 > /proc/sys/vm/drop_caches
      log "$E $MODE open cold $L"; TAG="\"run\": $L, \"cache\": \"cold\","; run $E open $N $M $((L+10))
    done
    log "$E $MODE hold $K"; TAG="\"run\": 1,"; run $E hold $N $K 1
  done
done
log "done"
