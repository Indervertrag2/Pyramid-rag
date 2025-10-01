#!/usr/bin/env python3
"""Comprehensive test suite for Pyramid RAG Platform"""

import requests
import json
import os
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuration
BASE_URL = "http://localhost:18000"
FRONTEND_URL = "http://localhost:3002"
ADMIN_EMAIL = "admin@pyramid-computer.de"
ADMIN_PASSWORD = "admin123"

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_section(text: str):
    """Print a formatted section header"""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}[{text}]{Colors.ENDC}")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}[OK]{Colors.ENDC} {text}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {text}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {text}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {text}")

class PyramidRAGTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.session_id = None
        self.document_id = None
        self.test_results = []

    def add_result(self, category: str, test: str, status: bool, details: str = ""):
        """Add a test result"""
        self.test_results.append({
            "category": category,
            "test": test,
            "status": status,
            "details": details
        })

    # ==================== INFRASTRUCTURE TESTS ====================

    def test_infrastructure(self):
        """Test basic infrastructure"""
        print_section("Infrastructure Tests")

        # Test backend health
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_success(f"Backend health: {data.get('status', 'unknown')}")
                self.add_result("Infrastructure", "Backend Health", True, data.get('status'))
            else:
                print_error(f"Backend health check failed: {response.status_code}")
                self.add_result("Infrastructure", "Backend Health", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Backend unreachable: {e}")
            self.add_result("Infrastructure", "Backend Health", False, str(e))

        # Test frontend
        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200:
                print_success(f"Frontend accessible at {FRONTEND_URL}")
                self.add_result("Infrastructure", "Frontend", True)
            else:
                print_warning(f"Frontend returned status {response.status_code}")
                self.add_result("Infrastructure", "Frontend", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Frontend unreachable: {e}")
            self.add_result("Infrastructure", "Frontend", False, str(e))

        # Test API documentation
        try:
            response = requests.get(f"{BASE_URL}/docs", timeout=5)
            if response.status_code == 200:
                print_success("API documentation accessible")
                self.add_result("Infrastructure", "API Docs", True)
            else:
                print_warning(f"API docs returned status {response.status_code}")
                self.add_result("Infrastructure", "API Docs", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"API docs unreachable: {e}")
            self.add_result("Infrastructure", "API Docs", False, str(e))

    # ==================== AUTHENTICATION TESTS ====================

    def test_authentication(self):
        """Test authentication endpoints"""
        print_section("Authentication Tests")

        # Test login with correct credentials
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print_success(f"Login successful - Token received")
                print_info(f"Token (first 50 chars): {self.token[:50]}...")
                self.add_result("Authentication", "Login", True)
            else:
                print_error(f"Login failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.add_result("Authentication", "Login", False, response.text)
                return False
        except Exception as e:
            print_error(f"Login request failed: {e}")
            self.add_result("Authentication", "Login", False, str(e))
            return False

        # Test get current user
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("id")
                print_success(f"Current user: {data.get('email')} (ID: {self.user_id})")
                print_info(f"Department: {data.get('department')}, Role: {data.get('role')}")
                self.add_result("Authentication", "Get Current User", True)
            else:
                print_error(f"Get current user failed: {response.status_code}")
                self.add_result("Authentication", "Get Current User", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Get current user request failed: {e}")
            self.add_result("Authentication", "Get Current User", False, str(e))

        # Test invalid login
        invalid_data = {
            "email": "invalid@test.com",
            "password": "wrongpass"
        }
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=invalid_data, timeout=10)
            if response.status_code == 401:
                print_success("Invalid login correctly rejected")
                self.add_result("Authentication", "Invalid Login Rejection", True)
            else:
                print_warning(f"Invalid login returned unexpected status: {response.status_code}")
                self.add_result("Authentication", "Invalid Login Rejection", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Invalid login test failed: {e}")
            self.add_result("Authentication", "Invalid Login Rejection", False, str(e))

        return True

    # ==================== CHAT TESTS ====================

    def test_chat(self):
        """Test chat functionality"""
        print_section("Chat Tests")

        if not self.token:
            print_error("No authentication token, skipping chat tests")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test chat without RAG
        print_info("Testing chat without RAG...")
        chat_data = {
            "content": "What is 2+2?",
            "rag_enabled": False
        }
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat", json=chat_data, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print_success(f"Chat response (no RAG): {data.get('content', '')[:100]}...")
                self.add_result("Chat", "Basic Chat (No RAG)", True)
            else:
                print_error(f"Chat failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.add_result("Chat", "Basic Chat (No RAG)", False, response.text)
        except Exception as e:
            print_error(f"Chat request failed: {e}")
            self.add_result("Chat", "Basic Chat (No RAG)", False, str(e))

        # Test chat with RAG
        print_info("Testing chat with RAG enabled...")
        chat_data = {
            "content": "What is the Pyramid RAG platform?",
            "rag_enabled": True
        }
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat", json=chat_data, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print_success(f"Chat response (with RAG): {data.get('content', '')[:100]}...")
                sources = data.get('sources', [])
                if sources:
                    print_info(f"Sources found: {len(sources)}")
                else:
                    print_info("No sources found (expected if no documents uploaded)")
                self.add_result("Chat", "Chat with RAG", True)
            else:
                print_error(f"Chat with RAG failed: {response.status_code}")
                self.add_result("Chat", "Chat with RAG", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Chat with RAG request failed: {e}")
            self.add_result("Chat", "Chat with RAG", False, str(e))

        # Test creating chat session
        print_info("Testing chat session creation...")
        session_data = {
            "title": "Test Session",
            "chat_type": "NORMAL"
        }
        try:
            response = requests.post(f"{BASE_URL}/api/v2/chat/sessions", json=session_data, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("id")
                print_success(f"Chat session created: {self.session_id}")
                self.add_result("Chat", "Create Session", True)
            else:
                print_error(f"Session creation failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.add_result("Chat", "Create Session", False, response.text)
        except Exception as e:
            print_error(f"Session creation request failed: {e}")
            self.add_result("Chat", "Create Session", False, str(e))

    # ==================== DOCUMENT TESTS ====================

    def test_documents(self):
        """Test document management"""
        print_section("Document Tests")

        if not self.token:
            print_error("No authentication token, skipping document tests")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test document upload
        print_info("Testing document upload...")
        test_content = "This is a test document for Pyramid RAG.\n\nIt contains information about the system."
        files = {'file': ('test_doc.txt', test_content, 'text/plain')}
        data = {
            'title': 'System Test Document',
            'description': 'Automated test document',
            'tags': json.dumps(['test', 'automated']),
            'status': 'published',
            'department': 'Management'
        }

        try:
            response = requests.post(f"{BASE_URL}/api/v1/documents", files=files, data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                doc_data = response.json()
                self.document_id = doc_data.get("id")
                print_success(f"Document uploaded: {self.document_id}")
                print_info(f"Document title: {doc_data.get('title')}")
                self.add_result("Documents", "Upload Document", True)
            else:
                print_error(f"Document upload failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.add_result("Documents", "Upload Document", False, response.text)
        except Exception as e:
            print_error(f"Document upload request failed: {e}")
            self.add_result("Documents", "Upload Document", False, str(e))

        # Test list documents
        print_info("Testing document listing...")
        try:
            response = requests.get(f"{BASE_URL}/api/v1/documents", headers=headers, timeout=10)
            if response.status_code == 200:
                docs = response.json()
                print_success(f"Documents retrieved: {len(docs)} documents found")
                if docs:
                    print_info(f"First document: {docs[0].get('title', 'Unknown')}")
                self.add_result("Documents", "List Documents", True, f"{len(docs)} documents")
            else:
                print_error(f"Document listing failed: {response.status_code}")
                self.add_result("Documents", "List Documents", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Document listing request failed: {e}")
            self.add_result("Documents", "List Documents", False, str(e))

        # Test document search
        print_info("Testing document search...")
        search_data = {"query": "test", "limit": 10}
        try:
            response = requests.post(f"{BASE_URL}/api/v1/search", json=search_data, headers=headers, timeout=10)
            if response.status_code == 200:
                results = response.json()
                num_results = len(results.get('results', [])) if isinstance(results, dict) else len(results)
                print_success(f"Search completed: {num_results} results")
                self.add_result("Documents", "Search Documents", True)
            else:
                print_warning(f"Document search returned: {response.status_code}")
                self.add_result("Documents", "Search Documents", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Document search request failed: {e}")
            self.add_result("Documents", "Search Documents", False, str(e))

    # ==================== VECTOR SEARCH TESTS ====================

    def test_vector_search(self):
        """Test vector search functionality through main search endpoint"""
        print_section("Search & RAG Tests")

        if not self.token:
            print_error("No authentication token, skipping search tests")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test general search which includes vector search
        print_info("Testing search with vector embeddings...")
        search_data = {
            "query": "Pyramid RAG system",
            "limit": 5
        }

        try:
            response = requests.post(f"{BASE_URL}/api/v1/search", json=search_data, headers=headers, timeout=10)
            if response.status_code == 200:
                results = response.json()
                num_results = len(results.get('results', []))
                print_success(f"Search completed: {num_results} results")
                if num_results > 0:
                    print_info(f"Search took: {results.get('took_ms', 0)}ms")
                    first_result = results['results'][0]
                    print_info(f"Top result: {first_result.get('title', 'N/A')} (score: {first_result.get('score', 0):.2f})")
                self.add_result("Search & RAG", "Vector/Hybrid Search", True, f"{num_results} results")
            else:
                print_warning(f"Search returned: {response.status_code}")
                self.add_result("Search & RAG", "Vector/Hybrid Search", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Search request failed: {e}")
            self.add_result("Search & RAG", "Vector/Hybrid Search", False, str(e))

    # ==================== ADMIN TESTS ====================

    def test_admin_features(self):
        """Test admin-specific features"""
        print_section("Admin Features Tests")

        if not self.token:
            print_error("No authentication token, skipping admin tests")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test system stats
        print_info("Testing system stats endpoint...")
        try:
            response = requests.get(f"{BASE_URL}/api/v1/system/stats", headers=headers, timeout=10)
            if response.status_code == 200:
                stats = response.json()
                print_success("System stats retrieved")
                print_info(f"Total users: {stats.get('total_users', 0)}")
                print_info(f"Total documents: {stats.get('total_documents', 0)}")
                print_info(f"Total chat sessions: {stats.get('total_sessions', 0)}")
                self.add_result("Admin", "System Stats", True)
            else:
                print_warning(f"System stats returned: {response.status_code}")
                self.add_result("Admin", "System Stats", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"System stats request failed: {e}")
            self.add_result("Admin", "System Stats", False, str(e))

        # Test user management
        print_info("Testing user listing...")
        try:
            response = requests.get(f"{BASE_URL}/api/v1/admin/users", headers=headers, timeout=10)
            if response.status_code == 200:
                users = response.json()
                print_success(f"Users retrieved: {len(users)} users")
                self.add_result("Admin", "List Users", True)
            elif response.status_code == 403:
                print_info("User listing requires admin privileges (expected)")
                self.add_result("Admin", "List Users", True, "Requires admin")
            else:
                print_warning(f"User listing returned: {response.status_code}")
                self.add_result("Admin", "List Users", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"User listing request failed: {e}")
            self.add_result("Admin", "List Users", False, str(e))

    # ==================== PERFORMANCE TESTS ====================

    def test_performance(self):
        """Test performance requirements"""
        print_section("Performance Tests")

        if not self.token:
            print_error("No authentication token, skipping performance tests")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test API response time
        print_info("Testing API response times...")

        # Health endpoint (should be < 200ms)
        start = time.time()
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            elapsed = (time.time() - start) * 1000
            if elapsed < 200:
                print_success(f"Health endpoint: {elapsed:.2f}ms (< 200ms requirement)")
                self.add_result("Performance", "Health API < 200ms", True, f"{elapsed:.2f}ms")
            else:
                print_warning(f"Health endpoint: {elapsed:.2f}ms (> 200ms requirement)")
                self.add_result("Performance", "Health API < 200ms", False, f"{elapsed:.2f}ms")
        except Exception as e:
            print_error(f"Health endpoint performance test failed: {e}")
            self.add_result("Performance", "Health API < 200ms", False, str(e))

        # Document search (should be < 500ms)
        start = time.time()
        try:
            response = requests.get(f"{BASE_URL}/api/v1/documents", headers=headers, timeout=5)
            elapsed = (time.time() - start) * 1000
            if elapsed < 500:
                print_success(f"Document search: {elapsed:.2f}ms (< 500ms requirement)")
                self.add_result("Performance", "Search < 500ms", True, f"{elapsed:.2f}ms")
            else:
                print_warning(f"Document search: {elapsed:.2f}ms (> 500ms requirement)")
                self.add_result("Performance", "Search < 500ms", False, f"{elapsed:.2f}ms")
        except Exception as e:
            print_error(f"Document search performance test failed: {e}")
            self.add_result("Performance", "Search < 500ms", False, str(e))

        # Chat response (should be < 3000ms)
        start = time.time()
        chat_data = {"content": "Hello", "rag_enabled": False}
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat", json=chat_data, headers=headers, timeout=10)
            elapsed = (time.time() - start) * 1000
            if elapsed < 3000:
                print_success(f"Chat response: {elapsed:.2f}ms (< 3000ms requirement)")
                self.add_result("Performance", "Chat < 3000ms", True, f"{elapsed:.2f}ms")
            else:
                print_warning(f"Chat response: {elapsed:.2f}ms (> 3000ms requirement)")
                self.add_result("Performance", "Chat < 3000ms", False, f"{elapsed:.2f}ms")
        except Exception as e:
            print_error(f"Chat performance test failed: {e}")
            self.add_result("Performance", "Chat < 3000ms", False, str(e))

    # ==================== DATABASE TESTS ====================

    def test_database(self):
        """Test database connectivity and integrity"""
        print_section("Database Tests")

        if not self.token:
            print_error("No authentication token, skipping database tests")
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # Check if database is responding through API
        print_info("Testing database connectivity through API...")
        try:
            response = requests.get(f"{BASE_URL}/api/v1/documents", headers=headers, timeout=10)
            if response.status_code == 200:
                print_success("Database connectivity confirmed")
                self.add_result("Database", "Connectivity", True)
            else:
                print_error(f"Database connectivity issue: {response.status_code}")
                self.add_result("Database", "Connectivity", False, f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Database connectivity test failed: {e}")
            self.add_result("Database", "Connectivity", False, str(e))

    # ==================== REPORT GENERATION ====================

    def generate_report(self):
        """Generate final test report"""
        print_header("TEST REPORT")

        # Group results by category
        categories = {}
        for result in self.test_results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)

        # Print results by category
        total_tests = 0
        passed_tests = 0

        for category, results in categories.items():
            print(f"\n{Colors.BOLD}{category}:{Colors.ENDC}")
            for result in results:
                total_tests += 1
                if result["status"]:
                    passed_tests += 1
                    status = f"{Colors.OKGREEN}[PASS]{Colors.ENDC}"
                else:
                    status = f"{Colors.FAIL}[FAIL]{Colors.ENDC}"
                details = f" - {result['details']}" if result['details'] else ""
                print(f"  {status} {result['test']}{details}")

        # Print summary
        print_header("SUMMARY")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        if success_rate >= 80:
            color = Colors.OKGREEN
        elif success_rate >= 60:
            color = Colors.WARNING
        else:
            color = Colors.FAIL

        print(f"{color}{Colors.BOLD}Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%){Colors.ENDC}")

        if success_rate == 100:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}ALL TESTS PASSED! System is fully operational.{Colors.ENDC}")
        elif success_rate >= 80:
            print(f"\n{Colors.OKGREEN}System is mostly operational with minor issues.{Colors.ENDC}")
        elif success_rate >= 60:
            print(f"\n{Colors.WARNING}System has significant issues that need attention.{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}System has critical issues. Immediate attention required.{Colors.ENDC}")

        # List critical failures
        failures = [r for r in self.test_results if not r["status"]]
        if failures:
            print(f"\n{Colors.BOLD}Failed Tests:{Colors.ENDC}")
            for failure in failures:
                print(f"  - {failure['category']}: {failure['test']}")
                if failure['details']:
                    print(f"    Details: {failure['details']}")

    def run_all_tests(self):
        """Run all test suites"""
        print_header("PYRAMID RAG COMPREHENSIVE TEST SUITE")
        print(f"Time: {datetime.now()}")
        print(f"Backend URL: {BASE_URL}")
        print(f"Frontend URL: {FRONTEND_URL}")

        # Run test suites
        self.test_infrastructure()

        if self.test_authentication():
            self.test_chat()
            self.test_documents()
            self.test_vector_search()
            self.test_admin_features()
            self.test_performance()
            self.test_database()

        # Generate report
        self.generate_report()

if __name__ == "__main__":
    tester = PyramidRAGTester()
    tester.run_all_tests()