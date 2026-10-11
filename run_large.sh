#!/bin/bash
# Large run, one command:  ./run_large.sh [N] [M] [K] [engines] [output file]
#   N = stores per engine (default 100000), M = random stores per open run (10000),
#   K = stores open at the same time (1000). Needs root for the cold run (drop_caches); skipped otherwise.
# Per engine two settings: standard, and mallopt (one allocator line in the benchmark program).
# Per setting: create, 3x open warm, 3x open cold (page cache dropped before), hold.
# BENCH_WORKLOAD=small (default; ten objects with a short text per store) or large (1,000 objects with a
# 300-character text), written in one transaction; each workload has its own data directory.
# BENCH_MAX_LOAD=1: before each phase, wait until the 1-minute load average is below this value.
# The 1-minute load average at the start of each phase is recorded as "load1".
N=${1:-100000}; M=${2:-10000}; K=${3:-1000}; ENGINES=${4:-"obx sqlite turso libsql"}; OUT=${5:-results_large.jsonl}
cd "$(dirname "$0")"; export BENCH_WORKLOAD=${BENCH_WORKLOAD:-small}
case $BENCH_WORKLOAD in small|large) ;; *) echo "unknown BENCH_WORKLOAD $BENCH_WORKLOAD (small|large)" >&2; exit 1;; esac
export BENCH_ROOT=${BENCH_ROOT:-$( [ $BENCH_WORKLOAD = small ] && echo data_large || echo data_large_$BENCH_WORKLOAD )}
set -o pipefail  # run(): report a failing measure_large.py, not only a failing sed
PYTHON=${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}
log() { echo "$(date -u +%H:%M:%S) $*"; }
wait_load() {
  [ -z "$BENCH_MAX_LOAD" ] && return
  until awk -v max="$BENCH_MAX_LOAD" '{exit !($1 < max)}' /proc/loadavg; do
    log "waiting for load < $BENCH_MAX_LOAD: $(cut -d' ' -f1-3 /proc/loadavg)"; sleep 30
  done
}
run() {
  wait_load; local load1; load1=$(cut -d' ' -f1 /proc/loadavg)
  "$PYTHON" measure_large.py "$@" | sed "s/^{/{$TAG \"load1\": $load1, /" >> "$OUT" || log "ERROR in $*"
}
for E in $ENGINES; do
  for MODE in standard mallopt; do
    if [ $MODE = mallopt ]; then export BENCH_MALLOPT=1; else unset BENCH_MALLOPT; fi
    rm -rf "$BENCH_ROOT/$E"; sync
    log "$E $MODE create $N ($BENCH_WORKLOAD)"; TAG="\"run\": 1,"; run $E create $N
    for L in 1 2 3; do
      log "$E $MODE open warm $L"; TAG="\"run\": $L, \"cache\": \"warm\","; run $E open $N $M $L
    done
    if [ -w /proc/sys/vm/drop_caches ]; then
      for L in 1 2 3; do
        sync; echo 3 > /proc/sys/vm/drop_caches
        log "$E $MODE open cold $L"; TAG="\"run\": $L, \"cache\": \"cold\","; run $E open $N $M $((L+10))
      done
    else
      log "$E $MODE open cold: skipped (dropping the page cache needs root)"
    fi
    log "$E $MODE hold $K"; TAG="\"run\": 1,"; run $E hold $N $K 1
  done
done
log "done"
