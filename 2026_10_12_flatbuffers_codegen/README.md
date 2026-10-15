# Large workload, create with the experimental FlatBuffers codegen (ObjectBox Python)

As of 2026-10-12 · measured on a desktop workstation. One phase of `../2026_10_11_large_workload/README.md` repeated: creating 10,000 stores with 1,000 objects of 300 characters each, ObjectBox with a cached model (`obx_cached`), default allocator settings; the objects are marshalled with the experimental FlatBuffers codegen of objectbox-python (unreleased branch `fast-flatbuffers-builder`) instead of the generic `flatbuffers.Builder`.

## Result in three sentences

With the experimental FlatBuffers codegen, creating a store and writing 1,000 objects takes 21.55 ms (median) instead of 30.73 ms, 30% less, and ObjectBox is now faster than SQLite (26.59 ms) in this phase. The gain of ~9 ms is less than the ~15 ms the generic builder spends on marshalling, as the codegen still needs some CPU time per object and the CPU work runs at a lower clock while the process mostly waits for disk syncs (see the caveats). The stored data is the same (472 KB per store; the codegen produces the same bytes as the generic builder).

## Create, write 1,000 objects, close: 10,000 stores

| | ObjectBox, cached model, generic builder (2026-10-11) | ObjectBox, cached model, FlatBuffers codegen | SQLite (2026-10-11) |
|---|---|---|---|
| Median | 30.73 ms | 21.55 ms | 26.59 ms |
| p95 | 37.41 ms | 28.49 ms | |
| p99 | 38.98 ms | 29.67 ms | |
| Mean | 32.14 ms | 22.38 ms | |
| Stores per second | 31 | 45 | 34 |
| Load at the start | 0.71 | 0.73 | |
| Space per store, files | 472 KB | 472 KB | 316 KB |

The new column is from `results_create.jsonl`; the others are from `../2026_10_11_large_workload/results_large.jsonl` (setting `standard`).

## What was measured

- The create phase of `measure_large.py` (create the directory, open the new store, put 1,000 `Note` objects in one transaction, close) for `obx_cached`, with `BENCH_WORKLOAD=large` and `BENCH_OBX_FLATBUFFERS=codegen`, which calls `objectbox.experimental.enable_flatbuffers_codegen()` (recorded as `"obx_flatbuffers": "codegen"`).
- objectbox from the objectbox-python checkout via `PYTHONPATH` (branch `fast-flatbuffers-builder`, c0e3088; the same C library 5.3.2 as the 2026-10-11 measurement).
- The phase was started at a load below 1 (0.73).

## Caveats

1. Only this one phase and variant was run, not the full suite; the comparison values are from the previous day's run (same machine, same load gate, same data directory). A same-day rerun with the generic builder was not done.
2. In profiles with the fast builder (the codegen's predecessor), the remaining CPU work ran at an effective ~3.1 GHz instead of ~4.4 GHz on disk: the process mostly waits for the two disk syncs per store, and the CPU clocks down. On tmpfs (no real disk sync), the marshalling step dropped from ~15 ms to ~2.7 ms per store; on disk, the gain is smaller. This was not profiled again for the codegen.
3. The FlatBuffers codegen is experimental and unreleased; the bytes it produces are verified against the generic builder in the objectbox-python tests.

## Reproduce

Versions (`environment.txt`): Linux 6.8, Python 3.12.3, objectbox from objectbox-python `fast-flatbuffers-builder` (c0e3088; package version 5.0.0b1) with objectbox-clib 5.3.2, flatbuffers 25.12.19, numpy 2.5.3. Venv as in `../2026_10_09_python_api_model_sync/README.md`.

```bash
OBJECTBOX_PYTHON=<objectbox-python checkout> ./2026_10_12_flatbuffers_codegen/run_create.sh > 2026_10_12_flatbuffers_codegen/run_create.log 2>&1
```

`run_create.sh` waits for a load below 1, deletes `data_large_large/obx_cached`, runs `measure_large.py obx_cached create 10000` and deletes the data again (4.5 GB). Runtime: 3 min 46 s (2026-10-12 07:18 to 07:22 UTC).
