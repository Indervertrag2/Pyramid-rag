#!/usr/bin/env python3
import requests
import json

# Quick test
login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

if response.status_code == 200:
    token = response.json().get("access_token")

    # Quick chat test
    chat_response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json={"content": "Test"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30
    )

    print(f"Chat status: {chat_response.status_code}")
    if chat_response.status_code == 200:
        content = chat_response.json().get("content", "No content")
        print(f"Response: {content[:50]}...")
    else:
        print(f"Error: {chat_response.text[:100]}")
else:
    print(f"Login failed: {response.status_code}")