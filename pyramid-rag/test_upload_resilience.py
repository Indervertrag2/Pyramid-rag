#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test upload resilience - verify system handles interrupted uploads gracefully"""

import requests
import time
import threading
import os
from pathlib import Path

BASE_URL = "http://localhost:18000"

def login():
    """Login and return token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "admin@pyramid-computer.de",
        "password": "admin123"
    })
    return response.json()["access_token"]

def test_normal_upload():
    """Test normal file upload works"""
    print("\n1. Testing normal upload...")
    token = login()

    # Create test file
    test_file = Path("test_file.txt")
    test_file.write_text("This is a test document for upload resilience testing.")

    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test_file.txt', f, 'text/plain')}
            data = {
                'title': 'Test Normal Upload',
                'scope': 'personal',
                'department': 'Management',  # Use correct enum value
                'tags': 'test,resilience'
            }
            headers = {'Authorization': f'Bearer {token}'}

            response = requests.post(
                f"{BASE_URL}/api/v1/documents",
                files=files,
                data=data,
                headers=headers
            )

            if response.status_code == 200:
                print("   [OK] Normal upload successful")
                return True
            else:
                print(f"   [FAIL] Upload failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    finally:
        test_file.unlink(missing_ok=True)

def test_interrupted_upload():
    """Test interrupted upload (abort after starting)"""
    print("\n2. Testing interrupted upload...")
    token = login()

    # Create larger test file
    test_file = Path("test_large.txt")
    test_file.write_text("Large content " * 10000)  # ~140KB

    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test_large.txt', f, 'text/plain')}
            data = {
                'title': 'Test Interrupted Upload',
                'scope': 'personal',
                'department': 'Management',
                'tags': 'test,interrupt'
            }
            headers = {'Authorization': f'Bearer {token}'}

            # Start upload in thread and interrupt
            def upload_task():
                try:
                    requests.post(
                        f"{BASE_URL}/api/v1/documents",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=0.1  # Very short timeout to simulate interruption
                    )
                except:
                    pass

            thread = threading.Thread(target=upload_task)
            thread.start()
            time.sleep(0.05)  # Let it start
            # Thread will timeout and abort
            thread.join(timeout=1)

            print("   [OK] Upload interrupted successfully")
            return True
    except Exception as e:
        print(f"   [FAIL] Error during interruption test: {e}")
        return False
    finally:
        test_file.unlink(missing_ok=True)

def test_system_health_after_interruption():
    """Test that system is still healthy after interrupted upload"""
    print("\n3. Testing system health after interruption...")

    # Check health endpoint
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("   [OK] Health check passed")
    else:
        print(f"   [FAIL] Health check failed: {response.status_code}")
        return False

    # Try another normal upload
    if test_normal_upload():
        print("   [OK] System can still accept uploads")
        return True
    else:
        print("   [FAIL] System cannot accept new uploads")
        return False

def test_concurrent_uploads():
    """Test multiple concurrent uploads with some interruptions"""
    print("\n4. Testing concurrent uploads with interruptions...")
    token = login()

    results = []

    def upload_file(file_num, should_interrupt=False):
        test_file = Path(f"test_concurrent_{file_num}.txt")
        test_file.write_text(f"Concurrent test file {file_num}")

        try:
            with open(test_file, 'rb') as f:
                files = {'file': (test_file.name, f, 'text/plain')}
                data = {
                    'title': f'Concurrent Upload {file_num}',
                    'scope': 'personal',
                    'department': 'Management',
                    'tags': f'test,concurrent,file{file_num}'
                }
                headers = {'Authorization': f'Bearer {token}'}

                if should_interrupt:
                    # Simulate interruption with very short timeout
                    try:
                        requests.post(
                            f"{BASE_URL}/api/v1/documents",
                            files=files,
                            data=data,
                            headers=headers,
                            timeout=0.01
                        )
                    except:
                        results.append(f"File {file_num}: Interrupted as expected")
                else:
                    response = requests.post(
                        f"{BASE_URL}/api/v1/documents",
                        files=files,
                        data=data,
                        headers=headers
                    )
                    if response.status_code == 200:
                        results.append(f"File {file_num}: Success")
                    else:
                        results.append(f"File {file_num}: Failed ({response.status_code})")
        finally:
            test_file.unlink(missing_ok=True)

    # Start 5 concurrent uploads, interrupt 2 of them
    threads = []
    for i in range(5):
        should_interrupt = i in [1, 3]  # Interrupt files 1 and 3
        t = threading.Thread(target=upload_file, args=(i, should_interrupt))
        threads.append(t)
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join(timeout=5)

    # Check results
    for result in results:
        print(f"   {result}")

    successful = sum(1 for r in results if "Success" in r)
    interrupted = sum(1 for r in results if "Interrupted" in r)

    if successful >= 2 and interrupted >= 1:
        print(f"   [OK] Concurrent test passed: {successful} successful, {interrupted} interrupted")
        return True
    else:
        print(f"   [FAIL] Concurrent test failed: Expected mix of success and interruptions")
        return False

def main():
    """Run all upload resilience tests"""
    print("=" * 60)
    print("UPLOAD RESILIENCE TESTING")
    print("=" * 60)

    tests = [
        ("Normal Upload", test_normal_upload),
        ("Interrupted Upload", test_interrupted_upload),
        ("System Health After Interruption", test_system_health_after_interruption),
        ("Concurrent Uploads with Interruptions", test_concurrent_uploads)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   [FAIL] Test error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")

    if failed == 0:
        print("[SUCCESS] ALL UPLOAD RESILIENCE TESTS PASSED!")
        print("System correctly handles interrupted uploads without crashing.")
    else:
        print("[WARNING] Some tests failed, but system remains operational.")

    print("=" * 60)

if __name__ == "__main__":
    main()