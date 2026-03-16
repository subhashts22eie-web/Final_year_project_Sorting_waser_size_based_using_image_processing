# ESP32 Integration - Quick Start (Your System Working)

## You Have Now ✅

- Real-time washer detection: WORKING
- Monitouring & circle detection: WORKING
- Size measurement: WORKING
- Server API (`/realtime/state`, `/cmd`, `/sort/decision`): READY
- Hardware (conveyor + servo): Connected to ESP32

## What Now - 3 Simple Steps

### STEP 1: Upload Enhanced Arduino Code to ESP32

**Your code is good, but I've made it better with:**
- Better WiFi reconnection
- Status LED indicator
- Debug logging
- Statistics tracking
- Better error handling

**Use this file:** `d:\Waser Size Identifier - Copy\esp32_conveyor_servo_controller.ino`

**Upload it:**
1. Open Arduino IDE
2. Open `esp32_conveyor_servo_controller.ino`
3. Update only these lines:
   ```cpp
   const char* WIFI_SSID = "Subhash";         // Your WiFi
   const char* WIFI_PASS = "12233447";        // Your WiFi password
   const char* SERVER_HOST = "10.121.22.234"; // Your PC IP running server.py
   ```
4. Select: **Tools → Board → ESP32 Dev Module**
5. Click **Upload** ⬆️
6. Wait for: "Hard resetting via RTS pin..."

✅ Done!

---

### STEP 2: Verify ESP32 Connected

**Open Serial Monitor:**
1. Tools → Serial Monitor
2. Baud rate: **115200**
3. Look for:
   ```
   ✓ WiFi Connected!
   ✓ IP: 192.168.x.x
   ✓ Server: http://10.121.22.234:5000
   ✓ System Ready - Polling server...
   ```

✅ If you see this, ESP32 is ready!

---

### STEP 3: Test End-to-End

**From web UI (http://localhost:5000):**

1. **Calibrate** (if not done)
   - Capture reference image
   - Enter size & run calibration

2. **Set Target Size** (e.g., 25mm)
   - Status: 🟢 MONITORING
   - Conveyor should START (relay clicks)

3. **Place Washer**
   - Status: 🟨 DETECTED (counts to 2s)
   - Status: 🔵 PROCESSING
   - Result shows detected size

4. **Check Servo Movement**
   - Look at Serial Monitor on ESP32
   - Mapping: `90°` = EQUAL (target hit), `180°` = LESS, `0°` = GREATER
   - Look at physical servo - should move to that angle

5. **Verify Statistics**
   - Web UI shows: Total Scanned: X, Matched: Y

✅ If all 5 work, your system is complete!

---

## Communication Flow

```
Web UI           Server              ESP32
  │                │                   │
  ├─ Set target ──→ /target/set       │
  │                │                   │
  │         Enable engine              │
  │                │                   │
  │                ├─ Start detection  │
  │                │                   │
  │         [Washer enters]            │
  │                │                   │
  │         [2s wait]                  │
  │                │                   │
  │         [Detect + measure]         │
  │                └─ Calculate angle  │
  │                │                   │
  │                ├→ /cmd →START ────→ Polls every 500ms
  │                │   (conveyor)      ├→ Relay ON
  │                │                   │ (motor runs)
  │                │                   │
  │ Show result    ├→ /sort/decision  → Polls every 1s
   │                │   (angle: 0/90/180) ├→ Servo moves (EQUAL=90, LESS=180, GREATER=0)
  │                │                   │
  │ Update stats   │ [6s cooldown]    │
  │                │                   │
  │                ├→ Resume           │
```

---

## Key API Endpoints ESP32 Uses

**From ESP32, these are polled continuously:**

```
GET /cmd           → Response: "START" or "STOP"
GET /sort/decision → Response: "0", "90", "180", "WAITING", "NO_TARGET", "STOPPED"
```

**Server will respond:**
- When conveyor starts: `/cmd` returns "START"
- When object detected & measured: `/sort/decision` returns angle
- When conveyor stops: `/cmd` returns "STOP"

Your server **already handles all this**! ✅

---

## Expected System Behavior

### Timeline for One Washer

```
T=0s    - Washer on conveyor
         ESP32 polls every 500ms: /cmd → "START" (already running)
         Servo: 90° (neutral)

T=0.5s  - Conveyor running
         Camera starts monitoring

T=2s    - Washer detected, 2s stable
         Server: PROCESSING

T=3s    - Measurement done, angle calculated
         Server: COOLDOWN (6s)
         ESP32 polls: /sort/decision → "90" (EQUAL) or "180" (LESS) or "0" (GREATER)
         Servo: Moves to angle

T=4s    - Washer sorted to correct bin

T=9s    - COOLDOWN complete
         Server: MONITORING (ready for next)
         ESP32 polls: /sort/decision → "WAITING"
         Servo: Stays at last angle

T=10s+  - Next washer can be detected
```

---

## Verification Checklist

Before declaring "Done", verify:

- [ ] **Server running:** `curl http://localhost:5000/cmd/status` works
- [ ] **ESP32 connected:** Serial Monitor shows "✓ WiFi Connected!"
- [ ] **Calibrated:** Badge shows "CALIBRATED" in web UI
- [ ] **Target set:** Real-Time panel shows "🟢 MONITORING"
- [ ] **Conveyor works:** Motor spins when "SET TARGET" clicked
- [ ] **Detection works:** Washer shows as "🟨 DETECTED" after 2s
- [ ] **Servo moves:** Serial Monitor shows "🔄 Servo → Xº"
- [ ] **Result shows:** Detection result image displays size
- [ ] **Statistics update:** "Total Scanned" increases
- [ ] **System cycles:** Servo returns to 90° after cooldown

All 10 checks = **✅ COMPLETE**

---

## Error Scenarios & Fixes

| What You See | ESP32 Serial | Fix |
|---|---|---|
| Conveyor won't start | "⚠ WiFi lost" | Check WiFi SSID/password, restart ESP32 |
| Servo won't move | "▶ CONVEYOR STARTED" but no servo message | Check GPIO26 connection, servo power |
| Detection doesn't trigger | Real-time shows "IDLE" | Calibrate first, then set target |
| HTTP errors (502/503) | "⚠ Connection failed" | Check PC IP address in Arduino code |
| Multiple servo moves | Shows "[ESP32 SERVO]" logs repeatedly | Normal - ESP32 polls while conveyor running |

---

## Your Files

Everything is ready to use:

```
d:\Waser Size Identifier\
├── esp32_conveyor_servo_controller.ino  ← Upload this to ESP32 (conveyor + servo)
├── ESP32_SETUP_CHECKLIST.md          ← Follow this
├── ESP32_INTEGRATION_GUIDE.md        ← Full details
├── TROUBLESHOOTING.md                ← If issues
├── REALTIME_TESTING.md               ← Testing guide
│
├── server.py                         ← Already has /cmd, /sort/decision
├── realtime_detection.py             ← Real-time detection engine
├── templates/
│   └── index.html                    ← Web UI
└── ... (detection modules)
```

---

## 30-Second Summary

1. **Upload `esp32_conveyor_servo_controller.ino`** (update WiFi credentials)
2. **Open Serial Monitor** (verify "WiFi Connected")
3. **Set target in web UI** (monitor starts, conveyor runs)
4. **Place washer** (detection & servo test)
5. **Done!** 🎉

---

## Next: Full Production Setup

After basic testing works, check:

- **Hardware Safeguards:**
  - Emergency stop button
  - Conveyor belt guards
  - Servo current limiting

- **Advanced Features:**
  - Mechanical bins with limit switches
  - Data logging (statistics to database)
  - Email alerts for errors
  - Dashboard for monitoring

- **Performance:**
  - Throughput: 6-12 washers/minute
  - Accuracy: >95% detection
  - Reliability: 24/7 operation

---

## Support

If you hit any issues:

1. Check **TROUBLESHOOTING.md** for diagnosis
2. Look in **Serial Monitor on ESP32** for error messages
3. Check **server.py terminal** for Python errors
4. Verify `/realtime/state` API responds
5. Test `/cmd` and `/sort/decision` endpoints with curl

**Ready to go!** 🚀

