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

    def test_ablauf(self):
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
            h.main(["--konfig", pfad])
        dateien = sorted(os.listdir(os.path.join(tmp, "Mathe")))
        p = "%s AB Brüche bearbeiten" % faellig.isoformat()
        self.assertEqual(dateien, [p + " - Aufgabe.pdf", p + " - ab.pdf"])


if __name__ == "__main__":
    unittest.main()
