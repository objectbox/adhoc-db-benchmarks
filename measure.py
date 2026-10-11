#!/usr/bin/env python3
"""One database per agent - measuring ObjectBox, SQLite, Turso, libSQL.

Usage (each phase in a fresh process so memory is clean):
  python3 measure.py <engine> create <N>      creates N databases with ROWS objects each (see BENCH_WORKLOAD)
  python3 measure.py <engine> open   <M>      opens M existing ones one after another: open, read, close
  python3 measure.py <engine> hold   <K>      keeps K open at the same time and measures memory
  engine: obx | obx_cached | obx_nosync | sqlite | turso | libsql
Output: one JSON line.
BENCH_WORKLOAD selects what is written per store, in one transaction: small (default; 10 objects with a short text)
or large (1,000 objects with a 300-character text).

ObjectBox is accessed through its Python API (package objectbox 5.0.0b1 with objectbox-clib 5.3.2);
the model IDs are kept in objectbox-model.json next to this file.
"""
import json, os, statistics, sys, time

WORKLOADS = {'small': (10, None), 'large': (1000, 300)}  # name: (objects per store, text length; None: short text)
WORKLOAD = os.environ.get('BENCH_WORKLOAD', 'small')
ROWS, TEXT_LEN = WORKLOADS[WORKLOAD]
FILLER = ('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna '
          'aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. '
          'Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint '
          'occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.')
def rows(i):
    """The (text, ts) values written to store i."""
    if TEXT_LEN is None: return [(f'note {j} of agent {i}', j) for j in range(ROWS)]
    return [((f'note {j} of agent {i}: ' + FILLER)[:TEXT_LEN], j) for j in range(ROWS)]
assert TEXT_LEN is None or len(rows(99999)[-1][0]) == TEXT_LEN
ROOT = os.environ.get('BENCH_ROOT', 'data')

# ---------------------------------------------------------------- ObjectBox (Python API)
MODEL_JSON = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'objectbox-model.json')

class Obx:
    """ObjectBox through its Python API (package objectbox). A new Model per store, i.e. the model is synced with
    the model JSON file on every open, as the objectbox package did for every Store before 5.0.0b1."""
    name = 'obx'
    def __init__(self):
        import objectbox
        from objectbox import Entity, Id, Int64, Model, Store, String
        @Entity()
        class Note:
            id = Id
            text = String
            ts = Int64
        self.Note, self.Model, self.Store = Note, Model, Store
        self.version = f'ObjectBox {objectbox.version} (C library {objectbox.version_core})'
        tune = os.environ.get('OBX_TUNE', '')
        self.options = {}
        if 'readers' in tune: self.options['max_readers'] = 8
        if 'maxkb' in tune: self.options['max_db_size_in_kb'] = 10240
        if 'notls' in tune: self.options['no_reader_thread_locals'] = True
    def model(self):
        m = self.Model(); m.entity(self.Note); return m
    def _open(self, path):
        return self.Store(model=self.model(), directory=path, model_json_file=MODEL_JSON, **self.options)
    def create(self, path): os.makedirs(path); return self._open(path)
    def open(self, path): return self._open(path)
    def write(self, s, i):
        s.box(self.Note).put([self.Note(text=text, ts=ts) for text, ts in rows(i)])  # one transaction
    def read(self, s): return s.box(self.Note).count()
    def close(self, s): s.close()

class ObxCached(Obx):
    """One Model for all stores: synced with the model JSON file only once per process (objectbox 5.0.0b1)."""
    name = 'obx_cached'
    def model(self):
        if not hasattr(self, '_model'): self._model = super().model()
        return self._model

class ObxNoSync(ObxCached):
    """Like ObxCached, plus skip_model_sync: existing stores are opened with the schema stored in their database,
    without checking it against the model (objectbox 5.0.0b1). New stores are still created with the model."""
    name = 'obx_nosync'
    def _open(self, path):
        return self.Store(model=self.model(), directory=path, model_json_file=MODEL_JSON, skip_model_sync=True, **self.options)

# ---------------------------------------------------------------- SQL engines
DDL = 'create table note(id integer primary key, text text, ts integer)'
INS = 'insert into note(text, ts) values(?, ?)'
CNT = 'select count(*) from note'

class Sqlite:
    name = 'sqlite'
    def __init__(self): import apsw; self.m = apsw; self.version = 'SQLite ' + apsw.sqlitelibversion() + ' (apsw ' + apsw.apswversion() + ')'
    def create(self, path): os.makedirs(path); c = self.m.Connection(path + '/db.sqlite'); c.execute(DDL); return c
    def open(self, path): return self.m.Connection(path + '/db.sqlite')
    def write(self, c, i):
        with c: c.executemany(INS, rows(i))
    def read(self, c): return c.execute(CNT).fetchall()[0][0]
    def close(self, c): c.close()

class Turso:
    name = 'turso'
    def __init__(self): import turso, importlib.metadata as md; self.m = turso; self.version = 'Turso Database (pyturso ' + md.version('pyturso') + ')'
    def create(self, path): os.makedirs(path); c = self.m.connect(path + '/db.sqlite'); c.execute(DDL); c.commit(); return c
    def open(self, path): return self.m.connect(path + '/db.sqlite')
    def write(self, c, i):
        cur = c.cursor(); cur.executemany(INS, rows(i)); c.commit()
    def read(self, c): cur = c.cursor(); cur.execute(CNT); return cur.fetchall()[0][0]
    def close(self, c): c.close()

class Libsql:
    name = 'libsql'
    def __init__(self): import libsql, importlib.metadata as md; self.m = libsql; self.version = 'libSQL (libsql ' + md.version('libsql') + ')'
    def create(self, path): os.makedirs(path); c = self.m.connect(path + '/db.sqlite'); c.execute(DDL); c.commit(); return c
    def open(self, path): return self.m.connect(path + '/db.sqlite')
    def write(self, c, i):
        c.executemany(INS, rows(i)); c.commit()
    def read(self, c): return c.execute(CNT).fetchall()[0][0]
    def close(self, c): c.close()

ENGINES = {'obx': Obx, 'obx_cached': ObxCached, 'obx_nosync': ObxNoSync, 'sqlite': Sqlite, 'turso': Turso, 'libsql': Libsql}

# ---------------------------------------------------------------- Helpers
def path(e, i): return f'{ROOT}/{e.name}/{i // 1000}/{i}'
def ms(ns): return ns / 1e6
def stat(xs):
    xs = sorted(xs); return {'median_ms': round(ms(statistics.median(xs)), 4), 'p95_ms': round(ms(xs[int(len(xs) * 0.95)]), 4), 'mean_ms': round(ms(sum(xs) / len(xs)), 4)}
def mem():
    d = {}
    for l in open('/proc/self/smaps_rollup'):
        p = l.split()
        if p[0] in ('Rss:', 'Pss:', 'Anonymous:', 'Private_Clean:', 'Private_Dirty:', 'Shared_Clean:'): d[p[0][:-1]] = int(p[1])
    return d
def status(key):
    for l in open('/proc/self/status'):
        if l.startswith(key): return int(l.split()[1])
def disk(p):
    files = {}; app = alloc = 0
    for f in sorted(os.listdir(p)):
        st = os.stat(os.path.join(p, f)); files[f] = st.st_size; app += st.st_size; alloc += st.st_blocks * 512
    return app, alloc, files
T = time.perf_counter_ns

# ---------------------------------------------------------------- Phases
def phase_create(e, n):
    to, tw, tc = [], [], []; t_all = T()
    for i in range(n):
        p = path(e, i); t0 = T(); h = e.create(p); t1 = T(); e.write(h, i); t2 = T(); e.close(h); t3 = T()
        to.append(t1 - t0); tw.append(t2 - t1); tc.append(t3 - t2)
    wall = T() - t_all
    app = alloc = 0; sample = None
    for i in range(n):
        a, b, f = disk(path(e, i)); app += a; alloc += b
        if i == n // 2: sample = f
    return {'n': n, 'total_per_db': stat([a + b + c for a, b, c in zip(to, tw, tc)]), 'create_with_schema': stat(to), 'write_ten_objects': stat(tw),
            'close': stat(tc), 'wall_ms_per_db': round(ms(wall) / n, 4), 'space_kb_apparent': round(app / n / 1024, 2), 'space_kb_allocated': round(alloc / n / 1024, 2),
            'sample_files': sample, 'max_rss_mb': round(status('VmHWM') / 1024, 1)}

def phase_open(e, m):
    to, tr, tc = [], [], []
    for i in range(m):
        p = path(e, i); t0 = T(); h = e.open(p); t1 = T(); c = e.read(h); t2 = T(); e.close(h); t3 = T()
        assert c == ROWS, c
        to.append(t1 - t0); tr.append(t2 - t1); tc.append(t3 - t2)
    return {'m': m, 'open': stat(to), 'first_query': stat(tr), 'close': stat(tc), 'total': stat([a + b + c for a, b, c in zip(to, tr, tc)])}

def phase_hold(e, k):
    import gc
    hs = []; m0 = mem(); t0 = T(); error = None
    try:
        for i in range(k):
            h = e.open(path(e, i)); e.read(h); hs.append(h)
    except Exception as ex:
        error = repr(ex)[:300]
    t1 = T(); m1 = mem(); n = max(len(hs), 1)
    fds = len(os.listdir('/proc/self/fd')); thr = status('Threads'); vsz = status('VmSize')
    t2 = T()
    for h in hs: e.close(h)
    t3 = T(); n_open = len(hs); hs.clear(); gc.collect(); m2 = mem()
    return {'k_requested': k, 'k_open': n_open, 'error': error,
            'rss_kb_per_db': round((m1['Rss'] - m0['Rss']) / n, 1), 'anon_kb_per_db': round((m1['Anonymous'] - m0['Anonymous']) / n, 1),
            'pss_kb_per_db': round((m1['Pss'] - m0['Pss']) / n, 1), 'fds_per_db': round(fds / n, 2), 'threads': thr, 'virtual_mb_per_db': round(vsz / 1024 / n, 2),
            'open_ms_per_db': round(ms(t1 - t0) / n, 4), 'close_ms_per_db': round(ms(t3 - t2) / n, 4),
            'rss_mb_open': round((m1['Rss'] - m0['Rss']) / 1024, 1), 'rss_mb_after_close': round((m2['Rss'] - m0['Rss']) / 1024, 1)}

if __name__ == '__main__':
    e = ENGINES[sys.argv[1]](); phase = sys.argv[2]; n = int(sys.argv[3])
    r = {'engine': e.name, 'version': e.version, 'phase': phase, 'workload': WORKLOAD}
    r.update({'create': phase_create, 'open': phase_open, 'hold': phase_hold}[phase](e, n))
    print(json.dumps(r, ensure_ascii=False))
