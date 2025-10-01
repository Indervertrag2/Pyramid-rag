#!/usr/bin/env python3
import requests
import json

# Login
login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

if response.status_code == 200:
    token = response.json().get("access_token")
    print("Login successful")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Test the exact format frontend should send
    chat_data = {"content": "Test after frontend restart - does chat work now?"}

    try:
        chat_response = requests.post(
            "http://localhost:18000/api/v1/chat",
            json=chat_data,
            headers=headers,
            timeout=30
        )

        print(f"Chat Status: {chat_response.status_code}")

        if chat_response.status_code == 200:
            content = chat_response.json().get("content", "No content")
            print(f"SUCCESS: {content}")
        else:
            print(f"ERROR: {chat_response.text}")

    except Exception as e:
        print(f"Exception: {str(e)}")
else:
    print("Login failed")