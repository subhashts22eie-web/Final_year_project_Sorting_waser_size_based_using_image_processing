import cv2
import os
import socket
import time
import threading
from flask import Flask, jsonify, request, render_template, send_file

from step3_save_image import save_image
from step7_washer_detection import detect_washer
from step8_calibration import load_calibration, save_calibration
from step9_compute_size import compute_washer_size_target, compute_washer_size, pixels_to_mm, match_standard_size
from realtime_detection import RealtimeDetectionEngine

CAMERA_INDEX = 0
CAMERA_READ_INTERVAL_SEC = 0.03
AUTO_PROCESS_INTERVAL_SEC = 2.0

app = Flask(__name__)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH   = os.path.join(PROJECT_DIR, "capture.jpg")
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
RESULT_IMG  = os.path.join(RESULTS_DIR, "step7_washer_detected.jpg")
CALIB_IMG   = os.path.join(RESULTS_DIR, "calibration_result.jpg")

os.makedirs(RESULTS_DIR, exist_ok=True)

# Conveyor command state for ESP32 polling (/cmd)
VALID_CONVEYOR_COMMANDS = {"START", "STOP"}
current_conveyor_cmd = "STOP"

# Sorting decision state for ESP32
desired_target_mm = None
latest_sort_result = {
    "ok": False,
    "message": "No sorting result yet"
}
last_sort_angle = 90

# Real-time detection engine
realtime_engine = None
realtime_thread = None
realtime_stop_event = threading.Event()

# Shared camera frame state
camera_lock = threading.Lock()
latest_frame = None
camera_ready = False
camera_thread = None
camera_stop_event = threading.Event()

# Auto processing loop state
auto_processing_enabled = False
auto_thread = None
auto_stop_event = threading.Event()

# Conveyor command lock for thread-safe state updates
cmd_lock = threading.Lock()
last_cmd_request_id = None  # Track request ID to prevent duplicates


def classify_angle(final_size_mm, target_mm):
    """Return 0 for equal, 90 for less, 180 for greater."""
    target_int = int(round(float(target_mm)))
    size_int = int(round(float(final_size_mm)))

    if size_int == target_int:
        return 0, "EQUAL"
    if size_int < target_int:
        return 90, "LESS"
    return 180, "GREATER"


def camera_worker():
    """Continuously read frames so live stream and detection share one camera source."""
    global latest_frame, camera_ready

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera for live feed")
        camera_ready = False
        return

    camera_ready = True
    print("[SERVER] Camera worker started")

    while not camera_stop_event.is_set():
        ret, frame = cap.read()
        if ret and frame is not None:
            with camera_lock:
                latest_frame = frame.copy()
        else:
            time.sleep(0.1)
            continue

        time.sleep(CAMERA_READ_INTERVAL_SEC)

    cap.release()
    camera_ready = False
    print("[SERVER] Camera worker stopped")


def start_camera_worker():
    global camera_thread
    if camera_thread and camera_thread.is_alive():
        return
    camera_stop_event.clear()
    camera_thread = threading.Thread(target=camera_worker, daemon=True)
    camera_thread.start()


def get_latest_frame_copy():
    with camera_lock:
        if latest_frame is None:
            return None
        return latest_frame.copy()


def auto_processing_worker():
    """Run periodic detection while conveyor is running and target is set."""
    global latest_sort_result, last_sort_angle

    print("[SERVER] Auto processing worker started")
    while not auto_stop_event.is_set():
        if auto_processing_enabled and current_conveyor_cmd == "START" and desired_target_mm is not None:
            response, status = run_detection(target_mm=desired_target_mm)
            latest_sort_result = {
                **response,
                "timestamp": time.time()
            }

            if status == 200 and response.get("ok"):
                last_sort_angle = int(response["angle"])
                print(
                    f"[SERVER] Auto detect: size={response['matched_size']} target={desired_target_mm} "
                    f"=> angle {last_sort_angle}"
                )
            else:
                print(f"[SERVER] Auto detect failed: {response.get('error', 'unknown')}" )

            time.sleep(AUTO_PROCESS_INTERVAL_SEC)
            continue

        time.sleep(0.2)

    print("[SERVER] Auto processing worker stopped")


def start_auto_processing_worker():
    global auto_thread
    if auto_thread and auto_thread.is_alive():
        return
    auto_stop_event.clear()
    auto_thread = threading.Thread(target=auto_processing_worker, daemon=True)
    auto_thread.start()


def realtime_worker():
    """Feed camera frames to the real-time detection engine."""
    global realtime_engine

    print("[SERVER] Real-time detection worker started")
    while not realtime_stop_event.is_set():
        if realtime_engine is not None and realtime_engine.is_enabled:
            frame = get_latest_frame_copy()
            if frame is not None:
                realtime_engine.process_frame(frame)

        time.sleep(0.03)  # ~30fps

    print("[SERVER] Real-time detection worker stopped")


def start_realtime_worker():
    global realtime_thread
    if realtime_thread and realtime_thread.is_alive():
        return
    realtime_stop_event.clear()
    realtime_thread = threading.Thread(target=realtime_worker, daemon=True)
    realtime_thread.start()


def run_detection(target_mm=None):
    """Capture one image, detect washer, save annotated result, and return data."""
    success = capture_and_save()
    if not success:
        return {"ok": False, "error": "Capture failed"}, 500

    calib = load_calibration()
    if calib is None:
        return {"ok": False, "error": "No calibration found. Use calibration first."}, 500

    img, circle, pixel_diameter = detect_washer()
    if img is None or circle is None:
        return {"ok": False, "error": "No washer detected"}, 500

    measured_mm = pixels_to_mm(pixel_diameter, calib["mm_per_pixel"])
    matched_size = match_standard_size(measured_mm)
    final_size = matched_size if matched_size else round(measured_mm)

    x, y, r = circle
    output = img.copy()
    cv2.circle(output, (x, y), r, (0, 255, 0), 3)
    cv2.circle(output, (x, y), 4, (0, 0, 255), -1)
    cv2.line(output, (x - r, y), (x + r, y), (255, 0, 0), 2)

    response = {
        "ok": True,
        "matched_size": int(final_size),
        "measured_mm": float(measured_mm),
        "pixel_diameter": int(pixel_diameter)
    }

    if target_mm is not None:
        angle, relation = classify_angle(final_size, target_mm)
        deviation = round(float(final_size) - float(target_mm), 2)
        response.update({
            "target_mm": float(target_mm),
            "deviation_mm": float(deviation),
            "is_match": bool(angle == 0),
            "angle": int(angle),
            "relation": relation
        })
        label = f"{final_size}mm | target:{target_mm}mm | angle:{angle}"
    else:
        label = f"{final_size}mm"

    cv2.putText(output, label, (10, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
    cv2.imwrite(RESULT_IMG, output)

    return response, 200


# ── Always return JSON on unhandled errors, never HTML ──────────────────────

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"[SERVER ERROR] {e}")
    return jsonify({"ok": False, "error": str(e)}), 500

@app.errorhandler(404)
def handle_404(e):
    return jsonify({"ok": False, "error": "Route not found"}), 404


# ── Helper ───────────────────────────────────────────────────────────────────

def capture_and_save():
    """Grab one frame from shared camera worker and save to disk."""
    frame = get_latest_frame_copy()
    if frame is None:
        start_camera_worker()
        time.sleep(0.2)
        frame = get_latest_frame_copy()
    if frame is None:
        print("[ERROR] Camera frame not available.")
        return False
    return save_image(frame) is not None


# ── Frontend routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/image/capture')
def image_capture():
    if not os.path.exists(SAVE_PATH):
        return "No image", 404
    return send_file(SAVE_PATH, mimetype='image/jpeg')


@app.route('/image/result')
def image_result():
    if not os.path.exists(RESULT_IMG):
        return "No result image", 404
    return send_file(RESULT_IMG, mimetype='image/jpeg')


@app.route('/image/calibration')
def image_calibration():
    if not os.path.exists(CALIB_IMG):
        return "No calibration image", 404
    return send_file(CALIB_IMG, mimetype='image/jpeg')


def mjpeg_stream_generator():
    while True:
        frame = get_latest_frame_copy()
        if frame is None:
            time.sleep(0.05)
            continue

        ok, encoded = cv2.imencode('.jpg', frame)
        if not ok:
            time.sleep(0.05)
            continue

        jpg = encoded.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
        time.sleep(0.05)


@app.route('/video_feed')
def video_feed():
    start_camera_worker()
    return app.response_class(
        mjpeg_stream_generator(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# ── Detect ───────────────────────────────────────────────────────────────────

@app.route('/detect')
def detect():
    target_mm = request.args.get('target', type=float)
    print(f"[SERVER] /detect — target={target_mm}mm" if target_mm else "[SERVER] /detect")

    try:
        response, status = run_detection(target_mm=target_mm)
        return jsonify(response), status

    except Exception as e:
        print(f"[SERVER ERROR] /detect: {e}")
        return jsonify({"ok": False, "error": f"Detection error: {str(e)}"}), 500


# ── Calibration ──────────────────────────────────────────────────────────────

@app.route('/calibration/status')
def calibration_status():
    calib = load_calibration()
    if calib is None:
        return jsonify({"calibrated": False})
    return jsonify({"calibrated": True, **calib})


@app.route('/calibrate', methods=['POST'])
def calibrate():
    try:
        data    = request.get_json(silent=True) or {}
        real_mm = data.get("real_mm")

        if real_mm is None or float(real_mm) <= 0:
            return jsonify({"ok": False, "error": "Provide real_mm > 0"}), 400

        real_mm = float(real_mm)
        print(f"[SERVER] /calibrate — real_mm={real_mm}")

        success = capture_and_save()
        if not success:
            return jsonify({"ok": False, "error": "Capture failed"}), 500

        img, circle, pixel_diameter = detect_washer()
        if img is None or circle is None:
            return jsonify({"ok": False, "error": "No washer detected. Reposition and try again."}), 500

        mm_per_pixel = real_mm / int(pixel_diameter)
        calib_data   = save_calibration(mm_per_pixel, real_mm, pixel_diameter)

        x, y, r = circle
        output = img.copy()
        cv2.circle(output, (x, y), r, (0, 200, 255), 3)
        cv2.circle(output, (x, y), 4, (0, 0, 255), -1)
        cv2.line(output, (x - r, y), (x + r, y), (255, 165, 0), 2)
        cv2.putText(output,
                    f"CAL: {real_mm}mm = {int(pixel_diameter)}px | {mm_per_pixel:.5f} mm/px",
                    (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 200, 255), 2)
        cv2.imwrite(CALIB_IMG, output)

        print(f"[SERVER] Calibration saved: {mm_per_pixel:.6f} mm/px")

        return jsonify({
            "ok"              : True,
            "mm_per_pixel"    : calib_data["mm_per_pixel"],
            "real_diameter_mm": calib_data["real_diameter_mm"],
            "pixel_diameter"  : calib_data["pixel_diameter"]
        })

    except Exception as e:
        print(f"[SERVER ERROR] /calibrate: {e}")
        return jsonify({"ok": False, "error": f"Calibration error: {str(e)}"}), 500


# ── ESP32 routes ─────────────────────────────────────────────────────────────

@app.route('/capture')
def capture():
    success = capture_and_save()
    if success:
        print("[SERVER] Image captured and saved.")
        return "CAPTURE_OK"
    return "CAPTURE_FAILED", 500


@app.route('/size')
def size():
    success = capture_and_save()
    if not success:
        return "ERROR:CAPTURE_FAILED", 500
    measured_mm, matched_size = compute_washer_size()
    if measured_mm is None:
        return "ERROR:NO_WASHER", 500
    result = f"SIZE:{matched_size}" if matched_size else f"SIZE:{round(measured_mm)}"
    print(f"[SERVER] ESP32 response: {result}")
    return result


@app.route('/measure')
def measure():
    target_raw = request.args.get("target", type=float)
    tolerance  = request.args.get("tolerance", default=0.5, type=float)
    if not target_raw or target_raw <= 0:
        return jsonify({"ok": False, "error": "Missing or invalid target (mm)"}), 400
    success = capture_and_save()
    if not success:
        return jsonify({"ok": False, "error": "Capture failed"}), 500
    measured_mm, evaluation = compute_washer_size_target(target_raw, tolerance_mm=tolerance)
    if measured_mm is None:
        return jsonify({"ok": False, "error": "Measurement failed"}), 500
    return jsonify({"ok": True, **evaluation})


@app.route('/cmd')
def receive_cmd():
    return current_conveyor_cmd


@app.route('/cmd/status')
def cmd_status():
    return jsonify({"ok": True, "command": current_conveyor_cmd})


@app.route('/cmd/set', methods=['POST'])
def cmd_set():
    global current_conveyor_cmd, auto_processing_enabled, realtime_engine, last_cmd_request_id

    data = request.get_json(silent=True) or {}
    cmd = str(data.get("command", "")).strip().upper()

    # Get a unique request ID (timestamp + random) to prevent duplicates
    request_id = data.get("request_id", f"{time.time()}")

    if cmd not in VALID_CONVEYOR_COMMANDS:
        return jsonify({
            "ok": False,
            "error": "Invalid command. Use START or STOP"
        }), 400

    # Acquire lock to prevent concurrent modifications
    with cmd_lock:
        # Prevent processing duplicate requests (same request within 500ms)
        if last_cmd_request_id == request_id:
            print(f"[SERVER] Duplicate request ignored: {cmd} (request_id={request_id})")
            return jsonify({"ok": True, "command": current_conveyor_cmd, "duplicate": True})

        last_cmd_request_id = request_id

        # Only update if command actually changed
        if current_conveyor_cmd == cmd:
            print(f"[SERVER] Command already set to: {cmd} (no change)")
            return jsonify({"ok": True, "command": current_conveyor_cmd})

        current_conveyor_cmd = cmd
        auto_processing_enabled = (current_conveyor_cmd == "START")

        # Handle real-time engine state
        if cmd == "STOP":
            # STOP: Disable real-time engine, preserve target for later
            if realtime_engine is not None:
                realtime_engine.disable()
            target_info = f"{desired_target_mm}mm" if desired_target_mm is not None else "(no target)"
            print(f"[SERVER] Conveyor STOPPED. Target preserved: {target_info}")

        elif cmd == "START":
            # START: Re-enable real-time engine if target is set
            if desired_target_mm is not None and realtime_engine is not None:
                realtime_engine.enable(target_mm=desired_target_mm)
                print(f"[SERVER] Conveyor STARTED. Real-time engine re-enabled with target: {desired_target_mm}mm")
            else:
                print("[SERVER] Conveyor STARTED. (No target set yet)")

        print(f"[SERVER] Conveyor command set by UI: {current_conveyor_cmd}")

    return jsonify({"ok": True, "command": current_conveyor_cmd})


@app.route('/target/status')
def target_status():
    return jsonify({"ok": True, "target_mm": desired_target_mm})


@app.route('/target/set', methods=['POST'])
def target_set():
    global desired_target_mm, current_conveyor_cmd, auto_processing_enabled, realtime_engine

    data = request.get_json(silent=True) or {}
    target = data.get("target_mm")

    try:
        target = float(target)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid target_mm"}), 400

    if target <= 0:
        return jsonify({"ok": False, "error": "target_mm must be > 0"}), 400

    desired_target_mm = target
    current_conveyor_cmd = "START"
    auto_processing_enabled = True
    start_auto_processing_worker()

    # Enable real-time detection engine
    if realtime_engine is not None:
        realtime_engine.enable(target_mm=target)
        print(f"[SERVER] Real-time engine enabled with target: {target}mm")

    print(f"[SERVER] Sorting target set by UI: {desired_target_mm}mm")
    return jsonify({"ok": True, "target_mm": desired_target_mm, "command": current_conveyor_cmd})


@app.route('/sort/latest')
def sort_latest():
    return jsonify(latest_sort_result)


@app.route('/sort/decision')
def sort_decision():
    global latest_sort_result

    if current_conveyor_cmd != "START":
        return "STOPPED"

    if desired_target_mm is None:
        return "NO_TARGET"

    if latest_sort_result.get("ok") and "angle" in latest_sort_result:
        return str(int(latest_sort_result["angle"]))

    return "WAITING"


# ── Real-Time Detection API ───────────────────────────────────────────────────

@app.route('/realtime/state')
def realtime_state():
    """Get current real-time detection state."""
    global realtime_engine

    if realtime_engine is None:
        return jsonify({"state": "IDLE", "error": "Engine not initialized"}), 500

    state_info = realtime_engine.get_state()
    return jsonify(state_info), 200


@app.route('/realtime/settings', methods=['POST'])
def realtime_settings():
    """Update real-time detection settings."""
    global realtime_engine

    if realtime_engine is None:
        return jsonify({"ok": False, "error": "Engine not initialized"}), 500

    try:
        data = request.get_json(silent=True) or {}

        # Update settings if provided
        if 'min_circularity' in data:
            realtime_engine.MIN_CIRCULARITY = float(data['min_circularity'])
        if 'stable_time' in data:
            realtime_engine.STABLE_TIME = float(data['stable_time'])
        if 'cooldown_time' in data:
            realtime_engine.COOLDOWN_TIME = float(data['cooldown_time'])
        if 'bg_history' in data:
            realtime_engine.BG_HISTORY = int(data['bg_history'])

        print(f"[SERVER] Real-time settings updated: {data}")
        return jsonify({"ok": True, "settings": data}), 200

    except Exception as e:
        print(f"[SERVER ERROR] /realtime/settings: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Initialize real-time detection engine
    realtime_engine = RealtimeDetectionEngine(shared_state_dict=latest_sort_result)

    start_camera_worker()
    start_auto_processing_worker()
    start_realtime_worker()

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"[SERVER] Running on http://{local_ip}:5000")
    print(f"[SERVER] Open in browser : http://{local_ip}:5000")
    print(f"[SERVER] ESP32 endpoints : /size  /capture  /measure?target=25  /cmd  /sort/decision")
    print(f"[SERVER] Conveyor UI API : /cmd/status  /cmd/set  /target/status  /target/set")
    print(f"[SERVER] Sort API        : /sort/latest")
    print(f"[SERVER] RealTime API    : /realtime/state  /realtime/settings")
    print(f"[SERVER] Camera API      : /video_feed")
    app.run(host='0.0.0.0', port=5000, debug=False)
