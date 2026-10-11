"""Profiles the create phase of obx_cached with the large workload: per-step timing of create, write (split into
the two C calls of Box.put and the Python FlatBuffers marshalling in between) and close.
Usage (from the repository root): BENCH_WORKLOAD=large BENCH_ROOT=<dir> .venv/bin/python 2026_10_11_large_workload/profile_create.py <n> [cprofile]"""
import cProfile, os, pstats, statistics, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
import measure as m
import objectbox.box as obox
from objectbox.c import obx_box_ids_for_put, obx_box_put_many

n = int(sys.argv[1]); e = m.ObxCached(); T = time.perf_counter_ns
steps = {k: [] for k in ('makedirs+open', 'build objects', 'ids_for_put (C)', 'FlatBuffers marshalling (Python)', 'put_many (C)', 'close', 'total')}

# Wrap the two C calls used by Box._put_many to time them separately; the rest of _put_many is marshalling
def timed(fn, key):
    def w(*a):
        t = T(); r = fn(*a); steps[key].append(T() - t); return r
    return w
obox.obx_box_ids_for_put = timed(obx_box_ids_for_put, 'ids_for_put (C)')
obox.obx_box_put_many = timed(obx_box_put_many, 'put_many (C)')

def run():
    for i in range(n):
        t0 = T(); s = e.create(m.path(e, i)); t1 = T()
        objs = [e.Note(text=text, ts=ts) for text, ts in m.rows(i)]; t2 = T()
        s.box(e.Note).put(objs); t3 = T()
        s.close(); t4 = T()
        steps['makedirs+open'].append(t1 - t0); steps['build objects'].append(t2 - t1)
        steps['FlatBuffers marshalling (Python)'].append((t3 - t2) - steps['ids_for_put (C)'][-1] - steps['put_many (C)'][-1])
        steps['close'].append(t4 - t3); steps['total'].append(t4 - t0)

e.create(m.path(e, n)).close()  # warm-up: model synced, libraries loaded (not counted)
if len(sys.argv) > 2:
    profile = cProfile.Profile(); profile.runcall(run)
    pstats.Stats(profile).sort_stats('tottime').print_stats(15)
else:
    run()
tot = statistics.median(steps['total'])
for k, v in steps.items():
    md = statistics.median(v) / 1e6
    print(f'{k:32s} median {md:7.3f} ms  mean {statistics.mean(v) / 1e6:7.3f} ms  {100 * statistics.median(v) / tot:5.1f} %')
