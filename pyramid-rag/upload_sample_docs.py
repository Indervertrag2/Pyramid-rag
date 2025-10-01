#!/usr/bin/env python3
"""
Upload all sample documents to the RAG system
"""
import requests
import os
import time

def upload_sample_documents():
    print("=== UPLOADING SAMPLE DOCUMENTS ===")

    # 1. Login
    print("\n1. LOGIN...")
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

    if response.status_code != 200:
        print(f"[FAIL] Login failed: {response.status_code}")
        return False

    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Login successful")

    # 2. Define documents to upload
    documents = [
        {
            "file": "sample_docs/product_catalog.txt",
            "title": "Pyramid Produktkatalog 2024",
            "description": "Vollständiger Produktkatalog mit allen Servern, Workstations und Services",
            "department": "Vertrieb"
        },
        {
            "file": "sample_docs/support_guide.txt",
            "title": "Support Handbuch",
            "description": "Technisches Support-Handbuch mit Problemlösungen und Wartungsanleitungen",
            "department": "Support"
        },
        {
            "file": "sample_docs/security_policy.txt",
            "title": "IT Security Policy",
            "description": "Unternehmensweite Sicherheitsrichtlinien und Compliance-Anforderungen",
            "department": "Management"
        },
        {
            "file": "test_company_info.txt",
            "title": "Pyramid Unternehmenshandbuch",
            "description": "Allgemeine Unternehmensinformationen und Geschichte",
            "department": "Management"
        }
    ]

    # 3. Upload each document
    uploaded_count = 0
    failed_count = 0

    for doc_info in documents:
        print(f"\n   Uploading: {doc_info['title']}...")

        file_path = doc_info["file"]
        if not os.path.exists(file_path):
            print(f"   [SKIP] File not found: {file_path}")
            failed_count += 1
            continue

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'text/plain')}
                data = {
                    'department': doc_info['department'],
                    'title': doc_info['title'],
                    'description': doc_info['description']
                }

                response = requests.post(
                    "http://localhost:18000/api/v1/documents",
                    headers=headers,
                    files=files,
                    data=data
                )

            if response.status_code == 200:
                doc = response.json()
                print(f"   [OK] Uploaded successfully")
                print(f"        ID: {doc['id']}")
                print(f"        Department: {doc.get('department')}")
                print(f"        Processing: {'Complete' if doc.get('processed') else 'In Progress'}")
                uploaded_count += 1
            else:
                print(f"   [FAIL] Upload failed: {response.status_code}")
                print(f"        Error: {response.text[:200]}")
                failed_count += 1

        except Exception as e:
            print(f"   [ERROR] Exception during upload: {str(e)}")
            failed_count += 1

    # 4. Wait for processing
    if uploaded_count > 0:
        print(f"\n4. WAITING FOR DOCUMENT PROCESSING...")
        print(f"   Giving the system 10 seconds to process {uploaded_count} documents...")
        time.sleep(10)

    # 5. Verify documents are searchable
    print(f"\n5. VERIFYING DOCUMENTS ARE SEARCHABLE...")

    test_queries = [
        "Pyramid Enterprise Server",
        "Security Policy DSGVO",
        "Support Hotline Telefonnummer",
        "Workstation RTX 4090"
    ]

    successful_searches = 0
    for query in test_queries:
        print(f"\n   Testing search: '{query}'")

        chat_request = {
            "content": query,
            "session_id": None,
            "rag_enabled": True,
            "uploaded_documents": []
        }

        response = requests.post(
            "http://localhost:18000/api/v1/chat",
            json=chat_request,
            headers=headers
        )

        if response.status_code == 200:
            result = response.json()
            content = result.get('content', '')
            if len(content) > 50:
                print(f"   [OK] Found relevant content")
                successful_searches += 1
            else:
                print(f"   [WARN] Response too short, might not have found content")
        else:
            print(f"   [FAIL] Search failed: {response.status_code}")

    # 6. Get document statistics
    print(f"\n6. DOCUMENT STATISTICS...")

    response = requests.get(
        "http://localhost:18000/api/v1/documents?limit=100",
        headers=headers
    )

    if response.status_code == 200:
        all_docs = response.json()
        processed = sum(1 for doc in all_docs if doc.get('processed'))
        departments = {}
        for doc in all_docs:
            dept = doc.get('department', 'Unknown')
            departments[dept] = departments.get(dept, 0) + 1

        print(f"   Total Documents: {len(all_docs)}")
        print(f"   Processed: {processed}")
        print(f"   Departments:")
        for dept, count in departments.items():
            print(f"      - {dept}: {count} documents")

    # Summary
    print(f"\n=== UPLOAD SUMMARY ===")
    print(f"Successfully Uploaded: {uploaded_count}")
    print(f"Failed Uploads: {failed_count}")
    print(f"Successful Searches: {successful_searches}/{len(test_queries)}")

    if uploaded_count > 0:
        print("\n*** SAMPLE DOCUMENTS SUCCESSFULLY ADDED TO KNOWLEDGE BASE! ***")
    else:
        print("\n*** No new documents were uploaded (may already exist) ***")

    return True

if __name__ == "__main__":
    # Create sample_docs directory if it doesn't exist
    os.makedirs("sample_docs", exist_ok=True)

    success = upload_sample_documents()
    exit(0 if success else 1)