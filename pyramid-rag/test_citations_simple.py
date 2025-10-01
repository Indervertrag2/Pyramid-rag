#!/usr/bin/env python3
"""Simple test to verify citation display feature"""

import requests

print("=" * 50)
print("TESTING CITATION DISPLAY IN CHAT")
print("=" * 50)

# 1. Login
print("\n1. Logging in...")
login = requests.post(
    "http://localhost:18000/api/v1/auth/login",
    json={"email": "admin@pyramid-computer.de", "password": "admin123"}
)

if login.status_code != 200:
    print(f"[FAIL] Login failed: {login.status_code}")
    exit(1)

token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[OK] Logged in successfully")

# 2. Chat with RAG enabled to get citations
print("\n2. Testing chat with RAG enabled...")
questions = [
    "Was sind die technischen Spezifikationen des Pyramid Enterprise Server ES-5000?",
    "Welche Sicherheitsrichtlinien gelten für Passwörter?",
    "Wie funktioniert die Backup-Strategie laut Support Guide?"
]

for question in questions:
    print(f"\n   Q: {question}")

    response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json={"content": question, "rag_enabled": True},
        headers=headers,
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()

        # Show part of answer
        content = data.get('content', '')
        if content:
            print(f"   A: {content[:150]}...")

        # Check for citations
        meta_data = data.get('meta_data', {})
        sources = meta_data.get('sources', [])

        if sources:
            print(f"   [OK] Found {len(sources)} citations:")
            for src in sources[:2]:  # Show first 2 citations
                title = src.get('document_title', 'Unknown')
                score = src.get('hybrid_score', 0)
                print(f"      - {title} (Relevanz: {score:.2f})")
        else:
            print("   [WARN] No citations found")
    else:
        print(f"   [FAIL] Chat request failed: {response.status_code}")

print("\n" + "=" * 50)
print("CITATION TEST COMPLETE")
print("=" * 50)
print("\nNOTE: To see the citations in the UI:")
print("1. Open http://localhost:3002")
print("2. Login with admin@pyramid-computer.de / admin123")
print("3. Ask a question about the uploaded documents")
print("4. Citations should appear below the answer with expandable details")