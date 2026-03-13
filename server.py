import cv2
import os
import socket
from flask import Flask, jsonify, request, render_template, send_file

from step3_save_image import save_image
from step7_washer_detection import detect_washer
from step8_calibration import load_calibration, save_calibration
from step9_compute_size import compute_washer_size_target, compute_washer_size, pixels_to_mm, match_standard_size

CAMERA_INDEX = 0

app = Flask(__name__)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH   = os.path.join(PROJECT_DIR, "capture.jpg")
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
RESULT_IMG  = os.path.join(RESULTS_DIR, "step7_washer_detected.jpg")
CALIB_IMG   = os.path.join(RESULTS_DIR, "calibration_result.jpg")

os.makedirs(RESULTS_DIR, exist_ok=True)


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
    """Open camera fresh, grab one frame, release, save to disk."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
        return False
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        print("[ERROR] Failed to read frame.")
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


# ── Detect ───────────────────────────────────────────────────────────────────

@app.route('/detect')
def detect():
    target_mm = request.args.get('target', type=float)
    print(f"[SERVER] /detect — target={target_mm}mm" if target_mm else "[SERVER] /detect")

    try:
        success = capture_and_save()
        if not success:
            return jsonify({"ok": False, "error": "Capture failed"}), 500

        calib = load_calibration()
        if calib is None:
            return jsonify({"ok": False, "error": "No calibration found. Use the Calibration panel first."}), 500

        img, circle, pixel_diameter = detect_washer()
        if img is None or circle is None:
            return jsonify({"ok": False, "error": "No washer detected. Check lighting and position."}), 500

        measured_mm  = pixels_to_mm(pixel_diameter, calib["mm_per_pixel"])
        matched_size = match_standard_size(measured_mm)
        final_size   = matched_size if matched_size else round(measured_mm)

        x, y, r = circle
        output = img.copy()
        cv2.circle(output, (x, y), r, (0, 255, 0), 3)
        cv2.circle(output, (x, y), 4, (0, 0, 255), -1)
        cv2.line(output, (x - r, y), (x + r, y), (255, 0, 0), 2)

        deviation = None
        is_match  = None

        if target_mm is not None:
            deviation  = round(float(measured_mm) - float(target_mm), 2)
            is_match   = bool(abs(deviation) <= 3.0)
            label = f"{final_size}mm | target:{target_mm}mm | {'MATCH' if is_match else 'NO MATCH'}"

        cv2.putText(output, label, (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
        cv2.imwrite(RESULT_IMG, output)

        print(f"[SERVER] Detected: {final_size}mm  measured: {measured_mm}mm  {pixel_diameter}px")

        response = {
            "ok"            : True,
            "matched_size"  : int(final_size),
            "measured_mm"   : float(measured_mm),
            "pixel_diameter": int(pixel_diameter)
        }
        if target_mm is not None:
            response["target_mm"]    = float(target_mm)
            response["deviation_mm"] = float(deviation)
            response["is_match"]     = bool(is_match)

        return jsonify(response)

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
    return "HELLO_ESP32"


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"[SERVER] Running on http://{local_ip}:5000")
    print(f"[SERVER] Open in browser : http://{local_ip}:5000")
    print(f"[SERVER] ESP32 endpoints : /size  /capture  /measure?target=25")
    app.run(host='0.0.0.0', port=5000, debug=False)
