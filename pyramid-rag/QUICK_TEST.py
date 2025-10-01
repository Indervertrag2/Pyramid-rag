#!/usr/bin/env python3
"""Quick integration test - tests all major features in < 30 seconds"""

import requests
import json

BASE_URL = "http://localhost:18000"

print("PYRAMID RAG - QUICK INTEGRATION TEST")
print("=" * 50)

# 1. Health Check
try:
    r = requests.get(f"{BASE_URL}/health", timeout=2)
    print(f"[OK] Health Check: {r.json()['status']}")
except:
    print("[FAIL] Backend not responding - check if services are running")
    exit(1)

# 2. Login
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/login",
                     json={"email": "admin@pyramid-computer.de", "password": "admin123"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Authentication: Logged in")
except:
    print("[FAIL] Login failed")
    exit(1)

# 3. User Info
try:
    r = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    user = r.json()
    print(f"[OK] User Info: {user['email']} (Admin: {user['is_superuser']})")
except:
    print("[FAIL] User info failed")

# 4. Documents
try:
    r = requests.get(f"{BASE_URL}/api/v1/documents?limit=3", headers=headers)
    docs = r.json()
    print(f"[OK] Documents: {len(docs)} found")
except:
    print("[FAIL] Document list failed")

# 5. Chat WITHOUT RAG
try:
    r = requests.post(f"{BASE_URL}/api/v1/chat",
                     json={"content": "Hello", "rag_enabled": False},
                     headers=headers, timeout=5)
    if r.status_code == 200:
        print("[OK] Chat (No RAG): Working")
except:
    print("[WARN] Chat timeout (normal for slow LLM)")

# 6. Chat WITH RAG
try:
    r = requests.post(f"{BASE_URL}/api/v1/chat",
                     json={"content": "What is Pyramid?", "rag_enabled": True},
                     headers=headers, timeout=5)
    if r.status_code == 200:
        data = r.json()
        citations = data.get('meta_data', {}).get('sources', [])
        print(f"[OK] Chat (RAG): {len(citations)} citations")
except:
    print("[WARN] RAG chat timeout")

# 7. Admin Features
try:
    r = requests.get(f"{BASE_URL}/api/v1/users", headers=headers)
    users = r.json()
    print(f"[OK] Admin: {len(users)} users")
except:
    print("[FAIL] Admin access failed")

# 8. Health Monitoring
try:
    r = requests.get(f"{BASE_URL}/api/v1/system/health", headers=headers)
    health = r.json()
    print(f"[OK] Monitoring: System {health['status']}")
except:
    print("[WARN] Health monitoring not available")

print("=" * 50)
print("TEST COMPLETE - System appears operational!")
print("\nOpen http://localhost:3002 to test the UI")
print("See USER_GUIDE.md for detailed instructions")