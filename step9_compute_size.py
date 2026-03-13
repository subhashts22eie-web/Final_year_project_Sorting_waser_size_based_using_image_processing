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


def evaluate_target_size(measured_mm, target_mm, tolerance_mm=0.5):
    """Return pass/fail for a user-defined target size."""
    measured_mm = float(measured_mm)
    target_mm = float(target_mm)
    tolerance_mm = float(tolerance_mm)

    deviation_mm = round(measured_mm - target_mm, 2)
    abs_error = abs(deviation_mm)
    is_ok = bool(abs_error <= tolerance_mm)

    if deviation_mm > 0:
        direction = "OVERSIZE"
    elif deviation_mm < 0:
        direction = "UNDERSIZE"
    else:
        direction = "ON_TARGET"

    return {
        "is_ok": is_ok,
        "target_mm": round(target_mm, 2),
        "measured_mm": round(measured_mm, 2),
        "tolerance_mm": round(tolerance_mm, 2),
        "deviation_mm": deviation_mm,
        "direction": direction,
        "min_ok_mm": round(target_mm - tolerance_mm, 2),
        "max_ok_mm": round(target_mm + tolerance_mm, 2),
    }


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


def compute_washer_size_target(target_mm, tolerance_mm=0.5, image_path=None):
    """
    Target-based flow (NO fixed standard list):
    Detect washer -> load calibration -> convert px to mm -> compare to target.

    Returns (measured_mm, evaluation_dict) or (None, None) on failure.
    """
    calib = load_calibration()
    if calib is None:
        return None, None

    mm_per_pixel = calib["mm_per_pixel"]

    kwargs = {"image_path": image_path} if image_path else {}
    img, circle, pixel_diameter = detect_washer(**kwargs)

    if circle is None:
        print("[ERROR] No washer detected.")
        return None, None

    measured_mm = pixels_to_mm(pixel_diameter, mm_per_pixel)
    evaluation = evaluate_target_size(measured_mm, target_mm, tolerance_mm)

    print(f"[INFO] Pixel diameter  : {pixel_diameter}px")
    print(f"[INFO] mm per pixel    : {mm_per_pixel}")
    print(f"[INFO] Measured size   : {measured_mm}mm")
    status = "PASS" if evaluation["is_ok"] else f"FAIL ({evaluation['direction']})"
    print(
        f"[INFO] Target check    : {status} "
        f"target={evaluation['target_mm']}mm tol=+/-{evaluation['tolerance_mm']}mm "
        f"dev={evaluation['deviation_mm']:+.2f}mm"
    )

    return measured_mm, evaluation


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
