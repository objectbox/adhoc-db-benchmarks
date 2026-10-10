#!/bin/bash
# Waits until the 1-minute load average is below 1, records the environment, then runs the full measurement.
cd "$(dirname "$0")/.."; D=2026_10_09_python_api_model_sync
log() { echo "$(date -u +%H:%M:%S) $*"; }
until awk '{exit !($1 < 1)}' /proc/loadavg; do log "waiting for load < 1: $(cut -d' ' -f1-3 /proc/loadavg)"; sleep 60; done
log "load ok: $(cut -d' ' -f1-3 /proc/loadavg)"
{
  echo "# Environment $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  uname -sr; grep -m1 'model name' /proc/cpuinfo; nproc; free -m | head -2
  df -T . | tail -1
  .venv/bin/python --version
  .venv/bin/python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['objectbox', 'objectbox-clib', 'apsw', 'pyturso', 'libsql', 'flatbuffers', 'numpy']})"
  echo "objectbox-python: $(git -C ../objectbox-python log -1 --format='%h %s')"
  echo "adhoc-db-benchmarks: $(git log -1 --format='%h %s')"
  echo "load average at start: $(cat /proc/loadavg)"
} > $D/environment_large.txt
rm -rf data_large
./run_large.sh 100000 10000 1000 "obx obx_cached obx_nosync sqlite turso libsql" $D/results_large.jsonl
