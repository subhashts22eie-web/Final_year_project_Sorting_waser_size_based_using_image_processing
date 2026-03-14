import os
import socket
import time
import threading

import cv2
import numpy as np
from flask import Flask, jsonify, request, render_template, Response

app = Flask(__name__)

VALID_COMMANDS = {"START", "STOP"}
current_cmd = "STOP"
desired_target_mm = None
last_cmd_request_id = None
last_cmd_poll_log_time = 0.0
cmd_poll_count = 0

cmd_lock = threading.Lock()

# Simple in-memory status for frontend display
latest_sort_result = {
    "ok": False,
    "message": "Test mode: no size detection",
    "timestamp": time.time()
}


def make_test_frame():
    """Create a simple frame so /video_feed works in test mode."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (20, 20, 20)

    status_text = f"CMD: {current_cmd}"
    target_text = f"TARGET: {desired_target_mm if desired_target_mm is not None else '-'} mm"
    mode_text = "CONVEYOR TEST SERVER (NO CAMERA/DETECTION)"

    cv2.putText(frame, mode_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(frame, status_text, (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 0), 2)
    cv2.putText(frame, target_text, (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 200, 0), 2)
    cv2.putText(frame, time.strftime("%H:%M:%S"), (20, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

    return frame


def mjpeg_stream_generator():
    while True:
        frame = make_test_frame()
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            time.sleep(0.1)
            continue

        jpg = encoded.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
        )
        time.sleep(0.2)


@app.route("/")
def index():
    return render_template("index.html")


# Frontend compatibility routes
@app.route("/video_feed")
def video_feed():
    return Response(
        mjpeg_stream_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/calibration/status")
def calibration_status():
    return jsonify({
        "calibrated": True,
        "mm_per_pixel": 0.1,
        "real_diameter_mm": 30,
        "pixel_diameter": 300
    })


@app.route("/sort/latest")
def sort_latest():
    return jsonify(latest_sort_result)


@app.route("/sort/decision")
def sort_decision():
    if current_cmd != "START":
        return "STOPPED"
    if desired_target_mm is None:
        return "NO_TARGET"
    return "WAITING"


@app.route("/realtime/state")
def realtime_state():
    state = "MONITORING" if current_cmd == "START" else "IDLE"
    return jsonify({
        "state": state,
        "elapsed_sec": 0.0,
        "max_time_sec": 0.0,
        "circle_detected": False,
        "detection_x": None,
        "detection_y": None,
        "detection_radius": None,
        "total_scanned": 0,
        "matched": 0,
        "success_rate": 0.0
    })


@app.route("/realtime/settings", methods=["POST"])
def realtime_settings():
    data = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "message": "Test mode settings accepted", "settings": data})


@app.route("/cmd")
def receive_cmd():
    global last_cmd_poll_log_time, cmd_poll_count

    cmd_poll_count += 1
    now = time.time()
    if now - last_cmd_poll_log_time >= 2.0:
        client_ip = request.remote_addr
        print(f"[TEST SERVER] /cmd polls={cmd_poll_count} from={client_ip} -> {current_cmd}")
        last_cmd_poll_log_time = now
    return current_cmd


@app.route("/cmd/status")
def cmd_status():
    return jsonify({"ok": True, "command": current_cmd})


@app.route("/cmd/set", methods=["POST"])
def cmd_set():
    global current_cmd, last_cmd_request_id

    data = request.get_json(silent=True) or {}
    cmd = str(data.get("command", "")).strip().upper()
    request_id = data.get("request_id", "")

    if cmd not in VALID_COMMANDS:
        return jsonify({"ok": False, "error": "Invalid command. Use START or STOP"}), 400

    with cmd_lock:
        if request_id and request_id == last_cmd_request_id:
            return jsonify({"ok": True, "command": current_cmd, "duplicate": True})
        last_cmd_request_id = request_id or None
        current_cmd = cmd

    print(f"[TEST SERVER] Conveyor command: {current_cmd}")
    return jsonify({"ok": True, "command": current_cmd})


@app.route("/target/status")
def target_status():
    return jsonify({"ok": True, "target_mm": desired_target_mm})


@app.route("/target/set", methods=["POST"])
def target_set():
    global desired_target_mm, current_cmd

    data = request.get_json(silent=True) or {}
    target = data.get("target_mm")

    try:
        target = float(target)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid target_mm"}), 400

    if target <= 0:
        return jsonify({"ok": False, "error": "target_mm must be > 0"}), 400

    desired_target_mm = target
    current_cmd = "START"

    print(f"[TEST SERVER] Target set to {desired_target_mm}mm, command=START")
    return jsonify({"ok": True, "target_mm": desired_target_mm, "command": current_cmd})


# Optional no-op routes used by parts of existing frontend
@app.route("/detect")
def detect_noop():
    return jsonify({"ok": False, "error": "Test mode: detection disabled"}), 501


@app.route("/capture")
def capture_noop():
    return "CAPTURE_DISABLED_TEST_MODE", 501


@app.route("/size")
def size_noop():
    return "SIZE_DISABLED_TEST_MODE", 501


@app.route("/measure")
def measure_noop():
    return jsonify({"ok": False, "error": "Test mode: measure disabled"}), 501


@app.route("/calibrate", methods=["POST"])
def calibrate_noop():
    return jsonify({"ok": False, "error": "Test mode: calibration disabled"}), 501


if __name__ == "__main__":
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"[TEST SERVER] Running on http://{local_ip}:5000")
    print("[TEST SERVER] Frontend routes: /cmd/status /cmd/set /target/status /target/set")
    print("[TEST SERVER] ESP32 poll route: /cmd")
    app.run(host="0.0.0.0", port=5000, debug=False)
