import requests

BASE_URL = "http://192.168.56.10:5000"

def test_flood():
    print("=== Test 1: Flood requests (simulate brute-force pattern) ===")
    for i in range(50):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if i % 10 == 0:
                print(f"Request {i}: status {r.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request {i} failed: {e}")

def test_injection_attempts():
    print("\n=== Test 2: Injection-style payloads on /simulate ===")
    payloads = [
        "success' OR '1'='1",
        "<script>alert(1)</script>",
        "../../etc/passwd",
        "success; rm -rf /",
        "A" * 5000,
    ]
    for payload in payloads:
        try:
            r = requests.get(f"{BASE_URL}/simulate", params={"status": payload}, timeout=5)
            print(f"Payload: {payload[:40]!r:45} -> status {r.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Payload {payload[:40]!r} caused error: {e}")

def test_type_confusion():
    print("\n=== Test 3: Unexpected types on numeric params ===")
    bad_values = ["abc", "-999999", "99999999999999999999", "3.14.15", ""]
    for val in bad_values:
        try:
            r = requests.get(f"{BASE_URL}/simulate", params={"duration": val}, timeout=5)
            print(f"duration={val!r:25} -> status {r.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"duration={val!r} caused error: {e}")

if __name__ == "__main__":
    test_flood()
    test_injection_attempts()
    test_type_confusion()
