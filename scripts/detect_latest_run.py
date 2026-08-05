import json
import os
import csv
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

model = joblib.load("data/model.joblib")
df = pd.read_csv("data/workflow_runs.csv")
df["is_failed"] = df["conclusion"].fillna("unknown").eq("failed").astype(int)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df["run_hour"] = df["created_at"].dt.hour
df["duration_log"] = np.log(df["duration_seconds"] + 1)

X = df[["duration_seconds", "is_failed", "run_hour", "duration_log"]].fillna(0)
df["anomaly_label"] = model.predict(X)
df["anomaly_score"] = model.decision_function(X)

# Résultat du dernier run (pour l'alerte email / warning GitHub, comportement inchangé)
latest = df.sort_values("created_at", ascending=False).iloc[0]
result = {
    "run_id": int(latest["run_id"]),
    "conclusion": latest["conclusion"],
    "duration_seconds": int(latest["duration_seconds"]),
    "anomaly_label": int(latest["anomaly_label"]),
    "anomaly_score": float(latest["anomaly_score"])
}
with open("data/latest_detection.json", "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))

# Historique complet : ajoute TOUTES les anomalies non encore enregistrées
history_file = "data/anomaly_history.csv"
exists = os.path.exists(history_file)
existing_ids = set()
if exists:
    existing = pd.read_csv(history_file)
    existing_ids = set(existing["run_id"].values)

anomalies = df[df["anomaly_label"] == -1]
new_entries = anomalies[~anomalies["run_id"].isin(existing_ids)]

if not new_entries.empty:
    with open(history_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["detected_at", "run_id", "conclusion", "duration_seconds", "anomaly_score", "html_url"])
        for _, row in new_entries.iterrows():
            writer.writerow([
                datetime.utcnow().isoformat(),
                int(row["run_id"]),
                row["conclusion"],
                int(row["duration_seconds"]),
                float(row["anomaly_score"]),
                row.get("html_url", "")
            ])
    print(f"Added {len(new_entries)} new anomalies to history")
else:
    print("No new anomalies to add to history")
