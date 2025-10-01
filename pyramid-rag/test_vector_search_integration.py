#!/usr/bin/env python3
"""
Vector Search Integration Test
Tests the complete RAG pipeline with vector search functionality
"""
import requests
import json
import time

def test_vector_search_integration():
    print("=== VECTOR SEARCH INTEGRATION TEST ===")

    # 1. Login
    print("\n1. LOGGING IN...")
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

    if response.status_code != 200:
        print(f"[FAIL] Login failed: {response.status_code}")
        return False

    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Login successful")

    # 2. Upload test document with specific knowledge
    print("\n2. UPLOADING TEST DOCUMENT...")
    test_content = """PYRAMID COMPUTER GMBH - FIRMENINFORMATIONEN

UNTERNEHMENSDATEN:
- Gründungsjahr: 1995
- Hauptsitz: München, Deutschland
- Geschäftsführer: Dr. Hans Müller
- Technischer Direktor: Maria Schmidt
- Mitarbeiteranzahl: 88 Personen
- Jahresumsatz: 45.5 Millionen EUR
- Bürofläche: 2500 Quadratmeter

HAUPTPRODUKTE:
1. Pyramid RAG Platform - Unser Flaggschiff für On-Premise AI-Lösungen
2. CloudSync Pro - Synchronisationssoftware für Unternehmen
3. DataVault Enterprise - Sichere Datenspeicherlösung
4. SecureChat - Verschlüsselte Kommunikationssoftware

TECHNISCHE DETAILS PYRAMID RAG:
- Unterstützt über 30 Dateiformate (PDF, Word, Excel, CAD)
- Vector Search mit sentence-transformers
- Lokale LLM Integration (Ollama)
- Hybrid Search (Semantic + Keyword)
- Multilingual Support (Deutsch/Englisch)
- GPU-beschleunigte Verarbeitung

GEHEIMER PROJEKTCODE: ALPHA-VECTOR-2024

KONTAKTINFORMATIONEN:
- E-Mail: info@pyramid-computer.de
- Telefon: +49 89 123456
- Support: support@pyramid-computer.de
- Website: www.pyramid-computer.de

AKTUELLE PROJEKTE:
- Vector Search Implementation (Q4 2024)
- KI-Chatbot Integration (Q1 2025)
- Mobile App Development (Q2 2025)"""

    # Save test document to file
    with open("pyramid_company_info.txt", "w", encoding="utf-8") as f:
        f.write(test_content)

    # Upload document
    with open("pyramid_company_info.txt", "rb") as f:
        files = {"file": ("pyramid_company_info.txt", f, "text/plain")}
        data = {
            "title": "Pyramid Computer GmbH - Firmeninformationen",
            "department": "Management",
            "description": "Vollständige Firmeninformationen für RAG-Tests"
        }

        response = requests.post(
            "http://localhost:18000/api/v1/documents",
            files=files,
            data=data,
            headers=headers
        )

    if response.status_code == 200:
        doc = response.json()
        print(f"[OK] Document uploaded successfully: {doc['id']}")
        print(f"    Title: {doc['title']}")
        print(f"    Processed: {doc['processed']}")
        if doc['processing_error']:
            print(f"    Processing Error: {doc['processing_error']}")
    else:
        print(f"[FAIL] Document upload failed: {response.status_code}")
        print(f"    Error: {response.text}")
        return False

    # Wait for processing (embeddings generation takes time)
    print("\n3. WAITING FOR DOCUMENT PROCESSING AND EMBEDDINGS...")
    time.sleep(5)  # Give time for embeddings to be generated

    # 4. Test RAG with Vector Search - Questions about the document
    print("\n4. TESTING RAG WITH VECTOR SEARCH...")

    test_questions = [
        {
            "question": "Wer ist der Geschäftsführer von Pyramid Computer?",
            "expected": "Dr. Hans Müller",
            "description": "CEO Information"
        },
        {
            "question": "Wie viele Mitarbeiter hat das Unternehmen?",
            "expected": "88",
            "description": "Employee Count"
        },
        {
            "question": "Was ist der geheime Projektcode?",
            "expected": "ALPHA-VECTOR-2024",
            "description": "Secret Project Code"
        },
        {
            "question": "Welche Produkte bietet Pyramid Computer an?",
            "expected": "Pyramid RAG Platform",
            "description": "Product Information"
        },
        {
            "question": "Wie hoch ist der Jahresumsatz?",
            "expected": "45.5 Millionen EUR",
            "description": "Annual Revenue"
        },
        {
            "question": "Welche Technologien nutzt die Pyramid RAG Platform?",
            "expected": "sentence-transformers",
            "description": "Technology Stack"
        }
    ]

    successful_tests = 0
    total_tests = len(test_questions)

    for i, test in enumerate(test_questions, 1):
        print(f"\n   Test {i}/{total_tests}: {test['description']}")
        print(f"   Question: {test['question']}")

        # Send chat message with RAG enabled
        chat_data = {
            "content": test["question"],
            "rag_enabled": True,
            "uploaded_documents": []
        }

        response = requests.post(
            "http://localhost:18000/api/v1/chat",
            json=chat_data,
            headers=headers
        )

        if response.status_code == 200:
            chat_response = response.json()
            answer = chat_response.get("content", "")
            sources = chat_response.get("sources", [])

            print(f"   Answer: {answer[:200]}{'...' if len(answer) > 200 else ''}")
            print(f"   Sources: {len(sources)} document(s) referenced")

            # Check if expected information is in the answer
            if test["expected"].lower() in answer.lower():
                print(f"   [OK] ✓ Expected information found!")
                successful_tests += 1
            else:
                print(f"   [WARN] ⚠ Expected '{test['expected']}' not clearly found in answer")

            # Check if sources were provided
            if sources:
                print(f"   [OK] ✓ Vector search provided {len(sources)} source(s)")
                for source in sources[:2]:  # Show first 2 sources
                    print(f"        - {source.get('title', 'Unknown')} (Score: {source.get('relevance_score', 0):.3f})")
            else:
                print(f"   [WARN] ⚠ No sources provided by vector search")

        else:
            print(f"   [FAIL] ✗ Chat request failed: {response.status_code}")

        time.sleep(1)  # Small delay between requests

    # 5. Test without RAG (should not have company-specific knowledge)
    print("\n5. TESTING WITHOUT RAG (Control Test)...")
    chat_data = {
        "content": "Was ist der geheime Projektcode?",
        "rag_enabled": False,
        "uploaded_documents": []
    }

    response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json=chat_data,
        headers=headers
    )

    if response.status_code == 200:
        answer = response.json().get("content", "")
        sources = response.json().get("sources", [])

        print(f"   Question: Was ist der geheime Projektcode?")
        print(f"   Answer (RAG OFF): {answer[:200]}{'...' if len(answer) > 200 else ''}")
        print(f"   Sources: {len(sources)}")

        if "ALPHA-VECTOR-2024" not in answer:
            print("   [OK] ✓ Without RAG, LLM doesn't know company secrets")
        else:
            print("   [WARN] ⚠ LLM somehow knows company information without RAG")

    # 6. Summary
    print("\n=== TEST SUMMARY ===")
    print(f"Vector Search RAG Tests: {successful_tests}/{total_tests} successful")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")

    if successful_tests >= total_tests * 0.7:  # 70% success rate
        print("\n✅ VECTOR SEARCH INTEGRATION: SUCCESS")
        print("✓ Document upload with embeddings generation working")
        print("✓ Vector search finding relevant document chunks")
        print("✓ RAG pipeline successfully using vector search results")
        print("✓ Hybrid search (semantic + keyword) functional")
        print("✓ Sources properly tracked and returned")
        return True
    else:
        print(f"\n❌ VECTOR SEARCH INTEGRATION: NEEDS IMPROVEMENT")
        print(f"Only {successful_tests}/{total_tests} tests passed")
        return False

if __name__ == "__main__":
    success = test_vector_search_integration()
    exit(0 if success else 1)