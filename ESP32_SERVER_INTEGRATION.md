# ESP32 ↔ Server Integration - Complete Documentation

## System Architecture Overview

```
┌─────────────────────────────────────────────┐
│          YOUR PC (Windows)                  │
│  ┌──────────────────────────────────────┐  │
│  │    Flask Server (server.py)          │  │
│  │                                      │  │
│  │  ▪ Real-Time Detection Engine       │  │
│  │  ▪ Camera Monitoring (2s stable)    │  │
│  │  ▪ Size Measurement & Classification│  │
│  │  ▪ Angle Determination (0/90/180)   │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │    Web Frontend (index.html)         │  │
│  │                                      │  │
│  │  ▪ Live Camera Feed                 │  │
│  │  ▪ Real-Time Status Display         │  │
│  │  ▪ START/STOP Conveyor Buttons      │  │
│  │  ▪ Target Size Control              │  │
│  │  ▪ Statistics Dashboard             │  │
│  └──────────────────────────────────────┘  │
│              ↓ HTTP API                     │
│  ┌──────────────────────────────────────┐  │
│  │     Flask REST Endpoints             │  │
│  │  ▪ /cmd (GET)                       │  │
│  │  ▪ /cmd/set (POST)                  │  │
│  │  ▪ /sort/decision (GET)             │  │
│  │  ▪ /realtime/state (GET)            │  │
│  │  ▪ /target/set (POST)               │  │
│  └──────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
        WiFi Network (192.168.x.x)
                   │
                   ▼
┌──────────────────────────────────────────┐
│       ESP32 Development Board            │
│  ┌──────────────────────────────────────┐│
│  │  Polling Loop (loop() function)      ││
│  │  ┌────────────────────────────────┐ ││
│  │  │ Every 500ms:                   │ ││
│  │  │ GET /cmd → "START" or "STOP"  │ ││
│  │  │ ↓ Controls GPIO27              │ ││
│  │  │ ↓ Relay switches motor         │ ││
│  │  └────────────────────────────────┘ ││
│  │  ┌────────────────────────────────┐ ││
│  │  │ Every 1000ms (if running):     │ ││
│  │  │ GET /sort/decision → angle     │ ││
│  │  │ ↓ Controls GPIO26              │ ││
│  │  │ ↓ Servo moves to angle         │ ││
│  │  └────────────────────────────────┘ ││
│  │  ┌────────────────────────────────┐ ││
│  │  │ WiFi Check (10s):              │ ││
│  │  │ Reconnect if lost              │ ││
│  │  │ Update status LED              │ ││
│  │  └────────────────────────────────┘ ││
│  └──────────────────────────────────────┘│
│              ↓ GPIO Control               │
│  ┌──────────────────────────────────────┐│
│  │  GPIO27: Relay Module (Conveyor)    ││
│  │  GPIO26: Servo Motor PWM            ││
│  │  GPIO2: Status LED (WiFi + State)   ││
│  └──────────────────────────────────────┘│
└──────────────────┬──────────────────────┬┘
                   │                      │
        ┌──────────┴──────────┐  ┌───────┴────────┐
        ▼                     ▼  ▼                ▼
   ┌─────────┐          ┌────────────┐      ┌─────────┐
   │ Relay   │          │   Servo    │      │  LED    │
   │ Module  │          │   Motor    │      │ Status  │
   └────┬────┘          └────────────┘      └─────────┘
        │
        ▼
   ┌─────────┐
   │ Conveyor│
   │ Motor   │
   └─────────┘
```

---

## Communication Flow Diagram

### Sequence 1: User Sets Target → Conveyor Runs

```
User @ Browser                   Server              ESP32
   │                               │                   │
   ├─ Set target 25mm ─────────────→                  │
   │                        /target/set               │
   │                               │                  │
   │                        Enable              │
   │                    real-time engine       │
   │                               │                  │
   │                        /cmd = "START"     │
   │                               │                  │
   │                               ├─ Poll /cmd ────→│
   │                               │                  │
   │                               │←─ "START"────────┤
   │                               │                  │
   │                               │           GPIO27 HIGH
   │                               │           Relay ON
   │                               │           Motor spins
   │                               │
   │◄─ Display "🟢 MONITORING"───────                │
```

### Sequence 2: Washer Detection & Sorting

```
Real-Time Engine       Server                ESP32
   │                     │                     │
   ├─ Monitor background │                     │
   │                     │                     │
   ├─ Detect washer ────→│                     │
   │ (2s stable)         │                     │
   │                     │                     │
   ├─ Capture frame ────→│                     │
   │                     │                     │
   ├─ Run detection ────→│                     │
   │                     │                     │
   ├─ Measure size ─────→│                     │
   │   Size = 25mm       │                     │
   │                     │                     │
   ├─ Classify: EQUAL ──→│                     │
   │   angle = 0°        │                     │
   │                     │                     │
   │                     ├─ Store angle ──────→│ /sort/decision
   │                     │                     │
   │                     │                ←─ Poll /sort/decision
   │                     │                     │
   │                     │                 GET "0"
   │                     │                     │
   │                     │              GPIO26 PWM: 0°
   │                     │              Servo moves
   │                     │
   ├─ COOLDOWN (6s) ────→│
   │                     │
   ├─ Resume MONITORING─→│
```

### Sequence 3: STOP & Resume

```
User @ Browser          Server              ESP32
   │                      │                   │
   ├─ Click STOP ────────→│                  │
   │              /cmd/set│                  │
   │              STOP    │                  │
   │                      │                  │
   │                 /cmd = "STOP"    │
   │                 (Target SAVED)   │
   │                      │                  │
   │◄─ UI shows stopped───│                  │
   │                      │                  │
   │                      ├─ Poll /cmd ─────→│
   │                      │                  │
   │                      │←─ "STOP"─────────┤
   │                      │                  │
   │                      │           GPIO27 LOW
   │                      │           Relay OFF
   │                      │           Motor stops
   │
   ├─ Click START ────────→│
   │              /cmd/set │
   │              START    │
   │                      │
   │                 Re-enable engine
   │                 /cmd = "START"  │
   │                 with saved target
   │                      │                  │
   │◄─ Monitoring resumes─│                  │
   │ (No need to set      │                  │
   │  target again!)      │                  │
   │                      ├─ Poll /cmd ─────→│
   │                      │                  │
   │                      │←─ "START"────────┤
   │                      │                  │
   │                      │          GPIO27 HIGH
   │                      │          Motor spins
```

---

## Frontend Controls → Server → ESP32 Flow

### Button: "▶ START CONVEYOR"

```javascript
// Frontend (index.html)
onclick="setConveyorCommand('START')"
    ↓
// HTTP Request
POST /cmd/set
{
  "command": "START"
}
    ↓
// Server (server.py)
@app.route('/cmd/set', methods=['POST'])
global current_conveyor_cmd = "START"
global auto_processing_enabled = True
    ↓
// ESP32 polls (every 500ms)
GET /cmd
    ↓
// Server response
"START"
    ↓
// ESP32 code
if (cmd == "START") {
  setConveyor(true);  // GPIO27 = HIGH
}
    ↓
// Hardware
Relay triggers → Motor spins
```

### Button: "⏹ STOP CONVEYOR"

```javascript
// Frontend (index.html)
onclick="setConveyorCommand('STOP')"
    ↓
// HTTP Request
POST /cmd/set
{
  "command": "STOP"
}
    ↓
// Server (server.py)
@app.route('/cmd/set', methods=['POST'])
global current_conveyor_cmd = "STOP"
global desired_target_mm  ← PRESERVED!
    ↓
// ESP32 polls (every 500ms)
GET /cmd
    ↓
// Server response
"STOP"
    ↓
// ESP32 code
if (cmd == "STOP") {
  setConveyor(false);  // GPIO27 = LOW
  sortServo.write(90);  // Reset to neutral
}
    ↓
// Hardware
Relay de-triggers → Motor stops
Servo → 90° (neutral)
```

### Input: "Set Target Size"

```javascript
// Frontend (index.html)
onclick="setTargetSize()"
    ↓
// HTTP Request
POST /target/set
{
  "target_mm": 25.0
}
    ↓
// Server (server.py)
@app.route('/target/set', methods=['POST'])
global desired_target_mm = 25.0
if realtime_engine is not None:
    realtime_engine.enable(target_mm=25.0)
global current_conveyor_cmd = "START"
    ↓
// Results:
1. Real-time engine starts monitoring
2. Conveyor CMD set to "START"
3. Frontend shows: "🟢 MONITORING"
    ↓
// ESP32 polls (every 500ms)
GET /cmd  → "START"
    ↓
// Motor spins, detection begins
```

---

## API Endpoints (ESP32 → Server)

### 1. GET /cmd (Conveyor Control)

**Polled by ESP32:** Every 500ms
**Returns:** "START" or "STOP"

```bash
# Example
GET http://10.121.22.234:5000/cmd

# Response (plain text)
START
```

**ESP32 Code:**
```cpp
void pollConveyorCommand() {
  String cmdUrl = String(serverBaseUrl) + "/cmd";
  http.begin(cmdUrl);
  int httpCode = http.GET();

  if (httpCode == 200) {
    String cmd = http.getString();
    cmd.trim();

    if (cmd == "START") {
      setConveyor(true);   // GPIO27 HIGH
    } else if (cmd == "STOP") {
      setConveyor(false);  // GPIO27 LOW
    }
  }
  http.end();
}
```

---

### 2. GET /sort/decision (Servo Control)

**Polled by ESP32:** Every 1000ms (only if conveyor running)
**Returns:** "0", "90", "180", "WAITING", "NO_TARGET", or "STOPPED"

```bash
# Example
GET http://10.121.22.234:5000/sort/decision

# Response (plain text)
0        # Servo → 0° (matches target)
90       # Servo → 90° (smaller than target)
180      # Servo → 180° (larger than target)
WAITING  # Still processing, don't move servo
```

**ESP32 Code:**
```cpp
void pollSortDecision() {
  if (!conveyorRunning) return;  // Only when running

  String sortUrl = String(serverBaseUrl) + "/sort/decision";
  http.begin(sortUrl);
  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    response.trim();

    if (response == "0") {
      setSortAngle(0);    // GPIO26 PWM → 0°
    } else if (response == "90") {
      setSortAngle(90);   // GPIO26 PWM → 90°
    } else if (response == "180") {
      setSortAngle(180);  // GPIO26 PWM → 180°
    }
    // WAITING: Don't move servo, wait for next poll
  }
  http.end();
}
```

---

### 3. GET /realtime/state (Optional Monitoring)

**Polled by:** Frontend (every 500ms) + Optional ESP32
**Returns:** JSON object with current state

```bash
# Example
GET http://10.121.22.234:5000/realtime/state

# Response (JSON)
{
  "state": "DETECTED",
  "elapsed_sec": 1.5,
  "max_time_sec": 2.0,
  "circle_detected": true,
  "detection_x": 320,
  "detection_y": 240,
  "detection_radius": 95,
  "total_scanned": 25,
  "matched": 18,
  "success_rate": 72.0
}
```

---

## Complete Workflow Example

### Step 1: User Calibrates (One Time)

```
1. Frontend: Capture reference washer
2. Frontend: Enter size (25mm)
3. Frontend: Click "Run Calibration"
4. Server: Detects washer, calculates mm/pixel
5. Server: Saves calibration.json
6. Badge changes to "CALIBRATED" ✅
```

### Step 2: User Sets Target

```
1. Frontend: Enter target size (25mm)
2. Frontend: Click "Set Target"
3. Server: real-time_engine.enable(target_mm=25.0)
4. Server: current_conveyor_cmd = "START"
5. Frontend: Status shows "🟢 MONITORING"
6. ESP32: Polls /cmd → "START"
7. ESP32: GPIO27 HIGH → Relay ON → Motor spins ✅
```

### Step 3: Washer Detection (Automatic)

```
Time: 0s
← Washer enters frame →

Time: 0-1s
Real-Time Engine: MONITORING
├─ Background subtraction active
├─ No objects detected yet

Time: 1-2s
Real-Time Engine: DETECTED (yellow status)
├─ Circular object found
├─ Tracking position
├─ Waiting for stability

Time: 2s
Real-Time Engine: PROCESSING (blue status)
├─ Object stable for 2 seconds
├─ Capture frame
├─ Run full detection pipeline
├─ Measure: 25mm
├─ Classification: EQUAL (0°)
├─ Save result image

Time: 2.5s
ESP32: Polls /sort/decision → "0"
ESP32: GPIO26 PWM → 0°
Servo: Rotates to 0°
Washer: Falls into correct bin ✅

Time: 2.5-8.5s
Real-Time Engine: COOLDOWN (orange status)
├─ Prevents duplicate detections
├─ Time remaining displayed

Time: 8.5s
Real-Time Engine: MONITORING (back to green)
├─ Ready for next washer
└─ Statistics incremented
    Total: 26, Matched: 26 ✅
```

### Step 4: User Stops Conveyor

```
1. Frontend: Click "STOP Conveyor"
2. Frontend: POST /cmd/set { "command": "STOP" }
3. Server: current_conveyor_cmd = "STOP"
4. Server: realtime_engine.disable()
5. Server: desired_target_mm PRESERVED (still 25.0)
6. ESP32: Polls /cmd → "STOP"
7. ESP32: GPIO27 LOW → Relay OFF → Motor stops ✅
8. ESP32: Servo → 90° (neutral)
```

### Step 5: User Resumes

```
1. Frontend: Click "START Conveyor"
2. Frontend: POST /cmd/set { "command": "START" }
3. Server: current_conveyor_cmd = "START"
4. Server: realtime_engine.enable(target_mm=25.0) ← RE-ENABLED with saved target!
5. Frontend: Status shows "🟢 MONITORING" (detection resumes)
6. ESP32: Polls /cmd → "START"
7. ESP32: GPIO27 HIGH → Relay ON → Motor spins
8. Detection continues automatically ✅
   (No need to set target again!)
```

---

## Frontend Controls (HTML)

### Conveyor Control Panel

```html
<div class="card" id="conveyor-panel">
  <div class="card-title">
    🚚 Conveyor Control (ESP32)
  </div>

  <!-- START/STOP Buttons -->
  <div class="cmd-panel">
    <button class="btn btn-success" onclick="setConveyorCommand('START')">
      ▶ START Conveyor
    </button>
    <button class="btn btn-danger" onclick="setConveyorCommand('STOP')">
      ■ STOP Conveyor
    </button>
  </div>

  <!-- Status Display -->
  <div class="cmd-status" id="cmd-status">
    Current command: --
  </div>
  <div class="cmd-status" id="cmd-target-status">
    Desired size: -- mm
  </div>
  <div class="cmd-status" id="cmd-sort-status">
    Latest angle: --
  </div>
</div>
```

### Target Size Control Panel

```html
<div class="form-group">
  <label class="form-label">
    Required Washer Size (mm)
  </label>
  <div class="form-row">
    <input class="form-input"
           id="input-target-size"
           type="number"
           placeholder="e.g., 25">
    <button class="btn btn-primary"
            onclick="setTargetSize()">
      ✓ Set Target
    </button>
  </div>
</div>
```

### Real-Time Monitoring Panel

```html
<div id="realtime-status-panel" class="card">
  <div class="card-title">
    🔍 Real-Time Detection Status
  </div>

  <!-- State Indicator -->
  <div style="display: flex; align-items: center; gap: 12px;">
    <div style="font-size: 1.2rem;" id="rt-status-indicator">
      ⚫
    </div>
    <div>
      <div style="color: var(--text-secondary); margin-bottom: 4px;">
        Current State
      </div>
      <div style="font-size: 1.1rem; font-weight: 600;" id="rt-status-text">
        IDLE
      </div>
    </div>
  </div>

  <!-- Statistics -->
  <div class="counters">
    <div class="counters-label">
      Total Scanned / Matched
    </div>
    <div class="counters-value">
      <span id="rt-total">0</span> / <span id="rt-matched">0</span>
      (<span id="rt-success-rate">0</span>%)
    </div>
  </div>
</div>
```

---

## JavaScript Functions (Frontend)

### Set Conveyor Command

```javascript
async function setConveyorCommand(command) {
  try {
    const res = await fetch(`${API_BASE}/cmd/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
    const data = await res.json();

    if (!data.ok) {
      throw new Error(data.error || 'Failed to set command');
    }

    // Update UI
    document.getElementById('cmd-status').textContent =
      `Current command: ${data.command}`;

    logSuccess(`Conveyor ${data.command}`);
    showSuccess(`Conveyor ${data.command}`);

    // Refresh sort result
    refreshLatestSortResult();

  } catch (e) {
    logError(`Conveyor command error: ${e.message}`);
    showError(`Conveyor command error: ${e.message}`);
  }
}
```

### Set Target Size

```javascript
async function setTargetSize() {
  const sizeStr = document.getElementById('input-target-size').value.trim();

  if (!sizeStr) {
    showError('Enter a valid target size');
    return;
  }

  const targetMM = parseFloat(sizeStr);
  if (isNaN(targetMM) || targetMM <= 0) {
    showError('Size must be a positive number');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/target/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_mm: targetMM })
    });
    const data = await res.json();

    if (!data.ok) {
      throw new Error(data.error || 'Failed to set target');
    }

    // Update UI
    document.getElementById('cmd-target-status').textContent =
      `Desired size: ${targetMM} mm`;
    document.getElementById('target-display').textContent = targetMM;
    document.getElementById('target-set-info').style.display = 'block';

    logSuccess(`Target set: ${targetMM}mm. Conveyor started.`);
    showSuccess(`Target set to ${targetMM}mm`);

  } catch (e) {
    logError(`Target update error: ${e.message}`);
    showError(`Target update error: ${e.message}`);
  }
}
```

### Update Real-Time Status

```javascript
async function refreshRealtimeState() {
  try {
    const res = await fetch(`${API_BASE}/realtime/state`);
    if (!res.ok) return;

    const state = await res.json();
    updateRealtimeUI(state);

  } catch (e) {
    // Silently ignore errors during polling
  }
}

function updateRealtimeUI(state) {
  const stateConfig = {
    'IDLE': { icon: '⚫', color: '#484f58', label: 'IDLE (No Target)' },
    'MONITORING': { icon: '🟢', color: '#3fb950', label: 'MONITORING' },
    'DETECTED': { icon: '🟨', color: '#fb8500',
      label: `DETECTED (${state.elapsed_sec}s/${state.max_time_sec}s)` },
    'PROCESSING': { icon: '🔵', color: '#58a6ff', label: 'PROCESSING...' },
    'COOLDOWN': { icon: '🟠', color: '#fb8500',
      label: `COOLDOWN (${state.max_time_sec - state.elapsed_sec}s)` }
  };

  const config = stateConfig[state.state] || stateConfig['IDLE'];

  document.getElementById('rt-status-indicator').textContent = config.icon;
  document.getElementById('rt-status-text').textContent = config.label;
  document.getElementById('rt-status-text').style.color = config.color;

  // Update statistics
  document.getElementById('rt-total').textContent = state.total_scanned;
  document.getElementById('rt-matched').textContent = state.matched;
  document.getElementById('rt-success-rate').textContent =
    state.success_rate.toFixed(0);
}
```

---

## ESP32 Code Flow

### Polling Pattern

```cpp
void loop() {
  // 1. Check WiFi every 10 seconds
  checkWiFiConnection();

  // 2. Poll /cmd every 500ms
  pollConveyorCommand();
  // └─ Gets: "START" or "STOP"
  // └─ Controls: GPIO27 (conveyor motor)

  // 3. Poll /sort/decision every 1s (only if running)
  pollSortDecision();
  // ├─ Gets: "0", "90", "180", "WAITING", etc
  // └─ Controls: GPIO26 PWM (servo angle)

  // 4. Update status LED
  updateStatusLed();
  // ├─ Indicator: Connected/Disconnected/Running

  // 5. Print diagnostics every 30s
  printStatus();
  // └─ Shows: WiFi, motor, servo, statistics

  // 6. Prevent watchdog timeout
  delay(10);
}
```

### State Management

```cpp
// Global state tracked by ESP32
String lastCmd = "";              // Previous /cmd response
int currentServoAngle = 90;       // Current servo position
bool conveyorRunning = false;     // Motor ON/OFF state
bool wifiConnected = false;       // WiFi status

// Only changes when server response changes
// Prevents unnecessary GPIO updates
```

### Error Handling

```cpp
// WiFi Reconnection (Automatic)
if (WiFi.status() != WL_CONNECTED) {
  // Auto-reconnect every 10 seconds
  if (millis() - lastWiFiCheckMs > 10000) {
    WiFi.reconnect();
  }
}

// HTTP Timeout (1.5 seconds)
http.setTimeout(1500);

// State-based polling
if (!conveyorRunning) {
  // Skip /sort/decision polling (saves bandwidth)
  pollSortDecision(); // returns immediately
}
```

---

## Expected System Outputs

### Server Terminal
```
[SERVER] Running on http://192.168.x.x:5000
[SERVER] Real-time detection worker started

[SERVER] Sorting target set by UI: 25.0mm
[SERVER] Real-time engine enabled with target: 25.0mm

[SERVER] Conveyor STOPPED. Target preserved: 25.0mm
[SERVER] Conveyor STARTED. Real-time engine re-enabled with target: 25.0mm
```

### ESP32 Serial Monitor (115200 baud)
```
═══════════════════════════════════════════════════════════
ESP32 Conveyor & Servo Controller
Real-Time Detection Integration
═══════════════════════════════════════════════════════════

✓ GPIO initialized
  - Conveyor: GPIO 27
  - Servo: GPIO 26
  - LED: GPIO 2
✓ Servo initialized at 90°

========== WiFi Connection ==========
✓ WiFi Connected!
✓ IP: 192.168.x.x
✓ Server: http://10.121.22.234:5000
=====================================

✓ System Ready - Polling server...
  - Conveyor poll: 500ms
  - Sort poll: 1000ms

▶ CONVEYOR STARTED
🔄 Servo → 0° (EQUAL (Target))
⏸ CONVEYOR STOPPED
↻ Servo reset to neutral (90°)

========== Status Report ==========
WiFi: ✓ Connected
Conveyor: ▶ Running
Servo Angle: 0°
Uptime: 245 seconds

Statistics:
  Conveyor polls: 490 (0 failed)
  Sort decisions: 245 (2 failed)
====================================
```

### Web Dashboard
```
Calibration Status: READY (0.0369 mm/px)
Target Size: 25mm
Real-Time Status: 🟢 MONITORING

Total Scanned: 25
Success Rate: 88% (22/25 matched)

Latest Detection:
  Size: 25mm
  Status: ✓ TARGET
  Angle: 0°
```

---

## Testing Checklist

### Pre-Flight Checks

- [ ] Python server running: `python server.py`
- [ ] Web UI accessible: `http://localhost:5000`
- [ ] System calibrated: Badge shows "CALIBRATED"
- [ ] ESP32 uploaded with correct WiFi credentials
- [ ] ESP32 USB connected to PC
- [ ] Relay module wired to GPIO27
- [ ] Servo wired to GPIO26
- [ ] Motor power connected (12V if applicable)

### Functionality Tests

**Test 1: Calibration**
- [ ] Click "Capture Reference"
- [ ] Place 25mm washer in frame
- [ ] Click "Run Calibration"
- [ ] Verify: Badge → "CALIBRATED", shows mm/px

**Test 2: Target Setting**
- [ ] Enter target: 25mm
- [ ] Click "Set Target"
- [ ] Verify: Status shows "🟢 MONITORING"
- [ ] Verify: Motor spins (conveyor starts)

**Test 3: Detection**
- [ ] Place washer in front of camera
- [ ] After 2s: Status shows "🟨 DETECTED"
- [ ] After measurement: Result image displays
- [ ] Verify: Servo rotates (check hardware)

**Test 4: Servo Movement**
- [ ] Check ESP32 Serial Monitor
- [ ] Should show: "🔄 Servo → Xº"
- [ ] Verify: Physical servo moves to that angle

**Test 5: Statistics**
- [ ] Total Scanned counter increases
- [ ] Matched counter increases (if target match)
- [ ] Success rate % calculated correctly

**Test 6: STOP/START Cycle**
- [ ] Click "STOP Conveyor"
- [ ] Verify: Motor stops
- [ ] Verify: Target still shows "25mm"
- [ ] Click "START Conveyor"
- [ ] Verify: Motor starts again
- [ ] Verify: **No need to set target again!** ✅

**Test 7: Multiple Washers**
- [ ] Place 3-5 washers continuously
- [ ] Each should be detected automatically
- [ ] Servo should rotate appropriately
- [ ] Statistics should increment
- [ ] No manual intervention needed

---

## Troubleshooting Quick Reference

| Issue | Check | Fix |
|-------|-------|-----|
| ESP32 won't connect to WiFi | SSID/password in code | Update credentials, re-upload |
| Server unreachable from ESP32 | IP address in code | Check `ipconfig`, update `/cmd/set` response |
| Motor won't respond to START button | Relay connections | Test with multimeter, swap contacts if needed |
| Servo won't move | GPIO26 connection | Check signal wire, test servo independently |
| Target gets lost after STOP | Server code old | Restart server: `python server.py` |
| Engine doesn't re-enable on START | Server code old | Restart server: `python server.py` |
| Status LED always off | GPIO2 power/connection | Check LED polarity, resistor value |

---

## Production Deployment Checklist

### Hardware Security
- [ ] Conveyor belt properly guarded
- [ ] Emergency stop button installed
- [ ] Servo current limiting in place
- [ ] Motor power properly isolated
- [ ] All wires properly secured

### Software Stability
- [ ] Server runs 24/7 without crashing
- [ ] WiFi reconnects automatically
- [ ] Statistics logged to database (optional)
- [ ] Error emails configured (optional)
- [ ] System monitors uptime

### Performance Optimization
- [ ] Detection accuracy >95%
- [ ] Throughput verified (6-12 washers/min)
- [ ] Response time <500ms
- [ ] No WiFi dropouts >1 minute
- [ ] Boot time <30 seconds

---

## Next Steps

1. ✅ Upload `ESP32_Controller.ino` to ESP32
2. ✅ Update WiFi credentials
3. ✅ Update server IP address
4. ✅ Verify WiFi connection (Serial Monitor)
5. ✅ Test button controls (START/STOP)
6. ✅ Test target setting
7. ✅ Test washer detection
8. ✅ Verify servo movement
9. ✅ Deploy to production

**System ready for production use!** 🚀

