import cv2
import os
import json

from step7_washer_detection import detect_washer

PROJECT_DIR    = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR    = os.path.join(PROJECT_DIR, "results")
CALIBRATION_FILE = os.path.join(PROJECT_DIR, "calibration.json")

os.makedirs(RESULTS_DIR, exist_ok=True)


def save_calibration(mm_per_pixel, real_diameter_mm, pixel_diameter):
    """Save calibration data to calibration.json."""
    data = {
        "mm_per_pixel"      : round(float(mm_per_pixel), 6),
        "real_diameter_mm"  : float(real_diameter_mm),
        "pixel_diameter"    : int(pixel_diameter)
    }
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"[OK] Calibration saved: {CALIBRATION_FILE}")
    return data


def load_calibration():
    """Load calibration data from calibration.json."""
    if not os.path.exists(CALIBRATION_FILE):
        print("[ERROR] No calibration file found. Run step8_calibration.py first.")
        return None

    with open(CALIBRATION_FILE, "r") as f:
        data = json.load(f)

    print(f"[OK] Calibration loaded: {data['mm_per_pixel']} mm/pixel")
    return data


def run_calibration():
    """
    Calibration flow:
    1. Detect washer in current capture.jpg
    2. Ask user for the real diameter in mm
    3. Calculate mm_per_pixel
    4. Save to calibration.json
    """
    print("\n--- Calibration ---")
    print("[INFO] Make sure a washer of KNOWN size is in the camera frame.")
    print("[INFO] Run step3_save_image.py first to capture the calibration image.\n")

    img, circle, pixel_diameter = detect_washer()

    if img is None or circle is None:
        print("[ERROR] Could not detect washer. Cannot calibrate.")
        return None

    x, y, r = circle
    print(f"\n[INFO] Detected pixel diameter: {pixel_diameter}px")

    # Ask user for real size
    while True:
        try:
            real_mm = float(input("\n[INPUT] Enter the REAL outer diameter of this washer in mm: "))
            if real_mm <= 0:
                print("[ERROR] Please enter a positive number.")
                continue
            break
        except ValueError:
            print("[ERROR] Invalid input. Enter a number like 20 or 25.4")

    # Calculate calibration factor
    mm_per_pixel = real_mm / pixel_diameter
    print(f"\n[RESULT] mm per pixel = {real_mm} / {pixel_diameter} = {mm_per_pixel:.6f}")

    # Save calibration
    data = save_calibration(mm_per_pixel, real_mm, pixel_diameter)

    # Draw calibration result on image and save
    output = img.copy()
    cv2.circle(output, (x, y), r, (0, 255, 0), 3)
    cv2.circle(output, (x, y), 4, (0, 0, 255), -1)
    cv2.line(output,   (x - r, y), (x + r, y), (255, 0, 0), 2)

    label = f"Real: {real_mm}mm  |  {pixel_diameter}px  |  {mm_per_pixel:.4f} mm/px"
    cv2.putText(output, label, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

    save_path = os.path.join(RESULTS_DIR, "step8_calibration.jpg")
    cv2.imwrite(save_path, output)
    print(f"[OK] Calibration image saved: {save_path}")

    cv2.imshow("Calibration Result", output)
    print("[INFO] Press any key to close.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("\n--- Calibration Complete ---")
    print(f"  Real diameter : {real_mm} mm")
    print(f"  Pixel diameter: {pixel_diameter} px")
    print(f"  mm per pixel  : {mm_per_pixel:.6f}")
    print("-----------------------------\n")

    return data


if __name__ == "__main__":
    run_calibration()
