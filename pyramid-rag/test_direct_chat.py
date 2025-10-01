#!/usr/bin/env python3
import requests
import json
import uuid

# Login first
login_data = {
    "email": "admin@pyramid-computer.de",
    "password": "admin123"
}

response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)
print(f"Login response: {response.status_code}")

if response.status_code == 200:
    token_data = response.json()
    token = token_data.get("access_token")
    print(f"Got token: {token[:20]}...")

    # Test direct chat endpoint
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    test_messages = [
        "Hello, what is 2+2?",
        "Was ist die Pyramid RAG Platform?",
        "Hallo, wie geht es dir?"
    ]

    for message in test_messages:
        print(f"\n--- Testing: {message}")

        chat_data = {
            "content": message
        }

        try:
            chat_response = requests.post(
                "http://localhost:18000/api/v1/chat",
                json=chat_data,
                headers=headers,
                timeout=60  # 60 second timeout
            )

            if chat_response.status_code == 200:
                response_data = chat_response.json()
                content = response_data.get("content", "No content")
                print(f"SUCCESS Response: {content[:200]}{'...' if len(content) > 200 else ''}")
            else:
                print(f"ERROR: {chat_response.status_code} - {chat_response.text[:200]}")

        except requests.exceptions.Timeout:
            print(f"TIMEOUT: Request took longer than 60 seconds")
        except Exception as e:
            print(f"EXCEPTION: {str(e)}")

else:
    print(f"Login failed: {response.text}")