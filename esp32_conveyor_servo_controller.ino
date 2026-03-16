#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// Reset reason helper (ESP-IDF / Arduino core)
// If the conveyor stops unexpectedly, check Serial for reset reasons (brownout is common with servo power issues).

// ===== WiFi =====
const char* WIFI_SSID = "Subhash";
const char* WIFI_PASS = "12233447";

// ===== Server (main server.py) =====
// ESP32 polls:
//   GET /cmd           -> START/STOP (conveyor)
//   GET /sort/decision -> 0/90/180 or WAITING/NO_TARGET/STOPPED (servo)
const char* SERVER_HOST = "10.121.22.234"; // PC IP running main server.py
const uint16_t SERVER_PORT = 5000;
const char* CMD_PATH = "/cmd";
const char* ANGLE_PATH = "/sort/decision";

// ===== Conveyor Output =====
// Set these pins to match your wiring (same as esp32_conveyor_test_client.ino)
const int CONVEYOR_PIN = 27; // Relay/driver input pin
const int LED_PIN = 2;       // Built-in LED on many ESP32 boards

// ===== Servo =====
const int SERVO_PIN = 14;
Servo sorterServo;

String lastCommand = "STOP";
int lastAngle = 90;
unsigned long lastPollMs = 0;
const unsigned long POLL_INTERVAL_MS = 300;


String buildAngleUrl() {
	return String("http://") + SERVER_HOST + ":" + String(SERVER_PORT) + ANGLE_PATH;
}


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
	Serial.print("[ESP32 IO] Conveyor command applied: ");
	Serial.println(cmd);
}


void applyServoAngle(int angle) {
	angle = constrain(angle, 0, 180);
	sorterServo.write(angle);
	Serial.print("[ESP32 SERVO] Servo moved to: ");
	Serial.println(angle);
}


void ensureWifi() {
	if (WiFi.status() == WL_CONNECTED) {
		return;
	}

	Serial.println("[ESP32 SERVO] WiFi disconnected, reconnecting...");
	WiFi.disconnect(true);
	WiFi.begin(WIFI_SSID, WIFI_PASS);

	unsigned long start = millis();
	while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
		delay(300);
		Serial.print(".");
	}
	Serial.println();

	if (WiFi.status() == WL_CONNECTED) {
		Serial.print("[ESP32 SERVO] WiFi connected. IP: ");
		Serial.println(WiFi.localIP());
		Serial.print("[ESP32 IO] Poll CMD URL: ");
		Serial.println(buildCmdUrl());
		Serial.print("[ESP32 SERVO] Poll ANGLE URL: ");
		Serial.println(buildAngleUrl());
	} else {
		Serial.println("[ESP32 SERVO] WiFi reconnect failed");
	}
}


String fetchCommand() {
	HTTPClient http;
	String url = buildCmdUrl();

	http.begin(url);
	http.setTimeout(2000);

	int code = http.GET();
	if (code != HTTP_CODE_OK) {
		Serial.print("[ESP32 IO] GET failed, code=");
		Serial.print(code);
		Serial.print(" err=");
		Serial.println(http.errorToString(code));
		http.end();
		return "";
	}

	String body = http.getString();
	http.end();
	body.trim();
	body.toUpperCase();

	if (body != "START" && body != "STOP") {
		Serial.print("[ESP32 IO] Invalid /cmd from server: ");
		Serial.println(body);
		return "";
	}

	return body;
}


int fetchAngle() {
	HTTPClient http;
	String url = buildAngleUrl();

	http.begin(url);
	http.setTimeout(2000);

	int code = http.GET();
	if (code != HTTP_CODE_OK) {
		Serial.print("[ESP32 SERVO] GET failed, code=");
		Serial.print(code);
		Serial.print(" err=");
		Serial.println(http.errorToString(code));
		http.end();
		return -1;
	}

	String body = http.getString();
	http.end();
	body.trim();
	body.toUpperCase();

	if (body == "WAITING" || body == "NO_TARGET" || body == "STOPPED") {
		Serial.print("[ESP32 SERVO] Decision state: ");
		Serial.println(body);
		return -1;
	}

	int angle = body.toInt();
	if (angle != 0 && angle != 90 && angle != 180) {
		Serial.print("[ESP32 SERVO] Invalid decision from server: ");
		Serial.println(body);
		return -1;
	}

	return angle;
}


void setup() {
	Serial.begin(115200);
	delay(200);
	Serial.println();
	Serial.println("[ESP32] Boot");
	Serial.print("[ESP32] Reset reason CPU0: ");
	Serial.println(esp_reset_reason());
	Serial.print("[ESP32] Reset reason CPU1: ");
	Serial.println(esp_reset_reason());

	pinMode(CONVEYOR_PIN, OUTPUT);
	pinMode(LED_PIN, OUTPUT);
	applyCommand("STOP");

	sorterServo.setPeriodHertz(50);
	sorterServo.attach(SERVO_PIN, 500, 2400);

	applyServoAngle(lastAngle);

	WiFi.mode(WIFI_STA);
	WiFi.begin(WIFI_SSID, WIFI_PASS);

	Serial.print("[ESP32 SERVO] Connecting to WiFi");
	while (WiFi.status() != WL_CONNECTED) {
		delay(400);
		Serial.print(".");
	}
	Serial.println();

	Serial.print("[ESP32 SERVO] Connected. IP: ");
	Serial.println(WiFi.localIP());
	Serial.print("[ESP32 IO] Poll CMD URL: ");
	Serial.println(buildCmdUrl());
	Serial.print("[ESP32 SERVO] Poll ANGLE URL: ");
	Serial.println(buildAngleUrl());
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

	// 1) Conveyor START/STOP
	String cmd = fetchCommand();
	if (cmd.length() > 0) {
		if (cmd != lastCommand) {
			Serial.print("[ESP32 IO] Server cmd: ");
			Serial.println(cmd);
			lastCommand = cmd;
			applyCommand(cmd);
		}
	}

	// 2) Servo decision (independent of conveyor START/STOP)
	int angle = fetchAngle();
	if (angle < 0) {
		return;
	}

	if (angle != lastAngle) {
		lastAngle = angle;
		Serial.print("[ESP32 SERVO] Server angle: ");
		Serial.println(angle);
		applyServoAngle(angle);
	}
}
