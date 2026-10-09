#!/usr/bin/env python3
"""Large run "one database per agent": many small stores per engine.

Usage:  python3 messung_gross.py <engine> <phase> <N> [M] [seed]
  engine: obx | sqlite | turso | libsql
  phase:  create  - create N new stores, write ten small objects each, close
          open    - M random ones of the N stores: open, one query, close
          hold    - keep M stores open at the same time: memory, file descriptors
Environment:
  BENCH_ROOT     data directory (default: data_gross)
  BENCH_MALLOPT  =1 sets mallopt(M_MMAP_THRESHOLD, 131072) in the process; otherwise defaults
  OBX_LIB        path to libobjectbox.so

The engine classes (schema, writing, query) come unchanged from messung.py.
One process per invocation, so memory values do not depend on previous phases.
"""
import ctypes, json, os, random, statistics, sys, time

TUNED = os.environ.get('BENCH_MALLOPT') == '1'
if TUNED:
    M_MMAP_THRESHOLD = -3
    assert ctypes.CDLL('libc.so.6').mallopt(M_MMAP_THRESHOLD, 131072) == 1

os.environ.setdefault('BENCH_ROOT', 'data_gross')
import messung as m            # reads BENCH_ROOT on import
from messung import ENGINES, ROWS, path, mem, status, T

def ms(ns): return ns / 1e6
def stat(xs):
    xs = sorted(xs); n = len(xs)
    return {'median_ms': round(ms(statistics.median(xs)), 4), 'p95_ms': round(ms(xs[int(n * 0.95)]), 4),
            'p99_ms': round(ms(xs[int(n * 0.99)]), 4), 'max_ms': round(ms(xs[-1]), 3), 'mean_ms': round(ms(sum(xs) / n), 4)}

def space(root):
    """Allocated space: files and directories separately, in blocks as the file system counts them."""
    files_alloc = dirs_alloc = apparent = 0; nfiles = ndirs = 0
    for d, subs, files in os.walk(root):
        dirs_alloc += os.lstat(d).st_blocks * 512; ndirs += 1
        for f in files:
            st = os.lstat(os.path.join(d, f)); files_alloc += st.st_blocks * 512; apparent += st.st_size; nfiles += 1
    return {'files_bytes_allocated': files_alloc, 'files_bytes_apparent': apparent, 'dirs_bytes_allocated': dirs_alloc, 'num_files': nfiles, 'num_dirs': ndirs}

def phase_create(e, n, _m, _seed):
    tot = []; t_all = T()
    for i in range(n):
        p = path(e, i); t0 = T(); h = e.create(p); e.write(h, i); e.close(h); tot.append(T() - t0)
    wall = T() - t_all
    sp = space(f'{m.ROOT}/{e.name}')
    sample = {f: os.stat(os.path.join(path(e, n // 2), f)).st_size for f in sorted(os.listdir(path(e, n // 2)))}
    return {'n': n, 'create_write_close': stat(tot), 'wall_s': round(wall / 1e9, 1), 'stores_per_s': round(n / (wall / 1e9), 1),
            'space_kb_per_store_files': round(sp['files_bytes_allocated'] / n / 1024, 2),
            'space_kb_per_store_with_dirs': round((sp['files_bytes_allocated'] + sp['dirs_bytes_allocated']) / n / 1024, 2),
            'space_gb_total': round((sp['files_bytes_allocated'] + sp['dirs_bytes_allocated']) / 1024**3, 3),
            'space': sp, 'sample_files': sample, 'max_rss_mb': round(status('VmHWM') / 1024, 1)}

def phase_open(e, n, mm, seed):
    ids = random.Random(seed).sample(range(n), mm)
    to, tr, tc = [], [], []
    for i in ids:
        p = path(e, i); t0 = T(); h = e.open(p); t1 = T(); c = e.read(h); t2 = T(); e.close(h); t3 = T()
        assert c == ROWS, (i, c)
        to.append(t1 - t0); tr.append(t2 - t1); tc.append(t3 - t2)
    return {'n': n, 'm': mm, 'seed': seed, 'open': stat(to), 'first_query': stat(tr), 'close': stat(tc),
            'total': stat([a + b + c for a, b, c in zip(to, tr, tc)])}

def phase_hold(e, n, k, seed):
    import gc
    ids = random.Random(seed).sample(range(n), k)
    hs = []; m0 = mem(); fd0 = len(os.listdir('/proc/self/fd')); t0 = T(); error = None
    try:
        for i in ids:
            h = e.open(path(e, i)); e.read(h); hs.append(h)
    except Exception as ex:
        error = repr(ex)[:300]
    t1 = T(); m1 = mem(); k_open = max(len(hs), 1)
    fds = len(os.listdir('/proc/self/fd')) - fd0; thr = status('Threads')
    for h in hs: e.close(h)
    n_open = len(hs); hs.clear(); gc.collect(); m2 = mem()
    return {'n': n, 'k_requested': k, 'k_open': n_open, 'error': error,
            'rss_kb_per_store': round((m1['Rss'] - m0['Rss']) / k_open, 1), 'anon_kb_per_store': round((m1['Anonymous'] - m0['Anonymous']) / k_open, 1),
            'fds_per_store': round(fds / k_open, 2), 'threads': thr, 'rss_mb_all_open': round((m1['Rss'] - m0['Rss']) / 1024, 1),
            'rss_mb_after_close': round((m2['Rss'] - m0['Rss']) / 1024, 1), 'open_ms_per_store': round(ms(t1 - t0) / k_open, 4)}

if __name__ == '__main__':
    e = ENGINES[sys.argv[1]](); phase = sys.argv[2]; n = int(sys.argv[3])
    mm = int(sys.argv[4]) if len(sys.argv) > 4 else 0; seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    r = {'engine': e.name, 'version': e.version, 'phase': phase, 'setting': 'mallopt' if TUNED else 'standard'}
    r.update({'create': phase_create, 'open': phase_open, 'hold': phase_hold}[phase](e, n, mm, seed))
    print(json.dumps(r, ensure_ascii=False))
