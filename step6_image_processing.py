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


def apply_clahe(gray):
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Larger tileGridSize (16x16) gives broader contrast regions,
    so the outer washer ring stands out vs. the inner texture noise.
    clipLimit=3.0 gives stronger contrast boost for dim/washed-out images.
    """
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16))
    enhanced = clahe.apply(gray)
    print(f"[OK] CLAHE contrast enhancement applied (clipLimit=3.0, tile=16x16).")
    return enhanced


def apply_blur(gray, ksize=9):
    """
    Apply Gaussian blur to reduce noise.
    ksize must be odd (e.g. 5, 7, 9, 11).
    Increased to 9 to better suppress internal washer texture
    before edge detection.
    """
    blurred = cv2.GaussianBlur(gray, (ksize, ksize), 0)
    print(f"[OK] Gaussian blur applied. Kernel size: {ksize}x{ksize}")
    return blurred


def apply_bilateral_filter(gray):
    """
    Apply bilateral filter to remove noise while PRESERVING sharp edges.
    Unlike Gaussian blur, bilateral filter keeps strong edges (the washer
    metal ring) crisp while smoothing out internal texture and grain.

    d=9      : diameter of pixel neighbourhood
    sigmaColor=75 : filter strength in colour/intensity space
    sigmaSpace=75 : filter strength in spatial space
    """
    filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    print(f"[OK] Bilateral filter applied (edge-preserving denoising).")
    return filtered


def apply_morphological_ops(gray):
    """
    Apply ONLY morphological opening (removes small noise particles).
    Removed closing operation — closing was filling and merging edges,
    which created false blobs that got detected as phantom circles.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    # Opening: erode then dilate (removes isolated noise pixels)
    opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel, iterations=1)

    print(f"[OK] Morphological open applied (noise removal only).")
    return opened


def detect_circles(blurred, dp=1.0, min_dist=100, param1=120, param2=45,
                   min_radius=120, max_radius=280):
    """
    Detect circles using Hough Circle Transform.

    KEY PARAMETER CHANGES:
    - param1=120: Much stricter Canny — only the strong outer metal ring edge
                  survives; weak inner texture edges are suppressed
    - param2=45 : Stricter accumulator — reduces false detections from noise
    - min_dist=100: Ensures only one circle per washer
    - min_radius=80: Outer washer is always larger than this
    - max_radius=280: Cap to exclude full-image false positives
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
        print("[WARN] No circles detected. Try lowering param1 or param2.")

    return circles


def run_pipeline(image_path=IMAGE_PATH):
    """
    Full processing pipeline with enhanced preprocessing:
    Load → Grayscale → CLAHE enhancement → Gaussian blur → Morphological ops → Hough Circle Detection
    
    Returns (original image, circles) or (None, None) on failure.
    """
    print("\n--- Image Processing Pipeline (Enhanced) ---")

    img = load_image(image_path)
    if img is None:
        return None, None

    gray      = convert_to_grayscale(img)
    enhanced  = apply_clahe(gray)                   # boost contrast
    denoised  = apply_bilateral_filter(enhanced)    # remove noise, keep edges sharp
    blurred   = apply_blur(denoised, ksize=9)       # smooth for Hough
    cleaned   = apply_morphological_ops(blurred)    # remove leftover noise pixels
    circles   = detect_circles(cleaned)

    print("---------------------------------\n")
    return img, circles


if __name__ == "__main__":
    img, circles = run_pipeline()

    if img is not None:
        # Show each pipeline stage side by side
        gray      = convert_to_grayscale(img)
        enhanced  = apply_clahe(gray)
        denoised  = apply_bilateral_filter(enhanced)
        blurred   = apply_blur(denoised, ksize=9)
        cleaned   = apply_morphological_ops(blurred)

        # Convert single-channel images to BGR for display
        gray_bgr     = cv2.cvtColor(gray,     cv2.COLOR_GRAY2BGR)
        enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        denoised_bgr = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
        blurred_bgr  = cv2.cvtColor(blurred,  cv2.COLOR_GRAY2BGR)
        cleaned_bgr  = cv2.cvtColor(cleaned,  cv2.COLOR_GRAY2BGR)

        # Draw detected circles on a copy of original
        result = img.copy()
        if circles is not None:
            for (x, y, r) in circles:
                cv2.circle(result, (x, y), r, (0, 255, 0), 2)   # outer circle
                cv2.circle(result, (x, y), 3, (0, 0, 255), -1)  # center dot

        # Stack: Original | Gray | CLAHE | Bilateral | Blur | Cleaned | Detected
        combined = np.hstack([img, gray_bgr, enhanced_bgr, denoised_bgr, blurred_bgr, cleaned_bgr, result])
        combined_resized = cv2.resize(combined, (0, 0), fx=0.28, fy=0.28)

        cv2.imshow("Pipeline: Original | Gray | CLAHE | Bilateral | Blur | Clean | Detected", combined_resized)

        # Save pipeline result to results folder
        save_path = os.path.join(RESULTS_DIR, "step6_pipeline.jpg")
        cv2.imwrite(save_path, combined_resized)
        print(f"[OK] Pipeline image saved: {save_path}")

        print("[INFO] Press any key to close.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
