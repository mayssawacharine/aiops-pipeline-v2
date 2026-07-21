import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

df = pd.read_csv("data/api_requests.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

# Feature 1 : le code de statut est-il une erreur ?
df["is_error"] = df["status_code"].apply(lambda x: 1 if int(x) >= 400 else 0)

# Feature 2 : combien de requêtes dans les 2 dernières secondes (même IP) ?
df["requests_last_2s"] = 0
for i in range(len(df)):
    now = df.loc[i, "timestamp"]
    ip = df.loc[i, "ip"]
    window = df[(df["timestamp"] > now - pd.Timedelta(seconds=2)) & (df["timestamp"] <= now) & (df["ip"] == ip)]
    df.loc[i, "requests_last_2s"] = len(window)

# Feature 3 : longueur des paramètres envoyés (payloads suspects sont souvent longs)
df["params_length"] = df["params"].fillna("").astype(str).apply(len)

features = df[["is_error", "requests_last_2s", "params_length"]]

model = IsolationForest(n_estimators=200, contamination=0.15, random_state=42)
df["security_anomaly"] = model.fit_predict(features)
df["security_score"] = model.decision_function(features)

os.makedirs("data", exist_ok=True)
df.to_csv("data/api_security_scored.csv", index=False)
joblib.dump(model, "data/security_model.joblib")

print(f"Total requests analyzed: {len(df)}")
print(f"Flagged as suspicious: {(df['security_anomaly'] == -1).sum()}")
print(df[["timestamp", "endpoint", "status_code", "requests_last_2s", "params_length", "security_anomaly"]].tail(15))
