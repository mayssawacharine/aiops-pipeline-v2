from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify, request
from datetime import datetime
import random
from flask import render_template
import pandas as pd
import os
import sys
import subprocess
from flask import redirect, url_for
app = Flask(__name__)

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
def simulate():
    status = request.args.get("status", "success")
    duration = int(request.args.get("duration", 45))
    failed_tests = int(request.args.get("failed_tests", 0))
    return jsonify({
        "build_id": random.randint(10000, 99999),
        "status": status,
        "duration_seconds": duration,
        "test_count": 20,
        "failed_tests": failed_tests,
        "timestamp": datetime.utcnow().isoformat()
    })
@app.get("/refresh")
def refresh():
    try:
        subprocess.run([sys.executable, "scripts/fetch_metrics.py"], check=True, timeout=60)
        subprocess.run(["python", "scripts/train_model.py"], check=True, timeout=60)
        if os.path.exists("data/anomalies.png"):
            subprocess.run(["cp", "data/anomalies.png", "app/static/anomalies.png"], check=True)
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
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
