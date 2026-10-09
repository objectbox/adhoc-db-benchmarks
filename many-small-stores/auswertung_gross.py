#!/usr/bin/env python3
"""Evaluates ergebnisse_gross*.jsonl: median across the three runs, plus the range."""
import json, statistics, sys
from collections import defaultdict
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f)]
E = ['obx', 'sqlite', 'turso', 'libsql']; MODES = ['standard', 'mallopt']
def pick(e, mode, phase, cache=None, n=None):
    return [r for r in rows if r['engine'] == e and r['setting'] == mode and r['phase'] == phase and (cache is None or r.get('cache') == cache) and (n is None or r['n'] == n)]
def med(xs): return statistics.median(xs)
for n in sorted({r['n'] for r in rows}):
    print(f'\n===== N = {n:,} stores per engine =====')
    for e in E:
        for mode in MODES:
            a = pick(e, mode, 'create', n=n)
            if not a: continue
            a = a[0]; print(f"\n{e:7s} {mode:9s} {a['version']}")
            s = a['create_write_close']
            print(f"  create:  median {s['median_ms']:.2f} ms  p99 {s['p99_ms']:.2f} ms  {a['stores_per_s']:.0f} stores/s  wall {a['wall_s']:.0f} s")
            print(f"  space:   files {a['space_kb_per_store_files']:.1f} KB allocated, {a['space']['files_bytes_apparent']/n/1024:.1f} KB apparent; with directories {a['space_kb_per_store_with_dirs']:.1f} KB; total {a['space_gb_total']:.2f} GB  {a['sample_files']}")
            for cache in ('warm', 'cold'):
                o = pick(e, mode, 'open', cache, n)
                if not o: continue
                m_ = [r['total']['median_ms'] for r in o]; p = [r['total']['p99_ms'] for r in o]
                oo = med([r['open']['median_ms'] for r in o]); q = med([r['first_query']['median_ms'] for r in o]); c = med([r['close']['median_ms'] for r in o])
                print(f"  open+query+close {cache}: median {med(m_):.3f} ms ({min(m_):.3f}-{max(m_):.3f})  p99 {med(p):.3f} ms ({min(p):.3f}-{max(p):.3f})   [open {oo:.3f} / query {q:.3f} / close {c:.3f}]")
            for h in pick(e, mode, 'hold', n=n):
                print(f"  hold:    {h['k_open']} open  RSS {h['rss_kb_per_store']:.0f} KB per store (anonymous {h['anon_kb_per_store']:.0f})  total {h['rss_mb_all_open']:.0f} MB  fds {h['fds_per_store']:.0f} per store  error {h['error']}")
