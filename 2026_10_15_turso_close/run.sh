#!/bin/bash
# Runs check_close.py (results.jsonl) and traces the syscalls of one Turso and one SQLite WAL close (close_trace.txt).
# Usage (from the repository root): ./2026_10_15_turso_close/run.sh
set -e
D=2026_10_15_turso_close; PY=${PYTHON:-.venv/bin/python}; DATA=data_turso_close; rm -rf $DATA
export BENCH_WORKLOAD=large
while awk '{exit !($1 >= 1)}' /proc/loadavg; do sleep 30; done  # wait for a 1-minute load below 1
{ echo "# load: $(cut -d' ' -f1-3 /proc/loadavg)"; uname -sr; df --output=source,fstype . | tail -1; } > $D/environment.txt
$PY $D/check_close.py $DATA 200 > $D/results.jsonl
strace -f -T -e trace=fsync,fdatasync,ftruncate,pwrite64,unlink $PY $D/check_close.py $DATA trace 2>&1 \
  | sed -n '/=== .* close start/,/=== .* close end/p' | grep -v '^write(2' | sed 's/^\[pid *[0-9]*\] //' | sed "s#$PWD/##" > $D/close_trace.txt
rm -rf $DATA
