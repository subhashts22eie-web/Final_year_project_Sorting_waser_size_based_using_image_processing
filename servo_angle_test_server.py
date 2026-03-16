import socket
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

VALID_ANGLES = {0, 90, 180}
current_angle = 90
last_set_source = "init"
last_set_time = time.time()


@app.route("/")
def index():
    return (
        "<h2>Servo Angle Test Server</h2>"
        "<p>Use these endpoints:</p>"
        "<ul>"
        "<li>GET /angle</li>"
        "<li>GET /angle/status</li>"
        "<li>POST /angle/set with JSON {\"angle\": 0|90|180}</li>"
        "<li>GET /angle/0, /angle/90, /angle/180</li>"
        "</ul>"
    )


@app.route("/angle")
def get_angle_plain():
    """ESP32 polling endpoint: returns plain angle text, e.g. '90'."""
    return str(current_angle)


@app.route("/angle/status")
def get_angle_status():
    return jsonify({
        "ok": True,
        "angle": current_angle,
        "last_set_source": last_set_source,
        "last_set_epoch": last_set_time,
    })


@app.route("/angle/set", methods=["POST"])
def set_angle_json():
    global current_angle, last_set_source, last_set_time

    data = request.get_json(silent=True) or {}
    angle = data.get("angle")

    try:
        angle = int(angle)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid angle. Use 0, 90, or 180."}), 400

    if angle not in VALID_ANGLES:
        return jsonify({"ok": False, "error": "Angle must be one of 0, 90, 180."}), 400

    current_angle = angle
    last_set_source = "json"
    last_set_time = time.time()
    print(f"[SERVO TEST] Angle set to {current_angle} deg via /angle/set")

    return jsonify({"ok": True, "angle": current_angle})


@app.route("/angle/<int:value>")
def set_angle_quick(value: int):
    global current_angle, last_set_source, last_set_time

    if value not in VALID_ANGLES:
        return jsonify({"ok": False, "error": "Angle must be one of 0, 90, 180."}), 400

    current_angle = value
    last_set_source = "quick"
    last_set_time = time.time()
    print(f"[SERVO TEST] Angle set to {current_angle} deg via /angle/{value}")

    return jsonify({"ok": True, "angle": current_angle})


if __name__ == "__main__":
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print(f"[SERVO TEST] Running on http://{local_ip}:5050")
    print("[SERVO TEST] ESP32 poll endpoint: /angle")
    print("[SERVO TEST] Set by browser: /angle/0 /angle/90 /angle/180")
    print("[SERVO TEST] Set by API: POST /angle/set")

    app.run(host="0.0.0.0", port=5050, debug=False)
