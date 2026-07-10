import os
import numpy as np
import joblib
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

os.makedirs("data", exist_ok=True)
df = pd.read_csv("data/workflow_runs.csv")

df["is_failed"] = df["conclusion"].fillna("unknown").eq("failed").astype(int)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df["run_hour"] = df["created_at"].dt.hour
df["duration_log"] = np.log(df["duration_seconds"] + 1)

features = df[["duration_seconds", "is_failed", "run_hour", "duration_log"]].fillna(0)
model = IsolationForest(n_estimators=200, contamination=0.10, random_state=42)
model.fit(features)

df["anomaly_label"] = model.fit_predict(features)
df["anomaly_score"] = model.decision_function(features)
joblib.dump(model, "data/model.joblib")
df.to_csv("data/scored_runs.csv", index=False)

plt.figure(figsize=(12,5))
colors = df["anomaly_label"].map({1: "#4dd4a0", -1: "#ff7c98"})
plt.scatter(df.index, df["duration_seconds"], c=colors)
plt.title("Workflow Duration with Detected Anomalies")
plt.xlabel("Row Index")
plt.ylabel("Duration (seconds)")
plt.tight_layout()
plt.savefig("data/anomalies.png", dpi=150)
print(df[["run_id","duration_seconds","conclusion","anomaly_label","anomaly_score"]].head())
