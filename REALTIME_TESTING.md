# Real-Time Detection Testing Guide

## Quick Start

### 1. Start the Server
```bash
cd d:/Waser\ Size\ Identifier
python server.py
```

Expected output:
```
[SERVER] Running on http://192.168.x.x:5000
[SERVER] Open in browser : http://192.168.x.x:5000
[RealtimeDetectionEngine] Initialized (IDLE state)
[SERVER] Camera worker started
[SERVER] Real-time detection worker started
[SERVER] Auto processing worker started
```

### 2. Open Web Interface
- Navigate to: `http://localhost:5000` (or your server IP)
- You should see:
  - Calibration panel (Step 1)
  - Live camera feed
  - Real-Time Monitoring status panel (NEW)
  - Detection panel (Step 2, initially disabled)

### 3. Calibrate System First
This is required before any detection works!

1. **Capture Reference Image**
   - Click "📸 Capture Reference" button
   - Place a washer of KNOWN size in front of camera
   - Image appears in "Captured Reference Image" section

2. **Run Calibration**
   - Enter the REAL washer size in mm (e.g., 25)
   - Click "✓ Run Calibration"
   - Wait for detection to complete
   - Calibration image shown with detected circle

3. **Verify Success**
   - Badge changes to "CALIBRATED" (green)
   - Shows: "mm per pixel" value
   - Shows: "Reference: mmm → px" conversion
   - Dashboard updates: Calibration Status → READY

### 4. Test Real-Time Detection

1. **Set Target Size**
   - In "Step 2 — Washer Detection" panel
   - Enter target size (e.g., 25mm)
   - Click "✓ Set Target"

2. **Observe Status Changes**
   - Real-Time Monitoring panel shows: 🟢 MONITORING
   - Place a washer in front of camera
   - After ~0.5s: Status → 🟨 DETECTED with timer
   - Timer counts from 0.0s to 2.0s
   - Progress bar fills during tracking

3. **Watch for Processing**
   - At 2.0s: Status → 🔵 PROCESSING... (spinning)
   - Server captures and measures washer
   - Result image updates with:
     - Green circle (detected edge)
     - Red dot (center)
     - Blue line (diameter)
     - Text: "XXmm | target:25mm | angle:0"

4. **Cooldown Phase**
   - After measurement: Status → 🟠 COOLDOWN (6s remaining)
   - Countdown timer shows remaining seconds
   - Cooldown bar depletes over 6 seconds

5. **Resume Monitoring**
   - After cooldown complete: Status → 🟢 MONITORING
   - Ready for next washer
   - Process repeats indefinitely

### 5. Check Statistics

Real-Time Monitoring panel shows:
```
Total Scanned / Matched: XX / YY (ZZ%)
```

Example:
- Total Scanned: 5 washers detected
- Matched: 4 matched target size
- Success Rate: 80%
- Updates in real-time

### 6. Test API Endpoints

**Check Current State:**
```bash
curl http://localhost:5000/realtime/state
```

Response example:
```json
{
  "state": "MONITORING",
  "elapsed_sec": 0.5,
  "max_time_sec": 0.0,
  "circle_detected": false,
  "detection_x": null,
  "detection_y": null,
  "detection_radius": null,
  "total_scanned": 5,
  "matched": 4,
  "success_rate": 80.0
}
```

**Update Settings (increase stability time to 3 seconds):**
```bash
curl -X POST http://localhost:5000/realtime/settings \
  -H "Content-Type: application/json" \
  -d '{"stable_time": 3.0}'
```

Response:
```json
{
  "ok": true,
  "settings": {"stable_time": 3.0}
}
```

**Test Manual Detection (ESP32 endpoint):**
```bash
curl http://localhost:5000/detect?target=25
```

**Test Sort Decision:**
```bash
curl http://localhost:5000/sort/decision
```

### 7. Verify Backwards Compatibility

**Manual Single-Shot Detection:**
```bash
curl http://localhost:5000/detect
```

Should still work independently of real-time engine.

**ESP32 Size Endpoint:**
```bash
curl http://localhost:5000/size
```

**ESP32 Measure Endpoint:**
```bash
curl http://localhost:5000/measure?target=25&tolerance=0.5
```

Both should work without real-time engine enabled.

## Troubleshooting

### Engine stays IDLE
- ✓ Check: Did you set target size in Step 2 panel?
- ✓ Check: Does calibration say CALIBRATED?
- ✓ Check: Click "Set Target" button (not just entering the number)

### Status shows MONITORING but nothing changes
- ✓ Camera might be learning background (first 60 frames)
- ✓ Check: Is object circular enough? (MIN_CIRCULARITY = 0.7)
- ✓ Try adjusting MIN_CIRCULARITY: `curl -X POST http://localhost:5000/realtime/settings -d '{"min_circularity": 0.6}'`
- ✓ Check: Object area > 1000 pixels (MIN_AREA)
- ✓ Try: `/realtime/settings` with `{"min_area": 500}`

### Status goes DETECTED but doesn't reach PROCESSING
- ✓ Object disappears before 2 seconds → increase stability wait
- ✓ Try: `/realtime/settings` with `{"stable_time": 3.0}`

### Detection shows but says "No washer detected"
- ✓ Circle is detected but Hough circles fails
- ✓ Try: Adjust lighting or camera position
- ✓ Manually test: `curl http://localhost:5000/detect`

### Frontend doesn't update in real-time
- ✓ Browser might cache pages → Hard refresh: Ctrl+F5
- ✓ Check browser console for JavaScript errors: F12 → Console tab
- ✓ Verify: `/realtime/state` responds with curl

### /realtime/state returns error
- ✓ Server might need restart
- ✓ Check server logs for [RealtimeDetectionEngine] errors
- ✓ Try: `curl http://localhost:5000/realtime/state` in terminal

## Performance Tips

1. **Reduce overhead:** Increase STABLE_TIME if washers are moving slowly
2. **More detections:** Decrease COOLDOWN_TIME (minimum recommended: 3.0s)
3. **Better accuracy:** Decrease MIN_CIRCULARITY (range: 0.0-1.0, default: 0.7)
4. **Faster response:** Reduce BG_HISTORY (range: 100-1000, default: 500)

## What's Next

Once you confirm real-time detection works:

1. **Test with ESP32:**
   - ESP32 polls `/sort/decision` to get servo angle
   - Angle classifies: 0 = EQUAL, 90 = LESS, 180 = GREATER
   - Conveyor moves based on angle

2. **Fine-tune Parameters:**
   - Based on actual washer sizes and speeds
   - Use `/realtime/settings` to adjust

3. **Add Conveyor Integration:**
   - Connect servo motor to angle output
   - Test full sorting cycle

## Common State Sequences

### Perfect Detection (Washer passes through)
```
MONITORING → DETECTED (timer: 0→2s) → PROCESSING (1s)
→ COOLDOWN (timer: 6→0) → MONITORING
Total time: ~9 seconds
```

### Object Disappears (Washer blocked/moved)
```
MONITORING → DETECTED (timer: 0→1s)
[Object leaves frame]
→ MONITORING (reset)
```

### Rapid Series
```
MONITORING → DETECTED → PROCESSING → COOLDOWN
[Repeat 5 times in ~45 seconds with 5 washers]
Total Scanned: 5, Matched: 5 (if all target size)
```

## Success Criteria ✓

- [ ] System calibrates and stores mm/pixel factor
- [ ] Frontend shows MONITORING after target is set
- [ ] Circle detected properly when object appears
- [ ] Status progression: DETECTED → PROCESSING → COOLDOWN → MONITORING
- [ ] Washer size measured and displayed correctly
- [ ] Statistics update (total_scanned, matched, success_rate)
- [ ] Detection result image shows annotated circle
- [ ] /realtime/state API responds with correct JSON
- [ ] All ESP32 endpoints still work
- [ ] Manual /detect endpoint still works independently
