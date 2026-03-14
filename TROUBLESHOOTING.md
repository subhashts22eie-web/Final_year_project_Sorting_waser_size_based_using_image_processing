# Troubleshooting Guide - Real-Time Detection + ESP32 Integration

## What Went Wrong? Diagnostic Steps

### STEP 1: Check Server Status

**Is the Flask server still running?**

```bash
# In the terminal where you started server.py, look for:
[SERVER] Running on http://192.168.x.x:5000

# If you see errors, check these:
```

**Common Server Errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'realtime_detection'` | Missing file | Check `realtime_detection.py` exists in project folder |
| `ImportError: cannot import name 'RealtimeDetectionEngine'` | Syntax error in realtime_detection.py | Run: `python -m py_compile realtime_detection.py` |
| `Address already in use` | Port 5000 occupied | Kill process: `netstat -ano \| findstr :5000` then `taskkill /PID <PID> /F` |
| `No module named 'step7_washer_detection'` | Missing dependencies | Check all step*.py files exist |

**Test server is working:**
```bash
curl http://localhost:5000/realtime/state
# Should return JSON, not error
```

---

### STEP 2: Check Real-Time Detection in Web UI

**Navigate to:** `http://localhost:5000`

**Look for:**

- [ ] Calibration panel visible → ("Step 1 — System Calibration")
- [ ] Live camera feed showing → (Real-time video)
- [ ] Real-Time Detection Status panel → (Below live camera with 🟢🟨🔵 indicators)
- [ ] Detection Results panel → (Shows measured size)

**If panels are missing:**
- Hard refresh browser: **Ctrl + F5**
- Clear browser cache
- Check browser console for JS errors: **F12 → Console**

---

### STEP 3: Verify Real-Time API Endpoint

**Test endpoint in command prompt:**

```bash
curl http://localhost:5000/realtime/state
```

**Expected Response:**
```json
{
  "state": "IDLE",
  "elapsed_sec": 0.0,
  "max_time_sec": 0.0,
  "circle_detected": false,
  "detection_x": null,
  "detection_y": null,
  "detection_radius": null,
  "total_scanned": 0,
  "matched": 0,
  "success_rate": 0.0
}
```

**If you get errors:**

| Error | Fix |
|-------|-----|
| `Connection refused` | Server not running |
| `404 Not Found` | Endpoint `/realtime/state` doesn't exist in server.py |
| `500 Internal Server Error` | Bug in realtime_detection.py or server.py |

---

### STEP 4: Test Calibration

**From web UI:**

1. Click "📸 Capture Reference"
2. Place washer in front of camera
3. Enter known size (e.g., 25mm)
4. Click "✓ Run Calibration"

**What should happen:**
- Reference image appears
- Calibration result shows
- Badge changes to green "CALIBRATED"
- mm/px factor displays

**If calibration fails:**

```
Common Issues:
❌ "Could not detect washer. Cannot calibrate."
   → Lighting too dark, washer not visible, or detection settings wrong
   → Solution: Improve lighting, adjust camera angle

❌ "No calibration file found"
   → calibration.json not saved
   → Solution: Check file permissions in project folder
```

---

### STEP 5: Test Real-Time Detection (Without ESP32)

**From web UI:**

1. Calibrate first (see Step 4)
2. In "Step 2 — Washer Detection" panel
3. Enter target size (e.g., 25mm)
4. Click "✓ Set Target"

**Expected:**
- Real-Time Status panel shows "🟢 MONITORING"
- Place washer in front of camera
- After ~2s: Status changes to "🟨 DETECTED" with timer

**If nothing happens:**

```bash
# Check if real-time engine is enabled:
curl http://localhost:5000/realtime/state

# Should show:
{
  "state": "MONITORING",  # ← This indicates engine is running
  ...
}

# If state is still "IDLE":
# - Did you click "Set Target"?
# - Is calibration done?
# - Check server logs for errors
```

---

### STEP 6: Check Server Logs for Errors

**Look in terminal running server.py for:**

```
[RealtimeDetectionEngine] ERROR: ...
[SERVER ERROR] ...
Traceback (most recent call last): ...
```

**Copy full error message and check against these:**

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `[RealtimeDetectionEngine] ERROR: No calibration found` | Calibration not completed | Run calibration first |
| `[RealtimeDetectionEngine] Detection failed: No washer detected` | Circle not found | Adjust MIN_CIRCULARITY or lighting |
| `Traceback... cv2.error` | OpenCV issue | Check camera is working |
| `[RealtimeDetectionEngine] Permission denied` | File write error | Check write permissions on project folder |

---

## Specific Issues & Solutions

### Issue 1: Real-Time Panel Shows "IDLE" Even After Setting Target

**Symptoms:**
- Status indicator: ⚫ IDLE
- No "MONITORING" state
- No detection happening

**Diagnosis:**
```bash
# Check if engine is actually enabled:
curl http://localhost:5000/realtime/state

# Check server logs:
Look for: "[SERVER] Real-time engine enabled with target:"
```

**Solutions:**

**Solution A: Restart Server**
```bash
# Stop server (Ctrl + C in terminal)
# Wait 2 seconds
# Restart: python server.py
# Try setting target again
```

**Solution B: Check Target Set API**
```bash
# Manually send target set command:
curl -X POST http://localhost:5000/target/set ^
  -H "Content-Type: application/json" ^
  -d "{\"target_mm\": 25.0}"

# Check response - should show:
# {"ok": true, "target_mm": 25.0, "command": "START"}

# If error, check server logs for issue
```

**Solution C: Check Calibration**
```bash
# Verify calibration exists:
curl http://localhost:5000/calibration/status

# Should show:
# {"ok": true, "calibrated": true, "mm_per_pixel": 0.0123, ...}

# If calibrated: false, run calibration in web UI first
```

---

### Issue 2: Detection Works But Servo Never Moves (ESP32)

**Symptoms:**
- Real-time detection works fine (shows DETECTED, PROCESSING, COOLDOWN)
- Detection result images show up
- ESP32 is connected to WiFi
- But servo never moves

**Diagnosis:**
```bash
# Check what /sort/decision returns:
curl http://localhost:5000/sort/decision

# Possible responses:
# "0"        → Should move servo to 0°
# "90"       → Should move servo to 90°
# "180"      → Should move servo to 180°
# "STOPPED"  → Conveyor not running
# "NO_TARGET" → No target set
# "WAITING"  → Still detecting

# If returns a number but servo doesn't move:
# - Problem is on ESP32 side (see ESP32 troubleshooting)
```

**Solutions:**

**ESP32 Serial Output Check:**

Open Serial Monitor on ESP32 (115200 baud) and look for:

```
✓ WiFi Connected!
✓ IP: 192.168.x.x
✓ Server: http://10.121.22.234:5000

▶ CONVEYOR STARTED
🔄 Servo → 0° (EQUAL (Target))
```

**If you see this:** Servo IS moving, check if servo is physically working

**If you DON'T see servo message:** ESP32 never received servo command

**Fixes:**

```
A. Check ESP32 WiFi Connection:
   - Serial should show: "✓ WiFi Connected!"
   - If shows disconnected, check SSID/password in Arduino code

B. Check Server IP in ESP32 code:
   - Look for: "const char* serverBaseUrl = "http://10.121.22.234:5000";"
   - Verify this matches your PC IP (use: ipconfig command)

C. Check Conveyor is Running:
   - Serial should show: "▶ CONVEYOR STARTED"
   - If shows "⏸ CONVEYOR STOPPED", click START in web UI

D. Check GPIO26 (Servo pin):
   - Multimeter should show ~1.5V when servo moving
   - If 0V always, servo pin not connected properly
```

---

### Issue 3: ESP32 Won't Connect to WiFi

**Symptoms:**
- Serial Monitor shows: "✗ WiFi Connection Failed!"
- Keeps retrying
- LED not lighting up

**Diagnosis:**

```cpp
// Check Arduino code has correct credentials:
const char* ssid = "Subhash";           // ← Your WiFi name
const char* password = "12233447";      // ← Your WiFi password
```

**Solutions:**

```
1. Verify WiFi Name (SSID) is correct:
   - Should be: "Subhash"
   - Check your phone WiFi list for exact name

2. Verify Password:
   - Should be: "12233447"
   - Check for typos (case-sensitive)

3. Switch to 2.4GHz WiFi:
   - ESP32 only supports 2.4GHz, NOT 5GHz
   - Check router settings or use separate 2.4GHz network

4. Reboot ESP32:
   - Disconnect USB
   - Wait 3 seconds
   - Reconnect USB
   - Watch Serial Monitor for connection attempts

5. Check Router:
   - Can other devices connect?
   - Check router isn't blocking ESP32 MAC address
   - Try temporarily disabling WiFi password (for testing)
```

---

### Issue 4: Can't Reach Server from ESP32

**Symptoms:**
- Serial shows: "⚠ Connection failed"
- Or: "⚠ HTTP error code: 502"

**Diagnosis:**

```bash
# From PC, test server is running:
curl http://localhost:5000/cmd/status

# Test ESP32 can reach PC:
ping YOUR_PC_IP  # Check from ESP32 serial or another PC

# Check Windows Firewall:
netstat -ano | findstr :5000  # Should show LISTENING on 5000
```

**Solutions:**

```
1. Verify PC IP Address:
   - Open Command Prompt
   - Type: ipconfig
   - Look for "IPv4 Address" (e.g., 192.168.x.x or 10.x.x.x)
   - Update ESP32 code with correct IP:
     const char* serverBaseUrl = "http://YOUR_CORRECT_IP:5000";

2. Allow Flask Through Firewall:
   - Windows Firewall might block port 5000
   - Settings → Firewall → Allow app through firewall
   - Add python.exe or Flask app

3. Check Network:
   - ESP32 and PC must be on SAME WiFi network
   - If separate networks, they can't communicate
   - Check WiFi name on both devices

4. Ping Test:
   - From another PC/phone on WiFi: ping YOUR_PC_IP
   - If fails: Network issue, not server issue
   - If works: Server reachability issue, check port 5000
```

---

### Issue 5: Detection Works Perfectly But ESP32 Stops Working After 5 Minutes

**Symptoms:**
- System works fine for a few minutes
- Then ESP32 stops receiving commands
- Serial shows: "⚠ WiFi disconnected!"

**Causes:**
- WiFi unstable
- Too many HTTP connections
- Memory leak

**Solutions:**

```
1. Improve WiFi Stability:
   - Move router closer to ESP32
   - Remove obstacles (metal, water)
   - Reduce distance between ESP32 and router to <10 meters
   - Check for WiFi interference (microwave, cordless phone)

2. Increase WiFi Check Interval:
   Edit ESP32_Controller.ino:
   const unsigned long WIFI_CHECK_INTERVAL_MS = 15000;  // Increase from 10000

3. Add Watchdog Reset:
   In ESP32 setup():
   esp_task_wdt_init(30, true);  // 30 second watchdog
   esp_task_wdt_add(NULL);

4. Rebuild and Re-upload:
   - Delete build cache: Arduino → Sketch → Verify/Compile
   - Upload fresh code
```

---

## Quick Diagnostic Commands

**PC Terminal - Test Server:**
```bash
# 1. Server running?
curl http://localhost:5000/cmd/status

# 2. Calibration done?
curl http://localhost:5000/calibration/status

# 3. Real-time engine working?
curl http://localhost:5000/realtime/state

# 4. Can set target?
curl -X POST http://localhost:5000/target/set -H "Content-Type: application/json" -d "{\"target_mm\": 25}"

# 5. What's the sort decision?
curl http://localhost:5000/sort/decision
```

**ESP32 Serial Monitor - Expected Output:**
```
=============================================
ESP32 Conveyor & Servo Controller
Real-Time Detection Integration
=============================================
✓ GPIO initialized
✓ Servo initialized at 90°
========== WiFi Connection ==========
✓ WiFi Connected!
✓ IP: 192.168.x.x
✓ Server: http://10.121.22.234:5000
=====================================
✓ System Ready - Polling server...
❌ If you don't see this, check errors above
```

---

## Emergency Checklist

If everything is broken, follow this in order:

- [ ] **Restart everything:**
  - Stop server (Ctrl+C)
  - Disconnect ESP32 USB
  - Wait 5 seconds
  - Start server again
  - Reconnect ESP32

- [ ] **Check files exist:**
  - `d:\Waser Size Identifier\server.py` ✓
  - `d:\Waser Size Identifier\realtime_detection.py` ✓
  - `d:\Waser Size Identifier\templates\index.html` ✓
  - `d:\Waser Size Identifier\ESP32_Controller.ino` ✓

- [ ] **Verify Python syntax:**
  ```bash
  python -m py_compile server.py realtime_detection.py
  # No errors should appear
  ```

- [ ] **Test imports:**
  ```bash
  python -c "from realtime_detection import RealtimeDetectionEngine; print('OK')"
  # Should print: OK
  ```

- [ ] **Reload page and calibrate:**
  - Browser: Ctrl+F5 (hard refresh)
  - Recalibrate from scratch
  - Set target again

- [ ] **Check network:**
  ```bash
  ping YOUR_PC_IP
  # Should respond with no timeouts
  ```

---

## Still Having Issues?

**Provide me:**
1. Error message (exact copy from terminal or serial)
2. What you were doing when it broke
3. Output of: `curl http://localhost:5000/realtime/state`
4. ESP32 Serial Monitor output (last 20 lines)
5. Server terminal output (last 20 lines)

Then I can diagnose and fix!

