# Hausaufgaben-Sammler (Untis + Logineo → GoodNotes)

Holt deine offenen Hausaufgaben aus **WebUntis**, sucht im passenden **Logineo-NRW-Kurs**
die zugehörigen Aufgaben und Arbeitsblätter und legt alles als PDFs in einen Ordner pro Fach:

```
Ausgabe/
  Mathe/
    2026-10-15 S. 45 Nr. 2 - Aufgabe.pdf      ← Aufgabentext + linierte Seiten zum Bearbeiten
    2026-10-15 S. 45 Nr. 2 - Bruchrechnung.pdf ← Arbeitsblatt aus Logineo
  Deutsch/
    ...
```

Die Ordner importierst du dann in GoodNotes in den gleichnamigen Ordner.

## Einrichtung auf dem iPad (a-Shell)

1. **a-Shell** aus dem App Store installieren (kostenlos, Python ist schon dabei).
2. In der Dateien-App in **iCloud Drive** einen Ordner `Hausaufgaben` anlegen.
3. Auf GitHub den Branch `claude/homework-untis-logineo-614iyx` öffnen, *Code → Download ZIP*,
   die ZIP in der Dateien-App öffnen und aus dem Ordner `hausaufgaben` die Dateien
   `hausaufgaben.py` und `config.example.json` in `iCloud Drive/Hausaufgaben` kopieren.
4. In der Dateien-App `config.example.json` duplizieren, in `config.json` umbenennen
   und ausfüllen (siehe unten). Zum Bearbeiten z. B. in a-Shell `vim config.json`, oder
   du schickst die Werte an Claude und lässt dir die fertige Datei geben.
5. a-Shell öffnen und eingeben:
   ```
   pickFolder
   ```
   Den Ordner `Hausaufgaben` in iCloud Drive auswählen. Das musst du nur einmal machen.
   Danach kommst du mit `cd ~bookmark/Hausaufgaben` wieder hin (oder direkt `pickFolder`).
6. Starten:
   ```
   python3 hausaufgaben.py
   ```
   Untis- und Logineo-Passwort eintippen. Die PDFs landen in
   `iCloud Drive/Hausaufgaben/Ausgabe/<Fach>/`.
7. In GoodNotes den Fach-Ordner öffnen, **+ → Importieren** und die neuen PDFs auswählen.

## Automatisch jeden Tag (Kurzbefehle)

1. In a-Shell einmalig: `pickFolder` → Ordner `Hausaufgaben` wählen, dann
   `bookmark hausaufgaben`. Danach kommst du immer mit `jump hausaufgaben` in den Ordner.
2. Kurzbefehle-App → **Automation** → **+** → **Tageszeit** (z. B. 15:30, täglich)
   → **Sofort ausführen**.
3. Aktion **a-Shell → Execute Command** hinzufügen, Befehle (je eine Zeile):
   ```
   jump hausaufgaben
   export UNTIS_PASSWORT='DEIN-UNTIS-PASSWORT'
   export LOGINEO_PASSWORT='DEIN-LOGINEO-PASSWORT'
   python3 hausaufgaben.py
   ```
   Achtung: Die Passwörter stehen dann im Klartext im Kurzbefehl (nur auf deinem iPad).
4. Optional danach die Aktion **Mitteilung anzeigen** („Hausaufgaben aktualisiert“).

## config.json ausfüllen

1. `config.example.json` nach `config.json` kopieren und ausfüllen:
   - `untis.server`: der Teil aus der WebUntis-Adresse, z. B. `remigianum.webuntis.com`.
   - `untis.schule`: darf leer bleiben, dann sucht das Skript den Schulnamen selbst.
   - `logineo.url`: die Adresse eurer Logineo-LMS-Seite (ohne `/my/` am Ende).
   - `faecher`: das Untis-Fachkürzel (z. B. `M`) → GoodNotes-Ordnername und ein Teil
     des Logineo-Kursnamens (oder eine Liste mehrerer Suchbegriffe). Findet das Skript
     einen Kurs nicht, listet es deine Logineo-Kurse auf.
   - `ausgabe_ordner`: am besten ein Ordner in iCloud Drive, dann siehst du die Dateien
     direkt in GoodNotes beim Importieren.
2. **Passwörter kommen nicht in die Datei.** Das Skript fragt sie beim Start ab
   (oder liest sie aus `UNTIS_PASSWORT` / `LOGINEO_PASSWORT`). `config.json` wird nicht
   mit ins Git hochgeladen.

## Benutzen

```
python3 hausaufgaben.py              # Hausaufgaben der nächsten 7 Tage
python3 hausaufgaben.py --tage 14
python3 hausaufgaben.py --ohne-logineo
```

Bereits vorhandene Dateien werden nicht überschrieben (`--ueberschreiben` erzwingt es).

**Aufräumen:** Nach dem Import in GoodNotes kannst du die Dateien in der Dateien-App löschen.
Das Skript merkt sich in `Ausgabe/.verlauf.json`, was es schon geliefert hat, und lädt
gelöschte Dateien nicht erneut. Dateien, deren Fälligkeitsdatum vorbei ist, löscht es
selbst (abschaltbar mit `"aufraeumen": false` in `config.json`).

## Grenzen

- Untis-Login mit Benutzername/Passwort. Wenn deine Schule nur Anmeldung per
  QR-Code/SSO erlaubt, klappt der Untis-Teil nicht.
- Logineo wird wie die Moodle-App angesprochen (`moodle_mobile_app`). Ist die bei
  eurer Schule abgeschaltet, nutze `--ohne-logineo`.
- Logineo-Dateien werden zugeordnet, wenn sie zwischen „aufgegeben“ und „fällig“
  hochgeladen wurden. Das ist eine Schätzung. Prüf also kurz, ob das Richtige dabei ist.
- Bearbeiten musst du die Aufgaben selbst. Bei Fragen zu einer Aufgabe kannst du
  Claude das PDF schicken und dir den Stoff erklären lassen.

## Tests

```
python3 -m unittest discover -s tests
```
