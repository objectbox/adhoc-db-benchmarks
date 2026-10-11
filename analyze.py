#!/usr/bin/env python3
"""Summarizes results.jsonl (path as optional argument): median across the runs, smallest and largest run in parentheses."""
import json, statistics as st, collections, sys
R = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else 'results.jsonl')]
E = ['obx', 'sqlite', 'turso', 'libsql']
def get(e, phase, f, cache=None): return [f(r) for r in R if r['engine'] == e and r['phase'] == phase and (cache is None or r.get('cache') == cache)]
def fmt(xs, nd=2):
    if not xs: return '-'
    m = st.median(xs); return f'{m:.{nd}f} ({min(xs):.{nd}f}-{max(xs):.{nd}f})'
rows = [
 ('Version', lambda e: [r['version'] for r in R if r['engine'] == e][0]),
 ('Runs', lambda e: str(len(get(e, 'create', lambda r: 1)))),
 ('CREATE  total per DB, ms', lambda e: fmt(get(e, 'create', lambda r: r['total_per_db']['median_ms']))),
 ('  create with schema, ms', lambda e: fmt(get(e, 'create', lambda r: r['create_with_schema']['median_ms']))),
 ('  write ten objects, ms', lambda e: fmt(get(e, 'create', lambda r: r['write_ten_objects']['median_ms']))),
 ('  close, ms', lambda e: fmt(get(e, 'create', lambda r: r['close']['median_ms']), 3)),
 ('  total p95, ms', lambda e: fmt(get(e, 'create', lambda r: r['total_per_db']['p95_ms']))),
 ('SPACE  apparent, KB', lambda e: fmt(get(e, 'create', lambda r: r['space_kb_apparent']), 1)),
 ('  allocated, KB', lambda e: fmt(get(e, 'create', lambda r: r['space_kb_allocated']), 1)),
 ('  files', lambda e: str(get(e, 'create', lambda r: r['sample_files'])[0])),
 ('WARM  open, ms', lambda e: fmt(get(e, 'open', lambda r: r['open']['median_ms'], 'warm'), 3)),
 ('  first query, ms', lambda e: fmt(get(e, 'open', lambda r: r['first_query']['median_ms'], 'warm'), 3)),
 ('  close, ms', lambda e: fmt(get(e, 'open', lambda r: r['close']['median_ms'], 'warm'), 3)),
 ('  total, ms', lambda e: fmt(get(e, 'open', lambda r: r['total']['median_ms'], 'warm'), 3)),
 ('  total p95, ms', lambda e: fmt(get(e, 'open', lambda r: r['total']['p95_ms'], 'warm'), 3)),
 ('COLD  open, ms', lambda e: fmt(get(e, 'open', lambda r: r['open']['median_ms'], 'cold'), 3)),
 ('  first query, ms', lambda e: fmt(get(e, 'open', lambda r: r['first_query']['median_ms'], 'cold'), 3)),
 ('  close, ms', lambda e: fmt(get(e, 'open', lambda r: r['close']['median_ms'], 'cold'), 3)),
 ('  total, ms', lambda e: fmt(get(e, 'open', lambda r: r['total']['median_ms'], 'cold'), 3)),
 ('  total p95, ms', lambda e: fmt(get(e, 'open', lambda r: r['total']['p95_ms'], 'cold'), 3)),
 ('HOLD  open', lambda e: fmt(get(e, 'hold', lambda r: r['k_open']), 0)),
 ('  RSS per DB, KB', lambda e: fmt(get(e, 'hold', lambda r: r['rss_kb_per_db']), 0)),
 ('  anonymous per DB, KB', lambda e: fmt(get(e, 'hold', lambda r: r['anon_kb_per_db']), 0)),
 ('  virtual per DB, MB', lambda e: fmt(get(e, 'hold', lambda r: r['virtual_mb_per_db']), 1)),
 ('  file descriptors per DB', lambda e: fmt(get(e, 'hold', lambda r: r['fds_per_db']), 2)),
 ('  RSS after close, MB', lambda e: fmt(get(e, 'hold', lambda r: r['rss_mb_after_close']), 0)),
]
w = 34
print(' ' * w + ''.join(f'{e:<30}' for e in E))
for name, f in rows:
    print(f'{name:<{w}}' + ''.join(f'{str(f(e))[:29]:<30}' for e in E))
