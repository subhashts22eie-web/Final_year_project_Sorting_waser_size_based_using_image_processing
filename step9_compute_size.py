import os

from step7_washer_detection import detect_washer
from step8_calibration import load_calibration

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Standard washer outer diameters in mm (M-series)
# Add or remove sizes to match the washers you are sorting
STANDARD_SIZES_MM = [7, 9, 10, 12, 17, 21, 25, 30]


def pixels_to_mm(pixel_diameter, mm_per_pixel):
    """Convert pixel diameter to real-world mm using calibration factor."""
    return round(pixel_diameter * mm_per_pixel, 2)


def match_standard_size(measured_mm, tolerance=3.0):
    """
    Match measured mm to the closest standard washer size.

    tolerance: max allowed difference in mm to accept a match.
               If no size is within tolerance, returns None.
    """
    closest     = min(STANDARD_SIZES_MM, key=lambda s: abs(s - measured_mm))
    difference  = abs(closest - measured_mm)

    if difference <= tolerance:
        print(f"[OK] Matched to standard size: {closest}mm  (measured: {measured_mm}mm, diff: {difference:.2f}mm)")
        return closest
    else:
        print(f"[WARN] Measured {measured_mm}mm does not match any standard size within {tolerance}mm tolerance.")
        print(f"[WARN] Closest was {closest}mm (diff: {difference:.2f}mm). Returning raw measurement.")
        return None


def compute_washer_size(image_path=None):
    """
    Full pipeline:
    Detect washer → load calibration → convert px to mm → match standard size.

    Returns (measured_mm, matched_size_mm) or (None, None) on failure.
    """
    # Load calibration
    calib = load_calibration()
    if calib is None:
        return None, None

    mm_per_pixel = calib["mm_per_pixel"]

    # Detect washer
    kwargs = {"image_path": image_path} if image_path else {}
    img, circle, pixel_diameter = detect_washer(**kwargs)

    if circle is None:
        print("[ERROR] No washer detected.")
        return None, None

    # Convert to mm
    measured_mm = pixels_to_mm(pixel_diameter, mm_per_pixel)
    print(f"[INFO] Pixel diameter  : {pixel_diameter}px")
    print(f"[INFO] mm per pixel    : {mm_per_pixel}")
    print(f"[INFO] Measured size   : {measured_mm}mm")

    # Match to standard size
    matched = match_standard_size(measured_mm)

    return measured_mm, matched


if __name__ == "__main__":
    print("\n--- Washer Size Computation ---")

    measured_mm, matched_size = compute_washer_size()

    if measured_mm is not None:
        print("\n=============================")
        print(f"  Measured  : {measured_mm} mm")

        if matched_size:
            print(f"  Size      : {matched_size} mm  (standard)")
        else:
            print(f"  Size      : {measured_mm} mm  (no match — check calibration or tolerance)")

        print("=============================\n")
    else:
        print("[ERROR] Could not compute washer size.")
