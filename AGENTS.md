# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## What this repo is

Ad-hoc database measurements (not an official benchmark). Each measurement lives in its own top-level folder containing the code, raw data (`.jsonl`), run logs, and a write-up `README.md`. The top-level `README.md` holds a table linking every measurement folder with a one-line summary and date — add a row when adding a new measurement.

Everything is in English: write-ups, identifiers, CLI arguments, JSON keys, log lines. Use English number formatting in write-ups (`2.24 ms`, `100,000 stores`).

## many-small-stores ("one database per agent")

Measures the fixed cost of many tiny databases (one per agent) for ObjectBox, SQLite, Turso Database, and libSQL. There is no build, lint, or test suite; "running" means running a measurement.

### Requirements

- Root (for `echo 3 > /proc/sys/vm/drop_caches` in cold-cache runs)
- `obxc/lib/libobjectbox.so` (ObjectBox C library 5.3.2; not tracked in git) or `OBX_LIB=<path>`
- Python 3.11 with `apsw 3.53.4.0`, `pyturso 0.8.1`, `libsql 0.1.11`, `flatbuffers 24.3.25`

### Commands (run from `many-small-stores/`)

```bash
# Full large run: N stores per engine, M random stores per open-run, K held open simultaneously
./lauf_gross.sh 100000 10000 1000 "obx sqlite turso libsql" ergebnisse_gross.jsonl
BENCH_ROOT=data_500k ./lauf_gross.sh 500000 10000 1000 "obx" ergebnisse_gross_500k.jsonl
python3 auswertung_gross.py ergebnisse_gross.jsonl ergebnisse_gross_500k.jsonl

# Single phase for one engine (each phase prints one JSON line)
python3 messung_gross.py <obx|sqlite|turso|libsql> create <N>
python3 messung_gross.py <engine> open   <N> <M> [seed]
python3 messung_gross.py <engine> hold   <N> <K> [seed]

# Older, smaller first measurement (2026-10-05): ./lauf.sh <run#> [N] [M] [K], evaluated by auswertung.py
```

Environment variables: `BENCH_ROOT` (data dir; `data` for `messung.py`, `data_gross` for `messung_gross.py`), `BENCH_MALLOPT=1` (sets `mallopt(M_MMAP_THRESHOLD, 131072)` before anything else is loaded), `OBX_LIB`, `OBX_TUNE` (substring flags `readers`, `maxkb`, `notls` for ObjectBox store options).

### Architecture

- `messung.py` is the core: one class per engine (`Obx`, `Sqlite`, `Turso`, `Libsql`) with the same interface `create/open/write/read/close`, registered in `ENGINES`, plus helpers (`path`, `mem`, `status`). ObjectBox is driven through the **C API via ctypes** (model built by hand with fixed UIDs, objects encoded with raw FlatBuffers), because the PyPI package bundles an older core. The SQL engines share `DDL`/`INS`/`CNT`. Schema everywhere: one table/type `Note(id, text, ts)`, 10 rows written in one transaction.
- `messung_gross.py` imports the engine classes unchanged from `messung.py` and adds its own phases (random sampling with seeds, p99, directory-inclusive disk usage). `BENCH_ROOT` must be set before `import messung`, since `ROOT` is read at import time.
- Store layout on disk: `<ROOT>/<engine>/<i // 1000>/<i>/`.
- Each phase runs in a **fresh process** so memory numbers are not polluted by earlier phases; the shell scripts orchestrate this and prefix each JSON line with run metadata (`run`, `cache`) via `sed`, appending to a `.jsonl` file.
- `lauf_gross.sh` runs, per engine, both settings `standard` and `mallopt`: create → 3× open warm → 3× open cold (drop_caches before each) → hold. `auswertung_gross.py` reports medians across the three runs.
- The two generations of scripts emit different JSON schemas (e.g. `rss_kb_per_db` vs. `rss_kb_per_store`); keep `auswertung.py` paired with `messung.py` output and `auswertung_gross.py` with `messung_gross.py` output.
- `grenze_test.py` (the ~1,022 open-store limit from pthread TLS keys) and `ram_pruefung.py` (where per-store RSS goes: smaps/mallinfo2) are investigation scripts; both expect `python3 messung.py obx create 3000` first.

### Write-up conventions

The measurement `README.md` follows a fixed shape: status line (date, internal/external, where it was measured), "Result in three sentences", result tables, "What was measured", numbered "Caveats", "Reproduce" (exact reproduce commands, versions, runtimes). Older write-ups are kept as dated files (`YYYY_MM_DD_<title>.md`). Results are internal until they have been reviewed; numbers in write-ups must be traceable to the committed raw `.jsonl` data and logs.
