# Hausaufgaben-Sammler

The project is now the homework collector in `hausaufgaben/`: a stdlib-only Python script that
reads homework from WebUntis, matching assignments/files from Logineo NRW (Moodle web services),
and writes per-subject PDFs to import into GoodNotes. Docs (German) in `hausaufgaben/README.md`.

- Keep it Python-stdlib-only so it runs on the iPad (a-Shell / Pythonista).
- Never store passwords: they come from `UNTIS_PASSWORT` / `LOGINEO_PASSWORT` or a prompt.
  `config.json` is git-ignored; only `config.example.json` with placeholders is committed.
- Tests: `cd hausaufgaben && python3 -m unittest discover -s tests`.

The user runs it on an iPad with a-Shell from a folder in iCloud Drive (see README).

The old Mensch-Radar PWA was removed from this branch; it still lives on branch
`claude/radar-app-person-detection-6xh9fq`, which GitHub Pages serves.
