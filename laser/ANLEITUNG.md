# Radar-Laser: Bauanleitung

Der Laser folgt einer erkannten Person, zielt dabei aber **immer auf den Boden kurz vor ihre Füße**,
nie auf Körper oder Gesicht.

```
iPhone (Mensch-Radar-App)  --Bluetooth-->  ESP32  -->  2 Servos (Pan/Tilt)  -->  Laser
```

## ⚠️ Sicherheit zuerst

- **Nur Laser der Klasse 1 oder 2 mit höchstens 1 mW.** Viele billige „Arduino-Lasermodule“
  (z. B. KY-008) haben 5 mW, das ist Klasse 3R und **nicht** harmlos. Kaufe nur Module, bei
  denen Klasse und Leistung klar angegeben sind.
- Der Laser schaltet sich automatisch ab, wenn
  - keine Person zu sehen ist oder ihre Füße nicht im Bild sind,
  - der Zielpunkt in der Nähe einer Person läge,
  - der Zielpunkt über der Waagerechten läge,
  - die App länger als 0,5 s keinen Befehl schickt oder die Verbindung abbricht.
- Trotzdem: nie absichtlich in Augen leuchten, nicht auf spiegelnde Flächen (Fenster, Spiegel)
  und nicht auf Straßen oder Fahrzeuge richten.

## Einkaufsliste (ca. 25 €)

| Teil | ca. Preis |
|---|---|
| ESP32-Entwicklungsboard (ESP32-WROOM-32 „DevKit“, mit USB) | 8 € |
| Pan-Tilt-Halterung mit 2 × SG90-Servo | 8 € |
| Lasermodul 650 nm, **Klasse 2, ≤ 1 mW**, 5 V | 4 € |
| NPN-Transistor (BC337 oder 2N2222) + 1-kΩ-Widerstand | 1 € |
| Steckbrett (Breadboard) + Jumper-Kabel | 4 € |
| Powerbank + USB-Kabel (hast du vielleicht schon) | – |
| Handyhalterung/-klemme, Kabelbinder oder Klebepads | – |

## Verkabelung

```
ESP32            Bauteil
-----            -------
5V / VIN  ───┬── Servo Pan  (rot)
             ├── Servo Tilt (rot)
             └── Laser  +
GND       ───┬── Servo Pan  (braun)
             ├── Servo Tilt (braun)
             └── Transistor Emitter (E)
GPIO 18   ────── Servo Pan  (orange, Signal)
GPIO 19   ────── Servo Tilt (orange, Signal)
GPIO 23   ──[1 kΩ]── Transistor Basis (B)
Laser  −  ────── Transistor Kollektor (C)
```

Hat dein Lasermodul drei Pins (S, +, −), kannst du statt des Transistors auch **S an GPIO 23**,
**+ an 5V** und **− an GND** anschließen.

## Aufbau

1. Den Laser auf die Pan-Tilt-Halterung kleben (Kabelbinder/Heißkleber).
2. Die Halterung **direkt unter der Rückkamera** des iPhones befestigen, z. B. Handyklemme und
   Halterung zusammen auf ein Brettchen schrauben. Handy und Laser dürfen sich danach nicht mehr
   gegeneinander verschieben.
3. Das Handy **hochkant** halten bzw. montieren.

## ESP32 programmieren

1. [Arduino IDE](https://www.arduino.cc/en/software) installieren.
2. Unter *Datei → Einstellungen → Zusätzliche Boardverwalter-URLs* eintragen:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
3. *Werkzeuge → Board → Boardverwalter*: „esp32“ installieren.
4. *Sketch → Bibliothek einbinden → Bibliotheken verwalten*: „ESP32Servo“ installieren.
5. `radar_laser/radar_laser.ino` öffnen, Board „ESP32 Dev Module“ wählen und hochladen.

Nach dem Start fahren beide Servos auf 90° (Mittelstellung). **Richte den Laser jetzt so aus,
dass er genau in Blickrichtung der Kamera zeigt**, also parallel zu ihr.

## Mit der App verbinden (iPhone)

Safari kann kein Bluetooth. Deshalb:

1. Im App Store den kostenlosen Browser **„Bluefy – Web BLE Browser“** installieren.
2. In Bluefy die Adresse `https://yjh2vhfhvt-pixel.github.io/First-one/` öffnen.
3. **Radar starten**, dann oben rechts auf **🎯** tippen (Laser-Modus).
4. **🔗 Laser verbinden** antippen und „Radar-Laser“ auswählen.

Auch ohne Hardware zeigt der Laser-Modus den Zielpunkt als roten Punkt auf dem Bildschirm an.
Tippst du auf eine Person, folgt der Laser ihr. Tippst du daneben, folgt er wieder der nächsten Person.

## Kalibrieren

Stell dich (oder jemand anderen) etwa 3 m vor die Kamera:

- Der echte Laserpunkt sollte ungefähr dort auf dem Boden landen, wo die App den roten Punkt zeigt.
- Läuft der Laser **in die falsche Richtung** (links statt rechts), setze `PAN_DIR = -1`.
  Geht er nach oben statt nach unten, setze `TILT_DIR = -1`.
- Liegt er **immer etwas daneben**, korrigiere `PAN_TRIM` / `TILT_TRIM` in kleinen Schritten
  (z. B. 3 Grad) und lade den Code erneut hoch.
