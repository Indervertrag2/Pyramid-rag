#!/usr/bin/env python3
"""Quick system test to verify everything is working"""

import requests
import json

BASE_URL = "http://localhost:18000"

print("=" * 60)
print("QUICK SYSTEM TEST")
print("=" * 60)

# 1. Test Backend Health
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"1. Backend Health: {'[OK]' if response.status_code == 200 else '[FAIL]'}")
except:
    print("1. Backend Health: [FAIL] - Cannot connect")

# 2. Test Login
try:
    login_data = {
        "email": "admin@pyramid-computer.de",
        "password": "admin123"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("2. Authentication: [OK]")
        headers = {"Authorization": f"Bearer {token}"}
    else:
        print(f"2. Authentication: [FAIL] - {response.status_code}")
        exit(1)
except Exception as e:
    print(f"2. Authentication: [FAIL] - {e}")
    exit(1)

# 3. Test Chat
try:
    chat_data = {
        "content": "Hallo, was ist das Pyramid RAG System?",
        "rag_enabled": True
    }
    response = requests.post(f"{BASE_URL}/api/v1/chat", json=chat_data, headers=headers)
    print(f"3. Chat API: {'[OK]' if response.status_code == 200 else '[FAIL]'}")
    if response.status_code == 200:
        print(f"   Response: {response.json()['content'][:100]}...")
except Exception as e:
    print(f"3. Chat API: [FAIL] - {e}")

# 4. Test Document List
try:
    response = requests.get(f"{BASE_URL}/api/v1/documents", headers=headers)
    print(f"4. Documents API: {'[OK]' if response.status_code == 200 else '[FAIL]'}")
    if response.status_code == 200:
        docs = response.json()
        print(f"   Documents found: {len(docs)}")
except Exception as e:
    print(f"4. Documents API: [FAIL] - {e}")

# 5. Test Frontend
try:
    response = requests.get("http://localhost:3002")
    print(f"5. Frontend: {'[OK]' if response.status_code == 200 else '[FAIL]'}")
except:
    print("5. Frontend: [FAIL] - Cannot connect")

print("=" * 60)
print("System is ready for testing!" if all else "Some components need attention")
print("=" * 60)