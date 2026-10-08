#!/usr/bin/env python3
"""Fasst ergebnisse.jsonl zusammen: Median ueber die Laeufe, in Klammern kleinster und groesster Lauf."""
import json, statistics as st, collections
R = [json.loads(l) for l in open('ergebnisse.jsonl')]
E = ['obx', 'sqlite', 'turso', 'libsql']
def get(e, phase, f, cache=None): return [f(r) for r in R if r['engine'] == e and r['phase'] == phase and (cache is None or r.get('cache') == cache)]
def fmt(xs, nd=2):
    if not xs: return '-'
    m = st.median(xs); return f'{m:.{nd}f} ({min(xs):.{nd}f}-{max(xs):.{nd}f})'
rows = [
 ('Version', lambda e: [r['version'] for r in R if r['engine'] == e][0]),
 ('Laeufe', lambda e: str(len(get(e, 'anlegen', lambda r: 1)))),
 ('ANLEGEN  gesamt je DB, ms', lambda e: fmt(get(e, 'anlegen', lambda r: r['gesamt_je_db']['median_ms']))),
 ('  neu anlegen mit Schema, ms', lambda e: fmt(get(e, 'anlegen', lambda r: r['neu_anlegen_mit_schema']['median_ms']))),
 ('  zehn Objekte schreiben, ms', lambda e: fmt(get(e, 'anlegen', lambda r: r['zehn_objekte_schreiben']['median_ms']))),
 ('  schliessen, ms', lambda e: fmt(get(e, 'anlegen', lambda r: r['schliessen']['median_ms']), 3)),
 ('  gesamt p95, ms', lambda e: fmt(get(e, 'anlegen', lambda r: r['gesamt_je_db']['p95_ms']))),
 ('PLATZ  scheinbar, KB', lambda e: fmt(get(e, 'anlegen', lambda r: r['platz_kb_scheinbar']), 1)),
 ('  belegt, KB', lambda e: fmt(get(e, 'anlegen', lambda r: r['platz_kb_belegt']), 1)),
 ('  Dateien', lambda e: str(get(e, 'anlegen', lambda r: r['dateien_beispiel'])[0])),
 ('WARM  oeffnen, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['oeffnen']['median_ms'], 'warm'), 3)),
 ('  erste Abfrage, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['erste_abfrage']['median_ms'], 'warm'), 3)),
 ('  schliessen, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['schliessen']['median_ms'], 'warm'), 3)),
 ('  Summe, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['summe']['median_ms'], 'warm'), 3)),
 ('  Summe p95, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['summe']['p95_ms'], 'warm'), 3)),
 ('KALT  oeffnen, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['oeffnen']['median_ms'], 'kalt'), 3)),
 ('  erste Abfrage, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['erste_abfrage']['median_ms'], 'kalt'), 3)),
 ('  schliessen, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['schliessen']['median_ms'], 'kalt'), 3)),
 ('  Summe, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['summe']['median_ms'], 'kalt'), 3)),
 ('  Summe p95, ms', lambda e: fmt(get(e, 'oeffnen', lambda r: r['summe']['p95_ms'], 'kalt'), 3)),
 ('HALTEN  offen', lambda e: fmt(get(e, 'halten', lambda r: r['k_offen']), 0)),
 ('  RSS je DB, KB', lambda e: fmt(get(e, 'halten', lambda r: r['rss_kb_je_db']), 0)),
 ('  anonym je DB, KB', lambda e: fmt(get(e, 'halten', lambda r: r['anonym_kb_je_db']), 0)),
 ('  virtuell je DB, MB', lambda e: fmt(get(e, 'halten', lambda r: r['virtuell_mb_je_db']), 1)),
 ('  Dateideskriptoren je DB', lambda e: fmt(get(e, 'halten', lambda r: r['fds_je_db']), 2)),
 ('  RSS nach Schliessen, MB', lambda e: fmt(get(e, 'halten', lambda r: r['rss_mb_nach_schliessen']), 0)),
]
w = 34
print(' ' * w + ''.join(f'{e:<30}' for e in E))
for name, f in rows:
    print(f'{name:<{w}}' + ''.join(f'{str(f(e))[:29]:<30}' for e in E))
