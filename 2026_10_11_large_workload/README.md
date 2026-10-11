# Large workload: 1,000 objects of 300 characters per store

As of 2026-10-11 · internal until the results have been reviewed · measured on a desktop workstation. Same setup as `../2026_10_09_python_api_model_sync/README.md` (ObjectBox through the Python API in three variants), but each store gets 1,000 objects with a 300-character text in one transaction instead of ten short ones; 10,000 stores per engine, warm page cache only, each phase started only when the 1-minute load average was below 1.

## Result in three sentences

With 1,000 objects per store, open, query (count), close takes 0.22 ms for ObjectBox with `skip_model_sync`, between libSQL (0.20 ms) and SQLite (0.28 ms); the ObjectBox count query itself is the fastest (0.09 ms vs. 0.13 ms for libSQL and 0.20 ms for SQLite). An open ObjectBox store costs 491 KB of resident memory, but only 19 KB of it is the process' own (anonymous) memory – the rest is the store's data file mapped from the OS page cache – while SQLite (409 KB) and libSQL (421 KB) hold their pages in their own heap. Creating a store and writing the 1,000 objects is slightly faster with SQLite (26.6 ms) than with ObjectBox (29.9–30.7 ms), and ObjectBox needs 472 KB of disk per store vs. 316 KB for the SQL engines.

## 10,000 stores per engine, defaults

Medians of the three warm open runs (all 10,000 stores in random order per run).

| | ObjectBox, sync every open | ObjectBox, cached model | ObjectBox, skip model sync | SQLite | Turso Database | libSQL |
|---|---|---|---|---|---|---|
| Create, write 1,000 objects, close (median) | 30.72 ms | 30.73 ms | 29.85 ms | 26.59 ms | 40.80 ms | 42.80 ms |
| Stores per second | 31 | 31 | 32 | 34 | 23 | 23 |
| Open (median) | 0.302 ms | 0.209 ms | 0.098 ms | 0.037 ms | 0.650 ms | 0.048 ms |
| Count query (median) | 0.095 ms | 0.087 ms | 0.086 ms | 0.204 ms | 0.379 ms | 0.130 ms |
| Open, query, close (median) | 0.433 ms | 0.332 ms | 0.218 ms | 0.275 ms | 7.524 ms | 0.195 ms |
| same, p99 | 0.555 ms | 0.457 ms | 0.338 ms | 0.361 ms | 12.297 ms | 0.251 ms |
| Close (median) | 0.035 ms | 0.034 ms | 0.033 ms | 0.033 ms | 6.405 ms | 0.017 ms |
| Memory per open store (1,000 open), resident | 2,538 KB | 2,534 KB | 491 KB | 409 KB | 2,470 KB | 421 KB |
| same, anonymous (process' own memory) | 2,065 KB | 2,062 KB | 19 KB | 407 KB | 2,466 KB | 418 KB |
| Load at start of the warm open runs (max) | 0.95 | 0.71 | 0.87 | 0.99 | 0.95 | 0.85 |
| Space per store, files | 472 KB | 472 KB | 472 KB | 316 KB | 316 KB | 316 KB |

## The same, with one allocator line in the benchmark program

`mallopt(M_MMAP_THRESHOLD, 131072)`, set identically for all engines.

| | ObjectBox, sync every open | ObjectBox, cached model | ObjectBox, skip model sync | SQLite | Turso Database | libSQL |
|---|---|---|---|---|---|---|
| Create, write 1,000 objects, close (median) | 31.02 ms | 30.89 ms | 31.46 ms | 29.53 ms | 40.68 ms | 38.93 ms |
| Stores per second | 31 | 31 | 31 | 32 | 23 | 24 |
| Open (median) | 0.270 ms | 0.186 ms | 0.085 ms | 0.036 ms | 0.748 ms | 0.051 ms |
| Count query (median) | 0.093 ms | 0.090 ms | 0.087 ms | 0.203 ms | 0.370 ms | 0.147 ms |
| Open, query, close (median) | 0.407 ms | 0.320 ms | 0.215 ms | 0.276 ms | 7.530 ms | 0.220 ms |
| same, p99 | 0.514 ms | 0.428 ms | 0.298 ms | 0.331 ms | 12.182 ms | 0.271 ms |
| Close (median) | 0.041 ms | 0.043 ms | 0.042 ms | 0.036 ms | 6.391 ms | 0.023 ms |
| Memory per open store (1,000 open), resident | 491 KB | 491 KB | 491 KB | 409 KB | 2,470 KB | 421 KB |
| same, anonymous (process' own memory) | 19 KB | 19 KB | 19 KB | 407 KB | 2,466 KB | 418 KB |
| Load at start of the warm open runs (max) | 0.83 | 0.72 | 0.79 | 0.74 | 0.94 | 0.73 |
| Space per store, files | 472 KB | 472 KB | 472 KB | 316 KB | 316 KB | 316 KB |

The tables are printed by `python3 tables.py` from `results_large.jsonl`.

## What was measured

- Same phases and ObjectBox variants as `../2026_10_09_python_api_model_sync/README.md`, with `BENCH_WORKLOAD=large`: per store 1,000 objects `Note(text, ts)` with a 300-character text (`note <j> of agent <i>: ` followed by Lorem ipsum, cut to 300 characters), written in one transaction. The query is a count over all 1,000 objects.
- 10,000 stores per engine (not 100,000: ~4.5 GB of data per ObjectBox variant and setting, 3 GB per SQL engine and setting, 23 GB in total). The open runs use all 10,000 stores in random order (seeds 1–3).
- Load control: `BENCH_MAX_LOAD=1`, i.e. before each phase (create, each open run, hold) `run_large.sh` waited until the 1-minute load average was below 1 (94 waits of 30 s); the load at each phase's start is in the results as `load1`. `load.log` samples the load average every 10 s during the whole run.

## Caveats

1. Warm page cache only (no root for `drop_caches`); all 10,000 stores (23 GB) fit into the 64 GB of memory, so the opens never read from disk.
2. The load was only controlled at the start of each phase. During creation it rose to 2–5 (highest 5.19 during Turso Database's create); on Linux the load average includes processes waiting for disk I/O, so this is very likely mostly the benchmark's own disk syncs, but other activity on the workstation was not excluded.
3. Creation is still dominated by the disk's sync latency (ext4 on NVMe), as in the 2026-10-10 measurement; the differences between engines in creation are smaller than with ten objects.
4. Resident memory for ObjectBox includes the pages of the memory-mapped data file that the count query touched (shared, file-backed, reclaimable by the OS); the SQL engines copy pages into their own page cache in the heap (anonymous). Both rows are given; which one matters depends on how memory is accounted (e.g. container limits count the page cache in part).
5. The count query in SQLite and libSQL scans the table; in ObjectBox it is a count of the entity's objects. A different query (e.g. reading all objects) would compare differently.
6. One run per setting and variant (three open runs each), 10,000 stores; not comparable in absolute numbers to the 100,000-store measurements.
7. objectbox 5.0.0b1 is unreleased (wheels built locally from objectbox-python `dev`, 5cc8f48). `skip_model_sync=True` trusts the schema stored in the database (see the 2026-10-10 write-up).

## Reproduce

Versions (`environment_large.txt`): Linux 6.8, Python 3.12.3, objectbox 5.0.0b1 / objectbox-clib 5.3.2 (C library), apsw 3.53.4.0, pyturso 0.8.1, libsql 0.1.11, flatbuffers 25.12.19, numpy 2.5.3; adhoc-db-benchmarks 5bf04fc. Venv as in `../2026_10_09_python_api_model_sync/README.md`.

```bash
./2026_10_11_large_workload/run_all.sh > 2026_10_11_large_workload/run_large.log 2>&1
python3 2026_10_11_large_workload/tables.py
```

`run_all.sh` starts the load sampler (`load.log`), records the environment, deletes `data_large_large` and runs `BENCH_WORKLOAD=large BENCH_MAX_LOAD=1 ./run_large.sh 10000 10000 1000 "obx obx_cached obx_nosync sqlite turso libsql"`. Runtime: 2 h 9 min (2026-10-11 13:21 to 15:30 UTC), of which ~47 min waiting for the load; creating 10,000 stores took 5.0–5.5 min for ObjectBox and SQLite and 7.0–7.4 min for Turso Database and libSQL per setting. Disk: 23 GB in `data_large_large` (deleted afterwards).
