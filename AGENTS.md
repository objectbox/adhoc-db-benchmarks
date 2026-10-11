# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## What this repo is

Ad-hoc database measurement (not an official benchmark), code in the repository root; each measurement in a dated sub-folder (`YYYY_MM_DD_<title>/`) with its write-up `README.md`, raw data (`.jsonl`), run logs and any measurement-specific scripts. The root `README.md` shows the main results (key rows of the latest Python API measurement, copied from its write-up; the C API measurements are side experiments, only linked) and lists the measurements.

Everything is in English: write-ups, identifiers, CLI arguments, JSON keys, log lines. Use English number formatting in write-ups (`2.24 ms`, `100,000 stores`).

## "One database per agent"

Measures the fixed cost of many tiny databases (one per agent) for ObjectBox, SQLite, Turso Database, and libSQL. There is no build, lint, or test suite; "running" means running a measurement.

### Requirements

- Root (for `echo 3 > /proc/sys/vm/drop_caches` in cold-cache runs; without it, `run_large.sh` skips the cold runs and logs that)
- A Python venv in `.venv/` (not tracked in git; the scripts use it if present) with `objectbox 5.0.0b1` (wheels built from objectbox-python, branch `dev`; brings `objectbox-clib 5.3.2`, the ObjectBox C library), `apsw 3.53.4.0`, `pyturso 0.8.1`, `libsql 0.1.11`:
  `python3 -m venv .venv && .venv/bin/pip install objectbox==5.0.0b1 --find-links <objectbox-python>/dist apsw==3.53.4.0 pyturso==0.8.1 libsql==0.1.11`

### Commands

```bash
# Full large run: N stores per engine, M random stores per open-run, K held open simultaneously
# (run from the repository root; write the output into the measurement's sub-folder)
./run_large.sh 100000 10000 1000 "obx sqlite turso libsql" <folder>/results_large.jsonl
BENCH_ROOT=data_500k ./run_large.sh 500000 10000 1000 "obx" <folder>/results_large_500k.jsonl
python3 analyze_large.py <folder>/results_large.jsonl <folder>/results_large_500k.jsonl

# Large workload: 1,000 objects of 300 characters per store
BENCH_WORKLOAD=large ./run_large.sh 100000 10000 1000 "obx_nosync sqlite" <folder>/results_large.jsonl

# Single phase for one engine (each phase prints one JSON line)
python3 measure_large.py <obx|sqlite|turso|libsql> create <N>
python3 measure_large.py <engine> open   <N> <M> [seed]
python3 measure_large.py <engine> hold   <N> <K> [seed]

# Older, smaller first measurement (2026-10-05): ./run.sh <run#> [N] [M] [K], writes results.jsonl, evaluated by analyze.py [results.jsonl]
```

Environment variables: `BENCH_WORKLOAD` (what each store gets, written in one transaction: `small`, the default, ten objects with a short text; `large`, 1,000 objects with a 300-character text; recorded as `workload` in the JSON output), `BENCH_ROOT` (data dir; `data` for `measure.py`, `data_large` for `measure_large.py`; `run_large.sh` uses `data_large_large` for the large workload), `BENCH_MALLOPT=1` (sets `mallopt(M_MMAP_THRESHOLD, 131072)` before anything else is loaded), `PYTHON` (interpreter for the shell scripts; default `.venv/bin/python`), `OBX_TUNE` (substring flags `readers`, `maxkb`, `notls` for ObjectBox store options).

### Architecture

- `measure.py` is the core: one class per engine (`Obx`, `Sqlite`, `Turso`, `Libsql`; ObjectBox variants: `obx` syncs the model on every open, `obx_cached` (`ObxCached`) reuses one synced model, `obx_nosync` (`ObxNoSync`) additionally opens existing stores with `skip_model_sync=True`, i.e. with the schema stored in the database) with the same interface `create/open/write/read/close`, registered in `ENGINES`, plus helpers (`path`, `mem`, `status`). ObjectBox is driven through its **Python API** (`objectbox` package: `Store`, `Box`, an `@Entity` class `Note`); the model IDs are kept in the committed `objectbox-model.json` (do not delete it: stores created with other IDs cannot be opened). Until 2026-10-06 the C API was used via ctypes (see the git history and the older write-ups). The SQL engines share `DDL`/`INS`/`CNT`. Schema everywhere: one table/type `Note(id, text, ts)`; the rows per store come from `rows(i)` (workload from `BENCH_WORKLOAD`), written in one transaction.
- `measure_large.py` imports the engine classes unchanged from `measure.py` and adds its own phases (random sampling with seeds, p99, directory-inclusive disk usage). `BENCH_ROOT` must be set before `import measure`, since `ROOT` is read at import time.
- Store layout on disk: `<ROOT>/<engine>/<i // 1000>/<i>/`.
- Each phase runs in a **fresh process** so memory numbers are not polluted by earlier phases; the shell scripts orchestrate this and prefix each JSON line with run metadata (`run`, `cache`) via `sed`, appending to a `.jsonl` file.
- `run_large.sh` runs, per engine, both settings `standard` and `mallopt`: create → 3× open warm → 3× open cold (drop_caches before each) → hold. `analyze_large.py` reports medians across the three runs.
- The two generations of scripts emit different JSON schemas (e.g. `rss_kb_per_db` vs. `rss_kb_per_store`); keep `analyze.py` paired with `measure.py` output and `analyze_large.py` with `measure_large.py` output.
- `limit_test.py` (the ~1,022 open-store limit from pthread TLS keys) and `ram_check.py` (where per-store RSS goes: smaps/mallinfo2) are investigation scripts; both expect `python3 measure.py obx create 3000` first.

### Write-up conventions

A measurement's `README.md` follows a fixed shape: status line (date, internal/external, where it was measured), "Result in three sentences", result tables, "What was measured", numbered "Caveats", "Reproduce" (exact reproduce commands, versions, runtimes). Each measurement gets a new dated sub-folder, listed in the root `README.md` (update its main results too); earlier measurements stay unchanged (their code state is a git commit, named in their Reproduce section). Results are internal until they have been reviewed; numbers in write-ups must be traceable to the committed raw `.jsonl` data and logs.
