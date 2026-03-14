# System Integration Guide

## ✅ Your System is Already Complete!

### What You Have

Your `server.py` already includes **ALL** ESP32 functionality:

#### **1. ESP32 Polling Endpoints** (Built-in)
```python
# In server.py (lines 27-37, 394-469):

@app.route('/cmd')           # ESP32 polls this for "START"/"STOP"
@app.route('/sort/decision') # ESP32 polls this for servo angles
@app.route('/cmd/set')       # Web UI sets conveyor command
@app.route('/target/set')    # Web UI sets target size
@app.route('/sort/latest')   # Web UI shows latest result
```

#### **2. Auto Processing** (Built-in)
```python
# Background thread automatically runs detection
# when conveyor is "START" and target is set
def auto_processing_worker():
    # Runs every 2 seconds automatically!
```

#### **3. Web Frontend** (Already Complete!)
Your `templates/index.html` has:
- ✅ Conveyor START/STOP buttons
- ✅ Target size setting
- ✅ Live camera feed
- ✅ Automatic detection display
- ✅ Statistics dashboard
- ✅ Calibration interface

---

## 🚀 How to Use Your Complete System

### **System Architecture**

```
┌─────────────────────────────────────────┐
│  Web Browser (Frontend)                 │
│  http://localhost:5000                  │
│                                          │
│  [START] [STOP] [Set Target: 25mm]     │
│  Live Camera Feed | Detection Results   │
└──────────────┬──────────────────────────┘
               │ REST API
               ▼
┌─────────────────────────────────────────┐
│  server.py (Flask Backend)              │
│                                          │
│  • /cmd → Returns "START" or "STOP"     │
│  • /sort/decision → Returns angle       │
│  • Auto detection thread (every 2s)     │
└──────────────┬──────────────────────────┘
               │ HTTP Polling
               ▼
┌─────────────────────────────────────────┐
│  ESP32 (Arduino)                        │
│                                          │
│  • Polls /cmd every 500ms               │
│  • Polls /sort/decision every 1s        │
│  • Controls conveyor (GPIO 27)          │
│  • Controls servo (GPIO 26)             │
└─────────────────────────────────────────┘
```

---

## 📋 Complete Setup Instructions

### **Step 1: Upload ESP32 Code**

1. Open `esp32_polling_controller.ino` in Arduino IDE
2. Edit WiFi credentials:
   ```cpp
   const char* ssid = "YourWiFi";
   const char* password = "YourPassword";
   ```
3. Edit server URL (use your PC's IP):
   ```cpp
   const char* serverBaseUrl = "http://10.121.22.234:5000";  // Your PC IP!
   ```
4. Upload to ESP32
5. Open Serial Monitor (115200 baud) - note the ESP32 IP

### **Step 2: Start Flask Server**

```bash
python server.py
```

Expected output:
```
[SERVER] Camera worker started
[SERVER] Auto processing worker started
[SERVER] Running on http://10.121.22.234:5000
[SERVER] Open in browser : http://10.121.22.234:5000
[SERVER] ESP32 endpoints : /size  /capture  /measure  /cmd  /sort/decision
```

### **Step 3: Open Web Interface**

```
http://localhost:5000
```

or

```
http://YOUR_PC_IP:5000
```

### **Step 4: Calibrate System**

1. **In Web UI:**
   - Click "📸 Capture Reference"
   - Enter known washer size (e.g., 25mm)
   - Click "✓ Run Calibration"
   - System should show "CALIBRATED" badge

### **Step 5: Start Detection**

1. **In Web UI:**
   - Enter target size (e.g., 25mm)
   - Click "✓ Set Target"
   - Conveyor will START automatically
   - Detection runs every 2 seconds automatically

### **Step 6: Monitor System**

Watch the web UI for:
- Live camera feed
- Detection results (size, match/no-match)
- Servo angles (0=EQUAL, 90=LESS, 180=GREATER)
- Statistics (total scanned, success rate)

Watch ESP32 Serial Monitor for:
- Conveyor commands (START/STOP)
- Servo movements (angle changes)

---

## 🎛️ Web UI Features

### **Dashboard (Top Section)**
```
⚙️ Calibration Status    🎯 Target Size    📊 Total Scanned    ✓ Success Rate
     READY                   25mm               157               94%
```

### **Conveyor Control Panel**
```
🚚 Conveyor Control (ESP32)

[▶ START Conveyor]  [■ STOP Conveyor]  [↻ Refresh Status]

Current command: START
Desired size: 25 mm
Latest angle: 0 deg | Size: 25 mm | EQUAL
```

### **Calibration Panel**
```
⚽ Step 1 — System Calibration  [CALIBRATED]

[📸 Capture Reference]

Reference Washer Size (mm): 25
[✓ Run Calibration]
```

### **Detection Panel**
```
🎯 Step 2 — Washer Detection

Required Washer Size (mm): 25
[✓ Set Target]

[Live Camera Feed showing real-time video]

Detected Size:   25mm
               ✓ TARGET

Measured: 24.87mm | Deviation: 0.13mm | Pixels: 171px
Matched / Total Scanned: 15 / 16
```

---

## 🔄 How Auto Detection Works

1. **Web UI:** User sets target size (25mm) and clicks "Set Target"
2. **Server:**
   - Sets `desired_target_mm = 25`
   - Sets `current_conveyor_cmd = "START"`
   - Starts auto processing thread
3. **Auto Thread:** Every 2 seconds:
   - Captures image
   - Detects washer
   - Measures size
   - Computes angle (0=EQUAL, 90=LESS, 180=GREATER)
   - Stores result in `latest_sort_result`
4. **ESP32:**
   - Polls `/cmd` → Gets "START" → Runs conveyor
   - Polls `/sort/decision` → Gets angle → Moves servo
5. **Web UI:**
   - Auto-refreshes every 2 seconds
   - Displays latest result

---

## 📊 Sorting Logic

```python
def classify_angle(final_size_mm, target_mm):
    if size == target:
        return 0    # EQUAL - Accept bin
    if size < target:
        return 90   # LESS - Maybe neutral/reject
    return 180      # GREATER - Reject bin
```

Example for target=25mm:
- Detected 25mm → Angle 0° (EQUAL/ACCEPT)
- Detected 22mm → Angle 90° (LESS)
- Detected 28mm → Angle 180° (GREATER/REJECT)

---

## ⚠️ Important Notes

### **No Need for main_system.py!**
Your `server.py` already has everything `main_system.py` does:
- ✅ Background camera worker
- ✅ Auto processing thread
- ✅ ESP32 endpoints
- ✅ Web UI endpoints
- ✅ Sorting logic

### **ESP32 Configuration**
Make sure in `esp32_polling_controller.ino`:
```cpp
const char* serverBaseUrl = "http://YOUR_PC_IP:5000";  // NOT localhost!
```

### **Firewall**
If ESP32 can't connect:
- Temporarily disable Windows Firewall
- Or add rule to allow port 5000

---

## 🧪 Testing Workflow

### **Test 1: Verify ESP32 Polling**
1. Start server.py
2. Check Serial Monitor shows:
   ```
   ✓ WiFi Connected!
   ✓ IP Address: 192.168.1.xxx
   ✓ Server: http://10.121.22.234:5000
   ✓ System Ready - Polling for commands...
   ```

### **Test 2: Manual Conveyor Control**
1. In Web UI, click "▶ START Conveyor"
2. ESP32 Serial Monitor should show:
   ```
   ▶ CONVEYOR STARTED
   ```
3. Click "■ STOP Conveyor"
4. ESP32 Serial Monitor should show:
   ```
   ⏸ CONVEYOR STOPPED
   ```

### **Test 3: Auto Detection**
1. Calibrate system
2. Set target size (25mm)
3. Web UI shows "Current command: START"
4. Every 2 seconds, server processes a washer
5. Web UI updates with results
6. ESP32 gets servo angles

### **Test 4: Full System**
1. Place washer on conveyor
2. System detects automatically
3. Displays size on web UI
4. ESP32 moves servo
5. Statistics update

---

## 🎯 Your Complete File List

### **Files You Use:**
```
d:\Waser Size Identifier\
├── server.py                          ✅ Main Flask server (USE THIS!)
├── esp32_polling_controller.ino       ✅ ESP32 firmware
├── templates/
│   └── index.html                     ✅ Web interface
├── step3_save_image.py               ✅ Image capture
├── step7_washer_detection.py         ✅ Detection
├── step8_calibration.py               ✅ Calibration
├── step9_compute_size.py              ✅ Size computation
└── calibration.json                   ✅ Calibration data
```

### **Files You DON'T Need:**
```
❌ main_system.py         (server.py has everything)
❌ server_esp32.py        (server.py has everything)
```

---

## 🚀 Quick Start Command

Just run this:

```bash
python server.py
```

Then open browser to:
```
http://localhost:5000
```

That's it! Everything is integrated and ready to go! 🎉

---

## 💡 Tips

1. **Live Camera Feed**
   - Automatically shows on web UI
   - No need to manually capture

2. **Auto Mode**
   - Set target size once
   - System runs automatically
   - ESP32 polls for commands

3. **Manual Control**
   - Use START/STOP buttons anytime
   - Override auto mode if needed

4. **Statistics**
   - Dashboard tracks everything
   - Total scanned, success rate
   - Real-time updates

5. **Debug**
   - Check browser console (F12)
   - Check Python terminal output
   - Check ESP32 Serial Monitor

Your system is production-ready! 🎯
