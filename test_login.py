import requests
import json

# Test direct backend login
print("Testing direct backend login on port 18000...")
try:
    response = requests.post(
        "http://localhost:18000/api/v1/auth/login",
        json={
            "email": "admin@pyramid-computer.de",
            "password": "PyramidAdmin2024!"
        }
    )
    if response.status_code == 200:
        data = response.json()
        print("[OK] Backend login successful!")
        print(f"  Token: {data['access_token'][:50]}...")
        print(f"  User: {data['user']['email']}")
    else:
        print(f"[FAIL] Backend login failed: {response.status_code}")
        print(f"  Response: {response.text}")
except Exception as e:
    print(f"[FAIL] Backend connection error: {e}")

print("\n" + "="*50 + "\n")

# Test frontend proxy
print("Testing frontend proxy on port 4000...")
try:
    response = requests.post(
        "http://localhost:4000/api/v1/auth/login",
        json={
            "email": "admin@pyramid-computer.de",
            "password": "PyramidAdmin2024!"
        }
    )
    if response.status_code == 200:
        data = response.json()
        print("[OK] Frontend proxy login successful!")
        print(f"  Token: {data['access_token'][:50]}...")
    else:
        print(f"[FAIL] Frontend proxy login failed: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"[FAIL] Frontend proxy error: {e}")

print("\n" + "="*50 + "\n")

# Test if frontend is serving
print("Testing frontend is serving...")
try:
    response = requests.get("http://localhost:4000/")
    if response.status_code == 200:
        print("[OK] Frontend is serving")
        if "Pyramid RAG" in response.text:
            print("  Found Pyramid RAG in response")
    else:
        print(f"[FAIL] Frontend not serving: {response.status_code}")
except Exception as e:
    print(f"[FAIL] Frontend connection error: {e}")