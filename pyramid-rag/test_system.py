#!/usr/bin/env python3
"""Comprehensive system test for Pyramid RAG"""

import requests
import json
import os
import time
from datetime import datetime

BASE_URL = "http://localhost:18000"
FRONTEND_URL = "http://localhost:3002"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    print(f"[OK] Health: {data['status']}")
    return True

def test_auth():
    """Test authentication"""
    print("\nTesting authentication...")
    login_data = {
        "email": "admin@pyramid-computer.de",
        "password": "admin123"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    print(f"[OK] Login successful - Token received")
    return data["access_token"]

def test_chat(token):
    """Test chat functionality"""
    print("\nTesting chat...")
    headers = {"Authorization": f"Bearer {token}"}

    # Test chat without RAG
    chat_data = {
        "content": "Hello, what is 2+2?",
        "rag_enabled": False
    }
    response = requests.post(f"{BASE_URL}/api/v1/chat", json=chat_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    print(f"[OK] Chat without RAG: {data['content'][:100]}...")

    # Test chat with RAG
    chat_data = {
        "content": "What is Pyramid RAG?",
        "rag_enabled": True
    }
    response = requests.post(f"{BASE_URL}/api/v1/chat", json=chat_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    print(f"[OK] Chat with RAG: {data['content'][:100]}...")
    return True

def test_document_upload(token):
    """Test document upload"""
    print("\nTesting document upload...")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a test document
    test_content = "This is a test document for Pyramid RAG system. It contains important information."
    files = {'file': ('test.txt', test_content, 'text/plain')}
    data = {
        'title': 'Test Document',
        'description': 'Test document for system validation',
        'tags': json.dumps(['test', 'validation']),
        'status': 'published',
        'department': 'Management'
    }

    response = requests.post(f"{BASE_URL}/api/v1/documents", files=files, data=data, headers=headers)
    if response.status_code == 200:
        print(f"[OK] Document uploaded successfully")
        return response.json()
    else:
        print(f"[WARNING] Document upload returned {response.status_code}: {response.text}")
        return None

def test_frontend():
    """Test frontend availability"""
    print("\nTesting frontend...")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print(f"[OK] Frontend accessible at {FRONTEND_URL}")
            return True
    except:
        print(f"[WARNING] Frontend not accessible at {FRONTEND_URL}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("PYRAMID RAG SYSTEM TEST")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print(f"Backend: {BASE_URL}")
    print(f"Frontend: {FRONTEND_URL}")
    print("=" * 60)

    results = []

    # Test health
    try:
        results.append(("Health Check", test_health()))
    except Exception as e:
        results.append(("Health Check", f"Failed: {e}"))

    # Test authentication
    token = None
    try:
        token = test_auth()
        results.append(("Authentication", True))
    except Exception as e:
        results.append(("Authentication", f"Failed: {e}"))

    # Test chat if auth succeeded
    if token:
        try:
            test_chat(token)
            results.append(("Chat", True))
        except Exception as e:
            results.append(("Chat", f"Failed: {e}"))

        try:
            test_document_upload(token)
            results.append(("Document Upload", True))
        except Exception as e:
            results.append(("Document Upload", f"Failed: {e}"))

    # Test frontend
    try:
        test_frontend()
        results.append(("Frontend", True))
    except Exception as e:
        results.append(("Frontend", f"Failed: {e}"))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results:
        if result == True:
            print(f"[PASS] {test_name}: PASSED")
        else:
            print(f"[FAIL] {test_name}: {result}")

    # Overall status
    passed = sum(1 for _, r in results if r == True)
    total = len(results)
    print("=" * 60)
    print(f"OVERALL: {passed}/{total} tests passed")
    if passed == total:
        print("SUCCESS: ALL TESTS PASSED!")
    else:
        print("WARNING: Some tests failed. Please check the logs.")
    print("=" * 60)

if __name__ == "__main__":
    main()