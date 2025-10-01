#!/usr/bin/env python3
"""Test streaming chat functionality"""

import requests
import json
import sys

# Login first
login_response = requests.post(
    'http://localhost:18000/api/v1/auth/login',
    json={
        'email': 'admin@pyramid-computer.de',
        'password': 'admin123'
    }
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    exit(1)

token = login_response.json()['access_token']
print("[OK] Login successful")

# Test streaming endpoint
print("\n=== Testing Streaming Chat ===")
print("Sending message: 'Erzähle mir eine kurze Geschichte.'")

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
}

request_data = {
    "messages": [
        {
            "role": "user",
            "content": "Erzähle mir eine kurze Geschichte."
        }
    ],
    "tools": ["chat"],
    "session_id": "test-streaming",
    "context": {
        "rag_enabled": False,
        "department": "MANAGEMENT"
    }
}

print("\n[Streaming Response]")
print("-" * 40)

try:
    with requests.post(
        'http://localhost:18000/api/v1/mcp/stream',
        json=request_data,
        headers=headers,
        stream=True
    ) as response:

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            exit(1)

        # Process the stream
        buffer = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')

                if line_str.startswith('event:'):
                    event_type = line_str[6:].strip()

                elif line_str.startswith('data:'):
                    data_str = line_str[5:].strip()
                    try:
                        data = json.loads(data_str)

                        if event_type == 'message' and 'chunk' in data:
                            chunk = data['chunk']
                            print(chunk, end='', flush=True)

                        elif event_type == 'done':
                            print("\n\n[Streaming Complete]")
                            print(f"Session ID: {data.get('session_id')}")

                        elif event_type == 'error':
                            print(f"\n[Error]: {data.get('error')}")

                    except json.JSONDecodeError:
                        pass

except Exception as e:
    print(f"\nStreaming error: {e}")

print("\n" + "-" * 40)
print("[Test Complete]")