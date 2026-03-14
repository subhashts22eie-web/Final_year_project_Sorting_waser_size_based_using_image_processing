# WASHER DETECTION SYSTEM - STEP BY STEP GUIDE

## Overview
This guide walks through the 3-step washer detection system that replaces the IR sensor with vision-based circle detection.

**System Flow:**
1. **Conveyor Moving** → Webcam monitors for circular objects using background subtraction
2. **Circle Detected & Stable** → Capture image WHILE MOVING (fast response!)
3. **Stop Conveyor** → via ESP32
4. **Process Captured Image** → Measure washer size using existing detection system
5. **Start Conveyor** → Cooldown period and repeat

**Key Innovation:** Image is captured while the conveyor is still moving for faster response time!

---

## Prerequisites

### Hardware
- Webcam (min 720p recommended)
- ESP32 with L298N motor driver (for Step 3 only)
- Conveyor belt with motor
- Good lighting above conveyor

### Software
```bash
pip install opencv-python numpy requests
```

### Existing System Files (Must Have)
- `step3_save_image.py` - Save captured images
- `step7_washer_detection.py` - Detect washer in saved image
- `step8_calibration.py` - Load calibration data
- `step9_compute_size.py` - Convert pixels to mm and match standard sizes
- `calibration.json` - Calibration file (create using web interface)

---

## STEP 1: Test Circle Detection

### Purpose
Verify that background subtraction and circular object detection work correctly.

### Run
```bash
python step1_circle_detection.py
```

### What You'll See
- **Window 1**: Live video with detection overlay
- **Window 2**: Foreground mask (black = background, white = moving objects)

### Expected Behavior
1. First 2-3 seconds: "LEARNING BACKGROUND..." - Keep area clear!
2. Status changes to "MONITORING" - System ready
3. Move circular object into frame:
   - **Yellow circle + timer**: Object detected, tracking stability
   - **Green circle + "STABLE ✓"**: Object stable for 0.5s (would trigger capture in full system)
4. Console prints detection info when object becomes stable

### Troubleshooting

**Problem: No detection / Too many false detections**
- Adjust `MIN_AREA` - Increase to ignore small noise, decrease if washer not detected
- Adjust `MIN_CIRCULARITY` - Default 0.7 is good, reduce to 0.6 for less perfect circles
- Adjust `BG_VAR_THRESHOLD` - Lower = more sensitive (default 16)

**Problem: Background keeps changing**
- Keep lighting consistent
- Avoid shadows moving across conveyor
- Increase `BG_HISTORY` to 1000 for slower adaptation

**Problem: Detects belt as motion**
- Normal! The system filters by circularity - belt patterns won't be circular
- If belt has circular patterns, increase `MIN_CIRCULARITY` to 0.8

### Success Criteria
✅ Circular object detected when placed on conveyor
✅ Yellow → Green transition after 0.5 seconds
✅ Detection count increases
✅ No false detections from belt movement

---

## STEP 2: Test Detection + Sizing

### Purpose
Combine circle detection with washer size measurement (without ESP32 control).

### Prerequisites
**IMPORTANT:** System must be calibrated first!

```bash
# Run calibration server
python server.py

# Open browser
http://localhost:5000

# Follow calibration steps in web interface
```

### Run
```bash
# Without target size (detection only)
python step2_detection_with_sizing.py

# With target size (e.g., 25mm washers)
python step2_detection_with_sizing.py 25
```

### What You'll See
1. **Console Output:**
   ```
   ✓ Calibration loaded: 0.145679 mm/px
   ✓ Target size: 25mm  (if specified)
   MONITORING...
   ```

2. **Detection Process:**
   ```
   🔍 Circle detected - tracking...

   ================================================================================
   ✓ OBJECT STABLE - CAPTURING AND DETECTING SIZE
   ================================================================================
     📸 Clean image captured
     ✓ Detected: 25mm
       Measured: 24.87mm (171px)
       ✓ MATCH (deviation: 0.13mm)
     Statistics: 5/5 matched (100%)

   → In real system: Conveyor would START here
     Entering cooldown...

   ✓ Cooldown complete - resuming monitoring
   ```

3. **Saved Files:**
   - `capture.jpg` - Clean captured image
   - `results/detection_result.jpg` - Annotated result with size

### Expected Behavior
1. Status: "MONITORING" (green)
2. Circular object appears → "TRACKING (0.5s)" (yellow)
3. After 0.5s → "PROCESSING..." (purple)
4. Clean image captured (no background artifacts)
5. Size detected and displayed
6. If target specified: MATCH/NO MATCH status
7. "COOLDOWN" (light blue) for 2 seconds
8. Back to "MONITORING"

### Troubleshooting

**Problem: "ERROR: System not calibrated!"**
```bash
python server.py
# Visit http://localhost:5000 and calibrate
```

**Problem: "No washer detected in image"**
- Check `results/capture.jpg` - is washer clearly visible?
- Adjust camera angle/position
- Improve lighting
- Check calibration is correct

**Problem: Size always wrong**
- Re-calibrate system with accurate reference object
- Check camera hasn't moved since calibration
- Verify reference object size was entered correctly

**Problem: Matches when shouldn't / Doesn't match when should**
- Tolerance is ±3mm (hardcoded in `capture_clean_image_and_detect`)
- Improve calibration accuracy
- Check washer isn't deformed

### Success Criteria
✅ System loads calibration
✅ Circle detection triggers size measurement
✅ Clean image saved (no background subtraction artifacts)
✅ Size measured and matched to standard sizes
✅ If target specified: correct MATCH/NO MATCH
✅ Statistics tracking works

---

## STEP 3: Full System with ESP32

### Purpose
Complete production system with conveyor control.

### ESP32 Setup

#### 1. Upload Firmware
```cpp
// File: esp32_conveyor_controller.ino
// Configure WiFi:
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Upload to ESP32
// Note the IP address displayed in Serial Monitor
```

#### 2. Test ESP32 Endpoints
```bash
# Replace with your ESP32 IP
curl http://192.168.1.100/status
curl http://192.168.1.100/stop
curl http://192.168.1.100/start
```

#### 3. Configure Python Script
Edit `step3_full_system_esp32.py`:
```python
ESP32_IP = "192.168.1.100"  # ← YOUR ESP32 IP HERE
SIMULATION_MODE = False      # ← Set to False for real ESP32
```

### Run
```bash
# Test mode (no ESP32 needed)
python step3_full_system_esp32.py

# With target size
python step3_full_system_esp32.py 25

# Production mode (requires ESP32)
# 1. Edit ESP32_IP in script
# 2. Set SIMULATION_MODE = False
python step3_full_system_esp32.py 25
```

### What You'll See

**SIMULATION MODE:**
```
================================================================================
STEP 3: COMPLETE SYSTEM WITH ESP32
================================================================================

✓ Calibration: 0.145679 mm/px
⚠ SIMULATION MODE - No actual ESP32 control
  To use real ESP32:
    1. Set ESP32_IP = "192.168.1.100" (your ESP32 IP)
    2. Set SIMULATION_MODE = False
✓ Target: 25mm

Controls:
  Q - Quit
  R - Manually restart conveyor
================================================================================

✓ System ready - MONITORING conveyor...

🔍 Circle detected - tracking...

================================================================================
✓ OBJECT STABLE - CAPTURING IMAGE WHILE MOVING
================================================================================
  📸 Image captured (while moving)

⏸ STOPPING CONVEYOR
  [SIMULATED] ✓ Conveyor STOPPED

📊 PROCESSING CAPTURED IMAGE...
  ✓ Size: 25mm (24.87mm, 171px)
  ✓ MATCH (dev: 0.13mm)
  Stats: 1/1 (100%)

▶ STARTING CONVEYOR
  [SIMULATED] ✓ Conveyor STARTED
  Entering cooldown...

✓ Resuming monitoring
```

**PRODUCTION MODE (Real ESP32):**
```
✓ ESP32 IP: 192.168.1.100
  Testing connection...
  ✓ Conveyor STARTED

🔍 Circle detected - tracking...

================================================================================
✓ OBJECT STABLE - CAPTURING IMAGE WHILE MOVING
================================================================================
  📸 Image captured (while moving)

⏸ STOPPING CONVEYOR
  ✓ Conveyor STOPPED        ← Motor stops after capture!

📊 PROCESSING CAPTURED IMAGE...
  ✓ Size: 25mm (24.87mm, 171px)
  ✓ MATCH (dev: 0.13mm)
  Stats: 1/1 (100%)

▶ STARTING CONVEYOR
  ✓ Conveyor STARTED
  Entering cooldown...
```

### Expected Behavior
1. **MONITORING** - Conveyor running, camera watching
2. **Circle detected** - Yellow circle tracking
3. **STABLE** → **CAPTURE IMAGE** (while still moving!) ⚡
4. **STOP CONVEYOR** (HTTP request to ESP32)
5. **Wait 0.3s** - Motor stops completely
6. **PROCESSING** - Analyze captured image, detect size
7. **START CONVEYOR** (HTTP request to ESP32)
8. **COOLDOWN** - Wait 2 seconds (prevents duplicate detection)
9. **Back to MONITORING**

### Troubleshooting

**Problem: "Cannot connect to ESP32!"**
- Check ESP32 is powered and connected to WiFi
- Verify IP address: `curl http://ESP32_IP/status`
- Check firewall isn't blocking port 80
- Ensure PC and ESP32 on same network

**Problem: Motor doesn't stop**
- Test ESP32 endpoints directly: `curl http://ESP32_IP/stop`
- Check motor connections: GPIO 12 (ENA), 14 (IN1), 27 (IN2)
- Verify L298N power supply (motor power separate from ESP32)
- Check Serial Monitor for ESP32 errors

**Problem: Motor stops but doesn't restart**
- Check console for "Failed to start conveyor" errors
- Test: Press 'R' key to manually restart
- Verify ESP32 uptime (might have crashed)

**Problem: Detects same washer multiple times**
- Increase `COOLDOWN_TIME` (default 2.0 seconds)
- Increase `STABLE_TIME` (default 0.5 seconds)
- Check conveyor speed - might be too slow

**Problem: Misses some washers**
- Decrease `STABLE_TIME` to 0.3 seconds
- Decrease `MIN_AREA` if washers are small
- Check camera framerate (should be 30 FPS)

### Success Criteria
✅ ESP32 connection established
✅ Conveyor stops when washer detected
✅ Clean image captured while stopped
✅ Size measured correctly
✅ Conveyor restarts after measurement
✅ System handles continuous operation
✅ Statistics tracking accurate

---

## Configuration Tuning

### Detection Sensitivity

```python
# Increase to ignore small objects
MIN_AREA = 1000

# Perfect circle = 1.0, decrease to detect ovals
MIN_CIRCULARITY = 0.7

# How long object must be visible (seconds)
STABLE_TIME = 0.5
```

### Background Subtraction

```python
# Higher = more stable but slower to adapt
BG_HISTORY = 500

# Lower = more sensitive to small movements
BG_VAR_THRESHOLD = 16
```

### Timing

```python
# Wait after measurement before next detection
COOLDOWN_TIME = 2.0

# Wait after stopping motor (mechanical settling)
time.sleep(0.3)
```

---

## Production Checklist

Before deploying to production:

- [ ] System calibrated with accurate reference object
- [ ] Step 1 tested: Circle detection works reliably
- [ ] Step 2 tested: Size detection accurate
- [ ] ESP32 firmware uploaded and tested
- [ ] Motor control verified (stop/start)
- [ ] Lighting consistent and adequate
- [ ] Camera positioned correctly (perpendicular to belt)
- [ ] Camera focused
- [ ] Test with actual washers (multiple sizes if applicable)
- [ ] Verify match/no-match accuracy
- [ ] Test continuous operation (30+ minutes)
- [ ] Check for false positives/negatives
- [ ] Adjust timing parameters for conveyor speed
- [ ] Monitor statistics for accuracy

---

## Common Issues

### False Detections
- Shadows moving across belt → Improve lighting consistency
- Belt vibration → Increase MIN_AREA
- Reflections → Use diffused lighting, avoid direct overhead lights

### Missed Detections
- Washer too small → Decrease MIN_AREA
- Washer not circular enough → Decrease MIN_CIRCULARITY
- Moving too fast → Increase camera framerate or slow conveyor

### Size Measurement Errors
- Camera moved since calibration → Re-calibrate
- Poor focus → Adjust camera focus
- Lighting changed → Maintain consistent lighting
- Washer tilted/warped → Ensure flat placement on belt

---

## System Architecture

```
┌─────────────┐
│   WEBCAM    │
└──────┬──────┘
       │ 30 FPS
       ▼
┌─────────────────────────────────────┐
│  BACKGROUND SUBTRACTION (MOG2)      │
│  - Detects moving objects           │
│  - Learns background dynamically    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  CIRCULARITY FILTER                 │
│  - Identifies circular objects      │
│  - Filters belt/noise               │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  STABILITY TRACKING                 │
│  - Tracks object for 0.5s           │
│  - Prevents false triggers          │
└──────┬──────────────────────────────┘
       │ STABLE
       ▼
┌─────────────────────────────────────┐
│  CAPTURE IMAGE (WHILE MOVING!) ⚡   │
│  - Fresh frame (no BG artifacts)    │
│  - Save as capture.jpg              │
│  - FAST: Don't wait for stop!       │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  STOP CONVEYOR (ESP32 HTTP)         │
│  GET http://ESP32_IP/stop           │
└──────┬──────────────────────────────┘
       │ Wait 0.3s
       ▼
┌─────────────────────────────────────┐
│  PROCESS CAPTURED IMAGE             │
│  - Hough Circle Transform           │
│  - Find washer in saved image       │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  SIZE CALCULATION                   │
│  - Pixels → mm (calibration)        │
│  - Match standard sizes             │
│  - Compare to target (optional)     │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  START CONVEYOR (ESP32 HTTP)        │
│  GET http://ESP32_IP/start          │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  COOLDOWN (2 seconds)               │
│  - Prevents duplicate detection     │
└──────┬──────────────────────────────┘
       │
       └──────► BACK TO MONITORING
```

---

## Quick Reference

### File Structure
```
Washer Size Identifier/
├── step1_circle_detection.py          # Test: Circle detection only
├── step2_detection_with_sizing.py     # Test: Detection + sizing
├── step3_full_system_esp32.py         # Production: Full system
├── step3_save_image.py                # Library: Save images
├── step7_washer_detection.py          # Library: Detect washer in image
├── step8_calibration.py               # Library: Calibration functions
├── step9_compute_size.py              # Library: Size calculations
├── calibration.json                   # Calibration data
├── esp32_conveyor_controller.ino      # ESP32 firmware
└── STEP_BY_STEP_GUIDE.md              # This file
```

### Command Quick Reference
```bash
# Step 1: Test circle detection
python step1_circle_detection.py

# Step 2: Test detection + sizing
python step2_detection_with_sizing.py 25

# Step 3: Full system (simulation)
python step3_full_system_esp32.py 25

# Step 3: Full system (production)
# Edit ESP32_IP and SIMULATION_MODE first
python step3_full_system_esp32.py 25

# Calibration
python server.py
# Visit http://localhost:5000
```

### Keyboard Controls
- **Q**: Quit program (auto-restarts conveyor)
- **R**: Manually restart conveyor (Step 3 only)

### Status Colors
- **Green**: MONITORING - Ready and watching
- **Yellow**: DETECTED/TRACKING - Object found, checking stability
- **Purple**: PROCESSING - Capturing and measuring
- **Light Blue**: COOLDOWN - Waiting before next detection

---

## Support

If you encounter issues not covered in this guide:

1. Check all files are present (especially calibration.json)
2. Verify Python dependencies installed
3. Test each step independently (1 → 2 → 3)
4. Check console output for specific error messages
5. Verify camera permissions and hardware connections

---

**System Ready!** Start with Step 1 and work your way through. Good luck! 🎯
