import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hausaufgaben as h  # noqa: E402


class Tests(unittest.TestCase):
    def test_html_zu_text(self):
        self.assertEqual(h.html_zu_text("<p>S. 12 Nr.&nbsp;3</p><p>a<br>b</p>"),
                         "S. 12 Nr. 3\na\nb")

    def test_dateiname(self):
        self.assertEqual(h.dateiname('AB: "Brüche"/Teil 2?'), "AB Brüche Teil 2")
        self.assertEqual(h.dateiname("   "), "Ohne Titel")
        self.assertLessEqual(len(h.dateiname("wort " * 30)), 60)

    def test_parse_untis(self):
        daten = {
            "lessons": [{"id": 7, "subject": "M"}],
            "homeworks": [
                {"id": 1, "lessonId": 7, "date": 20261012, "dueDate": 20261015,
                 "text": "S. 45 Nr. 2", "remark": "", "completed": False},
                {"id": 2, "lessonId": 99, "date": 20261012, "dueDate": 20261014,
                 "text": "Lesen", "remark": "Kap. 3", "completed": True},
            ],
        }
        hw = h.parse_untis_hausaufgaben(daten)
        self.assertEqual([x["id"] for x in hw], [2, 1])
        self.assertEqual(hw[0]["fach"], "Sonstiges")
        self.assertIn("Bemerkung: Kap. 3", hw[0]["text"])
        self.assertEqual(hw[1]["faellig"], dt.date(2026, 10, 15))

    def test_moodle_params(self):
        self.assertEqual(h.moodle_params({"courseids": [3, 5], "x": 1}),
                         {"courseids[0]": 3, "courseids[1]": 5, "x": 1})

    def test_finde_kurs(self):
        kurse = [{"id": 1, "shortname": "D-10b", "fullname": "Deutsch 10b"},
                 {"id": 2, "shortname": "M-10b", "fullname": "Mathematik 10b"}]
        self.assertEqual(h.finde_kurs(kurse, "mathematik")["id"], 2)
        self.assertIsNone(h.finde_kurs(kurse, "Physik"))
        self.assertEqual(h.finde_kurs(kurse, ["Physik", "Deutsch"])["id"], 1)

    def test_pdf(self):
        pdf = h.aufgaben_pdf("M: Hausaufgabe", ["Fällig: 15.10.2026"],
                             "Löse (a) und \\b)\n" + "lang " * 2000)
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertGreater(pdf.count(b"/Type /Page "), 2)
        # xref-Offsets muessen auf die Objekte zeigen
        xref = int(pdf.rsplit(b"startxref\n", 1)[1].split(b"\n")[0])
        eintraege = pdf[xref:].split(b"\n")[3:]
        for i, e in enumerate(eintraege, 1):
            if not e.endswith(b" n "):
                break
            self.assertTrue(pdf[int(e[:10]):].startswith(b"%d 0 obj" % i))

    def test_schule_suchen(self):
        from unittest import mock
        antwort = {"result": {"schools": [
            {"server": "andere.webuntis.com", "displayName": "A", "loginName": "a"},
            {"server": "remigianum.webuntis.com", "displayName": "Remi", "loginName": "Gym Remigianum"},
        ]}}
        with mock.patch.object(h.Http, "json", return_value=antwort):
            self.assertEqual(h.Untis.schule_suchen("remigianum.webuntis.com"), "Gym Remigianum")
        with mock.patch.object(h.Http, "json", return_value={"result": {"schools": []}}):
            with self.assertRaises(RuntimeError):
                h.Untis.schule_suchen("remigianum.webuntis.com")

    def test_einrichten(self):
        import json, shutil, tempfile
        from unittest import mock
        tmp = tempfile.mkdtemp()
        shutil.copy(os.path.join(os.path.dirname(h.__file__), "config.example.json"), tmp)
        pfad = os.path.join(tmp, "config.json")
        with mock.patch("builtins.input", side_effect=["untis.user", "", "logineo.user"]), \
             mock.patch("builtins.print"):
            k = h.lade_konfig(pfad)
        self.assertEqual(k["untis"]["benutzer"], "untis.user")
        with open(pfad) as f:
            k = json.load(f)
        self.assertEqual(k["logineo"]["benutzer"], "logineo.user")
        # fehlender Name in vorhandener config wird nachgefragt
        k["logineo"]["benutzer"] = ""
        with open(pfad, "w") as f:
            json.dump(k, f)
        with mock.patch("builtins.input", side_effect=["neu"]), mock.patch("builtins.print"):
            self.assertEqual(h.lade_konfig(pfad)["logineo"]["benutzer"], "neu")

    def test_passwort_datei(self):
        import tempfile
        from unittest import mock
        datei = os.path.join(tempfile.mkdtemp(), "pw.json")
        with mock.patch.object(h, "PASSWORT_DATEI", datei), \
             mock.patch.object(h, "eingabe_verdeckt", side_effect=["u-pw", "l-pw"]), \
             mock.patch("builtins.print"), mock.patch.dict(os.environ, {}, clear=True):
            h.passwoerter_speichern()
            self.assertEqual(oct(os.stat(datei).st_mode & 0o777), "0o600")
            self.assertEqual(h.passwort("UNTIS_PASSWORT", "x"), "u-pw")
            self.assertEqual(h.passwort("LOGINEO_PASSWORT", "x"), "l-pw")

    def test_kurs_material(self):
        import tempfile
        from unittest import mock
        tmp = tempfile.mkdtemp()
        konfig = {"logineo": {"url": "https://l", "benutzer": "u"},
                  "faecher": {"EK": {"ordner": "Erdkunde", "logineo_kurs": ["Erdkunde"]}}}
        dateien = [{"name": "Klima.pdf", "url": "https://l/1", "zeit": 0, "modul": "AB",
                    "abschnitt": "Thema 1: Klima"}]
        aufgaben = [{"id": 1, "name": "Referat", "duedate": 0, "intro": "<p>Vorbereiten</p>",
                     "introattachments": [{"filename": "info.pdf", "fileurl": "https://l/2"}]}]
        with mock.patch.dict(os.environ, {"LOGINEO_PASSWORT": "p"}), \
             mock.patch.object(h.Logineo, "anmelden"), \
             mock.patch.object(h.Logineo, "kurse", return_value=[{"id": 3, "fullname": "Erdkunde Q L1 Köhler"}]), \
             mock.patch.object(h.Logineo, "dateien", return_value=dateien), \
             mock.patch.object(h.Logineo, "aufgaben", return_value=aufgaben), \
             mock.patch.object(h.Logineo, "herunterladen", return_value=b"%PDF-x"), \
             mock.patch("builtins.print"):
            h.kurs_material(konfig, tmp, "Erdkunde")
        m = os.path.join(tmp, "Erdkunde", "Material")
        self.assertTrue(os.path.exists(os.path.join(m, "Thema 1 Klima", "Klima.pdf")))
        self.assertTrue(os.path.exists(os.path.join(m, "Aufgaben", "Referat", "Aufgabe.pdf")))
        self.assertTrue(os.path.exists(os.path.join(m, "Aufgaben", "Referat", "info.pdf")))
        # Material-Ordner wird vom Aufraeumen nicht angefasst
        self.assertEqual(h.aufraeumen(tmp, dt.date.today()), 0)

    def test_fach_info(self):
        k = {"faecher": {"CH": {"ordner": "Chemie", "logineo_kurs": ["Chemie"]}}}
        self.assertEqual(h.fach_info(k, "CH G2"), ("Chemie", ["Chemie"]))
        self.assertEqual(h.fach_info(k, "CH"), ("Chemie", ["Chemie"]))
        self.assertEqual(h.fach_info(k, "PH G1"), ("PH G1", None))

    def test_ablauf(self):
        self._lauf()

    def _lauf(self):
        import json, tempfile
        from unittest import mock
        heute = dt.date.today()
        faellig = heute + dt.timedelta(days=2)
        jetzt = int(dt.datetime.now().timestamp())
        tmp = tempfile.mkdtemp()
        konfig = {"untis": {"server": "s", "schule": "x", "benutzer": "u"},
                  "logineo": {"url": "https://l", "benutzer": "u"},
                  "ausgabe_ordner": tmp, "faecher": {"M": {"ordner": "Mathe", "logineo_kurs": "Mathe"}}}
        pfad = os.path.join(tmp, "config.json")
        with open(pfad, "w") as f:
            json.dump(konfig, f)
        hw = [{"id": 1, "fach": "M", "aufgegeben": heute, "faellig": faellig,
               "text": "AB Brüche bearbeiten", "erledigt": False}]
        aufgabe = {"id": 9, "name": "Brüche", "duedate": jetzt + 86400, "intro": "<p>Alles</p>",
                   "introattachments": [{"filename": "ab.pdf", "fileurl": "https://l/f/ab.pdf"}]}
        import contextlib

        @contextlib.contextmanager
        def patches():
            with mock.patch.dict(os.environ, {"UNTIS_PASSWORT": "p", "LOGINEO_PASSWORT": "p"}), \
                 mock.patch.object(h.Untis, "anmelden"), mock.patch.object(h.Untis, "abmelden"), \
                 mock.patch.object(h.Untis, "hausaufgaben", return_value=hw), \
                 mock.patch.object(h.Logineo, "anmelden"), \
                 mock.patch.object(h.Logineo, "kurse", return_value=[{"id": 4, "shortname": "Mathe 10", "fullname": ""}]), \
                 mock.patch.object(h.Logineo, "aufgaben", return_value=[aufgabe]), \
                 mock.patch.object(h.Logineo, "abgegeben", return_value=False), \
                 mock.patch.object(h.Logineo, "dateien", return_value=[]), \
                 mock.patch.object(h.Logineo, "herunterladen", return_value=b"%PDF-AB"), \
                 mock.patch("builtins.print"):
                yield

        with patches():
            h.main(["--konfig", pfad])
        dateien = sorted(os.listdir(os.path.join(tmp, "Mathe")))
        p = "%s AB Brüche bearbeiten" % faellig.isoformat()
        self.assertEqual(dateien, [p + " - Aufgabe.pdf", p + " - ab.pdf"])
        return tmp, pfad, patches

    def test_geloeschte_kommen_nicht_wieder(self):
        tmp, pfad, patches = self._lauf()
        mathe = os.path.join(tmp, "Mathe")
        for d in os.listdir(mathe):
            os.remove(os.path.join(mathe, d))
        # alte, ueberfaellige Datei wird aufgeraeumt
        alt = os.path.join(mathe, "2000-01-01 Alt - Aufgabe.pdf")
        open(alt, "wb").close()
        with patches():
            h.main(["--konfig", pfad])
        self.assertEqual(os.listdir(mathe), [])


if __name__ == "__main__":
    unittest.main()
