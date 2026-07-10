import os
import sqlite3
from datetime import datetime
import requests
import pandas as pd

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPO")
url = f"https://api.github.com/repos/{REPO}/actions/runs"
headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()
runs = response.json()["workflow_runs"]
rows = []
for run in runs:
    created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    updated = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
    duration_seconds = int((updated - created).total_seconds())
    rows.append({
        "run_id": run["id"],
        "name": run["name"],
        "status": run["status"],
        "conclusion": run.get("conclusion"),
        "event": run["event"],
        "branch": run["head_branch"],
        "created_at": run["created_at"],
        "updated_at": run["updated_at"],
        "duration_seconds": duration_seconds,
        "html_url": run["html_url"]
    })

df = pd.DataFrame(rows)
os.makedirs("data", exist_ok=True)
df.to_csv("data/workflow_runs.csv", index=False)

conn = sqlite3.connect("data/metrics.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id INTEGER PRIMARY KEY,
    name TEXT,
    status TEXT,
    conclusion TEXT,
    event TEXT,
    branch TEXT,
    created_at TEXT,
    updated_at TEXT,
    duration_seconds INTEGER,
    html_url TEXT
)
""")
for row in rows:
    conn.execute("""
    INSERT OR REPLACE INTO workflow_runs
    (run_id, name, status, conclusion, event, branch, created_at, updated_at, duration_seconds, html_url)
    VALUES (:run_id, :name, :status, :conclusion, :event, :branch, :created_at, :updated_at, :duration_seconds, :html_url)
    """, row)
conn.commit()
conn.close()
print(df.head())
