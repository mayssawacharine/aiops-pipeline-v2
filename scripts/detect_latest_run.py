import json
import joblib
import pandas as pd
import numpy as np

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

with open("data/latest_detection.json", "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
