#!/usr/bin/env python3
import requests
import json

# Login first
login_data = {
    "email": "admin@pyramid-computer.de",
    "password": "admin123"
}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)
print(f"Login response: {response.status_code}")
if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
print(f"Token received: {token[:50]}...")

# Test chat
headers = {"Authorization": f"Bearer {token}"}
chat_data = {
    "content": "Hello, what is 2+2?",
    "rag_enabled": False
}
response = requests.post("http://localhost:18000/api/v1/chat", json=chat_data, headers=headers)
print(f"\nChat response status: {response.status_code}")
print(f"Chat response: {json.dumps(response.json(), indent=2)}")
