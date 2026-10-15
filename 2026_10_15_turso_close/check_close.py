"""Checks where Turso Database's open, query, close time goes (large workload, one store): open, query and close timed
separately, for Turso as measured (measure.Turso) and with the settings that could avoid the cost of close, and for
SQLite with its default rollback journal (measure.Sqlite) and in WAL mode. One JSON line per variant.
Usage (from the repository root): BENCH_WORKLOAD=large .venv/bin/python 2026_10_15_turso_close/check_close.py <dir> [runs]
  <dir> must not exist; it gets one store per engine.
With `trace` instead of [runs], it opens, queries and closes the Turso store and the SQLite WAL store once each and writes
markers to stderr around each close, for strace (see run.sh)."""
import json, os, statistics, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
import measure as m
import importlib.metadata as md

root = sys.argv[1]; T = time.perf_counter_ns
turso, sqlite = m.Turso(), m.Sqlite()
tpath, spath, wpath = root + '/turso', root + '/sqlite', root + '/sqlite_wal'

if sys.argv[2:] == ['trace']:
    c = turso.open(tpath); assert turso.read(c) == m.ROWS
    os.write(2, b'=== turso close start\n'); turso.close(c); os.write(2, b'=== turso close end\n')
    c = sqlite.open(wpath); assert sqlite.read(c) == m.ROWS
    os.write(2, b'=== sqlite WAL close start\n'); sqlite.close(c); os.write(2, b'=== sqlite WAL close end\n')
    sys.exit()

runs = int(sys.argv[2]) if len(sys.argv) > 2 else 200
for e, p in ((turso, tpath), (sqlite, spath)):
    c = e.create(p); e.write(c, 0); e.close(c)
os.makedirs(wpath); c = sqlite.m.Connection(wpath + '/db.sqlite')
assert c.execute('pragma journal_mode=wal').fetchall() == [('wal',)]
c.execute(m.DDL); sqlite.write(c, 0); c.close()

def ms(ns): return round(ns / 1e6, 4)
def measure(variant, open_, read, close, note=''):
    to, tq, tc = [], [], []
    for _ in range(runs):
        t0 = T(); h = open_(); t1 = T(); n = read(h); t2 = T(); close(h); t3 = T()
        assert n == m.ROWS, n
        to.append(t1 - t0); tq.append(t2 - t1); tc.append(t3 - t2)
    med = statistics.median
    print(json.dumps({'variant': variant, 'runs': runs, 'open_ms': ms(med(to)), 'query_ms': ms(med(tq)),
                      'close_ms': ms(med(tc)), 'total_ms': ms(med([a + b + c for a, b, c in zip(to, tq, tc)])),
                      'note': note}), flush=True)

def turso_with(pragma):
    def open_():
        c = turso.open(tpath); c.execute(pragma); return c
    return open_

measure('turso', lambda: turso.open(tpath), turso.read, turso.close, 'as in the benchmark (measure.Turso)')
for pragma in ('PRAGMA synchronous=OFF', 'PRAGMA synchronous=NORMAL', 'PRAGMA wal_autocheckpoint=0',
               'PRAGMA query_only=1', 'PRAGMA journal_mode=DELETE'):
    measure('turso, ' + pragma, turso_with(pragma), turso.read, turso.close)
c = turso.open(tpath)
print(json.dumps({'variant': 'turso, PRAGMA values', 'journal_mode': c.execute('PRAGMA journal_mode').fetchall(),
                  'synchronous': c.execute('PRAGMA synchronous').fetchall(),
                  'wal_autocheckpoint': c.execute('PRAGMA wal_autocheckpoint').fetchall()}, default=str), flush=True)
c.close()
try:
    c = turso.m.connect('file:' + tpath + '/db.sqlite?mode=ro'); c.close(); ro = 'opened'
except Exception as ex:
    ro = f'{type(ex).__name__}: {ex}'
print(json.dumps({'variant': 'turso, file:...?mode=ro', 'result': ro}), flush=True)
keep = turso.open(tpath); turso.read(keep)
measure('turso, another connection open', lambda: turso.open(tpath), turso.read, turso.close,
        'close is not the last close of the database')
turso.close(keep)
measure('sqlite', lambda: sqlite.open(spath), sqlite.read, sqlite.close, 'as in the benchmark: rollback journal')
measure('sqlite, WAL', lambda: sqlite.open(wpath), sqlite.read, sqlite.close, 'journal_mode=wal set at creation')
print(json.dumps({'variant': 'versions', 'pyturso': md.version('pyturso'), 'sqlite': sqlite.version}), flush=True)
