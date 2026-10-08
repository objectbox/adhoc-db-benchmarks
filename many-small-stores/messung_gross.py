#!/usr/bin/env python3
"""Grosser Lauf "eine Datenbank pro Agent": viele kleine Stores je Engine.

Aufruf:  python3 messung_gross.py <engine> <phase> <N> [M] [seed]
  engine: obx | sqlite | turso | libsql
  phase:  anlegen  - N Stores neu anlegen, je zehn kleine Objekte schreiben, schliessen
          oeffnen  - M zufaellige der N Stores: oeffnen, eine Abfrage, schliessen
          halten   - M Stores gleichzeitig offen halten: Arbeitsspeicher, Dateideskriptoren
Umgebung:
  MESS_ROOT     Datenverzeichnis (Standard: data_gross)
  MESS_MALLOPT  =1 setzt im Prozess mallopt(M_MMAP_THRESHOLD, 131072); sonst Standardwerte
  OBX_LIB       Pfad zu libobjectbox.so

Die Engine-Klassen (Schema, Schreiben, Abfrage) kommen unveraendert aus messung.py.
Je Aufruf ein eigener Prozess, damit Speicherwerte nicht von vorherigen Phasen abhaengen.
"""
import ctypes, json, os, random, statistics, sys, time

TUNED = os.environ.get('MESS_MALLOPT') == '1'
if TUNED:
    M_MMAP_THRESHOLD = -3
    assert ctypes.CDLL('libc.so.6').mallopt(M_MMAP_THRESHOLD, 131072) == 1

os.environ.setdefault('MESS_ROOT', 'data_gross')
import messung as m            # liest MESS_ROOT beim Import
from messung import ENGINES, ROWS, path, mem, status, T

def ms(ns): return ns / 1e6
def stat(xs):
    xs = sorted(xs); n = len(xs)
    return {'median_ms': round(ms(statistics.median(xs)), 4), 'p95_ms': round(ms(xs[int(n * 0.95)]), 4),
            'p99_ms': round(ms(xs[int(n * 0.99)]), 4), 'max_ms': round(ms(xs[-1]), 3), 'mean_ms': round(ms(sum(xs) / n), 4)}

def platz(root):
    """Belegter Platz: Dateien und Verzeichnisse getrennt, in Bloecken wie das Dateisystem sie zaehlt."""
    dateien = verz = scheinbar = 0; nfiles = ndirs = 0
    for d, subs, files in os.walk(root):
        verz += os.lstat(d).st_blocks * 512; ndirs += 1
        for f in files:
            st = os.lstat(os.path.join(d, f)); dateien += st.st_blocks * 512; scheinbar += st.st_size; nfiles += 1
    return {'dateien_bytes_belegt': dateien, 'dateien_bytes_scheinbar': scheinbar, 'verzeichnisse_bytes_belegt': verz, 'anzahl_dateien': nfiles, 'anzahl_verzeichnisse': ndirs}

def anlegen(e, n, _m, _seed):
    ges = []; t_all = T()
    for i in range(n):
        p = path(e, i); t0 = T(); h = e.create(p); e.write(h, i); e.close(h); ges.append(T() - t0)
    wall = T() - t_all
    pl = platz(f'{m.ROOT}/{e.name}')
    beispiel = {f: os.stat(os.path.join(path(e, n // 2), f)).st_size for f in sorted(os.listdir(path(e, n // 2)))}
    return {'n': n, 'anlegen_schreiben_schliessen': stat(ges), 'wand_s': round(wall / 1e9, 1), 'stores_je_s': round(n / (wall / 1e9), 1),
            'platz_kb_je_store_dateien': round(pl['dateien_bytes_belegt'] / n / 1024, 2),
            'platz_kb_je_store_mit_verzeichnissen': round((pl['dateien_bytes_belegt'] + pl['verzeichnisse_bytes_belegt']) / n / 1024, 2),
            'platz_gb_gesamt': round((pl['dateien_bytes_belegt'] + pl['verzeichnisse_bytes_belegt']) / 1024**3, 3),
            'platz': pl, 'dateien_beispiel': beispiel, 'max_rss_mb': round(status('VmHWM') / 1024, 1)}

def oeffnen(e, n, mm, seed):
    ids = random.Random(seed).sample(range(n), mm)
    to, tr, tc = [], [], []
    for i in ids:
        p = path(e, i); t0 = T(); h = e.open(p); t1 = T(); c = e.read(h); t2 = T(); e.close(h); t3 = T()
        assert c == ROWS, (i, c)
        to.append(t1 - t0); tr.append(t2 - t1); tc.append(t3 - t2)
    return {'n': n, 'm': mm, 'seed': seed, 'oeffnen': stat(to), 'erste_abfrage': stat(tr), 'schliessen': stat(tc),
            'summe': stat([a + b + c for a, b, c in zip(to, tr, tc)])}

def halten(e, n, k, seed):
    import gc
    ids = random.Random(seed).sample(range(n), k)
    hs = []; m0 = mem(); fd0 = len(os.listdir('/proc/self/fd')); t0 = T(); fehler = None
    try:
        for i in ids:
            h = e.open(path(e, i)); e.read(h); hs.append(h)
    except Exception as ex:
        fehler = repr(ex)[:300]
    t1 = T(); m1 = mem(); k_offen = max(len(hs), 1)
    fds = len(os.listdir('/proc/self/fd')) - fd0; thr = status('Threads')
    for h in hs: e.close(h)
    offen = len(hs); hs.clear(); gc.collect(); m2 = mem()
    return {'n': n, 'k_gewuenscht': k, 'k_offen': offen, 'fehler': fehler,
            'rss_kb_je_store': round((m1['Rss'] - m0['Rss']) / k_offen, 1), 'anonym_kb_je_store': round((m1['Anonymous'] - m0['Anonymous']) / k_offen, 1),
            'fds_je_store': round(fds / k_offen, 2), 'threads': thr, 'rss_mb_alle_offen': round((m1['Rss'] - m0['Rss']) / 1024, 1),
            'rss_mb_nach_schliessen': round((m2['Rss'] - m0['Rss']) / 1024, 1), 'oeffnen_ms_je_store': round(ms(t1 - t0) / k_offen, 4)}

if __name__ == '__main__':
    e = ENGINES[sys.argv[1]](); phase = sys.argv[2]; n = int(sys.argv[3])
    mm = int(sys.argv[4]) if len(sys.argv) > 4 else 0; seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    r = {'engine': e.name, 'version': e.version, 'phase': phase, 'einstellung': 'mallopt' if TUNED else 'standard'}
    r.update({'anlegen': anlegen, 'oeffnen': oeffnen, 'halten': halten}[phase](e, n, mm, seed))
    print(json.dumps(r, ensure_ascii=False))
