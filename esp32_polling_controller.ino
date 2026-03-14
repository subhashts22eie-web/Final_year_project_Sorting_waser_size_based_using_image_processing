/*
 * ESP32 Conveyor & Servo Controller (Polling Mode)
 * =================================================
 * Polls Flask server for commands instead of acting as web server.
 *
 * Endpoints polled:
 *   GET /cmd             → Returns "START" or "STOP" for conveyor
 *   GET /sort/decision   → Returns servo angle "0", "90", or "180"
 *
 * Hardware:
 *   - Conveyor: GPIO 27 (relay or motor driver)
 *   - Servo: GPIO 26 (MG995 or SG90)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// ══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ══════════════════════════════════════════════════════════════════════════════

// WiFi Credentials
const char* ssid = "Subhash";
const char* password = "12233447";

// Flask Server URL (Your PC IP running Python)
const char* serverBaseUrl = "http://10.121.22.234:5000";

// GPIO Pins
const int CONVEYOR_PIN = 27;      // Conveyor motor control
const int SORT_SERVO_PIN = 26;    // Sorting servo control

// Servo Settings (MG995)
const int SERVO_MIN_US = 500;
const int SERVO_MAX_US = 2400;

// Polling Intervals
const unsigned long POLL_INTERVAL_MS = 500;    // Poll conveyor cmd every 500ms
const unsigned long SORT_INTERVAL_MS = 1000;   // Check sort decision every 1s (when running)

// ══════════════════════════════════════════════════════════════════════════════
// GLOBAL VARIABLES
// ══════════════════════════════════════════════════════════════════════════════

String lastCmd = "";
unsigned long lastPollMs = 0;
unsigned long lastSortMs = 0;
Servo sortServo;
int currentServoAngle = 90;  // Start at neutral position
bool conveyorRunning = false;

// ══════════════════════════════════════════════════════════════════════════════
// WIFI CONNECTION
// ══════════════════════════════════════════════════════════════════════════════

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.println("============================================================");
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi Connected!");
    Serial.print("✓ IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("✓ Server: ");
    Serial.println(serverBaseUrl);
    Serial.println("============================================================");
  } else {
    Serial.println("\n✗ WiFi Connection Failed!");
    Serial.println("  Check SSID and password");
    Serial.println("  Retrying in 5 seconds...");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// CONVEYOR CONTROL
// ══════════════════════════════════════════════════════════════════════════════

void setConveyor(bool run) {
  digitalWrite(CONVEYOR_PIN, run ? HIGH : LOW);
  conveyorRunning = run;

  if (run) {
    Serial.println("▶ CONVEYOR STARTED");
  } else {
    Serial.println("⏸ CONVEYOR STOPPED");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// SERVO CONTROL
// ══════════════════════════════════════════════════════════════════════════════

void setSortAngle(int angle) {
  int bounded = constrain(angle, 0, 180);

  if (bounded == currentServoAngle) {
    return;  // Already at this position
  }

  sortServo.write(bounded);
  currentServoAngle = bounded;

  Serial.print("🔄 Servo moved to: ");
  Serial.print(currentServoAngle);
  Serial.println("°");
}

// ══════════════════════════════════════════════════════════════════════════════
// SERVER POLLING
// ══════════════════════════════════════════════════════════════════════════════

void applyCommand(const String& cmd) {
  if (cmd == "START") {
    setConveyor(true);
  } else if (cmd == "STOP") {
    setConveyor(false);
  } else if (cmd == "IDLE" || cmd == "") {
    // No change - server hasn't issued new command
  } else {
    Serial.print("⚠ Unknown command: ");
    Serial.println(cmd);
  }
}

void pollServerCommand() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠ WiFi lost, reconnecting...");
    WiFi.reconnect();
    delay(1000);
    return;
  }

  HTTPClient http;
  String cmdUrl = String(serverBaseUrl) + "/cmd";

  http.begin(cmdUrl);
  http.setTimeout(2000);  // 2 second timeout

  int code = http.GET();

  if (code == 200) {
    String payload = http.getString();
    payload.trim();

    // Only apply if command changed
    if (payload != lastCmd) {
      lastCmd = payload;
      applyCommand(payload);
    }
  } else if (code > 0) {
    Serial.print("⚠ HTTP error code: ");
    Serial.println(code);
  } else {
    Serial.print("⚠ Connection failed: ");
    Serial.println(http.errorToString(code));
  }

  http.end();
}

void requestSortDecision() {
  // Only poll sort decision when conveyor is running
  if (!conveyorRunning) {
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  HTTPClient http;
  String sortUrl = String(serverBaseUrl) + "/sort/decision";

  http.begin(sortUrl);
  http.setTimeout(2000);

  int code = http.GET();

  if (code == 200) {
    String payload = http.getString();
    payload.trim();

    // Valid servo angles: 0, 90, 180
    if (payload == "0" || payload == "90" || payload == "180") {
      int angle = payload.toInt();
      setSortAngle(angle);
    } else if (payload == "NONE" || payload == "") {
      // No sort action needed
    } else {
      Serial.print("⚠ Invalid sort angle: ");
      Serial.println(payload);
    }
  } else if (code > 0) {
    Serial.print("⚠ Sort HTTP error: ");
    Serial.println(code);
  }

  http.end();
}

// ══════════════════════════════════════════════════════════════════════════════
// SETUP
// ══════════════════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n");
  Serial.println("============================================================");
  Serial.println("ESP32 Conveyor & Servo Controller");
  Serial.println("Polling Mode");
  Serial.println("============================================================");

  // Setup conveyor pin
  pinMode(CONVEYOR_PIN, OUTPUT);
  setConveyor(false);  // Start stopped

  // Setup servo
  sortServo.setPeriodHertz(50);
  sortServo.attach(SORT_SERVO_PIN, SERVO_MIN_US, SERVO_MAX_US);
  sortServo.write(currentServoAngle);
  Serial.print("✓ Servo initialized at ");
  Serial.print(currentServoAngle);
  Serial.println("°");

  // Connect to WiFi
  delay(500);
  connectWiFi();

  // Wait for WiFi
  while (WiFi.status() != WL_CONNECTED) {
    delay(5000);
    connectWiFi();
  }

  Serial.println("\n✓ System Ready - Polling for commands...\n");
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN LOOP
// ══════════════════════════════════════════════════════════════════════════════

void loop() {
  unsigned long now = millis();

  // Poll conveyor command
  if (now - lastPollMs >= POLL_INTERVAL_MS) {
    lastPollMs = now;
    pollServerCommand();
  }

  // Poll sort decision (only when conveyor running)
  if (conveyorRunning && (now - lastSortMs >= SORT_INTERVAL_MS)) {
    lastSortMs = now;
    requestSortDecision();
  }

  // Small delay to prevent WDT reset
  delay(10);
}
