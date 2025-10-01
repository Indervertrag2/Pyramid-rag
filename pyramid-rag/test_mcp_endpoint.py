#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test the MCP endpoint integration"""

import requests
import json
import sys
import io

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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

# Test MCP message endpoint
mcp_request = {
    "messages": [
        {
            "role": "user",
            "content": "Was ist die Pyramid RAG Platform?"
        }
    ],
    "tools": ["chat", "hybrid_search"],
    "session_id": "test-session-1",
    "context": {
        "rag_enabled": True,
        "department": "MANAGEMENT",
        "uploaded_documents": []
    }
}

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

print("\n[->] Sending MCP request...")
response = requests.post(
    'http://localhost:18000/api/v1/mcp/message',
    json=mcp_request,
    headers=headers
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print("\n[SUCCESS] MCP Response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get('success'):
        print("\n[RESPONSE] Assistant:")
        for msg in result.get('messages', []):
            print(f"  {msg.get('content', '')[:200]}...")

        if result.get('citations'):
            print("\n[CITATIONS] Found:")
            for citation in result['citations']:
                print(f"  - {citation.get('document_title')}: {citation.get('snippet', '')[:100]}...")
else:
    print(f"\n[ERROR] {response.text}")

# Test MCP tools endpoint
print("\n[INFO] Getting available MCP tools...")
tools_response = requests.get(
    'http://localhost:18000/api/v1/mcp/tools',
    headers=headers
)

if tools_response.status_code == 200:
    tools = tools_response.json()
    print("Available tools:", list(tools.get('tools', {}).keys()))
else:
    print(f"Failed to get tools: {tools_response.text}")