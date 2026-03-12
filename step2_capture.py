import cv2

CAMERA_INDEX = 0

def open_camera():
    """Open webcam and return the capture object."""
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
        return None

    print("[OK] Camera ready.")
    return cap


def capture_frame(cap):
    """
    Capture a single frame from the open camera.
    Returns the frame (numpy array) or None on failure.
    """
    ret, frame = cap.read()

    if not ret or frame is None:
        print("[ERROR] Failed to capture frame.")
        return None

    print(f"[OK] Frame captured. Shape: {frame.shape}")
    return frame


def preview_and_capture():
    """
    Show live preview.
    Press SPACE to capture a frame.
    Press Q to quit without capturing.
    """
    cap = open_camera()
    if cap is None:
        return None

    print("[INFO] Live preview started.")
    print("       Press SPACE to capture | Press Q to quit")

    captured_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Lost camera feed.")
            break

        # Show instruction on the preview window
        display = frame.copy()
        cv2.putText(display, "SPACE = Capture | Q = Quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2)

        cv2.imshow("Live Preview", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):  # SPACE key
            captured_frame = capture_frame(cap)
            if captured_frame is not None:
                print("[OK] Image captured successfully.")
            break

        elif key == ord('q'):
            print("[INFO] Quit without capturing.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return captured_frame


if __name__ == "__main__":
    frame = preview_and_capture()

    if frame is not None:
        # Show the captured frame in a new window
        cv2.imshow("Captured Frame", frame)
        print("[INFO] Showing captured frame. Press any key to close.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("[INFO] No frame was captured.")
