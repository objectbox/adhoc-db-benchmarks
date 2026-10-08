#!/usr/bin/env python3
"""Prueft, woher die Grenze von rund 1.000 gleichzeitig offenen ObjectBox-Stores je Prozess kommt.

Linux (glibc) erlaubt 1.024 Thread-lokale Schluessel je Prozess (PTHREAD_KEYS_MAX).
Der Test belegt vorab eine Anzahl solcher Schluessel und zaehlt, wie viele Stores sich danach oeffnen lassen.
Voraussetzung: vorher  python3 messung.py obx anlegen 3000
Achtung Arbeitsspeicher: jeder offene Store belegt rund 2 MB.
"""
import subprocess, sys
CODE = '''
import sys, ctypes, os
sys.argv = ["x"]; os.environ["OBX_TUNE"] = "{tune}"
import messung as M
libc = ctypes.CDLL("libc.so.6"); k = ctypes.c_uint()
for i in range({vorab}):
    assert libc.pthread_key_create(ctypes.byref(k), None) == 0
e = M.Obx(); n = 0; hs = []
try:
    for i in range({maximal}): hs.append(e.open(M.path(e, i))); n += 1
except Exception as ex:
    pass
print(n)
'''
def test(vorab, tune='', maximal=2500):
    r = subprocess.run([sys.executable, '-c', CODE.format(vorab=vorab, tune=tune, maximal=maximal)], capture_output=True, text=True)
    return (r.stdout.strip().splitlines() or ['abgebrochen'])[-1]
frei = subprocess.run([sys.executable, '-c', 'import ctypes\nl=ctypes.CDLL("libc.so.6");k=ctypes.c_uint();n=0\nwhile l.pthread_key_create(ctypes.byref(k),None)==0: n+=1\nprint(n)'], capture_output=True, text=True).stdout.strip()
print('freie Thread-lokale Schluessel in einem frischen Python-Prozess:', frei)
print('Standard,   0 Schluessel vorab belegt -> Stores offen:', test(0))
print('Standard, 500 Schluessel vorab belegt -> Stores offen:', test(500))
print('Standard, 900 Schluessel vorab belegt -> Stores offen:', test(900))
print('Option no_reader_thread_locals        -> Stores offen:', test(0, 'notls'))
