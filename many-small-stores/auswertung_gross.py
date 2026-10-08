#!/usr/bin/env python3
"""Wertet ergebnisse_gross*.jsonl aus: Median ueber die drei Laeufe, Spanne dazu."""
import json, statistics, sys
from collections import defaultdict
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f)]
E = ['obx', 'sqlite', 'turso', 'libsql']; MODES = ['standard', 'mallopt']
def pick(e, mode, phase, cache=None, n=None):
    return [r for r in rows if r['engine'] == e and r['einstellung'] == mode and r['phase'] == phase and (cache is None or r.get('cache') == cache) and (n is None or r['n'] == n)]
def med(xs): return statistics.median(xs)
for n in sorted({r['n'] for r in rows}):
    print(f'\n===== N = {n:,} Stores je Engine =====')
    for e in E:
        for mode in MODES:
            a = pick(e, mode, 'anlegen', n=n)
            if not a: continue
            a = a[0]; print(f"\n{e:7s} {mode:9s} {a['version']}")
            s = a['anlegen_schreiben_schliessen']
            print(f"  anlegen: median {s['median_ms']:.2f} ms  p99 {s['p99_ms']:.2f} ms  {a['stores_je_s']:.0f} Stores/s  Wand {a['wand_s']:.0f} s")
            print(f"  platz:   Dateien {a['platz_kb_je_store_dateien']:.1f} KB belegt, {a['platz']['dateien_bytes_scheinbar']/n/1024:.1f} KB scheinbar; mit Verzeichnissen {a['platz_kb_je_store_mit_verzeichnissen']:.1f} KB; gesamt {a['platz_gb_gesamt']:.2f} GB  {a['dateien_beispiel']}")
            for cache in ('warm', 'kalt'):
                o = pick(e, mode, 'oeffnen', cache, n)
                if not o: continue
                m_ = [r['summe']['median_ms'] for r in o]; p = [r['summe']['p99_ms'] for r in o]
                oo = med([r['oeffnen']['median_ms'] for r in o]); q = med([r['erste_abfrage']['median_ms'] for r in o]); c = med([r['schliessen']['median_ms'] for r in o])
                print(f"  oeffnen+abfrage+schliessen {cache}: median {med(m_):.3f} ms ({min(m_):.3f}-{max(m_):.3f})  p99 {med(p):.3f} ms ({min(p):.3f}-{max(p):.3f})   [oeffnen {oo:.3f} / abfrage {q:.3f} / schliessen {c:.3f}]")
            for h in pick(e, mode, 'halten', n=n):
                print(f"  halten:  {h['k_offen']} offen  RSS {h['rss_kb_je_store']:.0f} KB je Store (anonym {h['anonym_kb_je_store']:.0f})  gesamt {h['rss_mb_alle_offen']:.0f} MB  fds {h['fds_je_store']:.0f} je Store  Fehler {h['fehler']}")
