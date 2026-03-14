# 🐛 BUG FIX GUIDE - Reversed Buttons & State Issues

## Issue Summary

You're experiencing:
1. ✗ "START Conveyor" button **STOPS** the motor
2. ✗ "STOP Conveyor" button **STARTS** the motor
3. ✗ After STOP, setting target again doesn't auto-start
4. ✗ Asking for target every time START is clicked

## Root Causes & Fixes

### Issue 1: Reversed Button Logic

**Cause:** Either relay wiring is inverted OR GPIO logic needs to be inverted

**Diagnosis - Choose A or B:**

#### **Option A: Check YOUR Relay Wiring**

If using a relay module (most common):

```
Current wiring (if working backwards):
ESP32 GPIO27 → Relay IN
Relay COM ────→ +12V (Motor Power)
Relay NO ─────→ Motor Positive   ← THIS IS PROBLEM!

Should be:
ESP32 GPIO27 → Relay IN
Relay COM ────→ +12V (Motor Power)
Relay NC ─────→ Motor Positive   ← Switch to NC (Normally Closed)
```

**If motor keeps running when GPIO27 is LOW**, swap the relay contacts from NO (Normally Open) to NC (Normally Closed).

**Physical fix:**
1. Stop the system
2. Locate the relay module
3. Move the motor wire from "NO" contact to "NC" contact
4. Restart system - button should now work correctly

---

#### **Option B: Invert GPIO Logic in ESP32 Code**

If you don't want to rewire the relay, invert the logic in `ESP32_Controller.ino`:

**Find this function:**
```cpp
void setConveyor(bool run) {
  digitalWrite(CONVEYOR_PIN, run ? HIGH : LOW);  // ← Change this line
  ...
}
```

**Change to:**
```cpp
void setConveyor(bool run) {
  digitalWrite(CONVEYOR_PIN, run ? LOW : HIGH);  // ← Inverted!
  conveyorRunning = run;

  if (run) {
    Serial.println("▶ CONVEYOR STARTED");
  } else {
    Serial.println("⏸ CONVEYOR STOPPED");
  }
}
```

**Then:**
1. Save the file
2. Upload to ESP32 (Arduino IDE → Upload)
3. Restart ESP32 (unplug/replug USB)
4. Test - buttons should now work correctly

---

### Issue 2 & 3: Target Not Persisting + State Issues

**Fixed in server.py!** ✅

**Changes made:**
- ✅ When STOP is clicked: Target is NOW PRESERVED (not cleared)
- ✅ When START is clicked: Real-time engine NOW RE-ENABLES with saved target
- ✅ No need to set target again after STOP/START cycle

**To apply the fix:**
1. Restart Python server: `python server.py`
2. Test the flow:
   ```
   1. Calibrate
   2. Set target → engine monitors
   3. Click STOP → engine pauses (target saved)
   4. Click START → engine resumes with same target ✅ (NEW!)
   ```

---

## Complete Testing Procedure

### Step 1: Verify Server Fix

**Terminal at server (Windows Command Prompt):**

```bash
curl -X POST http://localhost:5000/cmd/set ^
  -H "Content-Type: application/json" ^
  -d "{\"command\": \"STOP\"}"

# Should respond:
# {"ok": true, "command": "STOP"}

# Check logs for:
# "[SERVER] Conveyor STOPPED. Target preserved: 25mm"
```

---

### Step 2: Fix the Reversed Buttons

**Choose ONE fix below:**

#### **Quick Fix: Swap Relay Contacts** (Physical, ~2 min)

1. Power off system
2. Locate relay module
3. Unplug motor wire from "NO" contact
4. Plug into "NC" contact instead
5. Power on and test

**Test:**
- Click "START Conveyor" → Motor should RUN ✅
- Click "STOP Conveyor" → Motor should STOP ✅

#### **Alternative: Change ESP32 Code** (Firmware, ~3 min)

1. Open Arduino IDE with `ESP32_Controller.ino`
2. Find line with: `digitalWrite(CONVEYOR_PIN, run ? HIGH : LOW);`
3. Change to: `digitalWrite(CONVEYOR_PIN, run ? LOW : HIGH);`
4. Save & Upload to ESP32
5. Test buttons

---

### Step 3: Complete System Flow Test

Once buttons are fixed, test this workflow:

```
1. Calibrate system ✓
   Serial Output: "✓ Calibration successful"

2. Set target (25mm) ✓
   Serial Output: "✓ WiFi Connected!"
   Web UI: Real-time panel shows "🟢 MONITORING"
   Conveyor: Starts (motor spins)

3. Click "STOP Conveyor" button
   Web UI: Real-time panel still shows target "25mm"
   Conveyor: Stops (motor stops)
   Server Log: "[SERVER] Conveyor STOPPED. Target preserved: 25mm"

4. Click "START Conveyor" button
   Conveyor: Starts again (motor spins)
   Real-time Engine: RE-ENABLES ✅ (NEW!)
   Web UI: Status should show "🟢 MONITORING"
   Server Log: "[SERVER] Conveyor STARTED. Real-time engine re-enabled with target: 25mm"

5. Place washer in front of camera
   After 2 seconds: Status → "🟨 DETECTED"
   Servo: Rotates to correct angle
   ✅ System works!

6. Click "STOP Conveyor" button again
   Engine: Pauses (but target still 25mm)
   Allows you to stop without resetting target

7. Click "START Conveyor" button again
   Engine: RESUMES with same target ✅ (No need to set target again!)
```

---

## Troubleshooting Quick Reference

| Symptom | Cause | Fix |
|---------|-------|-----|
| START button still stops motor after step 2 fix | Relay contacts wrong | Check both NO/NC contacts in relay |
| START button works but servo doesn't respond | Target not set | Set target first, THEN click START |
| "Conveyor STOPPED" but motor keeps running | GPIO27 logic inverted | Use Option B (change Arduino code) |
| Motor won't respond to any button | Relay power missing | Check +5V to relay VCC pin |
| Buttons work but target resets | Server not restarted | Restart server: `python server.py` |

---

## Verification Checklist

- [ ] Started Python server with new code: `python server.py`
- [ ] Fixed relay wiring OR changed Arduino code (chose one)
- [ ] Re-uploaded Arduino code if chose code fix
- [ ] Tested start button → motor spins
- [ ] Tested stop button → motor stops
- [ ] Set target, click STOP, click START → no need to set target again
- [ ] Detection continues after START (doesn't ask for target)
- [ ] Statistics counter increments with each washer

All checked? ✅ **System is fixed!**

---

## What Changed in server.py

**Before:**
```python
if cmd == "STOP":
    realtime_engine.disable()  # ← Disabled but target lost
```

**After:**
```python
if cmd == "STOP":
    realtime_engine.disable()  # ← Disabled but TARGET PRESERVED
elif cmd == "START":
    if desired_target_mm is not None:
        realtime_engine.enable(target_mm=desired_target_mm)  # ← RE-ENABLE!
```

This means:
- ✅ Target is saved when you click STOP
- ✅ Engine re-enables when you click START with saved target
- ✅ No need to set target again
- ✅ Seamless pause/resume workflow

---

## Expected System Behavior After Fix

```
Normal Workflow:
1. Calibrate ──→ Set target 25mm ──→ Conveyor runs
                                     ↓
                            Detection running
                                     ↓
                    Place washer → Auto sorted
                                     ↓
                         After 6s cooldown:
                            Ready for next

With STOP/START:
1. Conveyor running ──→ Click STOP
                           ↓
   Conveyor stops, target SAVED
                           ↓
       [Do something else]
                           ↓
                      Click START
                           ↓
   Conveyor resumes, detection continues
   (NO need to set target again!) ✅
```

---

## After Fixes Are Applied

**Run this to verify server fix is active:**

```bash
# Terminal 1: Restart server
python server.py

# Terminal 2: Test the workflow
curl -X POST http://localhost:5000/target/set ^
  -H "Content-Type: application/json" ^
  -d "{\"target_mm\": 25}"

# Should show target is 25mm

curl -X POST http://localhost:5000/cmd/set ^
  -H "Content-Type: application/json" ^
  -d "{\"command\": \"STOP\"}"

# Should show message in server log:
# "[SERVER] Conveyor STOPPED. Target preserved: 25mm"

curl -X POST http://localhost:5000/cmd/set ^
  -H "Content-Type: application/json" ^
  -d "{\"command\": \"START\"}"

# Should show message in server log:
# "[SERVER] Conveyor STARTED. Real-time engine re-enabled with target: 25mm"
```

✅ **If you see "Target preserved" and "re-enabled with target" messages, server fix is working!**

---

## Still Having Issues?

1. **Buttons still reversed after relay swap:**
   - Use Arduino code fix instead (Option B)

2. **Target keeps resetting:**
   - Make sure you restarted `python server.py`
   - Check server terminal for errors

3. **Motor won't respond:**
   - Check relay is getting 5V power
   - Check GPIO27 wire is connected properly
   - Test with multimeter: should see ~3.3V on GPIO27 when START clicked

4. **Serial shows error messages:**
   - Copy the exact error and check TROUBLESHOOTING.md

Let me know what happens after you apply these fixes! 🚀

