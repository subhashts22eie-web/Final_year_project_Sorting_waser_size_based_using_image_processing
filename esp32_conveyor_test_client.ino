#include <WiFi.h>
#include <HTTPClient.h>

// ===== WiFi =====
const char* WIFI_SSID = "Subhash";
const char* WIFI_PASS = "122333447";

// ===== Server =====
const char* SERVER_HOST = "10.1.71.103";   // PC IP running conveyor_test_server.py
const uint16_t SERVER_PORT = 5000;
const char* CMD_PATH = "/cmd";

// ===== Conveyor Output =====
const int CONVEYOR_PIN = 26; // Relay/driver input pin
const int LED_PIN = 2;       // Built-in LED on many ESP32 boards

String lastCommand = "STOP";
unsigned long lastPollMs = 0;
const unsigned long POLL_INTERVAL_MS = 300;
unsigned long lastHeartbeatMs = 0;
const unsigned long HEARTBEAT_MS = 5000;


String buildCmdUrl() {
  return String("http://") + SERVER_HOST + ":" + String(SERVER_PORT) + CMD_PATH;
}

void applyCommand(const String& cmd) {
  if (cmd == "START") {
    digitalWrite(CONVEYOR_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
  } else {
    digitalWrite(CONVEYOR_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
  }
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println("[ESP32] WiFi disconnected, reconnecting...");
  WiFi.disconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[ESP32] WiFi connected. IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("[ESP32] Gateway: ");
    Serial.println(WiFi.gatewayIP());
    Serial.print("[ESP32] Poll URL: ");
    Serial.println(buildCmdUrl());
  } else {
    Serial.println("[ESP32] WiFi reconnect failed");
  }
}

String fetchCommand() {
  HTTPClient http;
  String url = buildCmdUrl();

  http.begin(url);
  http.setTimeout(2000);

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.print("[ESP32] GET ");
    Serial.print(url);
    Serial.print(" failed, code=");
    Serial.println(code);
    Serial.print("[ESP32] HTTP error: ");
    Serial.println(http.errorToString(code));
    http.end();
    return "";
  }

  String body = http.getString();
  body.trim();
  http.end();

  body.toUpperCase();
  Serial.print("[ESP32] GET /cmd -> ");
  Serial.println(body);
  return body;
}

void setup() {
  Serial.begin(115200);

  pinMode(CONVEYOR_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  applyCommand("STOP");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("[ESP32] Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println();

  Serial.print("[ESP32] Connected. IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("[ESP32] Gateway: ");
  Serial.println(WiFi.gatewayIP());
  Serial.print("[ESP32] Poll URL: ");
  Serial.println(buildCmdUrl());
}

void loop() {
  ensureWifi();

  unsigned long now = millis();
  if (now - lastPollMs < POLL_INTERVAL_MS) {
    delay(10);
    return;
  }
  lastPollMs = now;

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  if (millis() - lastHeartbeatMs >= HEARTBEAT_MS) {
    lastHeartbeatMs = millis();
    Serial.print("[ESP32] Heartbeat: WiFi OK, RSSI=");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  }

  String cmd = fetchCommand();
  if (cmd.length() == 0) {
    return;
  }

  if (cmd != "START" && cmd != "STOP") {
    Serial.print("[ESP32] Invalid command from server: ");
    Serial.println(cmd);
    return;
  }

  if (cmd != lastCommand) {
    lastCommand = cmd;
    applyCommand(cmd);
    Serial.print("[ESP32] Conveyor command applied: ");
    Serial.println(cmd);
  }
}
