"""
Real-Time Washer Detection Engine
==================================
Continuous monitoring with state machine:
IDLE -> MONITORING -> DETECTED -> PROCESSING -> COOLDOWN -> MONITORING

Integrates background subtraction, circle tracking, and size measurement.
Thread-safe, designed to run as a background process in server.py.
"""

import cv2
import numpy as np
import time
import threading
from step3_save_image import save_image
from step7_washer_detection import detect_washer
from step8_calibration import load_calibration
from step9_compute_size import pixels_to_mm, match_standard_size

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class RealtimeDetectionEngine:
    """
    Real-time washer detection with state machine.

    States: IDLE, MONITORING, DETECTED, PROCESSING, COOLDOWN

    Usage:
        engine = RealtimeDetectionEngine(shared_state_dict, target_mm)
        engine.enable()  # Start monitoring
        while True:
            frame = camera.read()
            engine.process_frame(frame)
            state = engine.get_state()
            print(state['state'])
    """

    # Configuration constants
    MIN_AREA = 1000              # Minimum contour area
    MIN_CIRCULARITY = 0.7        # Minimum circularity (0-1)
    STABLE_TIME = 2.0            # Seconds to wait for stability

    BG_HISTORY = 500             # Frames for background learning
    BG_VAR_THRESHOLD = 16        # Sensitivity (lower = more sensitive)

    COOLDOWN_TIME = 6.0          # Seconds between detections

    def __init__(self, shared_state_dict, target_mm=None):
        """
        Initialize the detection engine.

        Args:
            shared_state_dict: Reference to server's shared state (e.g., latest_sort_result)
            target_mm: Target size in mm (can be set later via enable())
        """
        self.shared_state = shared_state_dict
        self.target_mm = target_mm

        # State machine
        self.state = "IDLE"
        self.state_start_time = None
        self.detection_start_time = None
        self.cooldown_start_time = None

        # Detection tracking
        self.detected_circle = None      # (x, y, radius) tuple if currently detected
        self.detection_frame_count = 0

        # Statistics
        self.total_scanned = 0
        self.matched_count = 0

        # Background subtractor (initialize when enabled)
        self.bg_subtractor = None
        self.is_enabled = False

        # Thread safety
        self.lock = threading.Lock()

        print("[RealtimeDetectionEngine] Initialized (IDLE state)")

    def enable(self, target_mm=None):
        """Start monitoring. Target size must be set."""
        if target_mm is not None:
            self.target_mm = target_mm

        if self.target_mm is None:
            print("[RealtimeDetectionEngine] ERROR: Cannot enable without target_mm")
            return False

        with self.lock:
            self.is_enabled = True
            self.state = "MONITORING"
            self.state_start_time = time.time()
            self.detection_start_time = None
            self.cooldown_start_time = None

            # Initialize background subtractor
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=self.BG_HISTORY,
                varThreshold=self.BG_VAR_THRESHOLD,
                detectShadows=False
            )

            print(f"[RealtimeDetectionEngine] Enabled - Target: {self.target_mm}mm")

        return True

    def disable(self):
        """Stop monitoring."""
        with self.lock:
            self.is_enabled = False
            self.state = "IDLE"
            self.state_start_time = None
            self.detection_start_time = None
            self.cooldown_start_time = None
            self.detected_circle = None
            self.bg_subtractor = None

        print("[RealtimeDetectionEngine] Disabled -> IDLE")

    def _find_circular_objects(self, frame, fg_mask):
        """
        Find circular objects in foreground mask.

        Returns:
            list of dicts: [{'x': int, 'y': int, 'radius': int, 'area': float, 'circularity': float}, ...]
        """
        # Clean mask with morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        circular_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.MIN_AREA:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity >= self.MIN_CIRCULARITY:
                (x, y), radius = cv2.minEnclosingCircle(contour)
                circular_objects.append({
                    'x': int(x),
                    'y': int(y),
                    'radius': int(radius),
                    'area': area,
                    'circularity': circularity
                })

        return circular_objects

    def _perform_detection(self):
        """
        Perform actual detection: capture, detect washer, calculate size.
        Updates shared_state with results.

        Returns:
            bool: True if detection successful
        """
        try:
            # Load calibration
            calib = load_calibration()
            if calib is None:
                print("[RealtimeDetectionEngine] ERROR: No calibration found")
                return False

            # Detect washer from last saved image (capture.jpg)
            img, circle, pixel_diameter = detect_washer()
            if img is None or circle is None:
                print("[RealtimeDetectionEngine] Detection failed: No washer detected")
                return False

            # Calculate size
            measured_mm = pixels_to_mm(pixel_diameter, calib['mm_per_pixel'])
            matched_size = match_standard_size(measured_mm)
            final_size = matched_size if matched_size else round(measured_mm)

            # Check if matches target
            is_match = False
            if self.target_mm is not None:
                deviation = abs(measured_mm - self.target_mm)
                is_match = deviation <= 3.0

            # Classify angle (for sorting)
            if self.target_mm is not None:
                target_int = int(round(float(self.target_mm)))
                size_int = int(round(float(final_size)))
                if size_int == target_int:
                    angle, relation = 0, "EQUAL"
                elif size_int < target_int:
                    angle, relation = 90, "LESS"
                else:
                    angle, relation = 180, "GREATER"
            else:
                angle, relation = 0, "EQUAL"

            # Save annotated result
            x, y, r = circle
            output = img.copy()
            cv2.circle(output, (x, y), r, (0, 255, 0), 3)
            cv2.circle(output, (x, y), 4, (0, 0, 255), -1)
            cv2.line(output, (x - r, y), (x + r, y), (255, 0, 0), 2)

            label = f"{final_size}mm"
            if self.target_mm is not None:
                label += f" | target:{self.target_mm}mm | angle:{angle}"

            cv2.putText(output, label, (10, 34),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

            import os
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            result_img = os.path.join(results_dir, "step7_washer_detected.jpg")
            cv2.imwrite(result_img, output)

            # Update shared state
            result = {
                "ok": True,
                "matched_size": int(final_size),
                "measured_mm": float(measured_mm),
                "pixel_diameter": int(pixel_diameter),
                "angle": int(angle),
                "relation": relation,
                "timestamp": time.time()
            }

            if self.target_mm is not None:
                result.update({
                    "target_mm": float(self.target_mm),
                    "deviation_mm": float(abs(measured_mm - self.target_mm)),
                    "is_match": bool(is_match)
                })

            # Update shared state (thread-safe via caller's lock)
            self.shared_state.update(result)

            # Update local statistics
            self.total_scanned += 1
            if is_match:
                self.matched_count += 1

            print(f"[RealtimeDetectionEngine] Detection SUCCESS: {final_size}mm")
            return True

        except Exception as e:
            print(f"[RealtimeDetectionEngine] Detection ERROR: {e}")
            return False

    def process_frame(self, frame):
        """
        Process one camera frame through the state machine.

        Args:
            frame: BGR frame from camera
        """
        if not self.is_enabled or self.bg_subtractor is None:
            return

        with self.lock:
            try:
                # Apply background subtraction
                fg_mask = self.bg_subtractor.apply(frame)

                # Find circular objects
                circular_objects = self._find_circular_objects(frame, fg_mask)

                # State machine
                if self.state == "MONITORING":
                    if len(circular_objects) > 0:
                        # First circle detected
                        obj = max(circular_objects, key=lambda o: o['area'])
                        self.detected_circle = (obj['x'], obj['y'], obj['radius'])
                        self.detection_start_time = time.time()
                        self.state = "DETECTED"
                        self.state_start_time = time.time()
                        print(f"[RealtimeDetectionEngine] DETECTED circle at {self.detected_circle}")

                elif self.state == "DETECTED":
                    if len(circular_objects) > 0:
                        # Object still present
                        obj = max(circular_objects, key=lambda o: o['area'])
                        self.detected_circle = (obj['x'], obj['y'], obj['radius'])

                        elapsed = time.time() - self.detection_start_time
                        if elapsed >= self.STABLE_TIME:
                            # Object stable - move to processing
                            self.state = "PROCESSING"
                            self.state_start_time = time.time()
                            print(f"[RealtimeDetectionEngine] PROCESSING (stable for {elapsed:.1f}s)")
                    else:
                        # Object disappeared
                        self.state = "MONITORING"
                        self.state_start_time = time.time()
                        self.detected_circle = None
                        print("[RealtimeDetectionEngine] Object disappeared -> MONITORING")

                elif self.state == "PROCESSING":
                    # Save current frame and run detection
                    save_image(frame)
                    success = self._perform_detection()

                    if success:
                        self.state = "COOLDOWN"
                        self.cooldown_start_time = time.time()
                        self.state_start_time = time.time()
                        self.detected_circle = None
                        print(f"[RealtimeDetectionEngine] COOLDOWN ({self.COOLDOWN_TIME}s)")
                    else:
                        self.state = "MONITORING"
                        self.state_start_time = time.time()
                        self.detected_circle = None
                        print("[RealtimeDetectionEngine] Detection failed -> MONITORING")

                elif self.state == "COOLDOWN":
                    elapsed = time.time() - self.cooldown_start_time
                    if elapsed >= self.COOLDOWN_TIME:
                        self.state = "MONITORING"
                        self.state_start_time = time.time()
                        self.detection_start_time = None
                        self.detected_circle = None
                        self.detection_frame_count = 0
                        print("[RealtimeDetectionEngine] MONITORING (cooldown complete)")

            except Exception as e:
                print(f"[RealtimeDetectionEngine] process_frame ERROR: {e}")

    def get_state(self):
        """
        Get current state information for API.

        Returns:
            dict: {
                'state': str (IDLE, MONITORING, DETECTED, PROCESSING, COOLDOWN),
                'elapsed_sec': float,
                'max_time_sec': float,
                'circle_detected': bool,
                'detection_x': int or None,
                'detection_y': int or None,
                'detection_radius': int or None,
                'total_scanned': int,
                'matched': int,
                'success_rate': float (0-100)
            }
        """
        with self.lock:
            now = time.time()
            elapsed = 0.0
            max_time = 0.0

            if self.state_start_time is not None:
                elapsed = now - self.state_start_time

                if self.state == "DETECTED":
                    max_time = self.STABLE_TIME
                elif self.state == "COOLDOWN":
                    max_time = self.COOLDOWN_TIME

            circle_x, circle_y, circle_r = None, None, None
            if self.detected_circle is not None:
                circle_x, circle_y, circle_r = self.detected_circle

            success_rate = 0.0
            if self.total_scanned > 0:
                success_rate = (self.matched_count / self.total_scanned) * 100.0

            return {
                'state': self.state,
                'elapsed_sec': round(elapsed, 2),
                'max_time_sec': max_time,
                'circle_detected': self.detected_circle is not None,
                'detection_x': circle_x,
                'detection_y': circle_y,
                'detection_radius': circle_r,
                'total_scanned': self.total_scanned,
                'matched': self.matched_count,
                'success_rate': round(success_rate, 1)
            }

    def get_statistics(self):
        """
        Get detection statistics.

        Returns:
            dict: {'total_scanned': int, 'matched': int, 'success_rate': float}
        """
        with self.lock:
            success_rate = 0.0
            if self.total_scanned > 0:
                success_rate = (self.matched_count / self.total_scanned) * 100.0

            return {
                'total_scanned': self.total_scanned,
                'matched': self.matched_count,
                'success_rate': round(success_rate, 1)
            }
