#!/bin/bash
# One phase only: ObjectBox obx_cached, create 10,000 stores with the large workload (1,000 objects of 300 characters),
# standard allocator, objects marshalled with the experimental FlatBuffers codegen.
# OBJECTBOX_PYTHON: checkout of objectbox-python, branch fast-flatbuffers-builder (used via PYTHONPATH).
# Run from the repository root: 2026_10_12_flatbuffers_codegen/run_create.sh
set -o pipefail
cd "$(dirname "$0")/.."
D=2026_10_12_flatbuffers_codegen; N=${1:-10000}; MAX_LOAD=${BENCH_MAX_LOAD:-1}
export BENCH_WORKLOAD=large BENCH_ROOT=data_large_large BENCH_OBX_FLATBUFFERS=codegen
export PYTHONPATH=${OBJECTBOX_PYTHON:?set OBJECTBOX_PYTHON to the objectbox-python checkout}
log() { echo "$(date -u +%H:%M:%S) $*"; }
until awk -v max="$MAX_LOAD" '{exit !($1 < max)}' /proc/loadavg; do
  log "waiting for load < $MAX_LOAD: $(cut -d' ' -f1-3 /proc/loadavg)"; sleep 30
done
rm -rf "$BENCH_ROOT/obx_cached"; sync
load1=$(cut -d' ' -f1 /proc/loadavg)
log "obx_cached standard create $N ($BENCH_WORKLOAD, $BENCH_OBX_FLATBUFFERS), load1 $load1"
.venv/bin/python measure_large.py obx_cached create "$N" | sed "s/^{/{\"run\": 1, \"load1\": $load1, /" >> $D/results_create.jsonl \
  || log "ERROR"
rm -rf "$BENCH_ROOT/obx_cached"
log "done"
