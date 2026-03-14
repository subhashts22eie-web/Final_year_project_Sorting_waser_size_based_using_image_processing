"""
STEP 3: Complete System with ESP32 (Non-Blocking)
==================================================
Full conveyor monitoring system with THREADING:
1. Detects circular objects in real-time
2. Wait 2 seconds for stable detection
3. Capture image WHILE MOVING
4. Send ESP32 commands in BACKGROUND THREAD (non-blocking!)
5. Process image while ESP32 is working
6. Cooldown and repeat

Key Innovation: ESP32 control runs in background - NO BLOCKING!
"""

import cv2
import numpy as np
import time
import threading
import queue
import requests
from step3_save_image import save_image
from step8_calibration import load_calibration
from step7_washer_detection import detect_washer
from step9_compute_size import pixels_to_mm, match_standard_size

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

CAMERA_INDEX = 0

# ESP32 Configuration
ESP32_IP = "192.168.1.100"          # ← CHANGE THIS TO YOUR ESP32 IP
SIMULATION_MODE = True               # ← Set to False when using real ESP32

ESP32_BASE_URL = f"http://{ESP32_IP}"

# Detection settings
MIN_AREA = 1000
MIN_CIRCULARITY = 0.7
STABLE_TIME = 2.0  # Wait 2 seconds for stable detection before capture

# Background subtraction
BG_HISTORY = 500
BG_VAR_THRESHOLD = 16

# Cooldown after processing (prevents detecting same object twice)
COOLDOWN_TIME = 6.0  # 6 seconds cooldown between detections

# ══════════════════════════════════════════════════════════════════════════════
# ESP32 CONTROLLER (Non-Blocking with Threading)
# ══════════════════════════════════════════════════════════════════════════════

class ESP32Controller:
    """
    Non-blocking ESP32 controller using background thread.
    Commands are queued and executed asynchronously.
    """

    def __init__(self, ip, simulation_mode=True):
        self.ip = ip
        self.base_url = f"http://{ip}"
        self.simulation_mode = simulation_mode
        self.command_queue = queue.Queue()
        self.running = True

        # Start background thread for ESP32 communication
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        """Background worker thread that processes ESP32 commands."""
        while self.running:
            try:
                # Get command from queue (block for 0.1s)
                cmd = self.command_queue.get(timeout=0.1)

                if cmd['action'] == 'stop_conveyor':
                    self._stop_conveyor()
                elif cmd['action'] == 'start_conveyor':
                    self._start_conveyor()
                elif cmd['action'] == 'servo_open':
                    self._servo_open()
                elif cmd['action'] == 'servo_close':
                    self._servo_close()

                self.command_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"  [ESP32 Thread Error] {e}")

    def _stop_conveyor(self):
        """Internal method to stop conveyor."""
        if self.simulation_mode:
            print("  [SIMULATED] ⏸ Conveyor STOPPED")
            return

        try:
            response = requests.get(f"{self.base_url}/stop", timeout=2)
            if response.status_code == 200:
                print("  ⏸ Conveyor STOPPED")
            else:
                print(f"  ✗ Failed to stop: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ Stop error: {e}")

    def _start_conveyor(self):
        """Internal method to start conveyor."""
        if self.simulation_mode:
            print("  [SIMULATED] ▶ Conveyor STARTED")
            return

        try:
            response = requests.get(f"{self.base_url}/start", timeout=2)
            if response.status_code == 200:
                print("  ▶ Conveyor STARTED")
            else:
                print(f"  ✗ Failed to start: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ Start error: {e}")

    def _servo_open(self):
        """Internal method to open servo (e.g., gate/pusher)."""
        if self.simulation_mode:
            print("  [SIMULATED] 🔓 Servo OPEN")
            return

        try:
            response = requests.get(f"{self.base_url}/servo/open", timeout=2)
            if response.status_code == 200:
                print("  🔓 Servo OPEN")
            else:
                print(f"  ✗ Servo open failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ Servo open error: {e}")

    def _servo_close(self):
        """Internal method to close servo."""
        if self.simulation_mode:
            print("  [SIMULATED] 🔒 Servo CLOSED")
            return

        try:
            response = requests.get(f"{self.base_url}/servo/close", timeout=2)
            if response.status_code == 200:
                print("  🔒 Servo CLOSED")
            else:
                print(f"  ✗ Servo close failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ Servo close error: {e}")

    # Public methods (non-blocking - just queue commands)

    def stop_conveyor(self):
        """Queue command to stop conveyor (non-blocking)."""
        self.command_queue.put({'action': 'stop_conveyor'})

    def start_conveyor(self):
        """Queue command to start conveyor (non-blocking)."""
        self.command_queue.put({'action': 'start_conveyor'})

    def servo_open(self):
        """Queue command to open servo (non-blocking)."""
        self.command_queue.put({'action': 'servo_open'})

    def servo_close(self):
        """Queue command to close servo (non-blocking)."""
        self.command_queue.put({'action': 'servo_close'})

    def test_connection(self):
        """Test ESP32 connection (blocking, for initialization only)."""
        if self.simulation_mode:
            return True

        try:
            response = requests.get(f"{self.base_url}/status", timeout=2)
            return response.status_code == 200
        except:
            return False

    def shutdown(self):
        """Shutdown the controller thread."""
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1)

# ══════════════════════════════════════════════════════════════════════════════
# SIZE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def process_captured_image(calib, target_mm=None):
    """
    Process the already-captured image and detect washer size.
    (Image was captured while conveyor was moving)

    Args:
        calib: Calibration data
        target_mm: Optional target size

    Returns:
        dict with success, final_size, measured_mm, pixel_diameter, is_match, deviation
    """
    # Detect washer from the saved image
    img, circle, pixel_diameter = detect_washer()
    if img is None or circle is None:
        print("  ✗ No washer detected in captured image")
        return {'success': False}

    measured_mm = pixels_to_mm(pixel_diameter, calib['mm_per_pixel'])
    matched_size = match_standard_size(measured_mm)
    final_size = matched_size if matched_size else round(measured_mm)

    is_match = None
    deviation = None
    if target_mm is not None:
        deviation = abs(measured_mm - target_mm)
        is_match = deviation <= 3.0

    # Save result
    x, y, r = circle
    result = img.copy()
    cv2.circle(result, (x, y), r, (0, 255, 0), 3)
    cv2.circle(result, (x, y), 4, (0, 0, 255), -1)

    label = f"{final_size}mm"
    if target_mm and is_match is not None:
        label += f" | {'MATCH' if is_match else 'NO MATCH'}"

    cv2.putText(result, label, (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.imwrite("results/detection_result.jpg", result)

    return {
        'success': True,
        'final_size': final_size,
        'measured_mm': measured_mm,
        'pixel_diameter': pixel_diameter,
        'is_match': is_match,
        'deviation': deviation
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main(target_mm=None):
    print("=" * 80)
    print("STEP 3: ESP32 SYSTEM WITH NON-BLOCKING CONTROL")
    print("=" * 80)
    print()

    # Load calibration
    calib = load_calibration()
    if calib is None:
        print("✗ ERROR: System not calibrated!")
        print("  Calibrate first using: python server.py")
        return

    print(f"✓ Calibration: {calib['mm_per_pixel']:.6f} mm/px")
    print(f"✓ Detection time: {STABLE_TIME}s")
    print(f"✓ Cooldown time: {COOLDOWN_TIME}s")

    # Initialize ESP32 controller
    esp32 = ESP32Controller(ESP32_IP, SIMULATION_MODE)

    if SIMULATION_MODE:
        print("⚠ SIMULATION MODE - No actual ESP32 control")
        print(f"  To use real ESP32:")
        print(f"    1. Set ESP32_IP = '{ESP32_IP}' (your ESP32 IP)")
        print(f"    2. Set SIMULATION_MODE = False")
    else:
        print(f"✓ ESP32 IP: {ESP32_IP}")
        print("  Testing connection...")
        if not esp32.test_connection():
            print("  ✗ Cannot connect to ESP32!")
            print("    Check IP address and WiFi connection")
            esp32.shutdown()
            return
        print("  ✓ Connected to ESP32")
        esp32.start_conveyor()  # Ensure conveyor is running

    if target_mm:
        print(f"✓ Target: {target_mm}mm")

    print()
    print("🔄 CONVEYOR WITH ESP32 CONTROL (Non-Blocking Threading)")
    print()
    print("Controls:")
    print("  Q - Quit")
    print("  S - Stop conveyor")
    print("  R - Start conveyor")
    print("  O - Open servo")
    print("  C - Close servo")
    print("=" * 80)
    print()

    # Open camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("✗ Cannot open camera!")
        esp32.shutdown()
        return

    # Background subtractor
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=BG_HISTORY,
        varThreshold=BG_VAR_THRESHOLD,
        detectShadows=False
    )

    print("✓ System ready - MONITORING...\n")

    # State
    state = "MONITORING"
    detection_start_time = None
    cooldown_start_time = None

    # Stats
    total_count = 0
    match_count = 0
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Background subtraction
            fg_mask = bg_subtractor.apply(frame)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

            # Find circles
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            display = frame.copy()

            circular_objects = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < MIN_AREA:
                    continue

                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue

                circularity = 4 * np.pi * area / (perimeter * perimeter)
                if circularity >= MIN_CIRCULARITY:
                    (x, y), radius = cv2.minEnclosingCircle(contour)
                    circular_objects.append({
                        'x': int(x), 'y': int(y), 'radius': int(radius)
                    })

            # ──────────────────────────────────────────────────────────────────────────
            # STATE MACHINE
            # ──────────────────────────────────────────────────────────────────────────

            if state == "MONITORING":
                status = "MONITORING"
                status_color = (0, 255, 0)

                if len(circular_objects) > 0:
                    obj = max(circular_objects, key=lambda o: o['radius'])
                    detection_start_time = time.time()
                    state = "DETECTED"
                    print(f"🔍 Circle detected - tracking...")
                    cv2.circle(display, (obj['x'], obj['y']), obj['radius'], (0, 255, 255), 2)

            elif state == "DETECTED":
                if len(circular_objects) > 0:
                    obj = max(circular_objects, key=lambda o: o['radius'])
                    elapsed = time.time() - detection_start_time

                    cv2.circle(display, (obj['x'], obj['y']), obj['radius'], (0, 255, 255), 3)
                    cv2.putText(display, f"{elapsed:.1f}s", (obj['x'] - 30, obj['y'] + obj['radius'] + 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    status = f"DETECTED ({elapsed:.1f}s)"
                    status_color = (0, 255, 255)

                    if elapsed >= STABLE_TIME:
                        print()
                        print("=" * 80)
                        print("✓ OBJECT STABLE - CAPTURING IMAGE")
                        print("=" * 80)

                        # CAPTURE IMAGE (while conveyor keeps moving)
                        ret, clean_frame = cap.read()
                        if ret and clean_frame is not None:
                            save_image(clean_frame)
                            print("  📸 Image captured (conveyor still moving)")
                        else:
                            print("  ✗ Failed to capture image")
                            state = "MONITORING"
                            detection_start_time = None
                            continue

                        # STOP CONVEYOR (non-blocking - runs in background thread!)
                        print("\n⏸ STOPPING CONVEYOR (background thread)...")
                        esp32.stop_conveyor()

                        state = "PROCESSING"

                else:
                    print("  Object disappeared - resetting...")
                    state = "MONITORING"
                    detection_start_time = None

            elif state == "PROCESSING":
                status = "PROCESSING"
                status_color = (255, 0, 255)

                # PROCESS THE CAPTURED IMAGE (while ESP32 is stopping conveyor!)
                print("\n📊 PROCESSING IMAGE (ESP32 working in background)...")
                result = process_captured_image(calib, target_mm)
                total_count += 1

                if result['success']:
                    print(f"  ✓ Size: {result['final_size']}mm ({result['measured_mm']:.2f}mm, {result['pixel_diameter']}px)")

                    if target_mm and result['is_match'] is not None:
                        if result['is_match']:
                            match_count += 1
                            print(f"  ✓ MATCH (dev: {result['deviation']:.2f}mm)")
                            # Optional: Trigger servo for sorting
                            # esp32.servo_open()
                            # time.sleep(0.5)  # Wait for object to pass
                            # esp32.servo_close()
                        else:
                            print(f"  ✗ NO MATCH (dev: {result['deviation']:.2f}mm)")
                        print(f"  Stats: {match_count}/{total_count} ({100*match_count/total_count:.0f}%)")
                else:
                    print("  ✗ Detection failed")

                print()
                print("▶ STARTING CONVEYOR (background thread)...")
                # START CONVEYOR (non-blocking!)
                esp32.start_conveyor()

                print(f"⏱ Entering cooldown ({COOLDOWN_TIME}s)...\n")
                state = "COOLDOWN"
                cooldown_start_time = time.time()
                detection_start_time = None

            elif state == "COOLDOWN":
                elapsed = time.time() - cooldown_start_time
                remaining = COOLDOWN_TIME - elapsed

                status = f"COOLDOWN ({remaining:.1f}s)"
                status_color = (128, 128, 255)

                if elapsed >= COOLDOWN_TIME:
                    print("✓ Resuming monitoring\n")
                    state = "MONITORING"
                    cooldown_start_time = None

            # ──────────────────────────────────────────────────────────────────────────
            # DISPLAY
            # ──────────────────────────────────────────────────────────────────────────

            if frame_count < 60:
                cv2.putText(display, "LEARNING BACKGROUND...", (10, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            else:
                cv2.putText(display, status, (10, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)

            if total_count > 0:
                stats = f"Scanned: {total_count}"
                if target_mm:
                    stats += f" | Matched: {match_count} ({100*match_count/total_count:.0f}%)"
                cv2.putText(display, stats, (10, 80),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Step 3: ESP32 System - Q=Quit | S=Stop | R=Start | O/C=Servo", display)
            cv2.imshow("Foreground Mask", fg_mask)

            # ──────────────────────────────────────────────────────────────────────────
            # KEYBOARD
            # ──────────────────────────────────────────────────────────────────────────

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n⏹ Stopping system...")
                esp32.start_conveyor()  # Ensure conveyor is running before exit
                time.sleep(0.5)  # Give thread time to process
                break
            elif key == ord('s'):
                print("\n⏸ Manual STOP conveyor...")
                esp32.stop_conveyor()
            elif key == ord('r'):
                print("\n▶ Manual START conveyor...")
                esp32.start_conveyor()
            elif key == ord('o'):
                print("\n🔓 Manual OPEN servo...")
                esp32.servo_open()
            elif key == ord('c'):
                print("\n🔒 Manual CLOSE servo...")
                esp32.servo_close()

    except KeyboardInterrupt:
        print("\n⏹ Interrupted by user...")
        esp32.start_conveyor()
        time.sleep(0.5)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        esp32.shutdown()

        print()
        print("=" * 80)
        print("SYSTEM STOPPED")
        print("=" * 80)
        if total_count > 0:
            print(f"Total scanned: {total_count}")
            if target_mm:
                print(f"Matched: {match_count} ({100*match_count/total_count:.1f}%)")
        print("✓ Non-blocking ESP32 system - No delays in image processing!")
        print()

# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    target = None
    if len(sys.argv) > 1:
        try:
            target = float(sys.argv[1])
        except ValueError:
            print(f"Invalid target: {sys.argv[1]}")
            sys.exit(1)

    main(target_mm=target)
