# Turso Database: why open, query, close takes 7.5 ms

As of 2026-10-15 · measured on a desktop workstation (the same as 2026-10-10 to 2026-10-14). A check of one number from `../2026_10_11_large_workload/README.md`: open, query, close took about 0.2–0.4 ms for ObjectBox, SQLite and libSQL, but 7.5 ms (median) for Turso Database. That seemed too high, so it was double-checked for wrong usage or a missing setting.

## Result in three sentences

The number is correct, and it is neither wrong usage nor a missing setting: 6.4 of Turso's 7.5 ms are spent in `close()`, which runs a checkpoint with three fsyncs when the last connection to a database closes, even if the connection only read and the WAL is empty. No setting available from Python avoids it (pyturso 0.8.1 as measured and 0.8.3, the latest): not `synchronous=OFF`, `wal_autocheckpoint=0`, `query_only` or `journal_mode=DELETE`, and pyturso has no read-only open, for which Turso would skip the checkpoint. SQLite in WAL mode does not sync on close (0.08 ms), so the cost is Turso's, not WAL's; it depends on the disk's sync latency and is not paid by an application that keeps its connection open.

## Where the time goes

One store of the large workload (1,000 objects of 300 characters), opened, queried (`select count(*)`) and closed 200 times; medians from `results.jsonl` (pyturso 0.8.1, as in the benchmark) and `results_pyturso_0.8.3.jsonl`.

| | Open | Query | Close | Total |
|---|---|---|---|---|
| Turso, as in the benchmark (`measure.Turso`), pyturso 0.8.1 | 0.045 ms | 0.192 ms | 6.262 ms | 6.498 ms |
| same, pyturso 0.8.3 | 0.044 ms | 0.195 ms | 6.266 ms | 6.502 ms |
| Turso, `PRAGMA synchronous=OFF` | 0.063 ms | 0.184 ms | 5.814 ms | 6.064 ms |
| Turso, `PRAGMA synchronous=NORMAL` | 0.065 ms | 0.185 ms | 6.247 ms | 6.495 ms |
| Turso, `PRAGMA wal_autocheckpoint=0` | 0.065 ms | 0.184 ms | 6.199 ms | 6.447 ms |
| Turso, `PRAGMA query_only=1` | 0.065 ms | 0.185 ms | 5.520 ms | 5.898 ms |
| Turso, `PRAGMA journal_mode=DELETE` | 0.064 ms | 0.183 ms | 6.150 ms | 6.378 ms |
| Turso, another connection to the store kept open | 0.027 ms | 0.141 ms | 0.0005 ms | 0.169 ms |
| SQLite, as in the benchmark (rollback journal) | 0.032 ms | 0.199 ms | 0.030 ms | 0.257 ms |
| SQLite, WAL mode | 0.036 ms | 0.312 ms | 0.078 ms | 0.423 ms |

The Turso rows with a `PRAGMA` are pyturso 0.8.1; with 0.8.3 (`results_pyturso_0.8.3.jsonl`), close took 5.82–6.27 ms in them. Differences of up to ~0.8 ms between the Turso rows are the variation of the fsyncs; none of these pragmas is checked on the close path (see below).

In the 2026-10-11 benchmark, Turso's open, query, close (median 7.45–7.64 ms, six runs) split into 0.65–0.75 ms open, 0.37–0.52 ms query and 6.39–6.45 ms close (`../2026_10_11_large_workload/results_large.jsonl`); open and query are higher there than here because each open was of a different one of 10,000 stores; close is about the same.

The syscalls of one Turso close of a store that was only read (`close_trace.txt`; fd 4 is the WAL, fd 3 the database file, with the time each call took):

```
fsync(4)            0.001647 s
fsync(3)            0.000485 s
ftruncate(4, 0)     0.000040 s   (the WAL had no frames: the store was only read)
fsync(4)            0.004534 s
```

The same trace for SQLite in WAL mode shows no sync: only the `-shm` and `-wal` files are deleted.

## Why: the shutdown checkpoint

In Turso's source (tursodatabase/turso, `main` at 7a0a7b8, 2026-10-15; the traced syscalls of 0.8.1 match it):

- `Connection::close` (`core/connection.rs`) calls `Pager::checkpoint_shutdown` when the last connection to a database closes, unless the database is read-only or in memory, or the WAL backend says not to (`should_checkpoint_on_close`, always `true` for the in-process WAL).
- `checkpoint_shutdown` (`core/storage/pager.rs`) first fsyncs the WAL unconditionally, then runs a `Truncate` checkpoint (fsync of the database file, truncate the WAL, fsync of the WAL) unless the connection's automatic WAL actions are disabled; only Turso's sync engine disables them, the Python API cannot.
- Neither step checks whether the WAL has frames; with nothing to checkpoint, the cost is the fsyncs, mostly the last one (the truncate is a metadata change, so ext4 commits its journal).
- `PRAGMA wal_autocheckpoint` returns nothing in pyturso 0.8.1 and 0.8.3, and the close path does not look at it.
- Turso can open a database read-only (`file:…?mode=ro` in the core's URI parser), which would skip the checkpoint, but pyturso's `connect()` has no such option and passes the URI on as a file name (`IoError: open: NotFound`).

SQLite, for comparison, also checkpoints when the last connection to a WAL database closes, but with an empty WAL there is nothing to copy and nothing to sync: it only deletes the WAL and shared-memory files (`close_trace.txt`).

## What this means for the results

- Turso's open, query, close in `../2026_10_11_large_workload/README.md` and the top-level README is a correct measurement of opening, querying and closing a store with pyturso 0.8.x; most of it is disk sync latency in close, so it varies with the disk.
- An application that keeps its Turso connections open does not pay it; one that opens a store per request does, on every close.
- Turso could avoid it by skipping the shutdown sync and checkpoint when the WAL has no frames, or pyturso by offering a read-only open; neither exists as of pyturso 0.8.3.

## What was measured

- `check_close.py`: creates one Turso store and one SQLite store with the large workload through `measure.py`'s engine classes, plus an SQLite store in WAL mode, then times open, query and close 200 times per variant; the Turso variants run one `PRAGMA` after open. It also records the pragma values, tries a read-only URI and measures Turso with a second connection kept open.
- `run.sh` runs it and traces the syscalls of one Turso close and one SQLite WAL close with `strace -T` (`close_trace.txt`). The stores are on the benchmark disk (`data_turso_close`, ext4 on NVMe), deleted afterwards.

## Caveats

1. One store, opened 200 times in a row: warm page cache, and open and query lower than in the benchmark (see above).
2. A check, not a benchmark run: `run.sh` waits for a 1-minute load below 1 once at the start (0.85, `environment.txt`; the 0.8.3 run started at 0.62), not before each variant.
3. The source was read at Turso's current `main`, not at the 0.8.1 tag; the traced syscalls of 0.8.1 match it. A trace of 0.8.3 during the investigation showed the same sequence; only the 0.8.1 trace is committed.
4. Only `close()` after a read was examined; after writes, the checkpoint also has to copy pages, which is expected and not part of this check.

## Reproduce

Versions: Linux 6.8, Python 3.12.3, pyturso 0.8.1 (benchmark venv), SQLite 3.53.4 (apsw 3.53.4.0); for 0.8.3, a separate venv with `pyturso==0.8.3 apsw==3.53.4.0`. Runtime: about 10 s.

```bash
./2026_10_15_turso_close/run.sh
# pyturso 0.8.3, in another venv:
BENCH_WORKLOAD=large <venv>/bin/python 2026_10_15_turso_close/check_close.py data_turso_close 200 > 2026_10_15_turso_close/results_pyturso_0.8.3.jsonl; rm -rf data_turso_close
```
