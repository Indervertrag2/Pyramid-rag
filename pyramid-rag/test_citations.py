#!/usr/bin/env python3
"""Test citations in chat responses"""

import requests
import json

# Login first
login_response = requests.post(
    "http://localhost:18000/api/v1/auth/login",
    json={"email": "admin@pyramid-computer.de", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Test with RAG enabled
print("Testing chat with RAG enabled...")
chat_response = requests.post(
    "http://localhost:18000/api/v1/chat",
    json={
        "content": "Was bietet die Pyramid Enterprise Server ES-5000?",
        "rag_enabled": True
    },
    headers=headers
)

if chat_response.status_code == 200:
    result = chat_response.json()
    print(f"\nResponse content:\n{result['content'][:500]}...")

    # Check for citations/sources in metadata
    if 'meta_data' in result:
        meta_data = result['meta_data']
        print(f"\nMetadata found:")
        print(json.dumps(meta_data, indent=2, ensure_ascii=False))

        if 'sources' in meta_data and meta_data['sources']:
            print(f"\nFound {len(meta_data['sources'])} citations!")
            for i, source in enumerate(meta_data['sources'], 1):
                print(f"\nCitation {i}:")
                print(f"  Document: {source.get('document_title', 'Unknown')}")
                print(f"  Score: {source.get('hybrid_score', 0):.2f}")
                print(f"  Preview: {source.get('chunk_content', '')[:200]}...")
        else:
            print("\nNo citations found in response")
    else:
        print("\nNo metadata in response")
else:
    print(f"Chat request failed: {chat_response.status_code}")
    print(chat_response.text)