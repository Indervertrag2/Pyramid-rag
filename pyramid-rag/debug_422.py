#!/usr/bin/env python3
import requests
import json

# Login first
login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

if response.status_code == 200:
    token = response.json().get("access_token")
    print("Login successful")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Test 1: Only content (should work)
    test_cases = [
        {"content": "Hello"},
        {"content": "Hello", "session_id": None},
        # This might be what frontend is sending:
        {"content": "Hello", "session_id": ""},
        {"content": "Hello", "session_id": "invalid-uuid"},
    ]

    for i, test_data in enumerate(test_cases, 1):
        print(f"\n=== Test {i}: {test_data} ===")

        try:
            chat_response = requests.post(
                "http://localhost:18000/api/v1/chat",
                json=test_data,
                headers=headers,
                timeout=10
            )

            print(f"Status: {chat_response.status_code}")
            if chat_response.status_code != 200:
                print(f"Error response: {chat_response.text}")
            else:
                content = chat_response.json().get("content", "No content")
                print(f"Success: {content[:50]}...")

        except Exception as e:
            print(f"Exception: {str(e)}")
else:
    print("Login failed")