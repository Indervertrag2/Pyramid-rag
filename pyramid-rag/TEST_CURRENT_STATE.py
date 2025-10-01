#!/usr/bin/env python3
"""Test current state of the Pyramid RAG system"""

import requests
import json
import time

BASE_URL = "http://localhost:18000"
print("="*60)
print("PYRAMID RAG - CURRENT STATE TEST")
print("="*60)

# Test results
results = {
    "backend_health": False,
    "login": False,
    "system_stats": False,
    "documents": False,
    "chat": False,
    "frontend": False
}

# 1. Backend Health Check
print("\n1. Testing Backend Health...")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    if r.status_code == 200:
        results["backend_health"] = True
        print(f"✓ Backend is running: {r.json()}")
    else:
        print(f"✗ Backend returned status code: {r.status_code}")
except Exception as e:
    print(f"✗ Backend not accessible: {e}")

# 2. Login Test
print("\n2. Testing Authentication...")
if results["backend_health"]:
    try:
        login_data = {
            "email": "admin@pyramid-computer.de",
            "password": "admin123"
        }
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=5)
        if r.status_code == 200:
            results["login"] = True
            token = r.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            print(f"✓ Login successful")
        else:
            print(f"✗ Login failed with status: {r.status_code}")
            headers = {}
    except Exception as e:
        print(f"✗ Login error: {e}")
        headers = {}
else:
    print("⊗ Skipped (backend not available)")

# 3. System Stats Test
print("\n3. Testing System Stats Endpoint...")
if results["login"]:
    try:
        r = requests.get(f"{BASE_URL}/api/v1/system/stats", headers=headers, timeout=5)
        if r.status_code == 200:
            results["system_stats"] = True
            print(f"✓ System stats working: {r.json()}")
        elif r.status_code == 404:
            print(f"✗ System stats endpoint not found (404)")
        else:
            print(f"✗ System stats returned status: {r.status_code}")
    except Exception as e:
        print(f"✗ System stats error: {e}")
else:
    print("⊗ Skipped (login required)")

# 4. Documents Test
print("\n4. Testing Documents Endpoint...")
if results["login"]:
    try:
        r = requests.get(f"{BASE_URL}/api/v1/documents?limit=5", headers=headers, timeout=5)
        if r.status_code == 200:
            results["documents"] = True
            docs = r.json()
            print(f"✓ Documents endpoint working: {len(docs)} documents found")
        else:
            print(f"✗ Documents returned status: {r.status_code}")
    except Exception as e:
        print(f"✗ Documents error: {e}")
else:
    print("⊗ Skipped (login required)")

# 5. Chat Test
print("\n5. Testing Chat Endpoint...")
if results["login"]:
    try:
        chat_data = {
            "content": "Hello, test message",
            "rag_enabled": False
        }
        r = requests.post(f"{BASE_URL}/api/v1/chat", json=chat_data, headers=headers, timeout=10)
        if r.status_code == 200:
            results["chat"] = True
            response = r.json()
            print(f"✓ Chat working: {response.get('content', '')[:100]}...")
        else:
            print(f"✗ Chat returned status: {r.status_code}")
    except Exception as e:
        print(f"✗ Chat error: {e}")
else:
    print("⊗ Skipped (login required)")

# 6. Frontend Test
print("\n6. Testing Frontend...")
try:
    r = requests.get("http://localhost:3002", timeout=5)
    if r.status_code == 200 and "Pyramid RAG" in r.text:
        results["frontend"] = True
        print("✓ Frontend is accessible")
    else:
        print(f"✗ Frontend returned status: {r.status_code}")
except Exception as e:
    print(f"✗ Frontend error: {e}")

# Summary
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
working = sum(1 for v in results.values() if v)
total = len(results)

for key, value in results.items():
    status = "✓" if value else "✗"
    print(f"{status} {key.replace('_', ' ').title()}")

print(f"\nOverall: {working}/{total} components working")

if working == total:
    print("\n🎉 ALL SYSTEMS OPERATIONAL!")
elif working >= total - 2:
    print("\n⚠️ System mostly functional, minor issues present")
else:
    print("\n❌ System has critical issues that need fixing")