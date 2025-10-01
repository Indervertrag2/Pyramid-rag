#!/usr/bin/env python3
"""
Comprehensive test suite for Pyramid RAG platform
Run this script to test all major features
"""

import requests
import json
import time
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:18000"
ADMIN_EMAIL = "admin@pyramid-computer.de"
ADMIN_PASSWORD = "admin123"

class TestSuite:
    def __init__(self):
        self.token = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }

    def login(self):
        """Authenticate and get token"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                return True
        except:
            pass
        return False

    def headers(self):
        """Get auth headers"""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def test(self, name, func):
        """Run a single test"""
        print(f"\n  Testing: {name}")
        try:
            result = func()
            if result:
                print(f"    ✓ PASSED")
                self.results["passed"] += 1
                self.results["tests"].append({"name": name, "status": "passed"})
            else:
                print(f"    ✗ FAILED")
                self.results["failed"] += 1
                self.results["tests"].append({"name": name, "status": "failed"})
        except Exception as e:
            print(f"    ✗ ERROR: {str(e)}")
            self.results["failed"] += 1
            self.results["tests"].append({"name": name, "status": "error", "error": str(e)})

    # Test functions
    def test_health_check(self):
        """Test basic health endpoint"""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200

    def test_authentication(self):
        """Test login functionality"""
        return self.login()

    def test_user_info(self):
        """Test getting current user info"""
        response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=self.headers(), timeout=5)
        return response.status_code == 200

    def test_document_list(self):
        """Test listing documents"""
        response = requests.get(f"{BASE_URL}/api/v1/documents", headers=self.headers(), timeout=5)
        return response.status_code == 200

    def test_chat_simple(self):
        """Test simple chat without RAG"""
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"content": "Hello", "rag_enabled": False},
            headers=self.headers(),
            timeout=10
        )
        return response.status_code == 200

    def test_chat_with_rag(self):
        """Test chat with RAG enabled"""
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"content": "What is Pyramid Computer?", "rag_enabled": True},
            headers=self.headers(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            # Check if response has content
            return bool(data.get("content"))
        return False

    def test_admin_stats(self):
        """Test admin statistics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/stats",
            headers=self.headers(),
            timeout=5
        )
        return response.status_code == 200

    def test_system_health(self):
        """Test detailed system health endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/system/health",
            headers=self.headers(),
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("status") in ["healthy", "degraded"]
        return False

    def test_metrics(self):
        """Test Prometheus metrics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/system/metrics",
            headers=self.headers(),
            timeout=5
        )
        return response.status_code == 200

    def test_user_management(self):
        """Test user list endpoint (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/v1/users",
            headers=self.headers(),
            timeout=5
        )
        return response.status_code == 200

    def test_document_upload(self):
        """Test document upload"""
        # Create a test file
        test_file = "test_upload.txt"
        with open(test_file, "w") as f:
            f.write("Test document content for Pyramid RAG system.")

        try:
            with open(test_file, "rb") as f:
                files = {"file": (test_file, f, "text/plain")}
                data = {
                    "title": "Test Document",
                    "description": "Automated test document",
                    "department": "Support"
                }
                response = requests.post(
                    f"{BASE_URL}/api/v1/documents",
                    headers=self.headers(),
                    files=files,
                    data=data,
                    timeout=10
                )
            os.remove(test_file)  # Clean up
            return response.status_code == 200
        except:
            if os.path.exists(test_file):
                os.remove(test_file)
            return False

    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 60)
        print("PYRAMID RAG PLATFORM - COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Target: {BASE_URL}")
        print("-" * 60)

        # Core Tests
        print("\n📋 CORE FUNCTIONALITY")
        self.test("Health Check", self.test_health_check)
        self.test("Authentication", self.test_authentication)
        self.test("User Info", self.test_user_info)

        # Document Management
        print("\n📄 DOCUMENT MANAGEMENT")
        self.test("List Documents", self.test_document_list)
        self.test("Upload Document", self.test_document_upload)

        # Chat System
        print("\n💬 CHAT SYSTEM")
        self.test("Simple Chat", self.test_chat_simple)
        self.test("Chat with RAG", self.test_chat_with_rag)

        # Admin Features
        print("\n👨‍💼 ADMIN FEATURES")
        self.test("Admin Statistics", self.test_admin_stats)
        self.test("User Management", self.test_user_management)

        # Monitoring
        print("\n📊 MONITORING")
        self.test("System Health", self.test_system_health)
        self.test("Prometheus Metrics", self.test_metrics)

        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"✓ Passed: {self.results['passed']}")
        print(f"✗ Failed: {self.results['failed']}")
        print(f"Total: {self.results['passed'] + self.results['failed']}")

        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100) if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")

        if self.results['failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! System is fully operational.")
        elif success_rate >= 80:
            print("\n⚠️ Most tests passed, but some features need attention.")
        else:
            print("\n❌ Multiple failures detected. System needs maintenance.")

        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("\nDetailed results saved to: test_results.json")

        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = TestSuite()
    success = tester.run_all_tests()
    exit(0 if success else 1)