import os
import requests
import pandas as pd

TOKEN = os.getenv("SONAR_API_TOKEN")
PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY")

url = "https://sonarcloud.io/api/issues/search"
params = {
    "componentKeys": PROJECT_KEY,
    "resolved": "false",
    "ps": 100
}
headers = {"Authorization": f"Bearer {TOKEN}"}

response = requests.get(url, headers=headers, params=params, timeout=30)
response.raise_for_status()
data = response.json()

rows = []
for issue in data.get("issues", []):
    rows.append({
        "rule": issue.get("rule"),
        "severity": issue.get("severity"),
        "type": issue.get("type"),
        "message": issue.get("message"),
        "component": issue.get("component", "").split(":")[-1],
        "line": issue.get("line", ""),
        "status": issue.get("status"),
        "creation_date": issue.get("creationDate", "")[:10]
    })

df = pd.DataFrame(rows)
os.makedirs("data", exist_ok=True)
df.to_csv("data/sonar_issues.csv", index=False)
print(f"Total issues fetched: {len(df)}")
if not df.empty:
    print(df["severity"].value_counts())
