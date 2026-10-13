#!/usr/bin/env python3
"""Hausaufgaben-Sammler: WebUntis + Logineo NRW (Moodle) -> PDFs fuer GoodNotes.

Holt die Hausaufgaben der naechsten Tage aus WebUntis, sucht im passenden
Logineo-Kurs die zugehoerigen Aufgaben und Dateien und legt alles in einen
Ordner pro Fach ab:

    <ausgabe_ordner>/<Fach-Ordner>/<Faellig-Datum> <Titel> - Aufgabe.pdf
    <ausgabe_ordner>/<Fach-Ordner>/<Faellig-Datum> <Titel> - <Anhang>.pdf

Die Ordner importierst du in GoodNotes (Importieren > Dateien), am einfachsten
aus iCloud Drive.

Nur Python-Standardbibliothek, laeuft also auch in Pythonista / a-Shell (iPad).
Passwoerter werden nie gespeichert: sie kommen aus den Umgebungsvariablen
UNTIS_PASSWORT / LOGINEO_PASSWORT oder werden beim Start abgefragt.
"""

import argparse
import base64
import datetime as dt
import getpass
import html
import http.cookiejar
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
USER_AGENT = "hausaufgaben-sammler/1.0"


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def html_zu_text(s):
    """Wandelt das HTML aus Untis/Moodle in lesbaren Klartext um."""
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|li|h\d)>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "- ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    return s.strip()


def dateiname(s, max_len=60):
    """Macht aus beliebigem Text einen fuer iOS/Windows gueltigen Dateinamen."""
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0].strip(" .") or s[:max_len]
    return s or "Ohne Titel"


def untis_datum(n):
    """20261014 -> date(2026, 10, 14)"""
    n = int(n)
    return dt.date(n // 10000, n // 100 % 100, n % 100)


def kurztitel(text, max_len=40):
    erste_zeile = next((z for z in text.splitlines() if z.strip()), "Hausaufgabe")
    return dateiname(erste_zeile, max_len)


# --------------------------------------------------------------------------
# Minimaler PDF-Schreiber (Text + Linien zum Schreiben in GoodNotes)
# --------------------------------------------------------------------------

def _pdf_text(s):
    b = s.encode("cp1252", "replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _umbrechen(text, zeichen):
    zeilen = []
    for absatz in text.split("\n"):
        if not absatz.strip():
            zeilen.append("")
            continue
        aktuell = ""
        for wort in absatz.split():
            while len(wort) > zeichen:
                if aktuell:
                    zeilen.append(aktuell)
                    aktuell = ""
                zeilen.append(wort[:zeichen])
                wort = wort[zeichen:]
            if not aktuell:
                aktuell = wort
            elif len(aktuell) + 1 + len(wort) <= zeichen:
                aktuell += " " + wort
            else:
                zeilen.append(aktuell)
                aktuell = wort
        if aktuell:
            zeilen.append(aktuell)
    return zeilen


def aufgaben_pdf(titel, kopfzeilen, text, leerseiten=1):
    """Erzeugt ein A4-PDF: Titel, Infos, Aufgabentext, danach linierte Flaeche."""
    breite, hoehe, rand = 595, 842, 50
    abstand_linien = 24
    befehle_seiten = []
    zeilen = [("titel", titel)] + [("info", z) for z in kopfzeilen] + [("", "")]
    zeilen += [("text", z) for z in _umbrechen(text, 88)]

    y = hoehe - rand
    seite = []
    for art, z in zeilen:
        groesse = {"titel": 18, "info": 10}.get(art, 11)
        schrift = "F2" if art == "titel" else "F1"
        if y - groesse < rand:
            befehle_seiten.append(seite)
            seite, y = [], hoehe - rand
        y -= groesse + 6
        if z:
            seite.append(b"BT /%s %d Tf %d %d Td (%s) Tj ET"
                         % (schrift.encode(), groesse, rand, y, _pdf_text(z)))

    def linien(von_y):
        cmds = [b"0.8 0.8 0.8 RG 0.5 w"]
        ly = von_y - abstand_linien
        while ly > rand:
            cmds.append(b"%d %d m %d %d l S" % (rand, ly, breite - rand, ly))
            ly -= abstand_linien
        return cmds

    seite += linien(y - 10)
    befehle_seiten.append(seite)
    for _ in range(leerseiten):
        befehle_seiten.append(linien(hoehe - rand))

    objekte = []  # Index 0 -> Objekt 1

    def neu(inhalt):
        objekte.append(inhalt)
        return len(objekte)

    katalog = neu(None)
    seiten = neu(None)
    f1 = neu(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
             b"/Encoding /WinAnsiEncoding >>")
    f2 = neu(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
             b"/Encoding /WinAnsiEncoding >>")
    seiten_ids = []
    for cmds in befehle_seiten:
        stream = b"\n".join(cmds)
        inhalt = neu(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        seiten_ids.append(neu(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
            % (seiten, breite, hoehe, f1, f2, inhalt)))
    objekte[katalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % seiten
    objekte[seiten - 1] = (b"<< /Type /Pages /Kids [%s] /Count %d >>"
                           % (b" ".join(b"%d 0 R" % i for i in seiten_ids), len(seiten_ids)))

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objekte, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objekte) + 1)
    for o in offsets:
        out += b"%010d 00000 n \n" % o
    out += (b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objekte) + 1, katalog, xref))
    return bytes(out)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

class Http:
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies))

    def anfrage(self, url, daten=None, json_body=None, kopf=None):
        headers = {"User-Agent": USER_AGENT}
        headers.update(kopf or {})
        body = None
        if json_body is not None:
            body = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        elif daten is not None:
            body = urllib.parse.urlencode(daten).encode()
        req = urllib.request.Request(url, data=body, headers=headers)
        with self.opener.open(req, timeout=30) as r:
            return r.read()

    def json(self, *a, **kw):
        return json.loads(self.anfrage(*a, **kw).decode("utf-8"))


# --------------------------------------------------------------------------
# WebUntis
# --------------------------------------------------------------------------

class Untis:
    def __init__(self, server, schule, benutzer, passwort):
        self.basis = "https://%s/WebUntis" % server
        self.schule = schule
        self.benutzer = benutzer
        self.passwort = passwort
        self.http = Http()
        self.session = None

    @staticmethod
    def schule_suchen(server):
        """Ermittelt den Untis-Schulnamen (loginName) ueber die oeffentliche Schulsuche."""
        suche = server.split(".")[0]
        antwort = Http().json("https://mobile.webuntis.com/ms/schoolquery2", json_body={
            "id": "1", "jsonrpc": "2.0", "method": "searchSchool",
            "params": [{"search": suche}]})
        schulen = (antwort.get("result") or {}).get("schools", [])
        passend = [s for s in schulen
                   if server in (s.get("server", "") + " " + s.get("serverUrl", ""))]
        treffer = passend or (schulen if len(schulen) == 1 else [])
        if len(treffer) != 1:
            namen = ", ".join("%s (%s)" % (s.get("displayName"), s.get("loginName"))
                              for s in schulen) or "keine"
            raise RuntimeError("Untis-Schule nicht eindeutig gefunden. Treffer: %s. "
                               "Trag 'schule' in config.json selbst ein." % namen)
        return treffer[0]["loginName"]

    def _rpc(self, methode, params=None):
        url = "%s/jsonrpc.do?school=%s" % (self.basis, urllib.parse.quote(self.schule))
        antwort = self.http.json(url, json_body={
            "id": "1", "jsonrpc": "2.0", "method": methode, "params": params or {}})
        if "error" in antwort:
            raise RuntimeError("Untis: %s" % antwort["error"].get("message", antwort["error"]))
        return antwort.get("result")

    def anmelden(self):
        res = self._rpc("authenticate", {
            "user": self.benutzer, "password": self.passwort, "client": USER_AGENT})
        self.session = res["sessionId"]

    def abmelden(self):
        if self.session:
            try:
                self._rpc("logout")
            except Exception:
                pass

    def hausaufgaben(self, von, bis):
        url = "%s/api/homeworks/lessons?startDate=%s&endDate=%s" % (
            self.basis, von.strftime("%Y%m%d"), bis.strftime("%Y%m%d"))
        schulname = "_" + base64.b64encode(self.schule.encode()).decode()
        daten = self.http.json(url, kopf={
            "Cookie": 'JSESSIONID=%s; schoolname="%s"' % (self.session, schulname)})
        return parse_untis_hausaufgaben(daten.get("data", daten))


def parse_untis_hausaufgaben(daten):
    """Macht aus der Untis-Antwort eine Liste einfacher dicts."""
    stunden = {l["id"]: l for l in daten.get("lessons", [])}
    ergebnis = []
    for hw in daten.get("homeworks", []):
        stunde = stunden.get(hw.get("lessonId"), {})
        text = html_zu_text(hw.get("text", ""))
        bemerkung = html_zu_text(hw.get("remark", ""))
        ergebnis.append({
            "id": hw.get("id"),
            "fach": (stunde.get("subject") or "Sonstiges").strip(),
            "aufgegeben": untis_datum(hw["date"]),
            "faellig": untis_datum(hw["dueDate"]),
            "text": text + ("\n\nBemerkung: " + bemerkung if bemerkung else ""),
            "erledigt": bool(hw.get("completed")),
        })
    ergebnis.sort(key=lambda h: (h["faellig"], h["fach"]))
    return ergebnis


# --------------------------------------------------------------------------
# Logineo NRW (Moodle Web-Services, wie die Moodle-App)
# --------------------------------------------------------------------------

def moodle_params(params, prefix=""):
    """{'courseids': [1, 2]} -> {'courseids[0]': 1, 'courseids[1]': 2}"""
    flach = {}
    for k, v in params.items():
        name = "%s[%s]" % (prefix, k) if prefix else str(k)
        if isinstance(v, dict):
            flach.update(moodle_params(v, name))
        elif isinstance(v, (list, tuple)):
            flach.update(moodle_params(dict(enumerate(v)), name))
        else:
            flach[name] = v
    return flach


class Logineo:
    def __init__(self, url, benutzer, passwort):
        self.basis = url.rstrip("/")
        self.benutzer = benutzer
        self.passwort = passwort
        self.http = Http()
        self.token = None

    def anmelden(self):
        res = self.http.json(self.basis + "/login/token.php", daten={
            "username": self.benutzer, "password": self.passwort,
            "service": "moodle_mobile_app"})
        if "token" not in res:
            raise RuntimeError("Logineo: %s" % res.get("error", res))
        self.token = res["token"]

    def ws(self, funktion, **params):
        daten = {"wstoken": self.token, "wsfunction": funktion,
                 "moodlewsrestformat": "json"}
        daten.update(moodle_params(params))
        res = self.http.json(self.basis + "/webservice/rest/server.php", daten=daten)
        if isinstance(res, dict) and res.get("exception"):
            raise RuntimeError("Logineo %s: %s" % (funktion, res.get("message")))
        return res

    def kurse(self):
        uid = self.ws("core_webservice_get_site_info")["userid"]
        return self.ws("core_enrol_get_users_courses", userid=uid)

    def aufgaben(self, kurs_id):
        res = self.ws("mod_assign_get_assignments", courseids=[kurs_id])
        return [a for k in res.get("courses", []) for a in k.get("assignments", [])]

    def abgegeben(self, aufgabe_id):
        try:
            res = self.ws("mod_assign_get_submission_status", assignid=aufgabe_id)
        except RuntimeError:
            return False
        sub = (res.get("lastattempt") or {}).get("submission") or {}
        return sub.get("status") == "submitted"

    def dateien(self, kurs_id):
        """Alle Dateien aus Material-Aktivitaeten des Kurses."""
        dateien = []
        for abschnitt in self.ws("core_course_get_contents", courseid=kurs_id):
            for modul in abschnitt.get("modules", []):
                for inhalt in modul.get("contents", []) or []:
                    if inhalt.get("type") == "file":
                        dateien.append({
                            "name": inhalt.get("filename", "datei"),
                            "url": inhalt.get("fileurl"),
                            "zeit": inhalt.get("timemodified") or 0,
                            "modul": modul.get("name", ""),
                        })
        return dateien

    def herunterladen(self, url):
        trenner = "&" if "?" in url else "?"
        return self.http.anfrage(url + trenner + "token=" + urllib.parse.quote(self.token))


def finde_kurs(kurse, suchbegriffe):
    """Erster Kurs, dessen Name einen der Suchbegriffe enthaelt (String oder Liste)."""
    if isinstance(suchbegriffe, str):
        suchbegriffe = [suchbegriffe]
    for begriff in suchbegriffe or []:
        s = begriff.lower()
        for k in kurse:
            if s in (k.get("shortname") or "").lower() or s in (k.get("fullname") or "").lower():
                return k
    return None


# --------------------------------------------------------------------------
# Ablauf
# --------------------------------------------------------------------------

def lade_konfig(pfad):
    if not os.path.exists(pfad):
        return einrichten(pfad)
    with open(pfad, encoding="utf-8") as f:
        konfig = json.load(f)
    if fehlende_namen_abfragen(konfig):
        speichere_konfig(pfad, konfig)
    return konfig


def frage(text):
    antwort = ""
    while not antwort:
        antwort = input(text).strip()
    return antwort


def fehlende_namen_abfragen(konfig):
    geaendert = False
    if not konfig["untis"].get("benutzer"):
        konfig["untis"]["benutzer"] = frage("Untis-Benutzername: ")
        geaendert = True
    l = konfig.get("logineo") or {}
    if l.get("url") and not l.get("benutzer"):
        l["benutzer"] = frage("Logineo-Benutzername: ")
        geaendert = True
    return geaendert


def speichere_konfig(pfad, konfig):
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(konfig, f, indent=2, ensure_ascii=False)
    print("Gespeichert in %s\n" % pfad)


def einrichten(pfad):
    """Erster Start: legt config.json aus config.example.json an und fragt die Benutzernamen."""
    vorlage = os.path.join(os.path.dirname(pfad), "config.example.json")
    if not os.path.exists(vorlage):
        raise RuntimeError("Weder %s noch config.example.json gefunden." % pfad)
    with open(vorlage, encoding="utf-8") as f:
        konfig = json.load(f)
    print("Erste Einrichtung (Passwoerter werden NICHT gespeichert).")
    konfig["untis"]["benutzer"] = ""
    konfig.setdefault("logineo", {})["benutzer"] = ""
    fehlende_namen_abfragen(konfig)
    speichere_konfig(pfad, konfig)
    return konfig


def passwort(env, text):
    if os.environ.get(env):
        return os.environ[env]
    if auf_ipad():
        # getpass blendet in a-Shell die Tastatur aus; deshalb normal einlesen
        # und die Zeile danach sofort wieder vom Bildschirm loeschen.
        wert = input(text)
        print("\033[1A\033[2K%s********" % text)
        return wert
    return getpass.getpass(text)


def auf_ipad():
    import platform
    return platform.machine().startswith(("iPad", "iPhone"))


def fach_info(konfig, fach):
    """Untis-Fach -> (Ordner, Logineo-Suchbegriffe). 'CH G2' passt auch auf 'CH'."""
    faecher = konfig.get("faecher", {})
    eintrag = faecher.get(fach) or faecher.get(fach.split()[0] if fach.split() else fach, {})
    return eintrag.get("ordner") or fach, eintrag.get("logineo_kurs")


class Verlauf:
    """Merkt sich, welche Dateien schon einmal geliefert wurden.

    So kommen Dateien, die du nach dem Import in GoodNotes geloescht hast,
    beim naechsten Lauf nicht wieder.
    """

    def __init__(self, ziel):
        self.ziel = ziel
        self.pfad = os.path.join(ziel, ".verlauf.json")
        try:
            with open(self.pfad, encoding="utf-8") as f:
                self.dateien = set(json.load(f))
        except (OSError, ValueError):
            self.dateien = set()

    def _key(self, pfad):
        return os.path.relpath(pfad, self.ziel)

    def bekannt(self, pfad):
        return self._key(pfad) in self.dateien

    def merken(self, pfad):
        self.dateien.add(self._key(pfad))

    def speichern(self, heute):
        # Eintraege, die laenger als 60 Tage faellig sind, braucht niemand mehr
        grenze = (heute - dt.timedelta(days=60)).isoformat()
        behalten = sorted(d for d in self.dateien
                          if os.path.basename(d)[:10] >= grenze)
        os.makedirs(self.ziel, exist_ok=True)
        with open(self.pfad, "w", encoding="utf-8") as f:
            json.dump(behalten, f, indent=1, ensure_ascii=False)


def aufraeumen(ziel, heute):
    """Loescht Hausaufgaben-Dateien, deren Faelligkeitsdatum vorbei ist."""
    geloescht = 0
    if not os.path.isdir(ziel):
        return 0
    for ordner in os.listdir(ziel):
        basis = os.path.join(ziel, ordner)
        if not os.path.isdir(basis):
            continue
        for name in os.listdir(basis):
            try:
                faellig = dt.date.fromisoformat(name[:10])
            except ValueError:
                continue
            if faellig < heute and name[10:11] == " ":
                os.remove(os.path.join(basis, name))
                geloescht += 1
    return geloescht


def speichern(pfad, daten, ueberschreiben):
    if os.path.exists(pfad) and not ueberschreiben:
        return False
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "wb") as f:
        f.write(daten)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--konfig", default=os.path.join(HIER, "config.json"))
    ap.add_argument("--tage", type=int, help="wie viele Tage voraus (Standard aus config)")
    ap.add_argument("--ueberschreiben", action="store_true",
                    help="vorhandene Dateien neu schreiben")
    ap.add_argument("--ohne-logineo", action="store_true")
    args = ap.parse_args(argv)

    konfig = lade_konfig(args.konfig)
    heute = dt.date.today()
    bis = heute + dt.timedelta(days=args.tage or konfig.get("tage_voraus", 7))
    ziel = os.path.expanduser(konfig.get("ausgabe_ordner") or os.path.join(HIER, "Ausgabe"))
    if not os.path.isabs(ziel):
        ziel = os.path.join(HIER, ziel)

    u = konfig["untis"]
    if not u.get("schule"):
        u["schule"] = Untis.schule_suchen(u["server"])
        print("Untis-Schule gefunden: %s" % u["schule"])
    untis = Untis(u["server"], u["schule"], u["benutzer"],
                  passwort("UNTIS_PASSWORT", "Untis-Passwort: "))
    untis.anmelden()
    try:
        # Aufgaben, die heute oder spaeter faellig sind, koennen bis zu 4 Wochen
        # vorher aufgegeben worden sein.
        alle = untis.hausaufgaben(heute - dt.timedelta(days=28), bis)
    finally:
        untis.abmelden()
    offen = [h for h in alle if heute <= h["faellig"] <= bis and not h["erledigt"]]
    print("%d offene Hausaufgabe(n) bis %s." % (len(offen), bis.strftime("%d.%m.%Y")))

    logineo, kurse = None, []
    if not args.ohne_logineo and konfig.get("logineo", {}).get("url"):
        l = konfig["logineo"]
        logineo = Logineo(l["url"], l["benutzer"],
                          passwort("LOGINEO_PASSWORT", "Logineo-Passwort: "))
        logineo.anmelden()
        kurse = logineo.kurse()

    verlauf = Verlauf(ziel)
    neue = 0
    if konfig.get("aufraeumen", True):
        weg = aufraeumen(ziel, heute)
        if weg:
            print("%d alte Datei(en) geloescht (Faelligkeit vorbei)." % weg)

    kurs_cache = {}
    kurse_gezeigt = False
    for hw in offen:
        ordner, kurs_name = fach_info(konfig, hw["fach"])
        praefix = "%s %s" % (hw["faellig"].isoformat(), kurztitel(hw["text"]))
        basis = os.path.join(ziel, dateiname(ordner))
        kopf = ["Fach: %s" % hw["fach"],
                "Aufgegeben: %s" % hw["aufgegeben"].strftime("%d.%m.%Y"),
                "Faellig: %s" % hw["faellig"].strftime("%d.%m.%Y")]
        texte = [hw["text"] or "(kein Text in Untis)"]
        anhaenge = []

        kurs = finde_kurs(kurse, kurs_name) if logineo else None
        if logineo and kurs_name and not kurs:
            print("  ! Logineo-Kurs '%s' nicht gefunden." % (
                kurs_name if isinstance(kurs_name, str) else "' / '".join(kurs_name)))
            if not kurse_gezeigt:
                print("    Deine Logineo-Kurse: " + "; ".join(
                    k.get("fullname") or k.get("shortname", "?") for k in kurse))
                kurse_gezeigt = True
        if kurs:
            if kurs["id"] not in kurs_cache:
                kurs_cache[kurs["id"]] = (logineo.aufgaben(kurs["id"]), logineo.dateien(kurs["id"]))
            aufgaben, dateien = kurs_cache[kurs["id"]]
            von_ts = int(dt.datetime.combine(hw["aufgegeben"] - dt.timedelta(days=1),
                                             dt.time()).timestamp())
            bis_ts = int(dt.datetime.combine(hw["faellig"] + dt.timedelta(days=1),
                                             dt.time()).timestamp())
            for a in aufgaben:
                if not (von_ts <= (a.get("duedate") or 0) <= bis_ts):
                    continue
                if logineo.abgegeben(a["id"]):
                    continue
                kopf.append("Logineo-Aufgabe: %s" % a.get("name", ""))
                beschreibung = html_zu_text(a.get("intro", ""))
                if beschreibung:
                    texte.append("Logineo - %s:\n%s" % (a.get("name", ""), beschreibung))
                for d in a.get("introattachments", []):
                    anhaenge.append((d["filename"], d["fileurl"]))
            for d in dateien:
                if von_ts <= d["zeit"] <= bis_ts:
                    anhaenge.append((d["name"], d["url"]))

        pdf = aufgaben_pdf("%s: Hausaufgabe" % hw["fach"], kopf, "\n\n".join(texte))
        dateien = [(os.path.join(basis, praefix + " - Aufgabe.pdf"), lambda pdf=pdf: pdf)]
        for name, url in anhaenge:
            dateien.append((os.path.join(basis, "%s - %s" % (praefix, dateiname(name, 80))),
                            lambda url=url: logineo.herunterladen(url)))
        for pfad, inhalt in dateien:
            if not args.ueberschreiben and (verlauf.bekannt(pfad) or os.path.exists(pfad)):
                verlauf.merken(pfad)
                continue
            try:
                speichern(pfad, inhalt(), True)
                verlauf.merken(pfad)
                neue += 1
                print("+ %s" % os.path.relpath(pfad, ziel))
            except Exception as e:
                print("  ! %s konnte nicht geladen werden: %s" % (os.path.basename(pfad), e))

    verlauf.speichern(heute)
    print("Fertig: %d neue Datei(en) in %s" % (neue, ziel))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print("Fehler: %s" % e, file=sys.stderr)
        sys.exit(1)
