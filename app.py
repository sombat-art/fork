"""
Minimal server for the post-use evaluation form.

- GET  /        -> serves form.html as-is
- POST /submit  -> validates the submission and appends one row to evaluations.csv
- GET  /thanks  -> plain thank-you page
- GET  /export  -> downloads evaluations.csv (HTTP Basic Auth)

No database. One folder, two files to run (form.html + app.py), one CSV file
that grows as people submit. Good fit for ~500 submissions; not meant to
scale past that without moving to a real database.

Run:
    pip install flask
    python3 app.py
    # open http://localhost:8000

Deploy: same idea as any small Flask app — gunicorn behind Caddy/nginx for
HTTPS, or just `python3 app.py` behind a reverse proxy. See README.md.
"""

import csv
import os
import threading
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, Response, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.environ.get("CSV_PATH", os.path.join(BASE_DIR, "evaluations.csv"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "change-me")

app = Flask(__name__)
_csv_lock = threading.Lock()

USAGE_FREQUENCY = ["ไม่ใช้เลย", "นานๆครั้ง", "บ่อยแต่ไม่ทุกวัน", "ทุกวัน แต่ไม่ทุกมื้อ", "ทุกวัน และทุกมื้อ"]
CALIBRATION_AWARENESS = ["ไม่ทราบเลย", "ทราบ แต่ไม่เคยทำ", "ทราบ และเคยทำแล้ว"]
PRICE_AGREEMENT = ["เห็นด้วย", "ไม่เห็นด้วย"]

SATISFACTION_KEYS = [
    "sat_shape", "sat_grip", "sat_weight", "sat_button", "sat_light_display",
    "sat_light_brightness", "sat_speed", "sat_accuracy", "sat_cleaning",
    "sat_coating_durability", "sat_battery_life", "sat_storage",
    "sat_portability", "sat_dipped_food", "sat_health_benefit",
    "sat_switch_likelihood",
]

FIELDNAMES = (
    ["submitted_at", "usage_frequency"]
    + SATISFACTION_KEYS
    + ["calibration_awareness", "calibration_times", "price_agreement", "suggestions"]
)


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASS:
            return Response(
                "Authentication required", 401,
                {"WWW-Authenticate": 'Basic realm="Evaluation form admin"'},
            )
        return view(*args, **kwargs)
    return wrapped


def ensure_csv_header():
    if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0:
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(BASE_DIR, "form.html")


@app.route("/submit", methods=["POST"])
def submit():
    form = request.form
    errors = []

    usage_frequency = form.get("usage_frequency", "")
    if usage_frequency not in USAGE_FREQUENCY:
        errors.append("missing/invalid usage_frequency")

    satisfaction = {}
    for key in SATISFACTION_KEYS:
        val = form.get(key, "")
        if val not in ("1", "2", "3", "4", "5"):
            errors.append("missing/invalid {}".format(key))
        satisfaction[key] = val

    calibration = form.get("calibration", "")
    if calibration not in CALIBRATION_AWARENESS:
        errors.append("missing/invalid calibration")

    price_agreement = form.get("price_agreement", "")
    if price_agreement not in PRICE_AGREEMENT:
        errors.append("missing/invalid price_agreement")

    if errors:
        return (
            "กรุณากลับไปตอบคำถามให้ครบทุกข้อ แล้วส่งแบบฟอร์มใหม่อีกครั้ง "
            "(" + "; ".join(errors) + ")",
            400,
        )

    row = {
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "usage_frequency": usage_frequency,
        "calibration_awareness": calibration,
        "calibration_times": form.get("calibration_times", "").strip() if calibration == "ทราบ และเคยทำแล้ว" else "",
        "price_agreement": price_agreement,
        "suggestions": form.get("suggestions", "").strip(),
    }
    row.update(satisfaction)

    with _csv_lock:
        ensure_csv_header()
        with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writerow(row)

    return send_from_directory(BASE_DIR, "thanks.html")


@app.route("/export", methods=["GET"])
@require_admin
def export():
    ensure_csv_header()
    return send_from_directory(BASE_DIR, os.path.basename(CSV_PATH), as_attachment=True)


@app.route("/healthz", methods=["GET"])
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    ensure_csv_header()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
