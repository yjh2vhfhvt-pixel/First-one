// Radar-Laser: ESP32 empfängt per Bluetooth Winkel von der Mensch-Radar-App
// und richtet einen schwachen Laser (Klasse 1/2, max. 1 mW) mit zwei Servos aus.
//
// Befehle (Text, eine Zeile pro Befehl):  "P12.3 T8.0 L1"  oder  "L0"
//   P = Schwenken in Grad (rechts positiv), T = Neigen in Grad (unten positiv),
//   L = Laser an (1) / aus (0)
//
// Benötigte Bibliothek: "ESP32Servo" (Arduino IDE -> Bibliotheken verwalten)
// Board: "ESP32 Dev Module"

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <ESP32Servo.h>

// ---- Anschlüsse ----
const int PIN_PAN   = 18;   // Signal Servo unten (links/rechts)
const int PIN_TILT  = 19;   // Signal Servo oben (hoch/runter)
const int PIN_LASER = 23;   // über Transistor zum Laser

// ---- Kalibrierung (siehe ANLEITUNG.md) ----
const int   PAN_DIR   = 1;     // -1, falls der Laser in die falsche Richtung schwenkt
const int   TILT_DIR  = 1;     // -1, falls der Laser hoch statt runter geht
const float PAN_TRIM  = 0;     // Grad, Feinjustierung links/rechts
const float TILT_TRIM = 0;     // Grad, Feinjustierung hoch/runter

// ---- Sicherheit ----
const float PAN_LIMIT     = 60;   // max. Schwenkwinkel
const float TILT_MIN      = 0;    // Laser nie über die Kamera-Achse (nie nach oben)
const float TILT_MAX      = 60;
const unsigned long WATCHDOG_MS = 500;  // ohne neue Befehle -> Laser aus

#define SERVICE_UUID "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  // Nordic UART Service
#define RX_UUID      "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

Servo panServo, tiltServo;

volatile float targetPan = 0, targetTilt = 0;
volatile bool  laserWanted = false;
volatile unsigned long lastCommand = 0;
volatile bool  newCommand = false;
bool connected = false;

void laserOff() { digitalWrite(PIN_LASER, LOW); }

// Zerlegt z. B. "P12.3 T8.0 L1"
void parseCommand(const char* line) {
  float pan = targetPan, tilt = targetTilt;
  bool laser = false, hasAngles = false;
  for (const char* c = line; *c; c++) {
    if (*c == 'P') { pan = atof(c + 1); hasAngles = true; }
    else if (*c == 'T') { tilt = atof(c + 1); hasAngles = true; }
    else if (*c == 'L') { laser = (c[1] == '1'); }
  }
  // Ziel oberhalb der Kamera-Achse oder außer Reichweite -> Laser aus
  if (tilt < TILT_MIN || tilt > TILT_MAX || fabs(pan) > PAN_LIMIT) laser = false;
  if (hasAngles) {
    targetPan  = constrain(pan, -PAN_LIMIT, PAN_LIMIT);
    targetTilt = constrain(tilt, TILT_MIN, TILT_MAX);
  }
  laserWanted = laser;
  lastCommand = millis();
  newCommand = true;
}

class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* characteristic) override {
    auto value = characteristic->getValue();   // String oder std::string, je nach ESP32-Version
    parseCommand(value.c_str());
  }
};

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer*) override { connected = true; }
  void onDisconnect(BLEServer* server) override {
    connected = false;
    laserWanted = false;
    laserOff();
    server->getAdvertising()->start();         // wieder auffindbar sein
  }
};

void setup() {
  pinMode(PIN_LASER, OUTPUT);
  laserOff();

  panServo.attach(PIN_PAN, 500, 2400);
  tiltServo.attach(PIN_TILT, 500, 2400);
  panServo.write(90 + PAN_TRIM);
  tiltServo.write(90 + TILT_TRIM);

  BLEDevice::init("Radar-Laser");
  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService* service = server->createService(SERVICE_UUID);
  BLECharacteristic* rx = service->createCharacteristic(
    RX_UUID, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  rx->setCallbacks(new RxCallbacks());
  service->start();
  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->start();
}

void loop() {
  if (newCommand) {
    newCommand = false;
    panServo.write(constrain(90 + PAN_DIR * targetPan + PAN_TRIM, 0, 180));
    tiltServo.write(constrain(90 + TILT_DIR * targetTilt + TILT_TRIM, 0, 180));
  }

  // Laser nur an, wenn verbunden, gewünscht und die letzte Anweisung frisch ist
  bool on = connected && laserWanted && (millis() - lastCommand < WATCHDOG_MS);
  digitalWrite(PIN_LASER, on ? HIGH : LOW);
  delay(10);
}
