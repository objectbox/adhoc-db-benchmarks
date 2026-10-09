# Adhoc DB Benchmarks: one database per agent

Ad-hoc measurement, not an official benchmark: many small stores per engine – ObjectBox, SQLite, Turso Database, libSQL; 100,000 stores per engine, ObjectBox additionally 500,000.

As of 2026-10-06 · internal until the results have been reviewed · measured in a cloud sandbox. Builds on the first measurement from 2026-10-05 (`2026_10_05_first_measurement_one_db_per_agent.md`, 10,000 stores) and confirms it.

## Result in three sentences

Creating an ObjectBox database and writing ten objects takes a little over 2 ms, an idle store costs 24 KB of disk, and open, query, close stays below one millisecond at the median – even with 500,000 stores. Against Turso Database, ObjectBox is ahead on opening and on memory. Against SQLite, ObjectBox is ahead on memory (with one allocator line), behind on space and on opening.

## 100,000 stores per engine, defaults

| | ObjectBox 5.3.2 | SQLite 3.53.4 | Turso Database 0.8.1 | libSQL 0.1.11 |
|---|---|---|---|---|
| Create, write ten objects, close (median) | 2.24 ms | 2.29 ms | 3.66 ms | 2.38 ms |
| same, p99 | 4.72 ms | 5.44 ms | 6.86 ms | 5.41 ms |
| Stores per second | 422 | 403 | 262 | 392 |
| Space per store, files | 24 KB | 8 KB | 8 KB | 8 KB |
| Space for all 100,000, with directories | 2.67 GB | 1.15 GB | 1.15 GB | 1.15 GB |
| Open, query, close (median) | 0.34 ms | 0.05 ms | 1.19 ms | 0.08 ms |
| same, p99 | 0.63 ms | 0.13 ms | 2.59 ms | 0.21 ms |
| same without page cache (median) | 0.77 ms | 0.18 ms | 1.38 ms | 0.22 ms |
| same without page cache, p99 | 1.65 ms | 0.69 ms | 2.72 ms | 0.75 ms |
| Memory per open store (1,000 open) | 2,082 KB | 152 KB | 2,135 KB | 163 KB |
| File descriptors per open store | 3 | 1 | 2 | 1 |

## The same 100,000 stores, with one allocator line in the benchmark program

`mallopt(M_MMAP_THRESHOLD, 131072)`, set identically for all engines.

| | ObjectBox | SQLite | Turso Database | libSQL |
|---|---|---|---|---|
| Create, write, close (median) | 2.08 ms | 2.43 ms | 3.73 ms | 2.73 ms |
| Stores per second | 452 | 381 | 255 | 344 |
| Open, query, close (median) | 0.10 ms | 0.06 ms | 1.24 ms | 0.09 ms |
| same, p99 | 0.36 ms | 0.17 ms | 2.83 ms | 0.23 ms |
| same without page cache (median) | 0.35 ms | 0.19 ms | 1.46 ms | 0.24 ms |
| Memory per open store | 39 KB | 152 KB | 2,135 KB | 163 KB |

## ObjectBox alone, 500,000 stores

| | Defaults | with allocator line |
|---|---|---|
| Create, write, close (median) | 2.24 ms | 1.83 ms |
| Stores per second | 422 | 510 |
| Duration for all 500,000 | 19 min 46 s | 16 min 21 s |
| Space for all 500,000, with directories | 13.37 GB | 13.37 GB |
| Open, query, close (median) | 0.81 ms | 0.38 ms |
| same, p99 | 2.56 ms | 1.72 ms |
| same after dropping the page cache (median) | 0.91 ms | 0.49 ms |
| Memory per open store | 2,082 KB | 39 KB |

Creation scales linearly: 422 stores per second at 100,000 as at 500,000. Opening is slower at 500,000 than at 100,000 because 13.4 GB of data do not fit into the machine's 8 GB of memory – a randomly chosen store is then usually not in the page cache and is read from disk.

## What was measured

- One directory per store, a schema with one table or type (`id`, `text`, `ts`), ten small entries in one transaction.
- Create: all stores one after another, one process, one run.
- Open, query, close: 10,000 randomly chosen stores, one count query per store. Three runs with different samples; the table shows the median of the three runs. "Without page cache" means: `sync` and `drop_caches` before each run.
- Memory: 1,000 random stores open at the same time, growth of resident memory (RSS) divided by 1,000.
- Each phase runs in its own process.

## Caveats

1. **Small stores.** Ten short entries per store. This shows the fixed cost of a database, not the behavior with real agent data (messages, vectors). The realistic profile is still pending.
2. **Python as the harness.** ObjectBox is accessed through the C API (ctypes), SQLite through apsw, Turso Database through pyturso, libSQL through the libsql package. The overhead of the bindings differs and is included in the times.
3. **Turso Database is the local engine, version 0.8.1**, not the Turso cloud service. The measurement says nothing about the service.
4. **Default durability settings.** Each engine writes as safely as it does without configuration. That is not the same for all of them and affects creation.
5. **One virtual machine.** 2 cores, 8 GB memory, virtual disk (ext4). Absolute times apply to this machine; the ratios between the engines are what holds.
6. **One process, one thread.** No concurrent access.
7. **The allocator line** does not change the engines. It makes glibc request memory blocks of 128 KB and more separately, so unused parts take no memory. ObjectBox benefits because LMDB allocates two lists totaling 3 MiB on open, which a reading store never writes to. For Turso Database the line changes nothing.
8. **Limit for ObjectBox:** With defaults, 1,022 stores can be kept open at the same time in one process (one thread-local key per store, Linux allows 1,024). The option `no_reader_thread_locals` removes this limit; it is not used here. Measured on 2026-10-05.
9. **Space for ObjectBox:** `data.mdb` 20 KB (5 pages) and `lock.mdb` 8 KB apparent, 4 KB allocated. The SQL engines get by with two pages. On disk, ObjectBox has **two files** per store. The row "File descriptors per open store: 3" counts open handles, not files: LMDB opens `data.mdb` twice (once normally, once with O_DSYNC for the meta pages) and `lock.mdb` once. Verified on an open store on 2026-10-06.

## Reproduce

```
./run_large.sh 100000 10000 1000 "obx sqlite turso libsql" results_large.jsonl
BENCH_ROOT=data_500k ./run_large.sh 500000 10000 1000 "obx" results_large_500k.jsonl
python3 analyze_large.py results_large.jsonl results_large_500k.jsonl
```

Needs root (for `drop_caches`), `libobjectbox.so` 5.3.2 under `obxc/lib/`, Python 3.11 with `apsw 3.53.4.0`, `pyturso 0.8.1`, `libsql 0.1.11`, `flatbuffers 24.3.25`. Files in this repository: `measure.py` (engine classes), `measure_large.py`, `run_large.sh`, `analyze_large.py`, raw data `results_large.jsonl` and `results_large_500k.jsonl`, logs `run_large.log` and `run_large_500k.log`, `environment_large.txt`.

Run times: 100,000 per engine in both settings 46 minutes (16:36–17:22 UTC), ObjectBox 500,000 in both settings 43 minutes (17:28–18:11 UTC). No errors.
