#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// Wi-Fi credentials
const char* ssid = "Subhash";
const char* password = "12233447";

// Flask server URL (PC IP)
const char* serverBaseUrl = "http://10.121.22.234:5000";

// Conveyor control pin (change if needed)
const int CONVEYOR_PIN = 27;

// MG995 sorting servo pin and PWM settings
const int SORT_SERVO_PIN = 26;
const int SERVO_MIN_US = 500;
const int SERVO_MAX_US = 2400;

// Poll interval
const unsigned long POLL_INTERVAL_MS = 1000;
const unsigned long SORT_INTERVAL_MS = 2500;

String lastCmd = "";
unsigned long lastPollMs = 0;
unsigned long lastSortMs = 0;
Servo sortServo;
int currentServoAngle = 90;

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void setConveyor(bool run) {
  digitalWrite(CONVEYOR_PIN, run ? HIGH : LOW); // invert if relay is active-low
}

void setSortAngle(int angle) {
  int bounded = constrain(angle, 0, 180);
  if (bounded == currentServoAngle) {
    return;
  }

  sortServo.write(bounded);
  currentServoAngle = bounded;
  Serial.print("Servo angle set: ");
  Serial.println(currentServoAngle);
}

void applyCommand(const String& cmd) {
  if (cmd == "START") {
    setConveyor(true);
    Serial.println("CMD: START -> Conveyor ON");
  } else if (cmd == "STOP") {
    setConveyor(false);
    Serial.println("CMD: STOP -> Conveyor OFF");
  } else {
    Serial.print("Unknown CMD: ");
    Serial.println(cmd);
  }
}

void pollServerCommand() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    WiFi.reconnect();
    return;
  }

  HTTPClient http;
  String cmdUrl = String(serverBaseUrl) + "/cmd";

  http.begin(cmdUrl);
  int code = http.GET();

  if (code > 0) {
    String payload = http.getString();
    payload.trim();

    if (payload != lastCmd) {
      lastCmd = payload;
      applyCommand(payload);
    }
  } else {
    Serial.print("HTTP error: ");
    Serial.println(code);
  }

  http.end();
}

void requestSortDecision() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  HTTPClient http;
  String sortUrl = String(serverBaseUrl) + "/sort/decision";

  http.begin(sortUrl);
  int code = http.GET();

  if (code > 0) {
    String payload = http.getString();
    payload.trim();

    if (payload == "0" || payload == "90" || payload == "180") {
      int angle = payload.toInt();
      setSortAngle(angle);
      Serial.print("SORT ANGLE CMD: ");
      Serial.println(angle);
    } else {
      Serial.print("Sort status: ");
      Serial.println(payload);
    }
  } else {
    Serial.print("Sort HTTP error: ");
    Serial.println(code);
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(CONVEYOR_PIN, OUTPUT);
  setConveyor(false);

  sortServo.setPeriodHertz(50);
  sortServo.attach(SORT_SERVO_PIN, SERVO_MIN_US, SERVO_MAX_US);
  sortServo.write(currentServoAngle);

  delay(1000);
  connectWiFi();
}

void loop() {
  unsigned long now = millis();
  if (now - lastPollMs >= POLL_INTERVAL_MS) {
    lastPollMs = now;
    pollServerCommand();
  }

  if (lastCmd == "START" && (now - lastSortMs >= SORT_INTERVAL_MS)) {
    lastSortMs = now;
    requestSortDecision();
  }
}