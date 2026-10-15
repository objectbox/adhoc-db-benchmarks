# Large workload, ObjectBox with objectbox-python 0ac38fa: generic builder and FlatBuffers codegen

As of 2026-10-14 · measured on a desktop workstation. The ObjectBox part of `../2026_10_11_large_workload/README.md` repeated with a newer objectbox-python: 10,000 stores per variant with 1,000 objects of 300 characters each, the three ObjectBox variants, both allocator settings, warm page cache only, each phase started only when the 1-minute load average was below 1. Each variant ran twice, with the generic `flatbuffers.Builder` (the default) and with the experimental FlatBuffers codegen.

## Result in three sentences

With the experimental FlatBuffers codegen, creating a store and writing 1,000 objects takes 17.5–18.0 ms (median, default allocator settings) instead of 30.5–31.2 ms with the generic builder, in all three ObjectBox variants; that is faster than SQLite's 26.59 ms (2026-10-11) and also faster than the 21.55 ms measured with the codegen on 2026-10-12, as objectbox-python has since been sped up further (puts, transactions). With the generic builder, the numbers are the same as on 2026-10-11 (within ~1 ms), as expected: the newer objectbox-python does not change how the generic builder marshals a batch of objects. Open, query and close, memory and disk space do not depend on the builder and match 2026-10-11 within noise (e.g. 0.22–0.23 ms for open, query, close with `skip_model_sync`).

## Create, write 1,000 objects, close: 10,000 stores, default allocator settings

| | ObjectBox, sync every open | ObjectBox, cached model | ObjectBox, skip model sync | SQLite (2026-10-11) |
|---|---|---|---|---|
| Generic builder (median) | 31.07 ms | 30.46 ms | 31.23 ms | |
| FlatBuffers codegen (median) | 17.88 ms | 18.02 ms | 17.46 ms | 26.59 ms |
| FlatBuffers codegen, p99 | 25.96 ms | 25.55 ms | 25.41 ms | |
| FlatBuffers codegen, stores per second | 52 | 51 | 52 | 34 |
| 2026-10-11, generic builder (objectbox-python 5cc8f48) | 30.72 ms | 30.73 ms | 29.85 ms | |
| 2026-10-12, codegen (objectbox-python c0e3088) | – | 21.55 ms | – | |

## All phases, by setting

Printed by `python3 tables.py` from `results_large.jsonl` (medians of the three warm open runs; the 2026-10-11 row is from `../2026_10_11_large_workload/results_large.jsonl`).

### Setting: standard

| | sync every open, generic | sync every open, codegen | cached model, generic | cached model, codegen | skip model sync, generic | skip model sync, codegen |
|---|---|---|---|---|---|---|
| Create, write 1,000 objects, close (median) | 31.07 ms | 17.88 ms | 30.46 ms | 18.02 ms | 31.23 ms | 17.46 ms |
| same, p99 | 39.00 ms | 25.96 ms | 38.41 ms | 25.55 ms | 38.90 ms | 25.41 ms |
| same, 2026-10-11 (dev 5cc8f48, generic) | 30.72 ms | – | 30.73 ms | – | 29.85 ms | – |
| Stores per second | 31 | 52 | 31 | 51 | 31 | 52 |
| Open (median) | 0.289 ms | 0.288 ms | 0.198 ms | 0.210 ms | 0.099 ms | 0.106 ms |
| Count query (median) | 0.095 ms | 0.093 ms | 0.085 ms | 0.090 ms | 0.085 ms | 0.090 ms |
| Open, query, close (median) | 0.418 ms | 0.418 ms | 0.317 ms | 0.338 ms | 0.217 ms | 0.232 ms |
| same, p99 | 0.471 ms | 0.504 ms | 0.374 ms | 0.443 ms | 0.260 ms | 0.297 ms |
| Close (median) | 0.034 ms | 0.034 ms | 0.032 ms | 0.034 ms | 0.033 ms | 0.037 ms |
| Memory per open store (1,000 open), resident | 2,538 KB | 2,538 KB | 2,534 KB | 2,535 KB | 491 KB | 491 KB |
| same, anonymous (process' own memory) | 2,065 KB | 2,065 KB | 2,062 KB | 2,062 KB | 19 KB | 19 KB |
| Load at the start of create | 0.55 | 0.73 | 0.78 | 0.81 | 0.84 | 0.72 |
| Load at start of the warm open runs (max) | 0.98 | 0.87 | 0.93 | 0.99 | 0.93 | 0.76 |
| Space per store, files | 472 KB | 472 KB | 472 KB | 472 KB | 472 KB | 472 KB |

### Setting: mallopt

`mallopt(M_MMAP_THRESHOLD, 131072)`, as in the 2026-10-11 measurement.

| | sync every open, generic | sync every open, codegen | cached model, generic | cached model, codegen | skip model sync, generic | skip model sync, codegen |
|---|---|---|---|---|---|---|
| Create, write 1,000 objects, close (median) | 31.91 ms | 18.52 ms | 31.43 ms | 18.25 ms | 31.41 ms | 20.34 ms |
| same, p99 | 39.83 ms | 26.43 ms | 39.35 ms | 26.67 ms | 39.46 ms | 26.73 ms |
| same, 2026-10-11 (dev 5cc8f48, generic) | 31.02 ms | – | 30.89 ms | – | 31.46 ms | – |
| Stores per second | 30 | 50 | 30 | 50 | 30 | 48 |
| Open (median) | 0.267 ms | 0.277 ms | 0.180 ms | 0.190 ms | 0.085 ms | 0.087 ms |
| Count query (median) | 0.093 ms | 0.096 ms | 0.087 ms | 0.088 ms | 0.086 ms | 0.093 ms |
| Open, query, close (median) | 0.405 ms | 0.418 ms | 0.309 ms | 0.325 ms | 0.215 ms | 0.224 ms |
| same, p99 | 0.489 ms | 0.509 ms | 0.402 ms | 0.473 ms | 0.304 ms | 0.300 ms |
| Close (median) | 0.043 ms | 0.044 ms | 0.042 ms | 0.044 ms | 0.044 ms | 0.043 ms |
| Memory per open store (1,000 open), resident | 491 KB | 491 KB | 491 KB | 491 KB | 491 KB | 491 KB |
| same, anonymous (process' own memory) | 19 KB | 19 KB | 19 KB | 19 KB | 19 KB | 19 KB |
| Load at the start of create | 0.89 | 0.88 | 0.77 | 0.69 | 0.93 | 0.67 |
| Load at start of the warm open runs (max) | 0.76 | 0.99 | 0.83 | 0.91 | 0.71 | 0.92 |
| Space per store, files | 472 KB | 472 KB | 472 KB | 472 KB | 472 KB | 472 KB |

## What was measured

- Same phases as `../2026_10_11_large_workload/README.md` (`measure_large.py` via `run_large.sh`: create, three warm open runs over all 10,000 stores in random order, hold 1,000 stores open), with `BENCH_WORKLOAD=large`, for `obx`, `obx_cached` and `obx_nosync`, settings `standard` and `mallopt`.
- Two passes: first with the generic `flatbuffers.Builder` (default), then with `BENCH_OBX_FLATBUFFERS=codegen`, which calls `objectbox.experimental.enable_flatbuffers_codegen()` (recorded as `"obx_flatbuffers": "codegen"`).
- objectbox 5.0.0b1 built from objectbox-python branch `fast-flatbuffers-builder` at `0ac38fa` (wheel SHA-256 in `environment.txt`), installed in the venv; C library 5.3.2, as on 2026-10-11. Compared to the 2026-10-11 measurement (`dev`, 5cc8f48), this includes faster puts and transactions, lazy imports of numpy and flatbuffers, and the experimental codegen.
- Load control: `BENCH_MAX_LOAD=1`; before each phase `run_large.sh` waited until the 1-minute load average was below 1 (155 waits of 30 s); the load at each phase's start is in the results as `load1`, and `load.log` samples it every 10 s.

## Caveats

1. Warm page cache only (no root for `drop_caches`).
2. From 06:57 UTC until at least 08:12 UTC, i.e. during most of the codegen pass (06:47–08:21 UTC), another benchmark process (single-threaded, pinned to one core) ran on the workstation. Phases still started only at a load below 1, but that process kept the load above 1 for long stretches (most of the waiting) and may have run during phases. The codegen numbers for open, query, close are 0.01–0.07 ms higher than the generic ones although the builder is not involved there; this is likely that interference, not the codegen.
   The highest load in `load.log` (up to 28 around 07:48 UTC, test suites run on the same workstation) fell into a wait between two phases (07:35–07:53 UTC); no measured phase overlapped it.
3. The load was only controlled at the start of each phase. During creation it rose to 2–3; on Linux the load average includes processes waiting for disk I/O, so this is mostly the benchmark's own disk syncs.
4. One run per setting, variant and builder (three open runs each); not comparable in absolute numbers to the 100,000-store measurements. SQLite was not re-run; its value is from 2026-10-11 (same machine, same load gate).
5. The FlatBuffers codegen is experimental and unreleased; the bytes it produces are verified against the generic builder in the objectbox-python tests.

## Reproduce

Versions (`environment.txt`): Linux 6.8, Python 3.12.3, objectbox 5.0.0b1 from objectbox-python `fast-flatbuffers-builder` (0ac38fa) with objectbox-clib 5.3.2, flatbuffers 25.12.19, numpy 2.5.3. Venv as in `../2026_10_09_python_api_model_sync/README.md`, with the wheels from objectbox-python's `dist/` (`pip install --force-reinstall objectbox==5.0.0b1 --find-links <objectbox-python>/dist`).

```bash
./2026_10_14_large_workload_objectbox/run_all.sh > 2026_10_14_large_workload_objectbox/run_large.log 2>&1
python3 2026_10_14_large_workload_objectbox/tables.py
```

`run_all.sh` starts the load sampler (`load.log`), records the environment, deletes `data_large_large`, runs `BENCH_WORKLOAD=large BENCH_MAX_LOAD=1 ./run_large.sh 10000 10000 1000 "obx obx_cached obx_nosync"` once without and once with `BENCH_OBX_FLATBUFFERS=codegen`, and deletes the data again. Runtime: 2 h 13 min (2026-10-14 06:08 to 08:21 UTC), of which ~77 min waiting for the load; creating 10,000 stores took ~5.5 min with the generic builder and 3.2–3.5 min with the codegen.
