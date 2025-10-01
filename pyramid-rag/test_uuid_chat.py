#!/usr/bin/env python3
import requests
import json
import uuid

# Login first
login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

if response.status_code == 200:
    token = response.json().get("access_token")
    print("Login successful")

    # Test chat with proper UUID
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    chat_data = {
        "content": "Hallo, funktioniert der Chat jetzt?"
        # No session_id - let backend create new session
    }

    try:
        chat_response = requests.post(
            "http://localhost:18000/api/v1/chat",
            json=chat_data,
            headers=headers,
            timeout=30
        )

        print(f"Chat response status: {chat_response.status_code}")

        if chat_response.status_code == 200:
            data = chat_response.json()
            content = data.get("content", "No content")
            print(f"SUCCESS - Chat response: {content}")
        else:
            print(f"ERROR: {chat_response.text}")

    except Exception as e:
        print(f"EXCEPTION: {str(e)}")

else:
    print(f"LOGIN FAILED: {response.text}")