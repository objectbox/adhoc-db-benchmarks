#!/usr/bin/env python3
"""Prints the Markdown tables of README.md from results_large.jsonl (medians across the three warm open runs)."""
import json, os, statistics

HERE = os.path.dirname(os.path.realpath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, 'results_large.jsonl'))]
ENGINES = [('obx', 'ObjectBox, sync every open'), ('obx_cached', 'ObjectBox, cached model'),
           ('obx_nosync', 'ObjectBox, skip model sync'), ('sqlite', 'SQLite'), ('turso', 'Turso Database'), ('libsql', 'libSQL')]
SETTINGS = ['standard', 'mallopt']


def pick(engine, setting, phase):
    return [r for r in rows if r['engine'] == engine and r['setting'] == setting and r['phase'] == phase
            and r.get('cache', 'warm') == 'warm']


def med(xs): return statistics.median(xs)
def fmt(x, digits=2): return f'{x:,.{digits}f}'


def table(setting, engines):
    present = [(e, label) for e, label in engines if pick(e, setting, 'create')]
    lines = ['| | ' + ' | '.join(label for _, label in present) + ' |', '|---' * (len(present) + 1) + '|']

    def row(title, fn):
        lines.append(f'| {title} | ' + ' | '.join(fn(e) for e, _ in present) + ' |')

    create = lambda e: pick(e, setting, 'create')[0]
    opens = lambda e: pick(e, setting, 'open')
    hold = lambda e: pick(e, setting, 'hold')[0]
    row('Create, write ten objects, close (median)', lambda e: fmt(create(e)['create_write_close']['median_ms']) + ' ms')
    row('Stores per second', lambda e: fmt(create(e)['stores_per_s'], 0))
    row('Open (median)', lambda e: fmt(med([r['open']['median_ms'] for r in opens(e)]), 3) + ' ms')
    row('Open, query, close (median)', lambda e: fmt(med([r['total']['median_ms'] for r in opens(e)]), 3) + ' ms')
    row('same, p99', lambda e: fmt(med([r['total']['p99_ms'] for r in opens(e)]), 3) + ' ms')
    row('Close (median)', lambda e: fmt(med([r['close']['median_ms'] for r in opens(e)]), 3) + ' ms')
    row('Memory per open store (1,000 open)', lambda e: fmt(hold(e)['rss_kb_per_store'], 0) + ' KB')
    row('Space per store, files', lambda e: fmt(create(e)['space_kb_per_store_files'], 0) + ' KB')
    return '\n'.join(lines)


for setting in SETTINGS:
    print(f'\n### Setting: {setting}\n')
    print(table(setting, ENGINES))
