import cv2
import os
import numpy as np

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH  = os.path.join(PROJECT_DIR, "capture.jpg")
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")

# Create results folder if it doesn't exist
os.makedirs(RESULTS_DIR, exist_ok=True)


def load_image(path=IMAGE_PATH):
    """Load image from disk."""
    img = cv2.imread(path)
    if img is None:
        print(f"[ERROR] Could not load image from: {path}")
        return None
    print(f"[OK] Image loaded. Size: {img.shape[1]}x{img.shape[0]}")
    return img


def convert_to_grayscale(img):
    """Convert BGR image to grayscale."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print(f"[OK] Converted to grayscale. Shape: {gray.shape}")
    return gray


def apply_blur(gray, ksize=5):
    """
    Apply Gaussian blur to reduce noise.
    ksize must be odd (e.g. 5, 7, 9).
    Higher ksize = more blur = less noise but less detail.
    """
    blurred = cv2.GaussianBlur(gray, (ksize, ksize), 0)
    print(f"[OK] Gaussian blur applied. Kernel size: {ksize}x{ksize}")
    return blurred


def detect_circles(blurred, dp=1.2, min_dist=50, param1=50, param2=30,
                   min_radius=20, max_radius=300):
    """
    Detect circles using Hough Circle Transform.

    Parameters:
        dp        - inverse ratio of resolution (1 = same as input, 2 = half)
        min_dist  - minimum distance between circle centers
        param1    - upper threshold for Canny edge detection
        param2    - accumulator threshold (lower = more circles detected)
        min_radius - minimum circle radius in pixels
        max_radius - maximum circle radius in pixels
    """
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=dp,
        minDist=min_dist,
        param1=param1,
        param2=param2,
        minRadius=min_radius,
        maxRadius=max_radius
    )

    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        print(f"[OK] {len(circles)} circle(s) detected.")
    else:
        print("[WARN] No circles detected. Try adjusting param2 or radius range.")

    return circles


def run_pipeline(image_path=IMAGE_PATH):
    """
    Full processing pipeline:
    Load → Grayscale → Blur → Hough Circle Detection
    Returns (original image, circles) or (None, None) on failure.
    """
    print("\n--- Image Processing Pipeline ---")

    img = load_image(image_path)
    if img is None:
        return None, None

    gray    = convert_to_grayscale(img)
    blurred = apply_blur(gray, ksize=5)
    circles = detect_circles(blurred)

    print("---------------------------------\n")
    return img, circles


if __name__ == "__main__":
    img, circles = run_pipeline()

    if img is not None:
        # Show each pipeline stage side by side
        gray    = convert_to_grayscale(img)
        blurred = apply_blur(gray)

        # Convert single-channel images to BGR for display
        gray_bgr    = cv2.cvtColor(gray,    cv2.COLOR_GRAY2BGR)
        blurred_bgr = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

        # Draw detected circles on a copy of original
        result = img.copy()
        if circles is not None:
            for (x, y, r) in circles:
                cv2.circle(result, (x, y), r, (0, 255, 0), 2)   # outer circle
                cv2.circle(result, (x, y), 3, (0, 0, 255), -1)  # center dot

        # Stack: Original | Grayscale | Blurred | Detected
        combined = np.hstack([img, gray_bgr, blurred_bgr, result])
        combined_resized = cv2.resize(combined, (0, 0), fx=0.5, fy=0.5)

        cv2.imshow("Pipeline: Original | Gray | Blurred | Detected", combined_resized)

        # Save pipeline result to results folder
        save_path = os.path.join(RESULTS_DIR, "step6_pipeline.jpg")
        cv2.imwrite(save_path, combined_resized)
        print(f"[OK] Pipeline image saved: {save_path}")

        print("[INFO] Press any key to close.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
