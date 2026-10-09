# Eine Datenbank pro Agent – Messung ObjectBox, SQLite, Turso, libSQL

Stand 05.10.2026, dritte Fassung (nach einer Rückfrage zum Arbeitsspeicher) · intern · eine Messung auf einem Rechner, kein Benchmark · nichts davon für außen. Die Deutung muss noch geprüft werden.

Frühere Fassungen vom selben Tag liegen unter `_to_delete_erste_Fassung/` (Python-Paket 4.0.0, nur ObjectBox gegen SQLite; Zahlen überholt, Vermutung zur Grenze falsch) und `_to_delete_zweite_Fassung/` (dort stand noch, der Arbeitsspeicher sei bei ObjectBox der Kostentreiber – das ist mit Abschnitt 3 überholt).

## 1 Anlass

Supabase hat Turso übernommen (02.10.2026, turso.tech/blog/turso-is-joining-supabase). Tursos These: „One agent, one task, one user" – die Economics müssen bei Millionen Datenbanken funktionieren. Viviens Frage: Wie viel Zeit und Kosten verursacht eine Datenbank, und liegt ObjectBox dabei in derselben Größenordnung wie Turso?

## 2 Ergebnis

Median aus drei Läufen. Je Datenbank ein Objekttyp mit zehn kleinen Objekten.

| | ObjectBox 5.3.2 | SQLite 3.53.4 | Turso Database 0.8.1 | libSQL 0.1.11 |
|---|---|---|---|---|
| Neu anlegen mit zehn Objekten | 2,5 ms | 2,9 ms | 3,8 ms | 2,6 ms |
| Platz je Datenbank | 28 KB | 8 KB | 8 KB | 8 KB |
| Öffnen | 0,36 ms | 0,02 ms | 0,55 ms | 0,05 ms |
| Erste Abfrage | 0,02 ms | 0,02 ms | 0,14 ms | 0,03 ms |
| Schließen | 0,02 ms | 0,01 ms | 0,48 ms | 0,01 ms |
| Summe öffnen, abfragen, schließen | 0,40 ms | 0,06 ms | 1,20 ms | 0,10 ms |
| Dieselbe Summe mit geleertem Dateicache | 0,75 ms | 0,25 ms | 1,29 ms | 0,21 ms |
| Arbeitsspeicher je offener Datenbank, Standard | 2,1 MB | 0,15 MB | 2,1 MB | 0,16 MB |
| Arbeitsspeicher mit Allokator-Einstellung (siehe unten) | **0,04 MB** | 0,15 MB | 2,1 MB | 0,16 MB |
| Gleichzeitig offen in einem Prozess | 1.022; mit Option und Allokator-Einstellung 6.000 geprüft | 5.000 geprüft | 2.500 geprüft | 5.000 geprüft |

Turso hat zwei Engines: **Turso Database** ist die neue, in Rust geschriebene; **libSQL** ist der ältere SQLite-Fork. Welche von beiden in Turso Cloud läuft, habe ich nicht geprüft.

## 3 Erklärungen

**Anlegen.** Alle vier liegen zwischen 2,3 und 3,9 ms. Die Unterschiede zwischen ObjectBox, SQLite und libSQL sind kleiner als die Streuung zwischen den Läufen (SQLite: 2,3 bis 2,9 ms). Turso Database ist klar am langsamsten.

**Platz.** ObjectBox legt zwei Dateien an: `data.mdb` (20 KB = 5 Seiten zu 4 KB) und `lock.mdb` (8 KB = 2 Seiten, davon 4 KB tatsächlich belegt). Die anderen kommen mit 8 KB aus. Stufen bei ObjectBox (Seitengröße 4 KB): nur mit Modell geöffnet, keine Objekte: `data.mdb` 3 Seiten (12 KB) · 1 oder 10 Objekte: 5 Seiten (20 KB) · 100 Objekte: 8 Seiten (32 KB) · 1.000 Objekte: 28 Seiten (112 KB). `lock.mdb` bleibt bei 8 KB. Erwartet waren auf Linux 8 KB; macOS (16-KB-Seiten) ist nicht gemessen. Eine Million ruhende Datenbanken wären 28 GB gegenüber 8 GB – beides auf Objektspeicher ein kleiner Betrag.

**Öffnen und Schließen.** SQLite und libSQL öffnen „faul": Beim Öffnen passiert fast nichts, die Datei wird erst bei der ersten Abfrage gelesen. Vergleichbar ist deshalb nur die Summe. ObjectBox braucht 0,40 ms und ist damit dreimal so schnell wie Turso Database und siebenmal so langsam wie SQLite. Schließen kostet bei ObjectBox 0,02 ms, bei Turso Database 0,48 ms (vermutlich räumt es dabei sein Schreibprotokoll auf; nicht geprüft). Bei ObjectBox muss bei jedem Öffnen das Datenmodell mitgegeben werden; das ist in der Öffnen-Zeit enthalten.

**Arbeitsspeicher.** Mit Standardeinstellungen wächst der Prozess je offenem ObjectBox-Store um 2,08 MB. Das ist geprüft, aber es ist kein Speicher, den ObjectBox braucht:
- **Der Anstieg ist echt und linear.** Der erste Store kostet 0,16 MB anonymen Speicher, jeder weitere 2,06 MB (gemessen bei 10, 100, 250, 500, 1.000, 1.500 und 2.500 offenen Stores). Bei rund 2.900 Stores hat der Kernel den Prozess mit 6,06 GB belegtem Speicher beendet.
- **Es ist nicht die mmap-Datei.** Von den 2.082 KB entfallen 16 KB auf `data.mdb` und 4 KB auf `lock.mdb`. Die übrigen 2.062 KB liegen im Heap des Prozesses. Die 1 GB virtuelle Abbildung je Store zählt nicht mit.
- **Ursache:** Beim Öffnen werden zwei große Blöcke angefordert, zusammen 3.080 KB (vermutlich 2 MiB und 1 MiB; welche das sind, ist noch offen). Mit Standardeinstellungen legt glibc sie in den Heap, und der größere wird dabei genullt – dadurch ist er belegt, obwohl ihn bei winzigen Datenbanken niemand benutzt.
- **Mit einer Einstellung des Allokators fällt das weg.** Die Umgebungsvariable `MALLOC_MMAP_THRESHOLD_=131072` lässt glibc große Blöcke immer per mmap holen; unbenutzte Seiten bleiben dann unbelegt. Ergebnis: **39 KB je offenem Store** (18 KB anonym, 20 KB Datei) statt 2.082 KB. Geprüft bis 6.000 gleichzeitig offene Stores (zusammen mit `no_reader_thread_locals`); dort begrenzen dann die Dateideskriptoren (drei je Store). Öffnen, abfragen, schließen sinkt dabei von 0,38 auf 0,13 ms.
- **Die anderen drei ändern sich mit derselben Einstellung nicht:** SQLite 153 KB, Turso Database 2.136 KB, libSQL 163 KB. In 1 GB passen damit rund 26.000 offene ObjectBox-Stores, rund 6.800 SQLite- und rund 490 Turso-Datenbanken.
- **Nicht geprüft:** ob die Einstellung unter Schreiblast Nachteile hat, und wie viel von den Blöcken bei echten Datenmengen tatsächlich belegt wird. Drei Optionen der C-API (`max_readers`, `max_db_size_in_kb`, `no_reader_thread_locals`) ändern am Standardwert nichts.
- Ohne die Einstellung wird der Speicher nach dem Schließen für den nächsten Store wiederverwendet, geht aber erst nach `malloc_trim` an das Betriebssystem zurück.

**Grenze bei 1.022.** Die Ursache ist gefunden: Linux erlaubt je Prozess 1.024 Thread-lokale Schlüssel, und ObjectBox belegt mit Standardeinstellungen einen je offenem Store. Geprüft durch Vorbelegen: mit 500 belegten Schlüsseln lassen sich 522 Stores öffnen, mit 900 belegten 122. Die Option `no_reader_thread_locals` hebt die Grenze auf (2.500 Stores ohne Fehler geöffnet). Das ist keine Eigenheit meiner Testumgebung, sondern gilt auf Linux allgemein. Meine erste Vermutung (Grenze für gesperrten Speicher) war falsch: Halbieren dieser Grenze änderte nichts.

**Was daraus folgt.**
1. Je Datenbank liegt ObjectBox mindestens in der Größenordnung von Tursos neuer Engine: schneller beim Anlegen, Öffnen und Schließen, größer auf der Platte.
2. Zeit ist kein Thema. Öffnen, abfragen und schließen bleibt überall unter 1,3 ms.
3. Der Arbeitsspeicher ist bei ObjectBox kein grundsätzliches Problem: Mit einer Allokator-Einstellung braucht ein offener Store 39 KB und damit ein Viertel von SQLite und ein Fünfzigstel von Turso Database. Mit Standardeinstellungen sind es 2,1 MB.
4. Auf den Anwendungsfall optimiert ist noch nichts. Die beiden Einstellungen hier sind von außen gesetzt; ob man sie in ObjectBox selbst lösen sollte, ist eine offene Frage.

## 4 Vorbehalte

- **Ein Rechner, drei Läufe.** Cloud-VM mit 2 virtuellen Kernen (Xeon 2,1 GHz), 8 GB RAM, Linux 6.18, ext4 auf virtueller Platte. Je Lauf 10.000 Datenbanken angelegt, 2.000 nacheinander geöffnet, 1.000 gleichzeitig offen gehalten. Die Spannen stehen in `ergebnisse.jsonl`.
- **Winzige Datenbanken.** Zehn kleine Objekte. Das sagt nichts über größere Datenmengen, parallele Zugriffe, Abfragen, Vektorsuche oder Sync.
- **Standardeinstellungen, nicht angeglichen.** SQLite und libSQL liefen mit Rollback-Journal und `synchronous=FULL`, Turso Database mit WAL und `synchronous=FULL`, ObjectBox mit seinen Standardwerten (welche Dauerhaftigkeit die bedeuten, habe ich nicht geprüft). Auf einer virtuellen Platte kann das Sichern auf die Platte unrealistisch schnell sein.
- **Alles über Python.** ObjectBox über die offizielle C-API mit einer selbst geschriebenen dünnen Hülle (`ctypes`), weil das Python-Paket auf PyPI (4.0.0, Mai 2024) einen alten Kern bündelt. Das ist kein offizielles Binding. Der Python-Anteil kostet bei allen vier etwas Zeit.
- **„Geleerter Dateicache"** heißt: Der Zwischenspeicher von Linux wurde geleert. Der Rechner darunter kann die Dateien trotzdem noch vorhalten. Ein echter Kaltstart aus Objektspeicher ist das nicht.
- **Arbeitsspeicher** ist der Zuwachs des Prozesses (RSS) bei 1.000 offenen Datenbanken, jede einmal abgefragt. Bei Turso Database habe ich keine eigene Option probiert, bei ObjectBox drei; die Allokator-Einstellung lief bei allen vieren.
- **Turso Cloud ist nicht gemessen.** Was eine Datenbank Turso im Betrieb kostet, sieht man von außen nicht. Turso beschreibt seinen Dienst als „diskless" mit WAL auf S3; das ist ein anderer Aufbau als lokale Dateien.
- **Nicht gemessen:** ObjectBox 6.0 beta, andere Betriebssysteme, andere Sprachen.

## 5 Versionen

| | Version | veröffentlicht | Quelle |
|---|---|---|---|
| ObjectBox C/C++ | 5.3.2 (letzte stabile; 6.0.0 beta nicht verwendet) | 05.05.2026 | github.com/objectbox/objectbox-c/releases |
| SQLite | 3.53.4, über apsw 3.53.4.0 | 24.07.2026 | sqlite.org/chronology.html |
| Turso Database | pyturso 0.8.1 | 29.09.2026 | pypi.org/project/pyturso |
| libSQL | libsql 0.1.11 | 02.09.2025 | pypi.org/project/libsql |

Bei Turso zeigt die GitHub-Seite 0.7.0 als „Latest", PyPI aber 0.8.1. Verwendet ist die Fassung von PyPI.

## 6 Offene Fragen

1. Welche zwei Blöcke (zusammen 3.080 KB) werden beim Öffnen angefordert, und ließen sie sich kleiner oder erst bei Bedarf anlegen?
2. Hat `MALLOC_MMAP_THRESHOLD_` unter echter Last Nachteile, oder wäre ein anderer Weg sauberer?
3. Ist `no_reader_thread_locals` für einen Dienst mit vielen Stores unbedenklich?
4. Braucht ein Store `lock.mdb`, wenn nur ein Prozess zugreift?
5. Passen die Zahlen zu dem, was von der C-Bibliothek zu erwarten ist?

## 7 Nachstellen

Voraussetzung: Linux, Python 3, `pip install apsw pyturso libsql flatbuffers`, dazu `objectbox-linux-x64.tar.gz` (5.3.2) nach `obxc/` entpackt.

- `./lauf.sh <Laufnummer>` – ein kompletter Lauf über alle vier Engines (für den Lauf mit geleertem Dateicache als root).
- `python3 auswertung.py` – fasst `ergebnisse.jsonl` zusammen.
- `python3 grenze_test.py` – der Test zur Grenze bei 1.022.
- `OBX_TUNE=readers,maxkb,notls python3 messung.py obx halten 200` – die drei Optionen.
- `python3 ram_pruefung.py 1000` – Arbeitsspeicher stufenweise, nach Speicherbereich und aus Sicht des Allokators. Mit `MALLOC_MMAP_THRESHOLD_=131072` davor für die Allokator-Einstellung.
- `MALLOC_MMAP_THRESHOLD_=131072 OBX_TUNE=notls python3 messung.py obx halten 6000` – 6.000 gleichzeitig offene Stores.
