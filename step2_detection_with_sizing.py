"""
STEP 2: Circle Detection + Size Detection
==========================================
Combines real-time circle detection with washer size measurement.
When circle is detected and stable, captures CLEAN image and measures.
"""

import cv2
import numpy as np
import time
from step3_save_image import save_image
from step8_calibration import load_calibration
from step7_washer_detection import detect_washer
from step9_compute_size import pixels_to_mm, match_standard_size

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

CAMERA_INDEX = 0

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
# SIZE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def capture_clean_image_and_detect(cap, calib, target_mm=None):
    """
    Capture a CLEAN image (no background subtraction) and detect washer size.

    Args:
        cap: Camera capture object
        calib: Calibration data
        target_mm: Optional target size

    Returns:
        dict with: success, size_mm, matched_size, measured_mm, is_match
    """
    # Capture a fresh clean frame directly from camera
    ret, frame = cap.read()
    if not ret or frame is None:
        print("  ✗ Failed to capture clean image")
        return {'success': False}

    # Save the clean image using save_image (no background artifacts)
    save_image(frame)
    print("  📸 Clean image captured")

    # Detect washer
    img, circle, pixel_diameter = detect_washer()

    if img is None or circle is None:
        print("  ✗ No washer detected in image")
        return {'success': False}

    # Calculate size
    measured_mm = pixels_to_mm(pixel_diameter, calib['mm_per_pixel'])
    matched_size = match_standard_size(measured_mm)
    final_size = matched_size if matched_size else round(measured_mm)

    # Check match if target specified
    is_match = None
    deviation = None
    if target_mm is not None:
        deviation = abs(measured_mm - target_mm)
        is_match = deviation <= 3.0

    # Save result image
    x, y, r = circle
    result = img.copy()
    cv2.circle(result, (x, y), r, (0, 255, 0), 3)
    cv2.circle(result, (x, y), 4, (0, 0, 255), -1)

    label = f"{final_size}mm"
    if target_mm and is_match is not None:
        label += f" | Target: {target_mm}mm | {'MATCH' if is_match else 'NO MATCH'}"

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
    print("STEP 2: CIRCLE DETECTION + SIZE DETECTION")
    print("=" * 80)
    print()

    # Load calibration
    calib = load_calibration()
    if calib is None:
        print("✗ ERROR: System not calibrated!")
        print("  Run: python server.py")
        print("  Then calibrate using web interface at http://localhost:5000")
        return

    print(f"✓ Calibration loaded: {calib['mm_per_pixel']:.6f} mm/px")

    if target_mm:
        print(f"✓ Target size: {target_mm}mm")
    else:
        print("⚠ No target size set (detection only mode)")

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

    # State machine
    state = "MONITORING"  # MONITORING, DETECTED, PROCESSING, COOLDOWN
    detection_start_time = None
    cooldown_start_time = None

    # Statistics
    total_count = 0
    match_count = 0

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Apply background subtraction
        fg_mask = bg_subtractor.apply(frame)

        # Clean mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Display
        display = frame.copy()

        # Detect circles
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
                    'x': int(x), 'y': int(y), 'radius': int(radius),
                    'area': area, 'circularity': circularity
                })

        # State machine
        if state == "MONITORING":
            status = "MONITORING"
            status_color = (0, 255, 0)

            if len(circular_objects) > 0:
                obj = max(circular_objects, key=lambda o: o['area'])
                detection_start_time = time.time()
                state = "DETECTED"
                print(f"🔍 Circle detected - tracking...")

                # Draw yellow circle
                cv2.circle(display, (obj['x'], obj['y']), obj['radius'], (0, 255, 255), 2)

        elif state == "DETECTED":
            if len(circular_objects) > 0:
                obj = max(circular_objects, key=lambda o: o['area'])
                elapsed = time.time() - detection_start_time

                # Draw circle
                cv2.circle(display, (obj['x'], obj['y']), obj['radius'], (0, 255, 255), 2)
                cv2.putText(display, f"{elapsed:.1f}s", (obj['x'] - 30, obj['y'] + obj['radius'] + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                status = f"TRACKING ({elapsed:.1f}s)"
                status_color = (0, 255, 255)

                if elapsed >= STABLE_TIME:
                    # Object stable - capture while moving!
                    print()
                    print("=" * 80)
                    print("✓ OBJECT STABLE - CAPTURING IMAGE (WHILE MOVING)")
                    print("=" * 80)

                    state = "PROCESSING"
                    status = "PROCESSING..."
                    status_color = (255, 0, 255)

            else:
                # Object disappeared
                print("  Object disappeared - resetting...")
                state = "MONITORING"
                detection_start_time = None

        elif state == "PROCESSING":
            status = "PROCESSING..."
            status_color = (255, 0, 255)

            # Capture clean image and detect
            result = capture_clean_image_and_detect(cap, calib, target_mm)

            total_count += 1

            if result['success']:
                print(f"  ✓ Detected: {result['final_size']}mm")
                print(f"    Measured: {result['measured_mm']:.2f}mm ({result['pixel_diameter']}px)")

                if target_mm and result['is_match'] is not None:
                    if result['is_match']:
                        match_count += 1
                        print(f"    ✓ MATCH (deviation: {result['deviation']:.2f}mm)")
                    else:
                        print(f"    ✗ NO MATCH (deviation: {result['deviation']:.2f}mm)")

                    print(f"  Statistics: {match_count}/{total_count} matched ({100*match_count/total_count:.1f}%)")
            else:
                print("  ✗ Detection failed")

            print()
            print("→ In real system: Conveyor would START here")
            print("  Entering cooldown...")
            print()

            # Enter cooldown
            state = "COOLDOWN"
            cooldown_start_time = time.time()
            detection_start_time = None

        elif state == "COOLDOWN":
            elapsed = time.time() - cooldown_start_time
            remaining = COOLDOWN_TIME - elapsed

            status = f"COOLDOWN ({remaining:.1f}s)"
            status_color = (128, 128, 255)

            if elapsed >= COOLDOWN_TIME:
                print("✓ Cooldown complete - resuming monitoring\n")
                state = "MONITORING"
                cooldown_start_time = None

        # Add status to display
        if frame_count < 60:
            cv2.putText(display, "LEARNING BACKGROUND...", (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        else:
            cv2.putText(display, status, (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)

        # Add statistics
        if total_count > 0:
            stats = f"Scanned: {total_count}"
            if target_mm:
                stats += f" | Matched: {match_count} ({100*match_count/total_count:.0f}%)"
            cv2.putText(display, stats, (10, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Show windows
        cv2.imshow("Step 2: Detection + Sizing - Press Q to quit", display)
        cv2.imshow("Foreground Mask", fg_mask)

        # Keyboard
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nStopping...")
            break

    cap.release()
    cv2.destroyAllWindows()

    print()
    print("=" * 80)
    print("STEP 2 COMPLETE")
    print("=" * 80)
    if total_count > 0:
        print(f"Total detected: {total_count}")
        if target_mm:
            print(f"Matched: {match_count} ({100*match_count/total_count:.1f}%)")
    print()
    print("Next: Step 3 - Add ESP32 communication to stop/start conveyor")
    print()

# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # Get target size from command line (optional)
    target = None
    if len(sys.argv) > 1:
        try:
            target = float(sys.argv[1])
        except ValueError:
            print(f"Invalid target: {sys.argv[1]}")
            sys.exit(1)

    main(target_mm=target)
