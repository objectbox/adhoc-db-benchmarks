#!/bin/bash
# Large workload (1,000 objects of 300 characters per store), 10,000 stores, ObjectBox only (three variants),
# objectbox 5.0.0b1 built from objectbox-python fast-flatbuffers-builder (0ac38fa), installed in .venv.
# Two passes: the generic flatbuffers.Builder (default), then the experimental FlatBuffers codegen.
# Each phase starts only when the 1-minute load average is below 1 (BENCH_MAX_LOAD); load.log samples it every 10 s.
cd "$(dirname "$0")/.."; D=2026_10_14_large_workload_objectbox
( while true; do echo "$(date -u +%H:%M:%S) $(cut -d' ' -f1-3 /proc/loadavg)"; sleep 10; done ) > $D/load.log &
SAMPLER=$!; trap 'kill $SAMPLER' EXIT
{
  echo "# Environment $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  uname -sr; grep -m1 'model name' /proc/cpuinfo; nproc; free -m | head -2
  df -T . | tail -1
  .venv/bin/python --version
  .venv/bin/python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['objectbox', 'objectbox-clib', 'flatbuffers', 'numpy']})"
  echo "objectbox-python: $(git -C ../objectbox-python log -1 --format='%h %s')"
  sha256sum ../objectbox-python/dist/objectbox-5.0.0b1-py3-none-any.whl
  echo "adhoc-db-benchmarks: $(git log -1 --format='%h %s')"
  echo "load average at start: $(cat /proc/loadavg)"
} > $D/environment.txt
ENGINES="obx obx_cached obx_nosync"
rm -rf data_large_large
echo "$(date -u +%H:%M:%S) pass 1: generic flatbuffers.Builder"
unset BENCH_OBX_FLATBUFFERS
BENCH_WORKLOAD=large BENCH_MAX_LOAD=1 ./run_large.sh 10000 10000 1000 "$ENGINES" $D/results_large.jsonl
echo "$(date -u +%H:%M:%S) pass 2: experimental FlatBuffers codegen"
BENCH_OBX_FLATBUFFERS=codegen BENCH_WORKLOAD=large BENCH_MAX_LOAD=1 ./run_large.sh 10000 10000 1000 "$ENGINES" $D/results_large.jsonl
rm -rf data_large_large
echo "$(date -u +%H:%M:%S) all done"
