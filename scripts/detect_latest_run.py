import json
import joblib
import pandas as pd
import numpy as np
import csv
import os
from datetime import datetime

model = joblib.load("data/model.joblib")
df = pd.read_csv("data/workflow_runs.csv")
df["is_failed"] = df["conclusion"].fillna("unknown").eq("failed").astype(int)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df["run_hour"] = df["created_at"].dt.hour
df["duration_log"] = np.log(df["duration_seconds"] + 1)

latest = df.tail(1).copy()
X = latest[["duration_seconds", "is_failed", "run_hour", "duration_log"]].fillna(0)
latest["anomaly_label"] = model.predict(X)
latest["anomaly_score"] = model.decision_function(X)

result = {
    "run_id": int(latest.iloc[0]["run_id"]),
    "conclusion": latest.iloc[0]["conclusion"],
    "duration_seconds": int(latest.iloc[0]["duration_seconds"]),
    "anomaly_label": int(latest.iloc[0]["anomaly_label"]),
    "anomaly_score": float(latest.iloc[0]["anomaly_score"])
}
if result["anomaly_label"] == -1:
    history_file = "data/anomaly_history.csv"
    exists = os.path.exists(history_file)
    already_logged = False
    if exists:
        existing = pd.read_csv(history_file)
        already_logged = result["run_id"] in existing["run_id"].values
    if not already_logged:
        with open(history_file, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["detected_at", "run_id", "conclusion", "duration_seconds", "anomaly_score", "html_url"])
            writer.writerow([
                datetime.utcnow().isoformat(),
                result["run_id"],
                result["conclusion"],
                result["duration_seconds"],
                result["anomaly_score"],
                df.tail(1).iloc[0].get("html_url", "")
            ])
with open("data/latest_detection.json", "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
