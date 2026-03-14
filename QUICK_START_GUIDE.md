# Quick Start Guide - Complete Washer Detection System

## System Overview

This system uses:
- **Python** - Image processing and Flask server
- **ESP32** - Polls Flask server for conveyor/servo commands
- **Webcam** - Detects circular objects and measures size

## 📁 Files You Need

### Arduino (ESP32)
- `esp32_polling_controller.ino` - Upload this to ESP32

### Python (PC)
- `main_system.py` - Main program (runs everything!)
- `server_esp32.py` - Flask server (imported by main_system.py)
- `step3_save_image.py` - Image capture
- `step7_washer_detection.py` - Washer detection
- `step8_calibration.py` - Calibration functions
- `step9_compute_size.py` - Size calculations
- `calibration.json` - Calibration data (must exist!)

---

## 🚀 Setup Instructions

### Step 1: Hardware Setup

#### ESP32 Wiring
```
Conveyor Motor (via relay or driver):
  GPIO 27 → Conveyor control

Servo Motor (MG995 or SG90):
  GPIO 26 → Servo signal (yellow/orange wire)
  5V      → Servo VCC (red wire)
  GND     → Servo GND (brown wire)
```

### Step 2: Upload ESP32 Firmware

1. **Edit WiFi credentials** in `esp32_polling_controller.ino`:
   ```cpp
   const char* ssid = "YourWiFiName";      // ← Change this
   const char* password = "YourPassword";   // ← Change this
   ```

2. **Get your PC IP address**:
   - Windows: Open CMD → `ipconfig` → Look for "IPv4 Address"
   - Example: `10.121.22.234`

3. **Edit server URL** in `esp32_polling_controller.ino`:
   ```cpp
   const char* serverBaseUrl = "http://10.121.22.234:5000";  // ← Your PC IP
   ```

4. **Upload to ESP32**:
   - Connect ESP32 via USB
   - Tools → Board → ESP32 Dev Module
   - Tools → Port → (Select your ESP32 port)
   - Click **Upload**

5. **Open Serial Monitor** (115200 baud):
   - Note the ESP32's IP address
   - Should show "✓ WiFi Connected!"
   - Should show "✓ System Ready - Polling for commands..."

### Step 3: Test ESP32 (Optional but Recommended)

Before running the full system, test ESP32 manually:

```bash
# Start a simple test server
python server_esp32.py
```

In another terminal:
```bash
# Test endpoints
curl http://localhost:5000/cmd
curl http://localhost:5000/sort/decision
curl http://localhost:5000/status
```

You should see ESP32 Serial Monitor responding to commands!

### Step 4: Calibrate the System

**IMPORTANT**: System must be calibrated before running!

```bash
# Start calibration server
python server.py

# Open browser
http://localhost:5000

# Follow calibration steps in web interface
```

This creates `calibration.json` file with mm/pixel ratio.

### Step 5: Run the Complete System

```bash
# Run with target size (e.g., 25mm washers)
python main_system.py 25

# Or run without target (detection only)
python main_system.py
```

Expected output:
```
================================================================================
WASHER DETECTION SYSTEM WITH FLASK SERVER
================================================================================

✓ Calibration: 0.145679 mm/px
✓ Detection time: 2.0s
✓ Cooldown time: 6.0s
✓ Target size: 25mm
✓ Auto-sorting: ENABLED
  - Accept angle: 0°
  - Reject angle: 180°

🌐 STARTING FLASK SERVER...
✓ Flask server running on http://0.0.0.0:5000

ESP32 should now poll:
  - http://YOUR_PC_IP:5000/cmd
  - http://YOUR_PC_IP:5000/sort/decision

⏸ Initializing conveyor as IDLE
  Press 'S' to start conveyor manually

Controls:
  Q - Quit
  S - Start conveyor
  P - Stop/Pause conveyor
  D - Debug: Show server state
================================================================================

✓ System ready - Waiting for START command...
```

### Step 6: Start Detection

Press **S** key in the video window to start the conveyor!

---

## 🎮 Keyboard Controls

| Key | Action |
|-----|--------|
| **S** | Start conveyor (begin monitoring) |
| **P** | Pause conveyor (stop monitoring) |
| **D** | Debug - show server state |
| **Q** | Quit system |

---

## 🔄 System Operation Flow

```
1. Press 'S' to START
   └─> ESP32 starts conveyor motor
   └─> System enters MONITORING state

2. MONITORING
   └─> Camera watches for circular objects
   └─> Background subtraction detects motion

3. CIRCLE DETECTED
   └─> Yellow circle appears on screen
   └─> Tracks for 2 seconds (STABLE_TIME)
   └─> Status shows "DETECTED (X.Xs)"

4. STABLE DETECTION
   └─> Image captured WHILE MOVING (fast!)
   └─> Server sends STOP command to ESP32
   └─> ESP32 stops conveyor

5. PROCESSING
   └─> Detect washer in captured image
   └─> Measure size (pixels → mm)
   └─> Match to standard sizes
   └─> Compare to target (if specified)

6. SORTING (if enabled)
   └─> MATCH: Server sends angle 0° (ACCEPT)
   └─> NO MATCH: Server sends angle 180° (REJECT)
   └─> ESP32 moves servo to position

7. RESUME
   └─> Server sends START command to ESP32
   └─> ESP32 starts conveyor
   └─> System enters COOLDOWN (6 seconds)

8. COOLDOWN
   └─> Wait 6 seconds
   └─> Prevents detecting same object twice
   └─> Servo returns to neutral (90°)
   └─> Back to MONITORING

9. REPEAT
   └─> Process next washer
```

---

## 📊 Understanding the Display

### Camera Window

**Status Colors:**
- **Gray**: WAITING FOR START - Press 'S'
- **Green**: MONITORING - Watching for objects
- **Yellow**: DETECTED - Tracking object
- **Purple**: PROCESSING - Analyzing image
- **Light Blue**: COOLDOWN - Waiting before next detection

**Statistics:**
```
Total: 10 | Accept: 8 | Reject: 2
```

### Serial Monitor (ESP32)

```
▶ CONVEYOR STARTED          ← Conveyor motor running
🔄 Servo moved to: 0°       ← Sorting accepted washer
⏸ CONVEYOR STOPPED          ← Motor stopped for processing
```

---

## ⚙️ Configuration

### In `main_system.py`

```python
# Flask Server
FLASK_PORT = 5000

# Detection timing
STABLE_TIME = 2.0      # Wait 2s before capture
COOLDOWN_TIME = 6.0    # Wait 6s between detections

# Detection thresholds
MIN_AREA = 1000         # Minimum object size (pixels)
MIN_CIRCULARITY = 0.7   # 0.7 = 70% circular (1.0 = perfect circle)

# Sorting
ENABLE_SORTING = True           # Enable/disable auto-sorting
SERVO_ACCEPT_ANGLE = 0          # Angle for accepted washers
SERVO_REJECT_ANGLE = 180        # Angle for rejected washers
SERVO_NEUTRAL_ANGLE = 90        # Neutral position
```

### In `esp32_polling_controller.ino`

```cpp
// WiFi
const char* ssid = "YourWiFi";
const char* password = "YourPassword";
const char* serverBaseUrl = "http://YOUR_PC_IP:5000";

// Pins
const int CONVEYOR_PIN = 27;
const int SORT_SERVO_PIN = 26;

// Polling rates
const unsigned long POLL_INTERVAL_MS = 500;    // Poll conveyor cmd
const unsigned long SORT_INTERVAL_MS = 1000;   // Poll sort decision
```

---

## 🐛 Troubleshooting

### ESP32 won't connect to WiFi
- ✓ Check SSID and password are correct
- ✓ ESP32 only supports 2.4GHz WiFi (not 5GHz)
- ✓ Check Serial Monitor for error messages
- ✓ Try resetting ESP32

### ESP32 can't reach Flask server
- ✓ Check PC IP address is correct
- ✓ Ensure PC and ESP32 on same WiFi network
- ✓ Test server: `curl http://YOUR_PC_IP:5000/status`
- ✓ Disable Windows Firewall temporarily (for testing)
- ✓ Check Flask server is running (should see "Flask server running...")

### Python error: "System not calibrated!"
```bash
# You must calibrate first!
python server.py
# Open http://localhost:5000 and calibrate
```

### Python error: "Cannot open camera!"
- ✓ Check webcam is connected
- ✓ Close other programs using webcam (Skype, Teams, etc.)
- ✓ Try `CAMERA_INDEX = 1` (or 2) in main_system.py

### No circles detected
- ✓ Adjust `MIN_AREA` - decrease if washers too small
- ✓ Adjust `MIN_CIRCULARITY` - decrease to 0.6 for less perfect circles
- ✓ Improve lighting - add overhead LED
- ✓ Check camera focus

### Detects circles when nothing there
- ✓ Increase `MIN_AREA` to ignore noise
- ✓ Increase `MIN_CIRCULARITY` to 0.8 for stricter detection
- ✓ Improve lighting consistency
- ✓ Reduce camera vibration

### Servo doesn't move
- ✓ Check servo wiring (GPIO 26, 5V, GND)
- ✓ Test servo: See Serial Monitor for "Servo moved to: X°"
- ✓ Check servo isn't mechanically stuck
- ✓ Verify servo type (MG995 or SG90)

### Conveyor doesn't stop/start
- ✓ Check GPIO 27 wiring
- ✓ See Serial Monitor for "CONVEYOR STARTED/STOPPED"
- ✓ Test with manual commands (S/P keys)
- ✓ Check relay or motor driver connections

---

## 📸 Saved Files

System automatically saves:

```
d:\Waser Size Identifier\
  ├── capture.jpg                    ← Raw captured image
  └── results/
      └── detection_result.jpg       ← Annotated result with size
```

New images overwrite previous ones. To save history, modify `save_image()` to add timestamps.

---

## 🎯 Testing Checklist

Before production use:

- [ ] ESP32 connected to WiFi
- [ ] ESP32 Serial Monitor shows "System Ready"
- [ ] Python shows "Flask server running"
- [ ] System calibrated (calibration.json exists)
- [ ] Webcam working (green window appears)
- [ ] Press 'S' → Conveyor starts
- [ ] Press 'P' → Conveyor stops
- [ ] Place washer → Circle detected (yellow)
- [ ] After 2s → Image captured
- [ ] Conveyor stops automatically
- [ ] Size detected and displayed
- [ ] Servo moves (if sorting enabled)
- [ ] Conveyor restarts automatically
- [ ] Statistics update correctly

---

## 💡 Tips

1. **Lighting is critical!**
   - Use diffused overhead LED
   - Avoid shadows and reflections
   - Consistent lighting = better detection

2. **Camera position**
   - Mount perpendicular to belt
   - Focus on detection area
   - Minimize vibration

3. **Calibration accuracy**
   - Use precise reference object
   - Measure with calipers if possible
   - Re-calibrate if camera moves

4. **Sorting timing**
   - Adjust `SORT_INTERVAL_MS` based on conveyor speed
   - Ensure servo has time to move before washer passes
   - Test with slow speed first

5. **Debug mode**
   - Press 'D' anytime to see server state
   - Check Serial Monitor for ESP32 commands
   - Watch statistics for accuracy

---

## 🚀 You're Ready!

Your complete washer detection and sorting system is now operational:

✅ **Image processing** - Real-time circle detection
✅ **Size measurement** - Accurate mm measurement
✅ **ESP32 control** - Non-blocking Flask polling
✅ **Automatic sorting** - Servo-based sorting
✅ **Statistics** - Accept/reject tracking

**Start the system:**
```bash
python main_system.py 25
```

Then press **'S'** in the video window to begin!

Good luck! 🎯
