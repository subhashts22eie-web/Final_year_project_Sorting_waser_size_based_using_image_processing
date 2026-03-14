/*
 * ESP32 Conveyor & Servo Controller (Real-Time Integration)
 * ==========================================================
 * Communicates with Flask server's Real-Time Detection System.
 *
 * SERVER INTEGRATION:
 *   - Polled every 500ms:  GET /cmd            → "START" or "STOP"
 *   - Polled every 1s:     GET /sort/decision  → "0", "90", "180", or status
 *   - Monitored:           GET /realtime/state → Current detection state (optional)
 *
 * HARDWARE MAPPING:
 *   - Conveyor Motor:  GPIO 27 (HIGH = run, LOW = stop)
 *   - Servo Motor:     GPIO 26 (PWM control, 0-180 degrees)
 *
 * OPERATION:
 *   1. ESP32 polls /cmd every 500ms → Controls conveyor START/STOP
 *   2. When conveyor running, polls /sort/decision every 1s → Controls servo angle
 *   3. Servo angles: 0° = EQUAL, 90° = LESS, 180° = GREATER (vs target)
 *   4. Servo holds position until new command received
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

// Flask Server (Your PC IP running server.py)
const char* serverBaseUrl = "http://10.121.22.234:5000";

// GPIO Pins
const int CONVEYOR_PIN = 27;      // Conveyor motor relay/driver
const int SORT_SERVO_PIN = 26;    // Servo PWM pin
const int STATUS_LED_PIN = 2;     // Status indicator (built-in LED)

// Servo Configuration (MG995 or SG90)
const int SERVO_MIN_US = 500;     // Minimum pulse width (0°)
const int SERVO_MAX_US = 2400;    // Maximum pulse width (180°)
const int SERVO_NEUTRAL = 90;     // Default/neutral position

// Polling Intervals (milliseconds)
const unsigned long POLL_CMD_INTERVAL_MS = 500;     // Check conveyor command
const unsigned long POLL_SORT_INTERVAL_MS = 1000;   // Check sort decision (when running)
const unsigned long WIFI_CHECK_INTERVAL_MS = 10000; // Check WiFi connection

// Debug Mode (set to true for serial output)
const bool DEBUG_MODE = true;

// ══════════════════════════════════════════════════════════════════════════════
// GLOBAL STATE
// ══════════════════════════════════════════════════════════════════════════════

HTTPClient http;
Servo sortServo;

// Timing
unsigned long lastCmdPollMs = 0;
unsigned long lastSortPollMs = 0;
unsigned long lastWiFiCheckMs = 0;
unsigned long lastStatusLedMs = 0;

// State
String lastCmd = "";
int currentServoAngle = SERVO_NEUTRAL;
bool conveyorRunning = false;
bool wifiConnected = false;

// Statistics
unsigned long totalCmdPolls = 0;
unsigned long failedCmdPolls = 0;
unsigned long totalSortDecisions = 0;
unsigned long failedSortDecisions = 0;

// ══════════════════════════════════════════════════════════════════════════════
// DEBUG LOGGING
// ══════════════════════════════════════════════════════════════════════════════

void debugLog(const String& message) {
  if (DEBUG_MODE) {
    Serial.print("[ESP32] ");
    Serial.println(message);
  }
}

void debugLogTime(const String& prefix, unsigned long timestamp) {
  if (DEBUG_MODE) {
    Serial.print("[");
    Serial.print(millis());
    Serial.print("ms] ");
    Serial.print(prefix);
    Serial.println(timestamp);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// WIFI MANAGEMENT
// ══════════════════════════════════════════════════════════════════════════════

void connectWiFi() {
  if (wifiConnected) {
    return;
  }

  debugLog("\n========== WiFi Connection ==========");
  debugLog("Connecting to: " + String(ssid));

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  const int MAX_ATTEMPTS = 20;  // ~10 seconds timeout

  while (WiFi.status() != WL_CONNECTED && attempts < MAX_ATTEMPTS) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    debugLog("✓ WiFi Connected!");
    debugLog("✓ IP: " + WiFi.localIP().toString());
    debugLog("✓ Server: " + String(serverBaseUrl));
    debugLog("=====================================\n");
    digitalWrite(STATUS_LED_PIN, HIGH);  // LED on = connected
  } else {
    wifiConnected = false;
    debugLog("✗ WiFi Connection Failed");
    debugLog("  Will retry automatically...");
    debugLog("=====================================\n");
    digitalWrite(STATUS_LED_PIN, LOW);   // LED off = disconnected
  }
}

void checkWiFiConnection() {
  unsigned long now = millis();

  // Check every WIFI_CHECK_INTERVAL_MS
  if (now - lastWiFiCheckMs < WIFI_CHECK_INTERVAL_MS) {
    return;
  }

  lastWiFiCheckMs = now;

  if (WiFi.status() != WL_CONNECTED) {
    if (wifiConnected) {
      debugLog("⚠ WiFi disconnected! Reconnecting...");
      wifiConnected = false;
      digitalWrite(STATUS_LED_PIN, LOW);
    }
    WiFi.reconnect();
    delay(500);
  } else if (!wifiConnected) {
    debugLog("✓ WiFi reconnected!");
    wifiConnected = true;
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// CONVEYOR CONTROL
// ══════════════════════════════════════════════════════════════════════════════

void setConveyor(bool run) {
  if (run == conveyorRunning) {
    return;  // No change needed
  }

  digitalWrite(CONVEYOR_PIN, run ? HIGH : LOW);
  conveyorRunning = run;

  if (run) {
    debugLog("▶ CONVEYOR STARTED");
  } else {
    debugLog("⏸ CONVEYOR STOPPED");
    // Reset servo to neutral when conveyor stops
    if (currentServoAngle != SERVO_NEUTRAL) {
      sortServo.write(SERVO_NEUTRAL);
      currentServoAngle = SERVO_NEUTRAL;
      debugLog("↻ Servo reset to neutral (90°)");
    }
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// SERVO CONTROL
// ══════════════════════════════════════════════════════════════════════════════

void setSortAngle(int angle) {
  // Constrain to valid servo range
  int bounded = constrain(angle, 0, 180);

  // Only move if position changed
  if (bounded == currentServoAngle) {
    return;
  }

  sortServo.write(bounded);
  currentServoAngle = bounded;

  // Decode angle to sorting decision
  String decision = "?";
  if (bounded == 0) {
    decision = "EQUAL (Target)";
  } else if (bounded == 90) {
    decision = "LESS (Smaller)";
  } else if (bounded == 180) {
    decision = "GREATER (Larger)";
  }

  debugLog("🔄 Servo → " + String(bounded) + "° (" + decision + ")");
}

// ══════════════════════════════════════════════════════════════════════════════
// SERVER POLLING - CONVEYOR COMMAND
// ══════════════════════════════════════════════════════════════════════════════

void pollConveyorCommand() {
  unsigned long now = millis();

  // Poll every POLL_CMD_INTERVAL_MS
  if (now - lastCmdPollMs < POLL_CMD_INTERVAL_MS) {
    return;
  }

  lastCmdPollMs = now;
  totalCmdPolls++;

  // Check WiFi before attempting connection
  if (!wifiConnected) {
    failedCmdPolls++;
    return;
  }

  String cmdUrl = String(serverBaseUrl) + "/cmd";
  http.begin(cmdUrl);
  http.setTimeout(1500);

  int httpCode = http.GET();

  if (httpCode == 200) {
    String cmd = http.getString();
    cmd.trim();

    // Only process if command changed
    if (cmd != lastCmd) {
      lastCmd = cmd;

      if (cmd == "START") {
        setConveyor(true);
      } else if (cmd == "STOP") {
        setConveyor(false);
      } else {
        debugLog("⚠ Unknown command: " + cmd);
      }
    }
  } else {
    failedCmdPolls++;
    if (httpCode > 0) {
      debugLog("⚠ /cmd HTTP " + String(httpCode));
    } else {
      debugLog("⚠ /cmd connection error");
    }
  }

  http.end();
}

// ══════════════════════════════════════════════════════════════════════════════
// SERVER POLLING - SORT DECISION
// ══════════════════════════════════════════════════════════════════════════════

void pollSortDecision() {
  unsigned long now = millis();

  // Only poll when conveyor is running
  if (!conveyorRunning) {
    return;
  }

  // Poll every POLL_SORT_INTERVAL_MS
  if (now - lastSortPollMs < POLL_SORT_INTERVAL_MS) {
    return;
  }

  lastSortPollMs = now;
  totalSortDecisions++;

  // Check WiFi
  if (!wifiConnected) {
    failedSortDecisions++;
    return;
  }

  String sortUrl = String(serverBaseUrl) + "/sort/decision";
  http.begin(sortUrl);
  http.setTimeout(1500);

  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    response.trim();

    // Valid angles: 0, 90, 180
    if (response == "0") {
      setSortAngle(0);
    } else if (response == "90") {
      setSortAngle(90);
    } else if (response == "180") {
      setSortAngle(180);
    } else if (response == "WAITING") {
      // Server still processing, wait for next poll
      // Don't change servo position
    } else if (response == "STOPPED") {
      // Conveyor stopped on server side
      setConveyor(false);
    } else if (response == "NO_TARGET") {
      // No target set, shouldn't happen if conveyor running
      setConveyor(false);
    } else {
      debugLog("⚠ Unknown angle: " + response);
    }
  } else {
    failedSortDecisions++;
    if (httpCode > 0) {
      debugLog("⚠ /sort/decision HTTP " + String(httpCode));
    } else {
      debugLog("⚠ /sort/decision connection error");
    }
  }

  http.end();
}

// ══════════════════════════════════════════════════════════════════════════════
// STATUS LED BLINK
// ══════════════════════════════════════════════════════════════════════════════

void updateStatusLed() {
  unsigned long now = millis();

  // Use LED to indicate status:
  // - Solid ON: WiFi connected
  // - Solid OFF: WiFi disconnected
  // - Blink: Conveyor running (blink every 100ms)

  if (!wifiConnected) {
    digitalWrite(STATUS_LED_PIN, LOW);
    return;
  }

  if (conveyorRunning) {
    // Blink while conveyor running
    unsigned long blinkPhase = (now / 100) % 2;
    digitalWrite(STATUS_LED_PIN, blinkPhase == 0 ? HIGH : LOW);
  } else {
    // Solid on when WiFi connected but conveyor stopped
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// DIAGNOSTICS
// ══════════════════════════════════════════════════════════════════════════════

void printStatus() {
  if (!DEBUG_MODE) {
    return;
  }

  Serial.println("\n========== Status Report ==========");
  Serial.print("WiFi: ");
  Serial.println(wifiConnected ? "✓ Connected" : "✗ Disconnected");
  Serial.print("Conveyor: ");
  Serial.println(conveyorRunning ? "▶ Running" : "⏸ Stopped");
  Serial.print("Servo Angle: ");
  Serial.print(currentServoAngle);
  Serial.println("°");
  Serial.print("Uptime: ");
  Serial.print(millis() / 1000);
  Serial.println(" seconds");
  Serial.println("\nStatistics:");
  Serial.print("  Conveyor polls: ");
  Serial.print(totalCmdPolls);
  Serial.print(" (");
  Serial.print(failedCmdPolls);
  Serial.println(" failed)");
  Serial.print("  Sort decisions: ");
  Serial.print(totalSortDecisions);
  Serial.print(" (");
  Serial.print(failedSortDecisions);
  Serial.println(" failed)");
  Serial.println("====================================\n");
}

// ══════════════════════════════════════════════════════════════════════════════
// SETUP
// ══════════════════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n");
  Serial.println("═══════════════════════════════════════════════════════════");
  Serial.println("ESP32 Conveyor & Servo Controller");
  Serial.println("Real-Time Detection Integration");
  Serial.println("═══════════════════════════════════════════════════════════");

  // Initialize GPIO pins
  pinMode(CONVEYOR_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(CONVEYOR_PIN, LOW);  // Conveyor off
  digitalWrite(STATUS_LED_PIN, LOW); // LED off (not connected yet)

  debugLog("✓ GPIO initialized");
  debugLog("  - Conveyor: GPIO " + String(CONVEYOR_PIN));
  debugLog("  - Servo: GPIO " + String(SORT_SERVO_PIN));
  debugLog("  - LED: GPIO " + String(STATUS_LED_PIN));

  // Initialize servo
  sortServo.setPeriodHertz(50);
  sortServo.attach(SORT_SERVO_PIN, SERVO_MIN_US, SERVO_MAX_US);
  sortServo.write(SERVO_NEUTRAL);
  currentServoAngle = SERVO_NEUTRAL;
  debugLog("✓ Servo initialized at " + String(SERVO_NEUTRAL) + "°");

  // Connect to WiFi
  delay(500);
  connectWiFi();

  // Keep trying to connect
  while (!wifiConnected) {
    delay(3000);
    connectWiFi();
  }

  debugLog("✓ System Ready - Polling server...");
  debugLog("  - Conveyor poll: " + String(POLL_CMD_INTERVAL_MS) + "ms");
  debugLog("  - Sort poll: " + String(POLL_SORT_INTERVAL_MS) + "ms");

  Serial.println("\n");
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN LOOP
// ══════════════════════════════════════════════════════════════════════════════

void loop() {
  // Periodic WiFi connection check
  checkWiFiConnection();

  // Poll server for conveyor command
  pollConveyorCommand();

  // Poll server for sort decision (only when conveyor running)
  pollSortDecision();

  // Update status LED
  updateStatusLed();

  // Print status report every 30 seconds
  static unsigned long lastStatusPrintMs = 0;
  if (millis() - lastStatusPrintMs > 30000) {
    lastStatusPrintMs = millis();
    printStatus();
  }

  // Small delay to prevent WDT reset
  delay(10);
}
