# PROJECT CLEANUP PLAN

## FILES TO KEEP ✅ (Essential for Image Processing & Frontend)

### Python Core Files (Image Processing)
- `server.py` - Main Flask API server ✅ KEEP
- `realtime_detection.py` - Real-time detection engine ✅ KEEP
- `step3_save_image.py` - Image saving utility ✅ KEEP
- `step7_washer_detection.py` - Washer detection pipeline ✅ KEEP
- `step8_calibration.py` - Calibration system ✅ KEEP
- `step9_compute_size.py` - Size calculation ✅ KEEP

### Frontend
- `templates/index.html` - Web UI ✅ KEEP

### Arduino/ESP32
- `ESP32_Controller.ino` - Latest ESP32 code ✅ KEEP

---

## FILES TO DELETE 🗑️ (Old/Duplicate/Unnecessary)

### Old Server Files (Duplicates/Backups)
- `server_esp32.py` - Old version
- `server_realtime.py` - Old version
- `server_working.py` - Old version/backup
- `main_system.py` - Old version

### Old Arduino Files (Duplicates)
- `esp32_conveyor_client.ino` - Old
- `esp32_conveyor_servo_controller.ino` - Old
- `esp32_polling_controller.ino` - Old

### Test/Debug Files (No longer needed)
- `diagnostic_test.py` - Testing file
- `imageprocess.py` - Old/unused
- `test_speed_comparison.py` - Benchmark (not needed)

### Step-by-step Test Files (No longer needed for final system)
- `step1_circle_detection.py`
- `step1_webcam_test.py`
- `step2_capture.py`
- `step2_detection_with_sizing.py`
- `step3_full_system_esp32.py`
- `step6_image_processing.py`

### Old Documentation (Too many, consolidate)
**DELETE (Duplicates/Old):**
- `ALGORITHM_IMPROVEMENTS.md`
- `APPLIED_FIX.md`
- `BUG_FIX_REVERSED_BUTTONS.md`
- `CODE_CHANGES_EXPLAINED.md`
- `ESP32_QUICK_START.md`
- `ESP32_SERVER_INTEGRATION.md`
- `ESP32_SETUP_CHECKLIST.md`
- `ESP32_SETUP_GUIDE.md`
- `FINAL_SUMMARY.md`
- `FIX_ACTION_PLAN.md`
- `HARDWARE_WIRING_GUIDE.md`
- `INTEGRATION_GUIDE.md`
- `QUICK_FIX_SUMMARY.md`
- `QUICK_TEST_RACE_CONDITION_FIX.md`
- `REALTIME_FIX.md`
- `REALTIME_TESTING.md`
- `SOLUTION.md`
- `STEP_BY_STEP_GUIDE.md`
- `SYSTEM_STATUS.md`
- `TROUBLESHOOTING.md`
- `TUNING_QUICK_REFERENCE.md`

**KEEP (Essential Documentation):**
- `START_HERE.md` - Main guide
- `QUICK_START_GUIDE.md` - Quick reference
- `RACE_CONDITION_FIX.md` - Important technical fix
- `FIX_SUMMARY.md` - Summary of latest fixes
- `ESP32_INTEGRATION_GUIDE.md` - ESP32 setup reference

---

## Summary

**Before Cleanup:**
- 45 total files (messy!)

**After Cleanup:**
- 13 essential files only
- 32 files deleted (duplicates/old)
- Clean, organized project structure

**File Breakdown:**
- 6 core Python modules (image processing)
- 1 frontend (HTML/JS)
- 1 ESP32 code (Arduino)
- 5 documentation files

