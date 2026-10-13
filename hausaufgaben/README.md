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

## Einrichtung

1. Python 3 installieren. Auf dem iPad geht das mit **a-Shell** (kostenlos) oder **Pythonista**.
2. `config.example.json` nach `config.json` kopieren und ausfüllen:
   - `untis.server` und `untis.schule`: steht in der Untis-App unter *Profil → Schule*
     oder in der Adresszeile von WebUntis (`https://SERVER.webuntis.com/WebUntis/?school=SCHULNAME`).
   - `logineo.url`: die Adresse eurer Logineo-LMS-Seite (ohne `/my/` am Ende).
   - `faecher`: das Untis-Fachkürzel (z. B. `M`) → GoodNotes-Ordnername und ein Teil
     des Logineo-Kursnamens.
   - `ausgabe_ordner`: am besten ein Ordner in iCloud Drive, dann siehst du die Dateien
     direkt in GoodNotes beim Importieren.
3. **Passwörter kommen nicht in die Datei.** Das Skript fragt sie beim Start ab
   (oder liest sie aus `UNTIS_PASSWORT` / `LOGINEO_PASSWORT`). `config.json` wird nicht
   mit ins Git hochgeladen.

## Benutzen

```
python3 hausaufgaben.py              # Hausaufgaben der nächsten 7 Tage
python3 hausaufgaben.py --tage 14
python3 hausaufgaben.py --ohne-logineo
```

Bereits vorhandene Dateien werden nicht überschrieben (`--ueberschreiben` erzwingt es).

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
