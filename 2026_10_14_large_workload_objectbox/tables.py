#!/usr/bin/env python3
"""Prints the Markdown tables of README.md from results_large.jsonl (ObjectBox, large workload; medians across the
three warm open runs), per setting: generic flatbuffers.Builder and experimental FlatBuffers codegen side by side,
with the 2026-10-11 measurement (objectbox-python dev, 5cc8f48) for comparison."""
import json, os, statistics

HERE = os.path.dirname(os.path.realpath(__file__))
load = lambda path: [json.loads(l) for l in open(path)]
rows = load(os.path.join(HERE, 'results_large.jsonl'))
before = load(os.path.join(HERE, '..', '2026_10_11_large_workload', 'results_large.jsonl'))
VARIANTS = [('obx', 'sync every open'), ('obx_cached', 'cached model'), ('obx_nosync', 'skip model sync')]
BUILDERS = [('', 'generic'), ('codegen', 'codegen')]
SETTINGS = ['standard', 'mallopt']


def pick(data, engine, setting, phase, builder):
    return [r for r in data if r['engine'] == engine and r['setting'] == setting and r['phase'] == phase
            and r.get('obx_flatbuffers', '') == builder and r.get('cache', 'warm') == 'warm']


def med(xs): return statistics.median(xs)
def fmt(x, digits=2): return f'{x:,.{digits}f}'


def table(setting):
    cols = [(e, b, f'{label}, {blabel}') for e, label in VARIANTS for b, blabel in BUILDERS
            if pick(rows, e, setting, 'create', b)]
    lines = ['| | ' + ' | '.join(c[2] for c in cols) + ' |', '|---' * (len(cols) + 1) + '|']

    def row(title, fn):
        lines.append(f'| {title} | ' + ' | '.join(fn(e, b) for e, b, _ in cols) + ' |')

    create = lambda e, b: pick(rows, e, setting, 'create', b)[0]
    opens = lambda e, b: pick(rows, e, setting, 'open', b)
    hold = lambda e, b: pick(rows, e, setting, 'hold', b)[0]
    row('Create, write 1,000 objects, close (median)', lambda e, b: fmt(create(e, b)['create_write_close']['median_ms']) + ' ms')
    row('same, p99', lambda e, b: fmt(create(e, b)['create_write_close']['p99_ms']) + ' ms')

    def prev(e, b):
        r = pick(before, e, setting, 'create', '') if not b else []
        return fmt(r[0]['create_write_close']['median_ms']) + ' ms' if r else '–'
    row('same, 2026-10-11 (dev 5cc8f48, generic)', prev)
    row('Stores per second', lambda e, b: fmt(create(e, b)['stores_per_s'], 0))
    row('Open (median)', lambda e, b: fmt(med([r['open']['median_ms'] for r in opens(e, b)]), 3) + ' ms')
    row('Count query (median)', lambda e, b: fmt(med([r['first_query']['median_ms'] for r in opens(e, b)]), 3) + ' ms')
    row('Open, query, close (median)', lambda e, b: fmt(med([r['total']['median_ms'] for r in opens(e, b)]), 3) + ' ms')
    row('same, p99', lambda e, b: fmt(med([r['total']['p99_ms'] for r in opens(e, b)]), 3) + ' ms')
    row('Close (median)', lambda e, b: fmt(med([r['close']['median_ms'] for r in opens(e, b)]), 3) + ' ms')
    row('Memory per open store (1,000 open), resident', lambda e, b: fmt(hold(e, b)['rss_kb_per_store'], 0) + ' KB')
    row('same, anonymous (process\' own memory)', lambda e, b: fmt(hold(e, b)['anon_kb_per_store'], 0) + ' KB')
    row('Load at the start of create', lambda e, b: fmt(create(e, b)['load1'], 2))
    row('Load at start of the warm open runs (max)', lambda e, b: fmt(max(r['load1'] for r in opens(e, b)), 2))
    row('Space per store, files', lambda e, b: fmt(create(e, b)['space_kb_per_store_files'], 0) + ' KB')
    return '\n'.join(lines)


for setting in SETTINGS:
    print(f'\n### Setting: {setting}\n')
    print(table(setting))
