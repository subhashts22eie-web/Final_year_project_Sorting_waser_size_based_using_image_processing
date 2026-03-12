import cv2
import os

from step2_capture import open_camera

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILENAME = "capture.jpg"
SAVE_PATH = os.path.join(PROJECT_DIR, SAVE_FILENAME)


def save_image(frame):
    """
    Save a frame as capture.jpg in the project folder.
    Overwrites the file if it already exists.
    Returns the save path on success, None on failure.
    """
    if frame is None:
        print("[ERROR] No frame to save.")
        return None

    success = cv2.imwrite(SAVE_PATH, frame)

    if success:
        print(f"[OK] Image saved: {SAVE_PATH}")
        return SAVE_PATH
    else:
        print(f"[ERROR] Failed to save image to: {SAVE_PATH}")
        return None


def capture_loop():
    """
    Keep camera open in a continuous loop.
    SPACE = capture and save.
    Q     = quit.
    """
    cap = open_camera()
    if cap is None:
        return

    print("[INFO] Camera running. SPACE = Capture | Q = Quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Lost camera feed.")
            break

        display = frame.copy()
        cv2.putText(display, "SPACE = Capture | Q = Quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2)

        cv2.imshow("Live Preview", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):
            saved = save_image(frame)
            if saved:
                cv2.imshow("Captured", frame)
                cv2.waitKey(500)
                cv2.destroyWindow("Captured")

        elif key == ord('q'):
            print("[INFO] Exiting.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    print(f"[INFO] Images will be saved to: {SAVE_PATH}")
    capture_loop()
