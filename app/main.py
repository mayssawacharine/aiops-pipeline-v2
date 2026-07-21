from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify, request
import csv
from datetime import datetime
import random
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import render_template
import pandas as pd
import os
import sys
import subprocess
import shutil
from flask import redirect, url_for
app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
def log_request(endpoint, status_code, params=None):
    os.makedirs("data", exist_ok=True)
    log_file = "data/api_requests.csv"
    exists = os.path.exists(log_file)
    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["timestamp", "endpoint", "status_code", "params", "ip"])
        writer.writerow([
            datetime.utcnow().isoformat(),
            endpoint,
            status_code,
            str(params) if params else "",
            request.remote_addr
        ])
@app.after_request
def after_request(response):
    log_request(request.path, response.status_code, dict(request.args))
    return response
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.get("/build-log")
def build_log():
    return jsonify({
        "build_id": random.randint(1000, 9999),
        "status": random.choice(["success", "success", "failed"]),
        "duration_seconds": random.randint(20, 180),
        "test_count": random.randint(10, 30),
        "failed_tests": random.randint(0, 5),
        "timestamp": datetime.utcnow().isoformat()
    })

@app.get("/simulate")
@limiter.limit("10 per minute")
def simulate():
    status = request.args.get("status", "success")

    try:
        duration = int(request.args.get("duration", 45))
    except (ValueError, TypeError):
        return jsonify({"error": "duration must be a valid integer"}), 400

    try:
        failed_tests = int(request.args.get("failed_tests", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "failed_tests must be a valid integer"}), 400

    if duration < 0 or duration > 3600:
        return jsonify({"error": "duration must be between 0 and 3600 seconds"}), 400

    return jsonify({
        "build_id": random.randint(10000, 99999),
        "status": status,
        "duration_seconds": duration,
        "test_count": 20,
        "failed_tests": failed_tests,
        "timestamp": datetime.utcnow().isoformat()
    })
@app.get("/refresh")
@limiter.limit("5 per hour")
def refresh():
    provided_secret = request.args.get("secret", "")
    expected_secret = os.getenv("REFRESH_SECRET", "")
    if not expected_secret or provided_secret != expected_secret:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        subprocess.run([sys.executable, "scripts/fetch_metrics.py"], check=True, timeout=60)
        subprocess.run([sys.executable, "scripts/train_model.py"], check=True, timeout=60)
        if os.path.exists("data/anomalies.png"):
            shutil.copy("data/anomalies.png", "app/static/anomalies.png")
        if os.path.exists("data/api_requests.csv"):
            subprocess.run([sys.executable, "scripts/detect_api_anomalies.py"], check=True, timeout=60)
    except subprocess.CalledProcessError as e:
        return f"Erreur lors du rafraîchissement : {e}", 500
    return redirect(url_for("dashboard"))
@app.get("/dashboard")
def dashboard():
    csv_path = "data/scored_runs.csv"
    if not os.path.exists(csv_path):
        return render_template("dashboard.html", rows=[], stats={}, chart_path=None)

    df = pd.read_csv(csv_path)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df = df.sort_values("created_at", ascending=False)

    stats = {
        "total_runs": int(len(df)),
        "failed_runs": int((df["conclusion"] == "failed").sum()),
        "anomalies": int((df["anomaly_label"] == -1).sum()),
        "avg_duration": round(df["duration_seconds"].mean(), 2)
    }
    df["created_at_display"] = df["created_at"].dt.strftime("%d/%m/%Y %H:%M")
    rows = df.head(20).to_dict(orient="records")
    return render_template("dashboard.html", rows=rows, stats=stats, chart_path="/static/anomalies.png")
@app.get("/security")
def security_dashboard():
    csv_path = "data/api_security_scored.csv"
    if not os.path.exists(csv_path):
        return render_template("security.html", rows=[], stats={})

    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp", ascending=False)

    stats = {
        "total_requests": int(len(df)),
        "suspicious_requests": int((df["security_anomaly"] == -1).sum()),
        "error_requests": int((df["is_error"] == 1).sum()),
        "max_payload_length": int(df["params_length"].max())
    }
    df["timestamp_display"] = df["timestamp"].dt.strftime("%H:%M:%S.%f").str[:-3]
    rows = df.head(30).to_dict(orient="records")
    return render_template("security.html", rows=rows, stats=stats)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
