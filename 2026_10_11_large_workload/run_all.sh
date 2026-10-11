#!/bin/bash
# Large workload (1,000 objects of 300 characters per store), 10,000 stores per engine, all engines.
# Each phase starts only when the 1-minute load average is below 1 (BENCH_MAX_LOAD); load.log samples it every 10 s.
cd "$(dirname "$0")/.."; D=2026_10_11_large_workload
( while true; do echo "$(date -u +%H:%M:%S) $(cut -d' ' -f1-3 /proc/loadavg)"; sleep 10; done ) > $D/load.log &
SAMPLER=$!; trap 'kill $SAMPLER' EXIT
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
rm -rf data_large_large
BENCH_WORKLOAD=large BENCH_MAX_LOAD=1 ./run_large.sh 10000 10000 1000 "obx obx_cached obx_nosync sqlite turso libsql" $D/results_large.jsonl
