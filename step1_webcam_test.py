import cv2

def test_webcam(camera_index=0):
    print(f"[INFO] Attempting to open camera at index {camera_index}...")

    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera. Check if it is connected and not used by another app.")
        return False

    print("[OK] Camera opened successfully.")
    print(f"[INFO] Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))} x {int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print("[INFO] Reading a test frame...")

    ret, frame = cap.read()

    if not ret or frame is None:
        print("[ERROR] Failed to read frame from camera.")
        cap.release()
        return False

    print("[OK] Frame captured successfully.")
    print(f"[INFO] Frame shape: {frame.shape}")  # (height, width, channels)

    # Show live feed until user presses 'q'
    print("[INFO] Showing live preview. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Lost connection to camera.")
            break

        cv2.imshow("Webcam Test - Press Q to quit", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[INFO] Preview closed by user.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[OK] Camera released.")
    return True


if __name__ == "__main__":
    test_webcam(camera_index=0)
