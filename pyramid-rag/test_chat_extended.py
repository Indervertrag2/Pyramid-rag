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

if response.status_code == 200:
    token_data = response.json()
    token = token_data.get("access_token")
    print(f"Got token: {token[:20]}...")

    # Test multiple chat messages
    test_prompts = [
        "Was ist die Pyramid RAG Platform?",
        "Wie kann ich Dokumente hochladen?",
        "What are the main features?",
        "Erkläre mir das System"
    ]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    session_id = "test-session-456"

    for prompt in test_prompts:
        print(f"\n--- Testing: {prompt}")

        chat_data = {
            "role": "user",
            "content": prompt
        }

        mcp_response = requests.post(
            f"http://localhost:18000/api/v1/mcp/message?session_id={session_id}",
            json=chat_data,
            headers=headers,
            timeout=30
        )

        if mcp_response.status_code == 200:
            response_data = mcp_response.json()
            content = response_data.get("content", "No content")
            # Limit output to 200 chars
            if len(content) > 200:
                content = content[:200] + "..."
            print(f"Response: {content}")
        else:
            print(f"Error: {mcp_response.status_code} - {mcp_response.text}")
else:
    print(f"Login failed: {response.text}")