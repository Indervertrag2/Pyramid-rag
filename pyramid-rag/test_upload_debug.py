#!/usr/bin/env python3
"""
Debug Upload 422 Error
"""
import requests
import json

def test_upload_debug():
    print("=== DEBUG UPLOAD 422 ERROR ===")

    # 1. Login
    print("\n1. Testing Login...")
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return

    token = response.json().get("access_token")
    print(f"[OK] Got token: {token[:20]}...")

    # 2. Test Upload with different department values
    print("\n2. Testing Upload with different parameters...")

    test_cases = [
        {"department": "Management", "description": "Test with Management"},
        {"department": "MANAGEMENT", "description": "Test with MANAGEMENT"},
        {"department": "Entwicklung", "description": "Test with Entwicklung"},
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n[TEST {i+1}] Department: {test_case['department']}")

        with open("test.txt", "w") as f:
            f.write(f"Test content {i+1}")

        with open("test.txt", "rb") as f:
            files = {"file": ("test.txt", f, "text/plain")}
            data = {
                "title": f"Test Document {i+1}",
                "department": test_case["department"],
                "description": test_case["description"]
            }

            headers = {"Authorization": f"Bearer {token}"}

            response = requests.post(
                "http://localhost:18000/api/v1/documents",
                files=files,
                data=data,
                headers=headers
            )

            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   [OK] Upload successful")
                doc_data = response.json()
                print(f"   Document ID: {doc_data.get('id')}")
                print(f"   Content extracted: {len(doc_data.get('content', ''))} chars")
            else:
                print(f"   [FAIL] Upload failed")
                print(f"   Error: {response.text[:500]}")

    # 3. Test what the frontend actually sends
    print("\n3. Simulating exact frontend behavior...")

    # This simulates what the frontend sends
    with open("frontend_test.txt", "w") as f:
        f.write("Frontend test content")

    with open("frontend_test.txt", "rb") as f:
        files = {"file": ("frontend_test.txt", f, "text/plain")}
        # Exactly what the frontend sends
        data = {
            "title": "frontend_test.txt",
            "department": "Management",  # Frontend uses this
            "description": "Chat upload: File uploaded in chat"
        }

        headers = {"Authorization": f"Bearer {token}"}

        print(f"   Sending: {data}")

        response = requests.post(
            "http://localhost:18000/api/v1/documents",
            files=files,
            data=data,
            headers=headers
        )

        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Full error: {response.text}")

if __name__ == "__main__":
    test_upload_debug()