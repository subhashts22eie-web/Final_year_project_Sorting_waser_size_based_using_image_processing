import cv2
import os
import socket
from flask import Flask

from step2_capture import open_camera
from step3_save_image import save_image

app = Flask(__name__)

# Open the camera once when server starts — keeps it ready between requests
camera = open_camera()

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(PROJECT_DIR, "capture.jpg")


def capture_and_save():
    """Capture one frame from the open camera and save it."""
    if camera is None:
        print("[ERROR] Camera not available.")
        return False

    ret, frame = camera.read()
    if not ret or frame is None:
        print("[ERROR] Failed to read frame from camera.")
        return False

    result = save_image(frame)
    return result is not None


@app.route('/cmd')
def receive_cmd():
    print("[SERVER] /cmd received from ESP32")
    return "HELLO_ESP32"


@app.route('/capture')
def capture():
    print("[SERVER] /capture request received — capturing image...")

    success = capture_and_save()

    if success:
        print("[SERVER] Image captured and saved successfully.")
        return "CAPTURE_OK"
    else:
        print("[SERVER] Capture failed.")
        return "CAPTURE_FAILED", 500


if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"[SERVER] Running on http://{local_ip}:5000")
    print(f"[SERVER] ESP32 endpoint: http://{local_ip}:5000/capture")
    app.run(host='0.0.0.0', port=5000, debug=False)
