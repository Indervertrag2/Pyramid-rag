#!/usr/bin/env python3
import requests
import json

print("=== Test Document Content Extraction ===")

# Login first
login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

if response.status_code == 200:
    token = response.json().get("access_token")
    print("[OK] Login successful")

    headers = {"Authorization": f"Bearer {token}"}

    # Get list of documents
    docs_response = requests.get("http://localhost:18000/api/v1/documents", headers=headers)

    if docs_response.status_code == 200:
        docs_data = docs_response.json()
        print(f"[OK] Found {len(docs_data.get('documents', []))} documents")

        if docs_data.get("documents"):
            # Get the most recent document (first in list should be newest)
            first_doc = docs_data["documents"][0]
            doc_id = first_doc["id"]
            print(f"[INFO] First document: {first_doc['title']} (ID: {doc_id})")
            print(f"[INFO] Processed: {first_doc.get('processed', 'Unknown')}")
            print(f"[INFO] File size: {first_doc.get('file_size', 'Unknown')} bytes")

            # Try to get detailed document info
            detail_response = requests.get(f"http://localhost:18000/api/v1/documents/{doc_id}", headers=headers)

            if detail_response.status_code == 200:
                doc_detail = detail_response.json()
                print(f"[OK] Document details retrieved")
                print(f"[INFO] Content length: {len(doc_detail.get('content', ''))}")
                print(f"[INFO] Content preview: {doc_detail.get('content', '')[:200]}...")
                print(f"[INFO] Metadata: {doc_detail.get('meta_data', {})}")

                if doc_detail.get('content'):
                    print("[SUCCESS] Document processing extracted text content!")
                else:
                    print("[WARNING] No content extracted from document")
            else:
                print(f"[FAIL] Could not get document details: {detail_response.status_code}")
        else:
            print("[WARNING] No documents found")
    else:
        print(f"[FAIL] Could not list documents: {docs_response.status_code}")
        print(f"Response: {docs_response.text}")

else:
    print(f"[FAIL] Login failed: {response.status_code}")
    print(response.text)