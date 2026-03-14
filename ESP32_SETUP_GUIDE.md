# ESP32 Hardware Setup Guide

## Overview
This system uses ESP32 to control:
1. **Conveyor Motor** - via L298N motor driver
2. **Servo Motor** - for sorting/gate mechanism

The Python system communicates with ESP32 using **non-blocking threading** to prevent delays in image processing.

---

## Required Hardware

### Main Components
- **ESP32 DevKit** (any variant with WiFi)
- **L298N Motor Driver Module**
- **DC Motor** (for conveyor belt, 12V recommended)
- **Servo Motor** (SG90 or MG996R)
- **12V Power Supply** (for motor)
- **5V Power Supply** (for ESP32, or use USB)

### Optional
- Breadboard and jumper wires
- LED for status indication

---

## Wiring Diagram

### L298N Motor Driver → ESP32
```
L298N Pin    →  ESP32 Pin
─────────────────────────
ENA (PWM)    →  GPIO 12
IN1          →  GPIO 14
IN2          →  GPIO 27
GND          →  GND
```

### L298N → DC Motor
```
L298N Pin    →  Motor
─────────────────────────
OUT1         →  Motor +
OUT2         →  Motor -
```

### L298N Power
```
L298N Pin    →  Power Supply
─────────────────────────
12V          →  12V+ (motor power)
GND          →  12V- (ground)
5V           →  Leave disconnected (or use for ESP32 if no USB)
```

### Servo Motor → ESP32
```
Servo Wire   →  ESP32 Pin
─────────────────────────
Signal (Yellow/Orange) → GPIO 13
VCC (Red)    →  5V
GND (Brown)  →  GND
```

### Complete Connection Summary
```
┌─────────────────┐
│     12V PSU     │
│   ┌───┐         │
│   │+12V│─────────┼───→ L298N (12V)
│   │GND │─────────┼───→ L298N (GND) ──→ ESP32 (GND)
│   └───┘         │
└─────────────────┘

┌─────────────────┐
│  L298N Driver   │
│  ┌────────────┐ │
│  │ ENA  → 12  │ │──→ ESP32
│  │ IN1  → 14  │ │──→ ESP32
│  │ IN2  → 27  │ │──→ ESP32
│  │ OUT1/OUT2  │ │──→ DC Motor
│  └────────────┘ │
└─────────────────┘

┌─────────────────┐
│   Servo Motor   │
│  ┌────────────┐ │
│  │ Signal→ 13 │ │──→ ESP32
│  │ VCC → 5V   │ │──→ ESP32 (or external 5V)
│  │ GND → GND  │ │──→ ESP32
│  └────────────┘ │
└─────────────────┘
```

---

## ESP32 Pin Configuration

| Function | ESP32 Pin | Purpose |
|----------|-----------|---------|
| Motor PWM | GPIO 12 | Speed control (ENA on L298N) |
| Motor Dir 1 | GPIO 14 | Direction control (IN1 on L298N) |
| Motor Dir 2 | GPIO 27 | Direction control (IN2 on L298N) |
| Servo Signal | GPIO 13 | Servo position control |

---

## Software Setup

### 1. Install Arduino IDE Libraries
```
Tools → Manage Libraries → Search and Install:
  - ESP32Servo (by Kevin Harrington)
```

### 2. Configure WiFi
Edit `esp32_conveyor_servo_controller.ino`:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

### 3. Upload to ESP32
1. Select Board: **ESP32 Dev Module**
2. Select Port: Your ESP32 COM port
3. Click **Upload**
4. Open **Serial Monitor** (115200 baud)
5. Note the IP address displayed

### 4. Configure Python Script
Edit `step3_full_system_esp32.py`:
```python
ESP32_IP = "192.168.1.100"          # ← Your ESP32 IP from Serial Monitor
SIMULATION_MODE = False              # ← Set to False for real ESP32
```

---

## Testing ESP32

### 1. Test via Web Browser
Open: `http://YOUR_ESP32_IP/`

You should see:
- Conveyor control buttons (START/STOP)
- Servo control buttons (OPEN/CLOSE)
- Current status

### 2. Test via Command Line
```bash
# Get status
curl http://YOUR_ESP32_IP/status

# Start conveyor
curl http://YOUR_ESP32_IP/start

# Stop conveyor
curl http://YOUR_ESP32_IP/stop

# Open servo
curl http://YOUR_ESP32_IP/servo/open

# Close servo
curl http://YOUR_ESP32_IP/servo/close
```

Expected response: `200 OK` with message

### 3. Test via Python
```bash
# Set SIMULATION_MODE = False in step3_full_system_esp32.py
python step3_full_system_esp32.py 25
```

During operation you can also use keyboard controls:
- **S** - Stop conveyor manually
- **R** - Start conveyor manually
- **O** - Open servo manually
- **C** - Close servo manually
- **Q** - Quit

---

## How It Works

### Non-Blocking Architecture

```
┌─────────────────────────────────────────────┐
│         PYTHON MAIN THREAD                  │
│  (IMAGE PROCESSING - Never blocked!)        │
│                                              │
│  1. Camera captures frames (30 FPS)         │
│  2. Background subtraction                  │
│  3. Circle detection                        │
│  4. Capture image when stable               │
│  5. Process image and detect size           │
│                                              │
└─────────────┬───────────────────────────────┘
              │
              │ Commands queued (non-blocking)
              ▼
┌─────────────────────────────────────────────┐
│       ESP32 CONTROLLER THREAD               │
│  (Background - Handles ESP32 commands)      │
│                                              │
│  - Processes command queue                  │
│  - Sends HTTP requests to ESP32             │
│  - No blocking of main thread!              │
│                                              │
└─────────────┬───────────────────────────────┘
              │
              │ HTTP Requests
              ▼
┌─────────────────────────────────────────────┐
│           ESP32 WEB SERVER                  │
│                                              │
│  /start        → Start conveyor motor       │
│  /stop         → Stop conveyor motor        │
│  /servo/open   → Open servo (90°)           │
│  /servo/close  → Close servo (0°)           │
│  /status       → Get system status          │
│                                              │
└─────────────────────────────────────────────┘
```

### Key Benefits
✅ **No Delays** - Image processing runs at full speed
✅ **No Blocking** - ESP32 commands execute in background
✅ **Real-time** - Camera processes at 30 FPS continuously
✅ **Responsive** - System reacts immediately to detections

---

## Typical Operation Sequence

```
1. MONITORING STATE
   Camera watching for circular objects
   Conveyor running ▶

2. CIRCLE DETECTED
   Yellow circle appears
   Tracking for 2 seconds... 🔍

3. STABLE DETECTION
   ✓ Circle stable for 2s
   📸 Capture image (conveyor still moving!)

4. BACKGROUND THREAD (ESP32)
   ⏸ Send stop command to ESP32
   (Python continues processing image...)

5. PROCESSING STATE
   📊 Detect washer size
   📏 Measure diameter
   ✓ Match to standard size

   💾 Save results:
   - capture.jpg (raw image)
   - results/detection_result.jpg (annotated)

6. RESTART & COOLDOWN
   ▶ Send start command to ESP32
   ⏱ Wait 6 seconds (cooldown)

7. BACK TO MONITORING
   Repeat from step 1
```

---

## Troubleshooting

### ESP32 Won't Connect to WiFi
- Check SSID and password are correct
- Ensure 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- Check WiFi signal strength
- Try resetting ESP32

### Motor Doesn't Run
- Check 12V power supply is connected
- Verify L298N wiring
- Check motor connections (try swapping OUT1/OUT2)
- Test with web interface first
- Adjust `MOTOR_SPEED` in Arduino code (0-255)

### Servo Not Moving
- Check servo is getting 5V power
- Verify GPIO 13 connection
- Test with web interface
- Try different servo angles in code
- Ensure servo is not mechanically stuck

### Python Can't Connect to ESP32
- Verify ESP32 IP address
- Check both on same WiFi network
- Test with: `curl http://ESP32_IP/status`
- Check firewall isn't blocking
- Set `SIMULATION_MODE = True` for testing without ESP32

### Image Processing Slow
- This should NOT happen with threading!
- Check CPU usage
- Reduce camera resolution if needed
- Verify ESP32 commands are in background thread

---

## Servo Motor Usage Examples

The servo can be used for:

### 1. Sorting Gate
```python
if result['is_match']:
    # Good washer - open gate to accept bin
    esp32.servo_open()
    time.sleep(0.5)  # Wait for washer to pass
    esp32.servo_close()
else:
    # Bad washer - keep gate closed (goes to reject bin)
    pass
```

### 2. Pusher Mechanism
```python
# Push detected washer off conveyor
esp32.servo_open()   # Push
time.sleep(0.3)
esp32.servo_close()  # Retract
```

### 3. Diverter Arm
Open servo to different angles for multiple bins:
```cpp
// In ESP32 code, add angle parameter endpoint:
server.on("/servo/angle", []() {
  int angle = server.arg("angle").toInt();
  sorterServo.write(angle);
  server.send(200, "text/plain", "OK");
});
```

---

## Adjustable Parameters

### In Arduino Code (`esp32_conveyor_servo_controller.ino`)
```cpp
const int MOTOR_SPEED = 200;         // Conveyor speed (0-255)
const int SERVO_CLOSED_ANGLE = 0;    // Closed position
const int SERVO_OPEN_ANGLE = 90;     // Open position
```

### In Python Code (`step3_full_system_esp32.py`)
```python
ESP32_IP = "192.168.1.100"    # Your ESP32 IP
SIMULATION_MODE = False        # True for testing, False for production
STABLE_TIME = 2.0              # Detection time (seconds)
COOLDOWN_TIME = 6.0            # Cooldown between detections
MIN_AREA = 1000                # Minimum object size (pixels)
MIN_CIRCULARITY = 0.7          # Circle detection threshold
```

---

## System Ready Checklist

- [ ] ESP32 powered and connected to WiFi
- [ ] IP address noted from Serial Monitor
- [ ] L298N connected to 12V power supply
- [ ] Motor wired to L298N (OUT1/OUT2)
- [ ] Servo connected to GPIO 13, 5V, GND
- [ ] Web interface accessible at `http://ESP32_IP/`
- [ ] Motor responds to START/STOP commands
- [ ] Servo responds to OPEN/CLOSE commands
- [ ] Python script configured with correct IP
- [ ] SIMULATION_MODE set to False
- [ ] System calibrated (calibration.json exists)
- [ ] Camera working and positioned correctly

---

## Next Steps

1. **Upload ESP32 firmware** → Note IP address
2. **Test endpoints** → Use browser or curl
3. **Configure Python script** → Set ESP32_IP
4. **Run system** → `python step3_full_system_esp32.py 25`
5. **Monitor operation** → Check Serial Monitor and Python output

The system is now ready for continuous operation with no blocking delays! 🚀
