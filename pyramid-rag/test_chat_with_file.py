#!/usr/bin/env python3
"""
Test Chat with File Content
"""
import requests
import json

def test_chat_with_file():
    print("=== TEST CHAT WITH FILE CONTENT ===")

    # 1. Login
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Logged in")

    # 2. Upload a test file
    print("\n1. Uploading test file...")
    test_content = """TESTDOKUMENT INHALT:
    Dies ist ein Testdokument mit spezifischem Inhalt.
    Testwort: PYRAMIDTEST123
    Testzahl: 424242
    Testdatum: 2024-12-24
    """

    with open("testfile.txt", "w", encoding="utf-8") as f:
        f.write(test_content)

    with open("testfile.txt", "rb") as f:
        files = {"file": ("testfile.txt", f, "text/plain")}
        data = {
            "title": "Test Document",
            "department": "Management",
            "description": "Test document for chat"
        }

        upload_response = requests.post(
            "http://localhost:18000/api/v1/documents",
            files=files,
            data=data,
            headers=headers
        )

        if upload_response.status_code == 200:
            doc_data = upload_response.json()
            print(f"[OK] Document uploaded: {doc_data['id']}")
            print(f"    Content in response: {doc_data.get('content', 'NO CONTENT')[:100]}")
        else:
            print(f"[FAIL] Upload failed: {upload_response.status_code}")
            print(upload_response.text)
            return

    # 3. Test chat WITHOUT sending the document content
    print("\n2. Testing chat WITHOUT document in request...")
    chat_data = {
        "content": "Was ist das Testwort im Dokument?",
        "rag_enabled": True
    }

    response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json=chat_data,
        headers=headers
    )

    if response.status_code == 200:
        answer = response.json().get("content", "")
        print(f"[ANSWER WITHOUT DOC]: {answer}")
        if "PYRAMIDTEST123" in answer:
            print("[OK] LLM found the document content via RAG!")
        else:
            print("[FAIL] LLM couldn't find the content via RAG")
    else:
        print(f"[FAIL] Chat failed: {response.status_code}")

    # 4. Test chat WITH sending the document content
    print("\n3. Testing chat WITH document in request...")
    chat_data = {
        "content": "Was ist das Testwort im Dokument?",
        "rag_enabled": True,
        "uploaded_documents": [{
            "id": doc_data["id"],
            "title": doc_data["title"],
            "content": doc_data.get("content", "")
        }]
    }

    # Debug: Show what we're sending
    print(f"[DEBUG] Sending uploaded_documents with content length: {len(doc_data.get('content', ''))}")

    response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json=chat_data,
        headers=headers
    )

    if response.status_code == 200:
        answer = response.json().get("content", "")
        print(f"[ANSWER WITH DOC]: {answer}")
        if "PYRAMIDTEST123" in answer:
            print("[OK] LLM found the specific test word!")
        else:
            print("[FAIL] LLM couldn't find the test word even with document")
    else:
        print(f"[FAIL] Chat failed: {response.status_code}")

    # 5. Test with RAG disabled but document provided
    print("\n4. Testing with RAG disabled but document provided...")
    chat_data = {
        "content": "Was ist das Testwort im Dokument?",
        "rag_enabled": False,
        "uploaded_documents": [{
            "id": doc_data["id"],
            "title": doc_data["title"],
            "content": doc_data.get("content", "")
        }]
    }

    response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json=chat_data,
        headers=headers
    )

    if response.status_code == 200:
        answer = response.json().get("content", "")
        print(f"[ANSWER RAG OFF]: {answer}")
        if "PYRAMIDTEST123" in answer:
            print("[OK] LLM uses uploaded document even with RAG off!")
        else:
            print("[INFO] LLM doesn't use document when RAG is off")

if __name__ == "__main__":
    test_chat_with_file()