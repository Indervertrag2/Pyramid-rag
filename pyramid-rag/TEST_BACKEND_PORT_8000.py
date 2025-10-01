#!/usr/bin/env python3
"""Test backend on port 8000"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing Backend on Port 8000")
print("=" * 40)

try:
    # Test health endpoint
    r = requests.get(f"{BASE_URL}/health", timeout=3)
    print(f"Health Check: {r.status_code}")
    if r.status_code == 200:
        print(f"Response: {r.json()}")
        print("\n✓ Backend is running on port 8000!")

        # Test login
        print("\nTesting authentication...")
        login_data = {
            "email": "admin@pyramid-computer.de",
            "password": "admin123"
        }
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=5)
        print(f"Login status: {r.status_code}")

        if r.status_code == 200:
            token = r.json().get("access_token")
            print("✓ Login successful!")

            # Test with token
            headers = {"Authorization": f"Bearer {token}"}

            # Test documents endpoint
            print("\nTesting documents endpoint...")
            r = requests.get(f"{BASE_URL}/api/v1/documents?limit=5", headers=headers, timeout=5)
            print(f"Documents status: {r.status_code}")
            if r.status_code == 200:
                docs = r.json()
                print(f"✓ Found {len(docs)} documents")

            # Test system stats endpoint
            print("\nTesting system stats endpoint...")
            r = requests.get(f"{BASE_URL}/api/v1/system/stats", headers=headers, timeout=5)
            print(f"System stats status: {r.status_code}")
            if r.status_code == 200:
                stats = r.json()
                print(f"✓ Stats: {stats}")
            elif r.status_code == 404:
                print("✗ System stats endpoint not found (needs fix)")

except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to backend on port 8000")
except requests.exceptions.Timeout:
    print("✗ Backend timeout on port 8000")
except Exception as e:
    print(f"✗ Error: {e}")