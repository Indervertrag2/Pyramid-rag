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

    # Test 1: RAG enabled (default)
    print("\n=== Test 1: RAG enabled ===")
    chat_data = {"content": "Was ist die Pyramid RAG Platform?", "rag_enabled": True}

    try:
        chat_response = requests.post(
            "http://localhost:18000/api/v1/chat",
            json=chat_data,
            headers=headers,
            timeout=30
        )

        print(f"Status: {chat_response.status_code}")
        if chat_response.status_code == 200:
            content = chat_response.json().get("content", "No content")
            print(f"RAG ON Response: {content}")
        else:
            print(f"Error: {chat_response.text}")

    except Exception as e:
        print(f"Exception: {str(e)}")

    # Test 2: RAG disabled
    print("\n=== Test 2: RAG disabled ===")
    chat_data = {"content": "Was ist die Pyramid RAG Platform?", "rag_enabled": False}

    try:
        chat_response = requests.post(
            "http://localhost:18000/api/v1/chat",
            json=chat_data,
            headers=headers,
            timeout=30
        )

        print(f"Status: {chat_response.status_code}")
        if chat_response.status_code == 200:
            content = chat_response.json().get("content", "No content")
            print(f"RAG OFF Response: {content}")
        else:
            print(f"Error: {chat_response.text}")

    except Exception as e:
        print(f"Exception: {str(e)}")

else:
    print(f"LOGIN FAILED: {response.text}")