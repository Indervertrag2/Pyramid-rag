#!/usr/bin/env python3
"""
Test if 422 upload error is fixed
"""
import requests
import json

def test_upload_fix():
    print("=== TEST UPLOAD FIX ===")

    # 1. Login
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Logged in")

    # 2. Test upload with exact frontend parameters
    print("\n1. Testing upload with Frontend parameters...")

    with open("test.txt", "w") as f:
        f.write("Test content for 422 fix")

    with open("test.txt", "rb") as f:
        files = {"file": ("test.txt", f, "text/plain")}
        # Exact parameters that frontend sends
        data = {
            "title": "test.txt",
            "department": "Management",
            "description": "Chat upload: File uploaded in chat"
        }

        response = requests.post(
            "http://localhost:18000/api/v1/documents",
            files=files,
            data=data,
            headers=headers
        )

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("[OK] Upload successful! 422 error is FIXED!")
            doc = response.json()
            print(f"Document ID: {doc['id']}")
            print(f"Processed: {doc['processed']}")
            return True
        else:
            print(f"[FAIL] Still getting error {response.status_code}")
            print(f"Error: {response.text}")
            return False

if __name__ == "__main__":
    success = test_upload_fix()
    if success:
        print("\n✓ 422 Upload Error ist behoben!")
    else:
        print("\n✗ Upload Error besteht weiterhin")
    exit(0 if success else 1)