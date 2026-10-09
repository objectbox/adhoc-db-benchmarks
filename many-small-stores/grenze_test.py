#!/usr/bin/env python3
"""Checks where the limit of about 1,000 simultaneously open ObjectBox stores per process comes from.

Linux (glibc) allows 1,024 thread-local keys per process (PTHREAD_KEYS_MAX).
The test pre-allocates a number of such keys and counts how many stores can be opened afterwards.
Prerequisite: first  python3 messung.py obx create 3000
Watch memory: each open store takes about 2 MB.
"""
import subprocess, sys
CODE = '''
import sys, ctypes, os
sys.argv = ["x"]; os.environ["OBX_TUNE"] = "{tune}"
import messung as M
libc = ctypes.CDLL("libc.so.6"); k = ctypes.c_uint()
for i in range({preallocated}):
    assert libc.pthread_key_create(ctypes.byref(k), None) == 0
e = M.Obx(); n = 0; hs = []
try:
    for i in range({limit}): hs.append(e.open(M.path(e, i))); n += 1
except Exception as ex:
    pass
print(n)
'''
def test(preallocated, tune='', limit=2500):
    r = subprocess.run([sys.executable, '-c', CODE.format(preallocated=preallocated, tune=tune, limit=limit)], capture_output=True, text=True)
    return (r.stdout.strip().splitlines() or ['aborted'])[-1]
free = subprocess.run([sys.executable, '-c', 'import ctypes\nl=ctypes.CDLL("libc.so.6");k=ctypes.c_uint();n=0\nwhile l.pthread_key_create(ctypes.byref(k),None)==0: n+=1\nprint(n)'], capture_output=True, text=True).stdout.strip()
print('free thread-local keys in a fresh Python process:', free)
print('default,   0 keys pre-allocated -> stores open:', test(0))
print('default, 500 keys pre-allocated -> stores open:', test(500))
print('default, 900 keys pre-allocated -> stores open:', test(900))
print('option no_reader_thread_locals  -> stores open:', test(0, 'notls'))
