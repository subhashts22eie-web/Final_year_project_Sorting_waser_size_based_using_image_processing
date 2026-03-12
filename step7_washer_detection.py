import cv2
import numpy as np
import os

from step6_image_processing import run_pipeline

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH  = os.path.join(PROJECT_DIR, "capture.jpg")
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)


def filter_valid_circles(circles, img_shape, min_area_variance=0.8):
    """
    Filter circles to find valid washer candidates:
    - Must not be near image edges
    - Must have reasonable area (filters out partial/noise circles)
    - Must have similar sizes (filters out outliers)
    
    Returns list of valid circles.
    """
    if circles is None:
        return []

    h, w = img_shape[:2]
    edge_margin = 5   # relaxed: washer can legitimately be close to the frame
    candidates = []

    for (x, y, r) in circles:
        # Reject circles too close to edges
        if (x - r) < edge_margin or (y - r) < edge_margin or \
           (x + r) > (w - edge_margin) or (y + r) > (h - edge_margin):
            print(f"  [SKIP] Circle at ({x}, {y}) r={r}: near image edge")
            continue
        
        candidates.append((x, y, r))

    if not candidates:
        print("[WARN] No valid circles after edge filtering. Release margin.")
        candidates = [(c[0], c[1], c[2]) for c in circles]

    # If multiple circles, filter by size consistency
    if len(candidates) > 1:
        radii = [r for _, _, r in candidates]
        mean_r = np.mean(radii)
        std_r = np.std(radii)
        
        # Keep circles within 1 standard deviation of mean
        filtered = [(x, y, r) for (x, y, r) in candidates 
                    if abs(r - mean_r) <= std_r]
        
        if filtered:  # Only use if we have results
            print(f"  [OK] Filtered by size: {len(candidates)} → {len(filtered)} circles")
            candidates = filtered
        else:
            print(f"  [WARN] Size filter rejected all circles, keeping originals")

    return candidates


def pick_washer_circle(circles, img_shape):
    """
    From all detected circles, pick the best candidate for the washer.

    Strategy:
    1. Reject circles too close to the image edge (likely partial circles)
    2. Filter by size consistency (removes outliers)
    3. Pick the LARGEST remaining circle (washer outer edge)

    Returns (x, y, radius) or None.
    """
    candidates = filter_valid_circles(circles, img_shape)

    if not candidates:
        print("[ERROR] No valid circles after filtering.")
        return None

    # Pick the largest circle — most likely the washer outer edge
    best = max(candidates, key=lambda c: c[2])
    print(f"[OK] Washer circle selected: center=({best[0]}, {best[1]}), radius={best[2]}px")
    return best


def get_pixel_diameter(circle):
    """Calculate diameter in pixels from (x, y, radius)."""
    _, _, r = circle
    diameter = r * 2
    print(f"[OK] Pixel diameter: {diameter}px  (radius: {r}px)")
    return diameter


def detect_washer(image_path=IMAGE_PATH):
    """
    Full washer detection:
    Run pipeline → pick best circle → return (image, circle, pixel_diameter).
    """
    img, circles = run_pipeline(image_path)

    if img is None:
        return None, None, None

    circle = pick_washer_circle(circles, img.shape)

    if circle is None:
        print("[ERROR] No washer detected.")
        return img, None, None

    diameter_px = get_pixel_diameter(circle)
    return img, circle, diameter_px


if __name__ == "__main__":
    img, circle, diameter_px = detect_washer()

    if img is not None and circle is not None:
        x, y, r = circle

        # Draw result on image
        output = img.copy()
        cv2.circle(output, (x, y), r, (0, 255, 0), 3)       # outer circle
        cv2.circle(output, (x, y), 4, (0, 0, 255), -1)      # center dot

        # Draw diameter line across the circle
        cv2.line(output, (x - r, y), (x + r, y), (255, 0, 0), 2)

        # Label
        cv2.putText(output, f"Diameter: {diameter_px}px",
                    (x - r, y - r - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        print(f"\n[RESULT] Washer pixel diameter: {diameter_px}px")
        print("[INFO]   Next step: calibrate to convert px → mm")

        # Save detection result to results folder
        save_path = os.path.join(RESULTS_DIR, "step7_washer_detected.jpg")
        cv2.imwrite(save_path, output)
        print(f"[OK] Detection image saved: {save_path}")

        cv2.imshow("Washer Detection", output)
        print("[INFO] Press any key to close.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("[ERROR] Could not detect washer. Try adjusting param2 in step6.")
