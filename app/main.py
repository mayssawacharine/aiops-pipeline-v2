from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify, request
import csv
from datetime import datetime
import random
from flask_talisman import Talisman
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

if os.getenv("RENDER"):
    Talisman(app, force_https=True, strict_transport_security=True, content_security_policy=None)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour", "20 per minute"]
)
def log_request(endpoint, status_code, params=None):
    os.makedirs("data", exist_ok=True)
    log_file = "data/api_requests.csv"
    exists = os.path.exists(log_file) and os.path.getsize(log_file) > 0
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
@app.post("/refresh")
@limiter.limit("20 per hour")
def refresh():
    provided_secret = request.headers.get("X-Refresh-Secret", "")
    expected_secret = os.getenv("REFRESH_SECRET", "")
    if not expected_secret or provided_secret != expected_secret:
        return jsonify({"error": "Unauthorized"}), 401

    scripts = ["scripts/fetch_metrics.py", "scripts/train_model.py", "scripts/detect_latest_run.py"]
    if os.path.exists("data/api_requests.csv"):
        scripts.append("scripts/detect_api_anomalies.py")
    if os.getenv("SONAR_API_TOKEN"):
        scripts.append("scripts/fetch_sonar_issues.py")
    for script in scripts:
        result = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"[REFRESH ERROR] {script} failed with code {result.returncode}")
            print(f"[REFRESH ERROR] stdout: {result.stdout}")
            print(f"[REFRESH ERROR] stderr: {result.stderr}")
            return jsonify({"error": f"Échec du script {script}"}), 500

    if os.path.exists("data/anomalies.png"):
        shutil.copy("data/anomalies.png", "app/static/anomalies.png")

    return redirect(url_for("dashboard"))
@app.get("/dashboard")
def dashboard():
    csv_path = "data/scored_runs.csv"
    if not os.path.exists(csv_path):
        return render_template("dashboard.html", rows=[], stats={}, chart_data=[])

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
    rows = df.head(50).to_dict(orient="records")

    chart_df = df.sort_values("created_at").tail(50)
    chart_data = [
        {
            "x": i,
            "y": int(row["duration_seconds"]),
            "anomaly": bool(row["anomaly_label"] == -1),
            "run_id": int(row["run_id"]),
            "date": row["created_at"].strftime("%d/%m %H:%M")
        }
        for i, (_, row) in enumerate(chart_df.iterrows())
    ]

    return render_template("dashboard.html", rows=rows, stats=stats, chart_data=chart_data)

@app.get("/security")
def security_dashboard():
    sonar_rows, sonar_stats = [], {}
    sonar_path = "data/sonar_issues.csv"
    if os.path.exists(sonar_path):
        sdf = pd.read_csv(sonar_path)
        sonar_stats = {
            "total_issues": int(len(sdf)),
            "critical": int((sdf["severity"] == "CRITICAL").sum()) if "severity" in sdf else 0,
            "major": int((sdf["severity"] == "MAJOR").sum()) if "severity" in sdf else 0,
            "minor": int((sdf["severity"] == "MINOR").sum()) if "severity" in sdf else 0,
            "vulnerabilities": int((sdf["type"] == "VULNERABILITY").sum()) if "type" in sdf else 0,
            "code_smells": int((sdf["type"] == "CODE_SMELL").sum()) if "type" in sdf else 0,
        }
        sdf = sdf.sort_values("severity", key=lambda s: s.map({"BLOCKER": 0, "CRITICAL": 1, "MAJOR": 2, "MINOR": 3, "INFO": 4}))
        sonar_rows = sdf.to_dict(orient="records")

    return render_template("security.html", sonar_rows=sonar_rows, sonar_stats=sonar_stats)
@app.get("/anomaly-history")
def anomaly_history():
    csv_path = "data/anomaly_history.csv"
    if not os.path.exists(csv_path):
        return render_template("anomaly_history.html", rows=[])
    df = pd.read_csv(csv_path)
    df["detected_at"] = pd.to_datetime(df["detected_at"])
    df = df.sort_values("detected_at", ascending=False)
    rows = df.to_dict(orient="records")
    return render_template("anomaly_history.html", rows=rows)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
