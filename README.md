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

Earlier measurements drove ObjectBox through its C API directly (ctypes): a side experiment, not how applications use ObjectBox from Python. Their numbers are only in the [2026-10-05](2026_10_05_first_measurement/README.md) and [2026-10-06](2026_10_06_c_api_100k_500k/README.md) write-ups and are not comparable to the results above (different machine, C API instead of the Python API).

## Measurements

Code (`measure.py`, `measure_large.py`, `run.sh`, `run_large.sh`, `analyze*.py`, investigation scripts) is in the repository root; each measurement is in a dated sub-folder with its write-up, raw data and logs:

| Measurement | Where | What |
|---|---|---|
| [2026-10-05: first measurement (side experiment, C API)](2026_10_05_first_measurement/README.md) | Cloud VM, 2 cores, 8 GB | 10,000 stores per engine; ObjectBox via the C API (ctypes); open-store limit and memory investigation |
| [2026-10-06: 100,000 and 500,000 stores (side experiment, C API)](2026_10_06_c_api_100k_500k/README.md) | Cloud VM, 2 cores, 8 GB | 100,000 stores per engine, ObjectBox also 500,000; warm and cold page cache; ObjectBox via the C API (ctypes) |
| [2026-10-10: Python API and model sync](2026_10_09_python_api_model_sync/README.md) | Workstation, Ryzen 9 5950X, 64 GB | 100,000 stores per engine, warm only; ObjectBox via the objectbox-python API: model synced on every open, once, or not at all |
