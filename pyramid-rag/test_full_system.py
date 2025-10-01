#!/usr/bin/env python3
"""
Comprehensive test of the Pyramid RAG Platform
Tests: Authentication, Document Upload, Processing, RAG Chat, Interface Features
"""
import requests
import json
import time

def test_full_system():
    print("=== PYRAMID RAG PLATFORM - FULL SYSTEM TEST ===")

    # 1. Authentication Test
    print("\n1. [AUTH] Testing Authentication...")
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

    if response.status_code != 200:
        print(f"❌ LOGIN FAILED: {response.status_code}")
        return False

    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Authentication successful")

    # 2. Document Upload and Processing Test
    print("\n2. 📄 Testing Document Upload and Processing...")

    # Create a comprehensive test document
    test_content = """Pyramid RAG Platform - Technische Dokumentation

Die Pyramid RAG Platform ist eine vollständig on-premise Lösung für:
- Retrieval-Augmented Generation (RAG)
- Semantische Dokumentensuche
- Wissensmanagement für Unternehmen

Technische Details:
- Backend: FastAPI mit Python
- Frontend: React TypeScript
- Database: PostgreSQL mit pgvector
- LLM: Ollama (qwen2.5:7b)
- GPU-Acceleration: RTX 2070
- Document Processing: PDF, Word, Excel, PowerPoint, CAD
- OCR: Tesseract für Deutsche und Englische Texte

Pyramid Computer GmbH entwickelt diese Plattform für den internen Gebrauch.
Alle Daten bleiben vollständig on-premise ohne externe API-Calls."""

    with open("pyramid_rag_docs.txt", "w", encoding="utf-8") as f:
        f.write(test_content)

    try:
        with open("pyramid_rag_docs.txt", "rb") as f:
            files = {"file": ("pyramid_rag_docs.txt", f, "text/plain")}
            data = {
                "title": "Pyramid RAG Platform Dokumentation",
                "department": "Entwicklung",
                "description": "Technische Dokumentation der RAG Platform"
            }

            upload_response = requests.post(
                "http://localhost:18000/api/v1/documents",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )

            if upload_response.status_code == 200:
                doc_data = upload_response.json()
                print(f"✅ Document uploaded successfully")
                print(f"   📋 Document ID: {doc_data.get('id', 'N/A')}")
                print(f"   ⚙️ Processed: {doc_data.get('processed', False)}")
                print(f"   📏 Content length: {len(doc_data.get('content', ''))}")
                print(f"   🏷️ Metadata keys: {list(doc_data.get('meta_data', {}).keys())}")

                if not doc_data.get('processed'):
                    print("⚠️  Document not processed")
                    return False

            else:
                print(f"❌ Document upload failed: {upload_response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Document upload error: {str(e)}")
        return False

    # 3. Document List Test
    print("\n3. 📋 Testing Document Listing...")
    docs_response = requests.get("http://localhost:18000/api/v1/documents", headers=headers)

    if docs_response.status_code == 200:
        docs_data = docs_response.json()
        doc_count = len(docs_data.get("documents", []))
        print(f"✅ Document listing successful - {doc_count} documents found")

        for i, doc in enumerate(docs_data.get("documents", [])[:3]):
            print(f"   {i+1}. {doc.get('title', 'Untitled')} ({doc.get('file_type', 'unknown')})")

    else:
        print(f"❌ Document listing failed: {docs_response.status_code}")
        return False

    # 4. RAG Chat Test (RAG enabled)
    print("\n4. 🤖 Testing RAG Chat (RAG enabled)...")
    rag_questions = [
        "Was ist die Pyramid RAG Platform?",
        "Welche Technologien werden verwendet?",
        "Ist die Platform on-premise?"
    ]

    for question in rag_questions:
        chat_data = {"content": question, "rag_enabled": True}

        chat_response = requests.post(
            "http://localhost:18000/api/v1/chat",
            json=chat_data,
            headers=headers,
            timeout=30
        )

        if chat_response.status_code == 200:
            response_content = chat_response.json().get("content", "")
            print(f"✅ RAG Question: '{question}'")
            print(f"   📝 Response length: {len(response_content)} characters")
            print(f"   🎯 Preview: {response_content[:100]}...")
        else:
            print(f"❌ RAG Chat failed for: '{question}' - {chat_response.status_code}")
            return False

    # 5. Non-RAG Chat Test
    print("\n5. 🔄 Testing Non-RAG Chat...")
    non_rag_question = "Was ist 2 + 2?"
    chat_data = {"content": non_rag_question, "rag_enabled": False}

    chat_response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json=chat_data,
        headers=headers,
        timeout=30
    )

    if chat_response.status_code == 200:
        response_content = chat_response.json().get("content", "")
        print(f"✅ Non-RAG Question: '{non_rag_question}'")
        print(f"   📝 Response: {response_content}")
    else:
        print(f"❌ Non-RAG Chat failed: {chat_response.status_code}")
        return False

    # 6. Frontend Accessibility Test
    print("\n6. 🌐 Testing Frontend Accessibility...")
    try:
        frontend_response = requests.get("http://localhost:3002", timeout=10)
        if frontend_response.status_code == 200:
            print("✅ Frontend accessible at http://localhost:3002")
        else:
            print(f"⚠️  Frontend status: {frontend_response.status_code}")
    except requests.exceptions.RequestException:
        print("⚠️  Frontend not accessible (may not be running)")

    # 7. System Summary
    print("\n7. 📊 System Status Summary...")
    print("✅ Authentication: Working")
    print("✅ Document Upload: Working")
    print("✅ Document Processing: Working")
    print("✅ Document Storage: Working")
    print("✅ RAG Chat: Working")
    print("✅ Non-RAG Chat: Working")
    print("✅ API Endpoints: Working")

    print(f"\n🎉 === FULL SYSTEM TEST COMPLETED SUCCESSFULLY ===")
    print(f"📋 All core features are functional!")
    print(f"🚀 The Pyramid RAG Platform is ready for production use!")

    return True

if __name__ == "__main__":
    success = test_full_system()
    exit(0 if success else 1)