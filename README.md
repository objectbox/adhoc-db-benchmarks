# Adhoc DB Benchmarks: one database per agent

Ad-hoc measurements, not an official benchmark: the fixed cost of many small stores (one per agent) for ObjectBox, SQLite, Turso Database and libSQL. All results are internal until they have been reviewed.

## Main results

**2026-10-10, workstation, ObjectBox through the Python API** ([details](2026_10_09_python_api_model_sync/README.md)): 100,000 stores per engine, warm page cache, default allocator settings.

| | ObjectBox, sync every open | ObjectBox, cached model | ObjectBox, skip model sync | SQLite | Turso Database | libSQL |
|---|---|---|---|---|---|---|
| Open, query, close (median) | 0.327 ms | 0.240 ms | 0.135 ms | 0.079 ms | 7.035 ms | 0.104 ms |
| same, p99 | 0.473 ms | 0.320 ms | 0.189 ms | 0.100 ms | 11.901 ms | 0.117 ms |
| Memory per open store (1,000 open) | 2,090 KB | 2,086 KB | 43 KB | 152 KB | 1,566 KB | 163 KB |
| Create, write ten objects, close (median) | 14.93 ms | 14.35 ms | 14.25 ms | 22.04 ms | 34.22 ms | 36.10 ms |
| Space per store, files | 24 KB | 24 KB | 24 KB | 8 KB | 8 KB | 8 KB |

Creation on this machine is dominated by the disk's sync latency. With `mallopt(M_MMAP_THRESHOLD, 131072)`, all three ObjectBox variants need 43 KB per open store.

**2026-10-11, workstation, large workload** ([details](2026_10_11_large_workload/README.md)): 1,000 objects with a 300-character text per store, 10,000 stores per engine, warm page cache, default allocator settings; each phase started at a load below 1.

| | ObjectBox, sync every open | ObjectBox, cached model | ObjectBox, skip model sync | SQLite | Turso Database | libSQL |
|---|---|---|---|---|---|---|
| Open, query, close (median) | 0.433 ms | 0.332 ms | 0.218 ms | 0.275 ms | 7.524 ms | 0.195 ms |
| same, p99 | 0.555 ms | 0.457 ms | 0.338 ms | 0.361 ms | 12.297 ms | 0.251 ms |
| Count query (median) | 0.095 ms | 0.087 ms | 0.086 ms | 0.204 ms | 0.379 ms | 0.130 ms |
| Memory per open store, resident | 2,538 KB | 2,534 KB | 491 KB | 409 KB | 2,470 KB | 421 KB |
| same, anonymous (process' own memory) | 2,065 KB | 2,062 KB | 19 KB | 407 KB | 2,466 KB | 418 KB |
| Create, write 1,000 objects, close (median) | 30.72 ms | 30.73 ms | 29.85 ms | 26.59 ms | 40.80 ms | 42.80 ms |
| same, estimated without the Python FlatBuffers marshalling | ~15.7 ms | ~15.7 ms | ~14.8 ms | – | – | – |
| Space per store, files | 472 KB | 472 KB | 472 KB | 316 KB | 316 KB | 316 KB |

ObjectBox's resident memory is mostly its data file mapped from the OS page cache; the SQL engines keep their pages in their own heap. About half of ObjectBox's create time (~15 ms per store) is the FlatBuffers marshalling of the 1,000 notes in Python; this is only the case with ObjectBox Python – other ObjectBox languages use generated code and efficient buffers, where marshalling is a much smaller fraction.

Earlier measurements drove ObjectBox through its C API directly (ctypes): a side experiment, not how applications use ObjectBox from Python. Their numbers are only in the [2026-10-05](2026_10_05_first_measurement/README.md) and [2026-10-06](2026_10_06_c_api_100k_500k/README.md) write-ups and are not comparable to the results above (different machine, C API instead of the Python API).

## Measurements

Code (`measure.py`, `measure_large.py`, `run.sh`, `run_large.sh`, `analyze*.py`, investigation scripts) is in the repository root; each measurement is in a dated sub-folder with its write-up, raw data and logs:

| Measurement | Where | What |
|---|---|---|
| [2026-10-05: first measurement (side experiment, C API)](2026_10_05_first_measurement/README.md) | Cloud VM, 2 cores, 8 GB | 10,000 stores per engine; ObjectBox via the C API (ctypes); open-store limit and memory investigation |
| [2026-10-06: 100,000 and 500,000 stores (side experiment, C API)](2026_10_06_c_api_100k_500k/README.md) | Cloud VM, 2 cores, 8 GB | 100,000 stores per engine, ObjectBox also 500,000; warm and cold page cache; ObjectBox via the C API (ctypes) |
| [2026-10-10: Python API and model sync](2026_10_09_python_api_model_sync/README.md) | Workstation, Ryzen 9 5950X, 64 GB | 100,000 stores per engine, warm only; ObjectBox via the objectbox-python API: model synced on every open, once, or not at all |
| [2026-10-11: large workload](2026_10_11_large_workload/README.md) | Workstation, Ryzen 9 5950X, 64 GB | 10,000 stores per engine with 1,000 objects of 300 characters each, warm only, load-gated; ObjectBox via the Python API in the same three variants |
