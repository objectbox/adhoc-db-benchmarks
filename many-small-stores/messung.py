#!/usr/bin/env python3
"""Eine Datenbank pro Agent - Messung ObjectBox, SQLite, Turso, libSQL.

Aufruf (jede Phase in einem frischen Prozess, damit der Speicher sauber ist):
  python3 messung.py <engine> anlegen  <N>      legt N Datenbanken mit je 10 Objekten an
  python3 messung.py <engine> oeffnen  <M>      oeffnet M vorhandene nacheinander: oeffnen, lesen, schliessen
  python3 messung.py <engine> halten   <K>      haelt K gleichzeitig offen und misst den Arbeitsspeicher
  engine: obx | sqlite | turso | libsql
Ausgabe: eine JSON-Zeile.

ObjectBox wird ueber die offizielle C-API (libobjectbox.so) per ctypes angesprochen,
weil das Python-Paket auf PyPI (4.0.0, Mai 2024) einen aelteren Kern buendelt.
Pfad zur Bibliothek: Umgebungsvariable OBX_LIB.
"""
import ctypes, json, os, statistics, sys, time

ROWS = 10
ROOT = os.environ.get('MESS_ROOT', 'data')

# ---------------------------------------------------------------- ObjectBox (C-API)
class Obx:
    name = 'obx'
    def __init__(self):
        import flatbuffers
        self.fb = flatbuffers
        C = ctypes.CDLL(os.environ.get('OBX_LIB', 'obxc/lib/libobjectbox.so'))
        vp, u64, u32, cp = ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint32, ctypes.c_char_p
        def sig(fn, res, *args): f = getattr(C, fn); f.restype = res; f.argtypes = list(args); return f
        self.version_string = sig('obx_version_string', cp)
        self.err = sig('obx_last_error_message', cp)
        self.model = sig('obx_model', vp)
        self.m_entity = sig('obx_model_entity', ctypes.c_int, vp, cp, u32, u64)
        self.m_prop = sig('obx_model_property', ctypes.c_int, vp, cp, ctypes.c_int, u32, u64)
        self.m_flags = sig('obx_model_property_flags', ctypes.c_int, vp, u32)
        self.m_lastprop = sig('obx_model_entity_last_property_id', ctypes.c_int, vp, u32, u64)
        self.m_lastent = sig('obx_model_last_entity_id', None, vp, u32, u64)
        self.opt = sig('obx_opt', vp)
        self.opt_dir = sig('obx_opt_directory', ctypes.c_int, vp, cp)
        self.opt_model = sig('obx_opt_model', ctypes.c_int, vp, vp)
        self.opt_max_readers = sig('obx_opt_max_readers', None, vp, ctypes.c_uint)
        self.opt_max_kb = sig('obx_opt_max_db_size_in_kb', None, vp, u64)
        self.opt_no_tls = sig('obx_opt_no_reader_thread_locals', None, vp, ctypes.c_bool)
        self.store_open = sig('obx_store_open', vp, vp)
        self.store_close = sig('obx_store_close', ctypes.c_int, vp)
        self.box = sig('obx_box', vp, vp, u32)
        self.id_for_put = sig('obx_box_id_for_put', u64, vp, u64)
        self.put = sig('obx_box_put', ctypes.c_int, vp, u64, ctypes.c_char_p, ctypes.c_size_t)
        self.count = sig('obx_box_count', ctypes.c_int, vp, u64, ctypes.POINTER(u64))
        self.txn_write = sig('obx_txn_write', vp, vp)
        self.txn_success = sig('obx_txn_success', ctypes.c_int, vp)
        self.version = self.version_string().decode()
        self.tune = os.environ.get('OBX_TUNE', '')
    def _open(self, path):
        m = self.model()
        self.m_entity(m, b'Note', 1, 0x1000000000000001)
        self.m_prop(m, b'id', 6, 1, 0x1000000000000011); self.m_flags(m, 1)
        self.m_prop(m, b'text', 9, 2, 0x1000000000000012)
        self.m_prop(m, b'ts', 6, 3, 0x1000000000000013)
        self.m_lastprop(m, 3, 0x1000000000000013)
        self.m_lastent(m, 1, 0x1000000000000001)
        o = self.opt(); self.opt_dir(o, path.encode()); self.opt_model(o, m)
        if 'readers' in self.tune: self.opt_max_readers(o, 8)
        if 'maxkb' in self.tune: self.opt_max_kb(o, 10240)
        if 'notls' in self.tune: self.opt_no_tls(o, True)
        s = self.store_open(o)
        if not s: raise RuntimeError(self.err().decode())
        return s
    def create(self, path): os.makedirs(path); return self._open(path)
    def open(self, path): return self._open(path)
    def write(self, s, i):
        b = self.box(s, 1); t = self.txn_write(s)
        for j in range(ROWS):
            oid = self.id_for_put(b, 0)
            fb = self.fb.Builder(96); txt = fb.CreateString(f'note {j} of agent {i}')
            fb.StartObject(3); fb.PrependInt64Slot(0, oid, 0); fb.PrependUOffsetTRelativeSlot(1, txt, 0); fb.PrependInt64Slot(2, j, 0)
            fb.Finish(fb.EndObject()); d = bytes(fb.Output())
            if self.put(b, oid, d, len(d)): raise RuntimeError(self.err().decode())
        if self.txn_success(t): raise RuntimeError(self.err().decode())
    def read(self, s):
        n = ctypes.c_uint64(0); self.count(self.box(s, 1), 0, ctypes.byref(n)); return n.value
    def close(self, s): self.store_close(s)

# ---------------------------------------------------------------- SQL-Engines
DDL = 'create table note(id integer primary key, text text, ts integer)'
INS = 'insert into note(text, ts) values(?, ?)'
CNT = 'select count(*) from note'

class Sqlite:
    name = 'sqlite'
    def __init__(self): import apsw; self.m = apsw; self.version = 'SQLite ' + apsw.sqlitelibversion() + ' (apsw ' + apsw.apswversion() + ')'
    def create(self, path): os.makedirs(path); c = self.m.Connection(path + '/db.sqlite'); c.execute(DDL); return c
    def open(self, path): return self.m.Connection(path + '/db.sqlite')
    def write(self, c, i):
        with c: c.executemany(INS, [(f'note {j} of agent {i}', j) for j in range(ROWS)])
    def read(self, c): return c.execute(CNT).fetchall()[0][0]
    def close(self, c): c.close()

class Turso:
    name = 'turso'
    def __init__(self): import turso, importlib.metadata as md; self.m = turso; self.version = 'Turso Database (pyturso ' + md.version('pyturso') + ')'
    def create(self, path): os.makedirs(path); c = self.m.connect(path + '/db.sqlite'); c.execute(DDL); c.commit(); return c
    def open(self, path): return self.m.connect(path + '/db.sqlite')
    def write(self, c, i):
        cur = c.cursor(); cur.executemany(INS, [(f'note {j} of agent {i}', j) for j in range(ROWS)]); c.commit()
    def read(self, c): cur = c.cursor(); cur.execute(CNT); return cur.fetchall()[0][0]
    def close(self, c): c.close()

class Libsql:
    name = 'libsql'
    def __init__(self): import libsql, importlib.metadata as md; self.m = libsql; self.version = 'libSQL (libsql ' + md.version('libsql') + ')'
    def create(self, path): os.makedirs(path); c = self.m.connect(path + '/db.sqlite'); c.execute(DDL); c.commit(); return c
    def open(self, path): return self.m.connect(path + '/db.sqlite')
    def write(self, c, i):
        c.executemany(INS, [(f'note {j} of agent {i}', j) for j in range(ROWS)]); c.commit()
    def read(self, c): return c.execute(CNT).fetchall()[0][0]
    def close(self, c): c.close()

ENGINES = {'obx': Obx, 'sqlite': Sqlite, 'turso': Turso, 'libsql': Libsql}

# ---------------------------------------------------------------- Hilfen
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

# ---------------------------------------------------------------- Phasen
def anlegen(e, n):
    to, tw, tc = [], [], []; t_all = T()
    for i in range(n):
        p = path(e, i); t0 = T(); h = e.create(p); t1 = T(); e.write(h, i); t2 = T(); e.close(h); t3 = T()
        to.append(t1 - t0); tw.append(t2 - t1); tc.append(t3 - t2)
    wall = T() - t_all
    app = alloc = 0; sample = None
    for i in range(n):
        a, b, f = disk(path(e, i)); app += a; alloc += b
        if i == n // 2: sample = f
    return {'n': n, 'gesamt_je_db': stat([a + b + c for a, b, c in zip(to, tw, tc)]), 'neu_anlegen_mit_schema': stat(to), 'zehn_objekte_schreiben': stat(tw),
            'schliessen': stat(tc), 'wand_ms_je_db': round(ms(wall) / n, 4), 'platz_kb_scheinbar': round(app / n / 1024, 2), 'platz_kb_belegt': round(alloc / n / 1024, 2),
            'dateien_beispiel': sample, 'max_rss_mb': round(status('VmHWM') / 1024, 1)}

def oeffnen(e, m):
    to, tr, tc = [], [], []
    for i in range(m):
        p = path(e, i); t0 = T(); h = e.open(p); t1 = T(); c = e.read(h); t2 = T(); e.close(h); t3 = T()
        assert c == ROWS, c
        to.append(t1 - t0); tr.append(t2 - t1); tc.append(t3 - t2)
    return {'m': m, 'oeffnen': stat(to), 'erste_abfrage': stat(tr), 'schliessen': stat(tc), 'summe': stat([a + b + c for a, b, c in zip(to, tr, tc)])}

def halten(e, k):
    import gc
    hs = []; m0 = mem(); t0 = T(); fehler = None
    try:
        for i in range(k):
            h = e.open(path(e, i)); e.read(h); hs.append(h)
    except Exception as ex:
        fehler = repr(ex)[:300]
    t1 = T(); m1 = mem(); n = max(len(hs), 1)
    fds = len(os.listdir('/proc/self/fd')); thr = status('Threads'); vsz = status('VmSize')
    t2 = T()
    for h in hs: e.close(h)
    t3 = T(); offen = len(hs); hs.clear(); gc.collect(); m2 = mem()
    return {'k_gewuenscht': k, 'k_offen': offen, 'fehler': fehler,
            'rss_kb_je_db': round((m1['Rss'] - m0['Rss']) / n, 1), 'anonym_kb_je_db': round((m1['Anonymous'] - m0['Anonymous']) / n, 1),
            'pss_kb_je_db': round((m1['Pss'] - m0['Pss']) / n, 1), 'fds_je_db': round(fds / n, 2), 'threads': thr, 'virtuell_mb_je_db': round(vsz / 1024 / n, 2),
            'oeffnen_ms_je_db': round(ms(t1 - t0) / n, 4), 'schliessen_ms_je_db': round(ms(t3 - t2) / n, 4),
            'rss_mb_offen': round((m1['Rss'] - m0['Rss']) / 1024, 1), 'rss_mb_nach_schliessen': round((m2['Rss'] - m0['Rss']) / 1024, 1)}

if __name__ == '__main__':
    e = ENGINES[sys.argv[1]](); phase = sys.argv[2]; n = int(sys.argv[3])
    r = {'engine': e.name, 'version': e.version, 'phase': phase}
    r.update({'anlegen': anlegen, 'oeffnen': oeffnen, 'halten': halten}[phase](e, n))
    print(json.dumps(r, ensure_ascii=False))
