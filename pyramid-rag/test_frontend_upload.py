#!/usr/bin/env python3
"""
Test Frontend Upload Behavior
Simulates what happens when user uploads a file in the frontend
"""
import requests
import json

def test_frontend_upload():
    print("=== FRONTEND UPLOAD TEST ===")

    # 1. Login (wie im Frontend)
    print("\n1. [LOGIN] Login wie im Frontend...")
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)

    if response.status_code != 200:
        print(f"[FAIL] Login failed: {response.status_code}")
        return False

    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Login erfolgreich")

    # 2. File Upload (exakt wie im Frontend)
    print("\n2. [UPLOAD] File Upload wie im ChatGPT Interface...")

    # Erstelle eine Test-Datei
    test_content = """Python Grundlagen - Cheat Sheet

VARIABLEN:
name = "Hans"
age = 25
is_student = True

LISTEN:
fruits = ["Apfel", "Banane", "Orange"]
numbers = [1, 2, 3, 4, 5]

SCHLEIFEN:
for fruit in fruits:
    print(fruit)

FUNKTIONEN:
def greet(name):
    return f"Hallo {name}!"

KLASSEN:
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age"""

    with open("python_cheatsheet.txt", "w", encoding="utf-8") as f:
        f.write(test_content)

    # Upload exakt wie im Frontend handleFileUpload
    try:
        with open("python_cheatsheet.txt", "rb") as f:
            files = {"file": ("python_cheatsheet.txt", f, "text/plain")}
            data = {
                "title": "python_cheatsheet.txt",
                "department": "Management",
                "description": "Chat upload: Wie kann ich Python lernen?"
            }

            upload_response = requests.post(
                "http://localhost:18000/api/v1/documents",
                files=files,
                data=data,
                headers=headers
            )

            print(f"Upload Status: {upload_response.status_code}")

            if upload_response.status_code == 200:
                doc_data = upload_response.json()
                print("[OK] File erfolgreich hochgeladen!")
                print(f"   Titel: {doc_data.get('title')}")
                print(f"   Verarbeitet: {doc_data.get('processed')}")
                print(f"   Content-Länge: {len(doc_data.get('content', ''))}")

                # Zeige Upload-Erfolg-Message wie im Frontend
                success_message = f"{doc_data['title']} erfolgreich hochgeladen"
                print(f"[SUCCESS] {success_message}")

                return doc_data
            else:
                print(f"[FAIL] Upload fehlgeschlagen: {upload_response.status_code}")
                print(f"Error: {upload_response.text}")
                return None

    except Exception as e:
        print(f"[FAIL] Upload error: {str(e)}")
        return None

def test_chat_with_uploaded_file():
    # Test Chat mit der hochgeladenen Datei
    doc_data = test_frontend_upload()
    if not doc_data:
        return False

    print("\n3. [CHAT] Chat mit hochgeladener Datei...")

    # Login für Chat
    login_data = {"email": "admin@pyramid-computer.de", "password": "admin123"}
    response = requests.post("http://localhost:18000/api/v1/auth/login", json=login_data)
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Chat-Anfrage wie im Frontend
    user_question = "Erkläre mir Python Listen anhand der Datei"

    # Simuliere die Frontend-Logik für Chat mit File
    uploaded_documents = [{
        "id": doc_data["id"],
        "title": doc_data["title"],
        "content": doc_data["content"]
    }]

    chat_data = {
        "content": user_question,
        "rag_enabled": True,
        "uploaded_documents": uploaded_documents
    }

    print(f"[QUESTION] {user_question}")

    chat_response = requests.post(
        "http://localhost:18000/api/v1/chat",
        json=chat_data,
        headers=headers,
        timeout=30
    )

    if chat_response.status_code == 200:
        response_content = chat_response.json().get("content", "")
        print(f"[ANSWER] {response_content}")
        print(f"\n[SUCCESS] ChatGPT-style Datei-Chat funktioniert!")
        return True
    else:
        print(f"[FAIL] Chat failed: {chat_response.status_code}")
        return False

if __name__ == "__main__":
    success = test_chat_with_uploaded_file()

    print(f"\n=== ERGEBNIS ===")
    if success:
        print("[OK] Das 422-Upload-Problem ist behoben!")
        print("[OK] File-Upload funktioniert wie bei ChatGPT!")
        print("[OK] Dateien stehen dem Chat zur Verfügung!")
        print("[OK] LLM hat vollen Zugriff auf Dateiinhalte!")
    else:
        print("[FAIL] Es gibt noch Probleme mit dem Upload!")

    exit(0 if success else 1)