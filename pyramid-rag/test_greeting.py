#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test simple greeting without document hallucination"""

import requests
import json

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

# Test simple greeting with RAG OFF
print("\n=== Test 1: Simple greeting WITH RAG OFF ===")
mcp_request = {
    "messages": [
        {
            "role": "user",
            "content": "Hi, wie geht es dir?"
        }
    ],
    "tools": ["chat"],  # Only chat, no search
    "session_id": "test-greeting-no-rag",
    "context": {
        "rag_enabled": False,  # RAG disabled
        "department": "MANAGEMENT",
        "uploaded_documents": []
    }
}

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

response = requests.post(
    'http://localhost:18000/api/v1/mcp/message',
    json=mcp_request,
    headers=headers,
    timeout=30
)

if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        for msg in result.get('messages', []):
            print(f"Assistant (NO RAG): {msg.get('content', '')}")
else:
    print(f"Error: {response.text}")

# Test simple greeting with RAG ON
print("\n=== Test 2: Simple greeting WITH RAG ON ===")
mcp_request['session_id'] = "test-greeting-with-rag"
mcp_request['context']['rag_enabled'] = True
mcp_request['tools'] = ["chat", "hybrid_search"]

response = requests.post(
    'http://localhost:18000/api/v1/mcp/message',
    json=mcp_request,
    headers=headers,
    timeout=30
)

if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        for msg in result.get('messages', []):
            print(f"Assistant (WITH RAG): {msg.get('content', '')}")
        if result.get('citations'):
            print(f"Citations found: {len(result['citations'])}")
else:
    print(f"Error: {response.text}")