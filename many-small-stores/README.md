# Messung: 100.000 kleine Stores je Engine, ObjectBox bis 500.000

Stand 06.10.2026 · intern, bis die Ergebnisse geprüft sind · gemessen in einer Cloud-Sandbox. Baut auf der Erstmessung vom 05.10. auf (`2026_10_05_Erstmessung_Eine_DB_pro_Agent.md`, 10.000 Stores) und bestätigt sie.

## Ergebnis in drei Sätzen

Eine ObjectBox-Datenbank anlegen und zehn Objekte schreiben dauert gut 2 ms, ein Store kostet im Leerlauf 24 KB Platte, öffnen, abfragen und schließen bleibt im Median unter einer Millisekunde – auch bei 500.000 Stores. Gegen Turso Database liegt ObjectBox beim Öffnen und beim Arbeitsspeicher vorn. Gegen SQLite liegt ObjectBox beim Arbeitsspeicher vorn (mit einer Allokator-Zeile), beim Platz und beim Öffnen hinten.

## 100.000 Stores je Engine, Standardwerte

| | ObjectBox 5.3.2 | SQLite 3.53.4 | Turso Database 0.8.1 | libSQL 0.1.11 |
|---|---|---|---|---|
| Anlegen, zehn Objekte schreiben, schließen (Median) | 2,24 ms | 2,29 ms | 3,66 ms | 2,38 ms |
| dasselbe, p99 | 4,72 ms | 5,44 ms | 6,86 ms | 5,41 ms |
| Stores je Sekunde | 422 | 403 | 262 | 392 |
| Platz je Store, Dateien | 24 KB | 8 KB | 8 KB | 8 KB |
| Platz für alle 100.000, mit Verzeichnissen | 2,67 GB | 1,15 GB | 1,15 GB | 1,15 GB |
| Öffnen, abfragen, schließen (Median) | 0,34 ms | 0,05 ms | 1,19 ms | 0,08 ms |
| dasselbe, p99 | 0,63 ms | 0,13 ms | 2,59 ms | 0,21 ms |
| dasselbe ohne Seitencache (Median) | 0,77 ms | 0,18 ms | 1,38 ms | 0,22 ms |
| dasselbe ohne Seitencache, p99 | 1,65 ms | 0,69 ms | 2,72 ms | 0,75 ms |
| Arbeitsspeicher je offenem Store (1.000 offen) | 2.082 KB | 152 KB | 2.135 KB | 163 KB |
| Dateideskriptoren je offenem Store | 3 | 1 | 2 | 1 |

## Dieselben 100.000 Stores, mit einer Allokator-Zeile im Messprogramm

`mallopt(M_MMAP_THRESHOLD, 131072)`, gesetzt für alle Engines gleich.

| | ObjectBox | SQLite | Turso Database | libSQL |
|---|---|---|---|---|
| Anlegen, schreiben, schließen (Median) | 2,08 ms | 2,43 ms | 3,73 ms | 2,73 ms |
| Stores je Sekunde | 452 | 381 | 255 | 344 |
| Öffnen, abfragen, schließen (Median) | 0,10 ms | 0,06 ms | 1,24 ms | 0,09 ms |
| dasselbe, p99 | 0,36 ms | 0,17 ms | 2,83 ms | 0,23 ms |
| dasselbe ohne Seitencache (Median) | 0,35 ms | 0,19 ms | 1,46 ms | 0,24 ms |
| Arbeitsspeicher je offenem Store | 39 KB | 152 KB | 2.135 KB | 163 KB |

## ObjectBox allein, 500.000 Stores

| | Standardwerte | mit Allokator-Zeile |
|---|---|---|
| Anlegen, schreiben, schließen (Median) | 2,24 ms | 1,83 ms |
| Stores je Sekunde | 422 | 510 |
| Dauer für alle 500.000 | 19 min 46 s | 16 min 21 s |
| Platz für alle 500.000, mit Verzeichnissen | 13,37 GB | 13,37 GB |
| Öffnen, abfragen, schließen (Median) | 0,81 ms | 0,38 ms |
| dasselbe, p99 | 2,56 ms | 1,72 ms |
| dasselbe nach geleertem Seitencache (Median) | 0,91 ms | 0,49 ms |
| Arbeitsspeicher je offenem Store | 2.082 KB | 39 KB |

Das Anlegen wächst linear: 422 Stores je Sekunde bei 100.000 wie bei 500.000. Das Öffnen ist bei 500.000 langsamer als bei 100.000, weil 13,4 GB Daten nicht in die 8 GB Arbeitsspeicher der Maschine passen – ein zufällig gewählter Store liegt dann meist nicht im Seitencache und wird von der Platte gelesen.

## Was gemessen wurde

- Je Store ein eigenes Verzeichnis, ein Schema mit einer Tabelle bzw. einem Typ (`id`, `text`, `ts`), zehn kleine Einträge in einer Transaktion.
- Anlegen: alle Stores nacheinander, ein Prozess, ein Lauf.
- Öffnen, abfragen, schließen: 10.000 zufällig gewählte Stores, eine Zählabfrage je Store. Drei Läufe mit verschiedenen Stichproben; die Tabelle zeigt den Median der drei Läufe. „Ohne Seitencache" heißt: vor jedem Lauf `sync` und `drop_caches`.
- Arbeitsspeicher: 1.000 zufällige Stores gleichzeitig offen, Zuwachs des belegten Speichers (RSS) geteilt durch 1.000.
- Jede Phase läuft in einem eigenen Prozess.

## Vorbehalte

1. **Kleine Stores.** Zehn kurze Einträge je Store. Das zeigt die Fixkosten einer Datenbank, nicht das Verhalten mit echten Agentendaten (Nachrichten, Vektoren). Das realistische Profil steht noch aus.
2. **Python als Messrahmen.** ObjectBox wird über die C-API angesprochen (ctypes), SQLite über apsw, Turso Database über pyturso, libSQL über das Paket libsql. Der Aufwand der Anbindungen ist verschieden und steckt in den Zeiten.
3. **Turso Database ist die lokale Engine in Version 0.8.1**, nicht der Cloud-Dienst Turso. Über den Dienst sagt die Messung nichts.
4. **Standardwerte für Dauerhaftigkeit.** Jede Engine schreibt so sicher, wie sie es ohne Einstellung tut. Das ist nicht bei allen gleich und beeinflusst das Anlegen.
5. **Eine virtuelle Maschine.** 2 Kerne, 8 GB Arbeitsspeicher, virtuelle Platte (ext4). Absolute Zeiten gelten für diese Maschine; die Verhältnisse zwischen den Engines sind das Belastbare.
6. **Ein Prozess, ein Thread.** Keine parallelen Zugriffe.
7. **Die Allokator-Zeile** ändert nichts an den Engines. Sie legt fest, dass glibc Speicherblöcke ab 128 KB getrennt anfordert, sodass ungenutzte Teile keinen Speicher belegen. ObjectBox profitiert, weil LMDB beim Öffnen zwei Listen von zusammen 3 MiB anlegt, die ein lesender Store nie beschreibt. Bei Turso Database ändert die Zeile nichts.
8. **Grenze bei ObjectBox:** Mit Standardwerten lassen sich 1.022 Stores gleichzeitig in einem Prozess offen halten (ein Thread-lokaler Schlüssel je Store, Linux erlaubt 1.024). Die Option `no_reader_thread_locals` hebt das auf; sie ist hier nicht verwendet. Gemessen am 05.10.
9. **Platz bei ObjectBox:** `data.mdb` 20 KB (5 Seiten) und `lock.mdb` 8 KB scheinbar, 4 KB belegt. Die SQL-Engines kommen mit zwei Seiten aus. Auf der Platte sind es bei ObjectBox **zwei Dateien** je Store. Die Zeile „Dateideskriptoren je offenem Store: 3" zählt offene Zugriffe, nicht Dateien: LMDB öffnet `data.mdb` zweimal (einmal normal, einmal mit O_DSYNC für die Meta-Seiten) und `lock.mdb` einmal. Am 06.10. an einem offenen Store nachgeprüft.

## Nachstellen

```
./lauf_gross.sh 100000 10000 1000 "obx sqlite turso libsql" ergebnisse_gross.jsonl
MESS_ROOT=data_500k ./lauf_gross.sh 500000 10000 1000 "obx" ergebnisse_gross_500k.jsonl
python3 auswertung_gross.py ergebnisse_gross.jsonl ergebnisse_gross_500k.jsonl
```

Braucht root (für `drop_caches`), `libobjectbox.so` 5.3.2 unter `obxc/lib/`, Python 3.11 mit `apsw 3.53.4.0`, `pyturso 0.8.1`, `libsql 0.1.11`, `flatbuffers 24.3.25`. Dateien im Ordner: `messung.py` (Engine-Klassen), `messung_gross.py`, `lauf_gross.sh`, `auswertung_gross.py`, Rohdaten `ergebnisse_gross.jsonl` und `ergebnisse_gross_500k.jsonl`, Protokolle `lauf_gross.log` und `lauf_gross_500k.log`, `umgebung_gross.txt`.

Laufzeiten: 100.000 je Engine in beiden Einstellungen 46 Minuten (16:36–17:22 UTC), ObjectBox 500.000 in beiden Einstellungen 43 Minuten (17:28–18:11 UTC). Keine Fehler.
