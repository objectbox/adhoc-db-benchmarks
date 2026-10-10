# ObjectBox via the Python API: syncing the model once, or not at all

As of 2026-10-10 · internal until the results have been reviewed · measured on a desktop workstation (not the cloud sandbox of the main write-up). Same measurement as `../README.md` (100,000 stores per engine), but ObjectBox is now driven through the regular objectbox-python API in three variants; warm page cache only.

## Result in three sentences

Through the Python API, open, query, close of an ObjectBox store takes 0.33 ms when the model is synced with its JSON file on every open, 0.24 ms when one model is synced once and reused, and 0.13 ms when existing stores are opened with `skip_model_sync=True`. Skipping the model also removes the ~2 MB of memory per open store even without the allocator line (43 KB instead of 2,090 KB), which puts ObjectBox below SQLite (152 KB) and libSQL (163 KB) on memory. SQLite (0.08 ms) and libSQL (0.10 ms) still open faster; on this machine, creating stores is dominated by the disk's sync latency, where ObjectBox is fastest (14.3 ms per store vs. 22.0 ms for SQLite).

## 100,000 stores per engine, defaults

Medians of the three warm open runs (10,000 random stores each).

| | ObjectBox, sync every open | ObjectBox, cached model | ObjectBox, skip model sync | SQLite | Turso Database | libSQL |
|---|---|---|---|---|---|---|
| Create, write ten objects, close (median) | 14.93 ms | 14.35 ms | 14.25 ms | 22.04 ms | 34.22 ms | 36.10 ms |
| Stores per second | 58 | 63 | 63 | 41 | 26 | 26 |
| Open (median) | 0.293 ms | 0.207 ms | 0.103 ms | 0.035 ms | 0.600 ms | 0.051 ms |
| Open, query, close (median) | 0.327 ms | 0.240 ms | 0.135 ms | 0.079 ms | 7.035 ms | 0.104 ms |
| same, p99 | 0.473 ms | 0.320 ms | 0.189 ms | 0.100 ms | 11.901 ms | 0.117 ms |
| Close (median) | 0.023 ms | 0.023 ms | 0.024 ms | 0.011 ms | 6.319 ms | 0.013 ms |
| Memory per open store (1,000 open) | 2,090 KB | 2,086 KB | 43 KB | 152 KB | 1,566 KB | 163 KB |
| Space per store, files | 24 KB | 24 KB | 24 KB | 8 KB | 8 KB | 8 KB |

## The same, with one allocator line in the benchmark program

`mallopt(M_MMAP_THRESHOLD, 131072)`, set identically for all engines.

| | ObjectBox, sync every open | ObjectBox, cached model | ObjectBox, skip model sync | SQLite | Turso Database | libSQL |
|---|---|---|---|---|---|---|
| Create, write ten objects, close (median) | 14.64 ms | 14.35 ms | 14.29 ms | 21.63 ms | 34.31 ms | 36.05 ms |
| Stores per second | 62 | 63 | 63 | 41 | 26 | 26 |
| Open (median) | 0.268 ms | 0.185 ms | 0.089 ms | 0.037 ms | 0.596 ms | 0.052 ms |
| Open, query, close (median) | 0.312 ms | 0.227 ms | 0.131 ms | 0.089 ms | 7.023 ms | 0.108 ms |
| same, p99 | 0.430 ms | 0.371 ms | 0.214 ms | 0.122 ms | 11.471 ms | 0.165 ms |
| Close (median) | 0.032 ms | 0.032 ms | 0.033 ms | 0.012 ms | 6.337 ms | 0.013 ms |
| Memory per open store (1,000 open) | 43 KB | 43 KB | 43 KB | 152 KB | 1,840 KB | 163 KB |
| Space per store, files | 24 KB | 24 KB | 24 KB | 8 KB | 8 KB | 8 KB |

The tables are printed by `python3 tables.py` from `results_large.jsonl`.

## What was measured

- Same phases as the main write-up (`../README.md`): create 100,000 stores (one directory each, schema `Note(id, text, ts)`, ten entries in one transaction), then three runs of open, count query, close for 10,000 random stores, then 1,000 random stores held open at the same time (RSS growth divided by 1,000). Each phase in a fresh process.
- ObjectBox through the Python API (`Store`, `Box`, an `@Entity` class `Note`, `measure.py`), objectbox 5.0.0b1 from objectbox-python `dev` (5cc8f48), which syncs a model with its JSON file only once per process and adds `skip_model_sync`. The three variants:
  - **sync every open** (`obx`): a new `Model` per store, so the model JSON file is read, matched and rewritten on every open. This is what an application gets when it builds the model per store.
  - **cached model** (`obx_cached`): one `Model` for all stores; it is synced with the JSON file once per process. The model is still passed to the C library, which checks it against the schema stored in each database.
  - **skip model sync** (`obx_nosync`): like the cached model, plus `skip_model_sync=True`: an existing store is opened without passing a model, i.e. with the schema stored in the database. New stores are still created with the model.
- SQLite (apsw), Turso Database and libSQL unchanged from the main write-up.

## Caveats

1. Warm page cache only. Cold runs need root for `drop_caches`, which was not available; `run_large.sh` skipped them (see the log).
2. A workstation with desktop applications running, not an idle machine. The run started once the 1-minute load average was below 1 (0.91, see `environment_large.txt`); it was not controlled during the 8.5 hours.
3. Creating stores is dominated by the disk's sync latency (ext4 on NVMe): ~14 ms per ObjectBox store here vs. ~2.2 ms in the cloud sandbox. The same likely explains Turso Database's 6.3 ms close (1.2 ms open, query, close in the sandbox). Create numbers say more about the disk than about the engines.
4. Not comparable in absolute numbers to the main write-up: different machine (AMD Ryzen 9 5950X, 64 GB vs. a cloud VM with 8 GB), Python 3.12 instead of 3.11, and the Python API instead of the C API via ctypes. The ObjectBox variants among each other, and the engines on this machine, are comparable.
5. objectbox 5.0.0b1 is unreleased (wheels built locally from objectbox-python `dev`, 5cc8f48).
6. `skip_model_sync=True` trusts the schema stored in the database: if the code's entity classes differ from it (e.g. an added property in the code but not in the store), this is not detected on open. Using it is only safe when all stores were created with the same model.
7. The ~2 MB per open store when a model is passed (without the allocator line) is very likely the two LMDB lists of 3 MiB in total (caveat 7 of `../README.md`) being touched while the model is checked against the stored schema (probably in a write transaction); without a model, a reading store never touches them. This was not traced inside the C library.
8. One run per setting and variant (three open runs each); no repetition across days.

## Reproduce

Versions (`environment_large.txt`): Linux 6.8, Python 3.12.3, objectbox 5.0.0b1 / objectbox-clib 5.3.2 (C library), apsw 3.53.4.0, pyturso 0.8.1, libsql 0.1.11, flatbuffers 25.12.19, numpy 2.5.3; adhoc-db-benchmarks d45d293.

```bash
# objectbox-python (dev, 5cc8f48): build the wheels into dist/
make depend build
# adhoc-db-benchmarks
python3 -m venv .venv && .venv/bin/pip install objectbox==5.0.0b1 --find-links <objectbox-python>/dist \
    apsw==3.53.4.0 pyturso==0.8.1 libsql==0.1.11
./2026_10_09_python_api_model_sync/run_all.sh > 2026_10_09_python_api_model_sync/run_large.log 2>&1
python3 2026_10_09_python_api_model_sync/tables.py
```

`run_all.sh` waits until the load average is below 1, records the environment, deletes `data_large` and runs `./run_large.sh 100000 10000 1000 "obx obx_cached obx_nosync sqlite turso libsql"`. Runtime: 8 h 25 min (2026-10-09 21:14 to 2026-10-10 05:39 UTC); creating 100,000 stores took 26–29 min per ObjectBox variant and setting, ~40 min for SQLite, ~63 min each for Turso Database and libSQL. Disk: ~12 GB in `data_large` (deleted afterwards).
