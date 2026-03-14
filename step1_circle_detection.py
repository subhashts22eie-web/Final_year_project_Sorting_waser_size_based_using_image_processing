"""
STEP 1: Real-time Circle Detection
===================================
Tests background subtraction and circular object detection.
This is the foundation for the conveyor monitoring system.

Run this first to verify circle detection works correctly.
"""

import cv2
import numpy as np
import time

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

CAMERA_INDEX = 0

# Detection settings
MIN_AREA = 1000           # Minimum contour area (pixels)
MIN_CIRCULARITY = 0.7     # Minimum circularity (0-1, 1 = perfect circle)
STABLE_TIME = 2.0         # How long object must be present (seconds)

# Background subtraction
BG_HISTORY = 500          # Number of frames for background learning
BG_VAR_THRESHOLD = 16     # Sensitivity (lower = more sensitive)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("STEP 1: REAL-TIME CIRCLE DETECTION")
    print("=" * 80)
    print()
    print("Configuration:")
    print(f"  MIN_AREA: {MIN_AREA} pixels")
    print(f"  MIN_CIRCULARITY: {MIN_CIRCULARITY}")
    print(f"  STABLE_TIME: {STABLE_TIME}s")
    print()
    print("Controls:")
    print("  Q - Quit")
    print("=" * 80)
    print()

    # Open camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("ERROR: Cannot open camera!")
        return

    print("✓ Camera opened")

    # Create background subtractor
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=BG_HISTORY,
        varThreshold=BG_VAR_THRESHOLD,
        detectShadows=False
    )

    print("✓ Background subtractor initialized")
    print()
    print("MONITORING... (keep area clear for 2-3 seconds)")
    print()

    # State tracking
    detection_start_time = None
    object_detected = False
    detection_count = 0
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Apply background subtraction
        fg_mask = bg_subtractor.apply(frame)

        # Clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Copy for display
        display = frame.copy()

        # Detect circular objects
        circular_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MIN_AREA:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            # Calculate circularity: 1.0 = perfect circle
            circularity = 4 * np.pi * area / (perimeter * perimeter)

            if circularity >= MIN_CIRCULARITY:
                (x, y), radius = cv2.minEnclosingCircle(contour)
                circular_objects.append({
                    'x': int(x),
                    'y': int(y),
                    'radius': int(radius),
                    'area': area,
                    'circularity': circularity
                })

        # Draw all detected circles
        for obj in circular_objects:
            cv2.circle(display, (obj['x'], obj['y']), obj['radius'], (0, 165, 255), 2)
            cv2.putText(display, f"C:{obj['circularity']:.2f}",
                       (obj['x'] - 30, obj['y'] - obj['radius'] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

        # Track largest circle
        if len(circular_objects) > 0:
            largest = max(circular_objects, key=lambda o: o['area'])

            if not object_detected:
                # New detection
                detection_start_time = time.time()
                object_detected = True
                print(f"🔍 Circle detected - tracking...")

            # Calculate stable time
            elapsed = time.time() - detection_start_time

            # Change color based on stability
            if elapsed >= STABLE_TIME:
                # STABLE - Green
                color = (0, 255, 0)
                cv2.circle(display, (largest['x'], largest['y']), largest['radius'], color, 3)
                cv2.putText(display, "STABLE ✓", (largest['x'] - 40, largest['y'] + largest['radius'] + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                if elapsed >= STABLE_TIME and elapsed < STABLE_TIME + 0.1:  # Just became stable
                    detection_count += 1
                    print(f"  ✓ STABLE detection #{detection_count}")
                    print(f"    Area: {largest['area']:.0f}px, Circularity: {largest['circularity']:.2f}")
                    print()
            else:
                # TRACKING - Yellow
                color = (0, 255, 255)
                cv2.circle(display, (largest['x'], largest['y']), largest['radius'], color, 3)
                cv2.putText(display, f"{elapsed:.1f}s", (largest['x'] - 30, largest['y'] + largest['radius'] + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        else:
            if object_detected:
                print("  Object disappeared")
            object_detected = False
            detection_start_time = None

        # Status overlay
        if frame_count < 60:
            cv2.putText(display, "LEARNING BACKGROUND...", (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        else:
            status = "MONITORING" if not object_detected else "DETECTED"
            color = (0, 255, 0) if not object_detected else (0, 255, 255)
            cv2.putText(display, status, (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

        if detection_count > 0:
            cv2.putText(display, f"Detections: {detection_count}", (10, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Show windows
        cv2.imshow("Step 1: Circle Detection - Press Q to quit", display)
        cv2.imshow("Foreground Mask", fg_mask)

        # Keyboard
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nStopping...")
            break

    cap.release()
    cv2.destroyAllWindows()

    print()
    print("=" * 80)
    print("STEP 1 COMPLETE")
    print("=" * 80)
    print(f"Total stable detections: {detection_count}")
    print()
    print("Next: Step 2 - Add size detection after circle is detected")
    print()

# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
