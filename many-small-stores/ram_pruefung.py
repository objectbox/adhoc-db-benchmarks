#!/usr/bin/env python3
"""Prueft, ob und wo der Arbeitsspeicher je offenem ObjectBox-Store ansteigt.
Aufruf: python3 ram_pruefung.py <K>     (vorher: python3 messung.py obx anlegen 3000)
Gibt je Stufe RSS, anonymen und dateigestuetzten Anteil aus, dazu die Aufteilung nach Speicherbereichen
und die Zahlen des Allokators (mallinfo2)."""
import ctypes, os, re, sys
sys.argv, K = ['x'], int(sys.argv[1])
import messung as M
libc = ctypes.CDLL('libc.so.6')
class MI(ctypes.Structure):
    _fields_ = [(n, ctypes.c_size_t) for n in ('arena','ordblks','smblks','hblks','hblkhd','usmblks','fsmblks','uordblks','fordblks','keepcost')]
libc.mallinfo2.restype = MI
def smaps():
    """Summiert Rss je Kategorie aus /proc/self/smaps."""
    cat = {}; name = None
    for l in open('/proc/self/smaps'):
        m = re.match(r'^[0-9a-f]+-[0-9a-f]+ \S+ \S+ \S+ \S+\s*(.*)$', l)
        if m:
            n = m.group(1).strip()
            name = 'data.mdb (mmap)' if n.endswith('data.mdb') else 'lock.mdb (mmap)' if n.endswith('lock.mdb') else '[heap]' if n == '[heap]' else 'anonym (ohne Namen)' if n == '' else 'Bibliotheken/sonstiges'
        elif l.startswith('Rss:'):
            cat[name] = cat.get(name, 0) + int(l.split()[1])
    return cat
e = M.Obx(); hs = []
m0, s0, a0 = M.mem(), smaps(), libc.mallinfo2()
stufen = [k for k in (1, 10, 100, 250, 500, 1000, 2000) if k <= K]
print('offen   RSS je Store   davon anonym   davon Datei (mmap)')
for k in stufen:
    while len(hs) < k:
        h = e.open(M.path(e, len(hs))); e.read(h); hs.append(h)
    m = M.mem(); rss = m['Rss'] - m0['Rss']; an = m['Anonymous'] - m0['Anonymous']
    print(f'{k:5d}   {rss / k:9.0f} KB   {an / k:9.0f} KB   {(rss - an) / k:9.1f} KB')
s1, a1 = smaps(), libc.mallinfo2(); n = len(hs)
print('\nZuwachs je Store nach Speicherbereich (KB):')
for c in sorted(set(s0) | set(s1)):
    print(f'  {c:26s} {(s1.get(c, 0) - s0.get(c, 0)) / n:9.1f}')
print('\nAllokator (glibc mallinfo2), Zuwachs je Store in KB:')
print(f'  per mmap geholt (hblkhd)   {(a1.hblkhd - a0.hblkhd) / 1024 / n:9.1f}   Anzahl mmap-Bloecke je Store: {(a1.hblks - a0.hblks) / n:.2f}')
print(f'  im Heap belegt (uordblks)  {(a1.uordblks - a0.uordblks) / 1024 / n:9.1f}')
print(f'  Heap-Groesse (arena)       {(a1.arena - a0.arena) / 1024 / n:9.1f}')
