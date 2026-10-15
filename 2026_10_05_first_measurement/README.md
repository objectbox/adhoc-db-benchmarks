# One database per agent – measuring ObjectBox, SQLite, Turso, libSQL

As of 2026-10-05, third version (after a follow-up question about memory) · one measurement on one machine, not a benchmark.

Earlier versions from the same day are in `_to_delete_erste_Fassung/` (Python package 4.0.0, only ObjectBox against SQLite; numbers outdated, the guess about the limit was wrong) and `_to_delete_zweite_Fassung/` (which still said memory was the cost driver for ObjectBox – superseded by section 3).

## 1 Background

Supabase has acquired Turso (2026-10-02, turso.tech/blog/turso-is-joining-supabase). Turso's thesis: "One agent, one task, one user" – the economics have to work at millions of databases. Vivien's question: how much time and cost does one database cause, and is ObjectBox in the same order of magnitude as Turso?

## 2 Result

Median of three runs. Per database one object type with ten small objects.

| | ObjectBox 5.3.2 | SQLite 3.53.4 | Turso Database 0.8.1 | libSQL 0.1.11 |
|---|---|---|---|---|
| Create with ten objects | 2.5 ms | 2.9 ms | 3.8 ms | 2.6 ms |
| Space per database | 28 KB | 8 KB | 8 KB | 8 KB |
| Open | 0.36 ms | 0.02 ms | 0.55 ms | 0.05 ms |
| First query | 0.02 ms | 0.02 ms | 0.14 ms | 0.03 ms |
| Close | 0.02 ms | 0.01 ms | 0.48 ms | 0.01 ms |
| Total open, query, close | 0.40 ms | 0.06 ms | 1.20 ms | 0.10 ms |
| Same total with dropped file cache | 0.75 ms | 0.25 ms | 1.29 ms | 0.21 ms |
| Memory per open database, default | 2.1 MB | 0.15 MB | 2.1 MB | 0.16 MB |
| Memory with allocator setting (see below) | **0.04 MB** | 0.15 MB | 2.1 MB | 0.16 MB |
| Open at the same time in one process | 1,022; with option and allocator setting 6,000 tested | 5,000 tested | 2,500 tested | 5,000 tested |

Turso has two engines: **Turso Database** is the new one, written in Rust; **libSQL** is the older SQLite fork. I did not check which of the two runs in Turso Cloud.

## 3 Explanations

**Create.** All four are between 2.3 and 3.9 ms. The differences between ObjectBox, SQLite and libSQL are smaller than the spread between runs (SQLite: 2.3 to 2.9 ms). Turso Database is clearly the slowest.

**Space.** ObjectBox creates two files: `data.mdb` (20 KB = 5 pages of 4 KB) and `lock.mdb` (8 KB = 2 pages, of which 4 KB are actually allocated). The others get by with 8 KB. Steps for ObjectBox (page size 4 KB): only opened with the model, no objects: `data.mdb` 3 pages (12 KB) · 1 or 10 objects: 5 pages (20 KB) · 100 objects: 8 pages (32 KB) · 1,000 objects: 28 pages (112 KB). `lock.mdb` stays at 8 KB. 8 KB had been expected on Linux; macOS (16 KB pages) was not measured. One million idle databases would be 28 GB versus 8 GB – either way a small amount on object storage.

**Open and close.** SQLite and libSQL open "lazily": almost nothing happens on open, the file is only read on the first query. Only the total is therefore comparable. ObjectBox needs 0.40 ms, which makes it three times as fast as Turso Database and seven times as slow as SQLite. Closing costs 0.02 ms for ObjectBox and 0.48 ms for Turso Database (presumably it cleans up its write-ahead log; not checked). ObjectBox has to be given the data model on every open; that is included in the open time.

**Memory.** With default settings the process grows by 2.08 MB per open ObjectBox store. This was checked, but it is not memory ObjectBox needs:
- **The growth is real and linear.** The first store costs 0.16 MB of anonymous memory, each further one 2.06 MB (measured at 10, 100, 250, 500, 1,000, 1,500 and 2,500 open stores). At about 2,900 stores the kernel killed the process at 6.06 GB of used memory.
- **It is not the mmap file.** Of the 2,082 KB, 16 KB are `data.mdb` and 4 KB `lock.mdb`. The remaining 2,062 KB are in the process heap. The 1 GB virtual mapping per store does not count.
- **Cause:** On open, two large blocks are requested, together 3,080 KB (presumably 2 MiB and 1 MiB; which ones they are is still open). With default settings glibc puts them on the heap, and the larger one gets zeroed – which makes it resident even though nobody uses it for tiny databases.
- **An allocator setting removes this.** The environment variable `MALLOC_MMAP_THRESHOLD_=131072` makes glibc always get large blocks via mmap; unused pages then stay unallocated. Result: **39 KB per open store** (18 KB anonymous, 20 KB file) instead of 2,082 KB. Tested up to 6,000 simultaneously open stores (together with `no_reader_thread_locals`); there the file descriptors become the limit (three per store). Open, query, close drops from 0.38 to 0.13 ms with it.
- **The other three do not change with the same setting:** SQLite 153 KB, Turso Database 2,136 KB, libSQL 163 KB. So 1 GB fits about 26,000 open ObjectBox stores, about 6,800 SQLite and about 490 Turso databases.
- **Not checked:** whether the setting has drawbacks under write load, and how much of the blocks is actually used with real data volumes. Three options of the C API (`max_readers`, `max_db_size_in_kb`, `no_reader_thread_locals`) change nothing about the default value.
- Without the setting, the memory is reused for the next store after closing, but only returned to the operating system after `malloc_trim`.

**Limit at 1,022.** The cause has been found: Linux allows 1,024 thread-local keys per process, and with default settings ObjectBox takes one per open store. Verified by pre-allocating: with 500 keys taken, 522 stores can be opened, with 900 taken, 122. The option `no_reader_thread_locals` removes the limit (2,500 stores opened without errors). This is not a quirk of my test environment but applies to Linux in general. My first guess (the locked-memory limit) was wrong: halving that limit changed nothing.

**What follows from this.**
1. Per database, ObjectBox is at least in the same order of magnitude as Turso's new engine: faster at creating, opening and closing, larger on disk.
2. Time is not an issue. Open, query and close stays below 1.3 ms everywhere.
3. Memory is not a fundamental problem for ObjectBox: with an allocator setting an open store needs 39 KB, which is a quarter of SQLite and a fiftieth of Turso Database. With default settings it is 2.1 MB.
4. Nothing has been optimized for the use case yet. Both settings here are applied from outside; whether they should be solved inside ObjectBox itself is an open question.

## 4 Caveats

- **One machine, three runs.** Cloud VM with 2 virtual cores (Xeon 2.1 GHz), 8 GB RAM, Linux 6.18, ext4 on a virtual disk. Per run 10,000 databases created, 2,000 opened one after another, 1,000 kept open at the same time. The ranges are in `results.jsonl`.
- **Tiny databases.** Ten small objects. This says nothing about larger data volumes, concurrent access, queries, vector search or sync.
- **Default settings, not aligned.** SQLite and libSQL ran with rollback journal and `synchronous=FULL`, Turso Database with WAL and `synchronous=FULL`, ObjectBox with its defaults (I did not check what durability they imply). On a virtual disk, syncing to disk can be unrealistically fast.
- **Everything via Python.** ObjectBox through the official C API with a self-written thin wrapper (`ctypes`), because the Python package on PyPI (4.0.0, May 2024) bundles an old core. This is not an official binding. The Python share costs some time for all four.
- **"Dropped file cache"** means: the Linux page cache was dropped. The machine underneath may still cache the files. This is not a real cold start from object storage.
- **Memory** is the growth of the process (RSS) with 1,000 open databases, each queried once. For Turso Database I tried no options of its own, for ObjectBox three; the allocator setting ran for all four.
- **Turso Cloud was not measured.** What a database costs Turso in operation cannot be seen from outside. Turso describes its service as "diskless" with WAL on S3; that is a different architecture than local files.
- **Not measured:** ObjectBox 6.0 beta, other operating systems, other languages.

## 5 Versions

| | Version | released | Source |
|---|---|---|---|
| ObjectBox C/C++ | 5.3.2 (latest stable; 6.0.0 beta not used) | 2026-05-05 | github.com/objectbox/objectbox-c/releases |
| SQLite | 3.53.4, via apsw 3.53.4.0 | 2026-07-24 | sqlite.org/chronology.html |
| Turso Database | pyturso 0.8.1 | 2026-09-29 | pypi.org/project/pyturso |
| libSQL | libsql 0.1.11 | 2025-09-02 | pypi.org/project/libsql |

For Turso, the GitHub page shows 0.7.0 as "Latest", but PyPI shows 0.8.1. The PyPI version was used.

## 6 Open questions

1. Which two blocks (together 3,080 KB) are requested on open, and could they be made smaller or allocated only when needed?
2. Does `MALLOC_MMAP_THRESHOLD_` have drawbacks under real load, or would another approach be cleaner?
3. Is `no_reader_thread_locals` safe for a service with many stores?
4. Does a store need `lock.mdb` if only one process accesses it?
5. Do the numbers match what is expected from the C library?

## 7 Reproduce

Prerequisites: Linux, Python 3, `pip install apsw pyturso libsql flatbuffers`, plus `objectbox-linux-x64.tar.gz` (5.3.2) extracted to `obxc/`.

Run from the repository root. These numbers were measured with ObjectBox driven through the C API (ctypes); to reproduce them, check out commit `79a2eeb`. `run.sh` writes `results.jsonl` in the root; the raw data of this measurement is in this folder.

- `./run.sh <run number>` – one complete run across all four engines (as root for the run with dropped file cache).
- `python3 analyze.py 2026_10_05_first_measurement/results.jsonl` – summarizes the results.
- `python3 limit_test.py` – the test for the limit at 1,022.
- `OBX_TUNE=readers,maxkb,notls python3 measure.py obx hold 200` – the three options.
- `python3 ram_check.py 1000` – memory step by step, by memory region and from the allocator's point of view. Prefix with `MALLOC_MMAP_THRESHOLD_=131072` for the allocator setting.
- `MALLOC_MMAP_THRESHOLD_=131072 OBX_TUNE=notls python3 measure.py obx hold 6000` – 6,000 simultaneously open stores.
