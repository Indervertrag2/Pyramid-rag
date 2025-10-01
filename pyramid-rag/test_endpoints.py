#!/usr/bin/env python3
"""Test specific endpoints that are failing"""

import requests
import json

# Get token first
login_data = {
    "email": "admin@pyramid-computer.de",
    "password": "admin123"
}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("Testing problematic endpoints...")
print("=" * 60)

# Test document search endpoint
print("\n1. Document Search Endpoint:")
try:
    response = requests.get("http://localhost:18000/api/v1/documents/search?q=test", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Test vector search endpoint
print("\n2. Vector Search Endpoint:")
search_data = {
    "query": "test",
    "limit": 5
}
try:
    response = requests.post("http://localhost:18000/api/v1/search/vector", json=search_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Results: {json.dumps(response.json(), indent=2)[:200]}")
    else:
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Test chat session creation with correct enum
print("\n3. Chat Session Creation:")
session_data = {
    "title": "Test Session",
    "chat_type": "NORMAL"
}
try:
    response = requests.post("http://localhost:18000/api/v2/chat/sessions", json=session_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Session ID: {response.json().get('id')}")
    else:
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Check what endpoints are actually available
print("\n4. Available endpoints from API docs:")
try:
    response = requests.get("http://localhost:18000/openapi.json")
    if response.status_code == 200:
        api_spec = response.json()
        paths = api_spec.get("paths", {})
        print("   Document-related endpoints:")
        for path in sorted(paths.keys()):
            if "document" in path.lower():
                methods = list(paths[path].keys())
                print(f"      {path} [{', '.join(methods).upper()}]")
        print("   Search-related endpoints:")
        for path in sorted(paths.keys()):
            if "search" in path.lower():
                methods = list(paths[path].keys())
                print(f"      {path} [{', '.join(methods).upper()}]")
except Exception as e:
    print(f"   Error getting API spec: {e}")