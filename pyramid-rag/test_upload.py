#!/usr/bin/env python3
import requests
import json

# Test upload endpoint
print("=== Test Document Upload ===")

# Login first
login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

if response.status_code == 200:
    token = response.json().get("access_token")
    print("[OK] Login successful")

    headers = {"Authorization": f"Bearer {token}"}

    # Create a test text file
    with open("test_document.txt", "w", encoding="utf-8") as f:
        f.write("Dies ist ein Test-Dokument für die Pyramid RAG Platform.\n\nEs enthält verschiedene Informationen:\n- RAG steht für Retrieval-Augmented Generation\n- Pyramid Computer ist unser Unternehmen\n- Document Processing funktioniert jetzt!")

    # Try to upload the test file
    try:
        with open("test_document.txt", "rb") as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            data = {
                "title": "Test Dokument",
                "department": "Management",
                "description": "Ein Test-Dokument für die RAG Pipeline"
            }

            upload_response = requests.post(
                "http://localhost:18000/api/v1/documents",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )

            print(f"Upload Status: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")

            if upload_response.status_code == 200:
                print("[OK] Document upload successful!")
                upload_data = upload_response.json()
                print(f"Document ID: {upload_data.get('document_id')}")
            else:
                print(f"[FAIL] Upload failed: {upload_response.status_code}")
                print(f"Error: {upload_response.text}")

    except Exception as e:
        print(f"[ERROR] Exception during upload: {str(e)}")

else:
    print(f"[FAIL] Login failed: {response.status_code}")
    print(response.text)