#!/usr/bin/env python3
"""
Test frontend-backend integration for Pyramid RAG platform
This script tests all major features through the API as the frontend would use them
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:18000"
FRONTEND_URL = "http://localhost:3002"

class FrontendIntegrationTest:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.session = requests.Session()

    def login(self):
        """Test login like frontend does"""
        print("\n1. TESTING LOGIN")
        print("-" * 40)

        response = self.session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "email": "admin@pyramid-computer.de",
                "password": "admin123"
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            print(f"✅ Login successful")
            print(f"   Token: {self.token[:20]}...")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False

    def test_user_info(self):
        """Test getting current user info"""
        print("\n2. TESTING USER INFO")
        print("-" * 40)

        headers = {"Authorization": f"Bearer {self.token}"}
        response = self.session.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)

        if response.status_code == 200:
            user = response.json()
            self.user_id = user.get("id")
            print(f"✅ User info retrieved")
            print(f"   Email: {user.get('email')}")
            print(f"   Username: {user.get('username')}")
            print(f"   Admin: {user.get('is_superuser')}")
            print(f"   Department: {user.get('primary_department')}")
            return True
        else:
            print(f"❌ Failed to get user info: {response.status_code}")
            return False

    def test_dashboard_data(self):
        """Test fetching dashboard data"""
        print("\n3. TESTING DASHBOARD DATA")
        print("-" * 40)

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test document list
        docs_response = self.session.get(
            f"{BASE_URL}/api/v1/documents?limit=5&sort_by=created_at&sort_order=desc",
            headers=headers
        )

        if docs_response.status_code == 200:
            docs = docs_response.json()
            print(f"✅ Documents retrieved: {len(docs)} documents")
            for doc in docs[:3]:
                print(f"   • {doc.get('title')} ({doc.get('department')})")
        else:
            print(f"❌ Failed to get documents: {docs_response.status_code}")

        return docs_response.status_code == 200

    def test_chat_functionality(self):
        """Test chat with and without RAG"""
        print("\n4. TESTING CHAT FUNCTIONALITY")
        print("-" * 40)

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test without RAG
        print("\n   Testing chat WITHOUT RAG...")
        response1 = self.session.post(
            f"{BASE_URL}/api/v1/chat",
            json={
                "content": "Hallo, wie geht es dir?",
                "rag_enabled": False
            },
            headers=headers,
            timeout=15
        )

        if response1.status_code == 200:
            data = response1.json()
            print(f"   ✅ Chat without RAG works")
            print(f"      Response: {data.get('content', '')[:100]}...")
        else:
            print(f"   ❌ Chat without RAG failed: {response1.status_code}")

        # Test with RAG
        print("\n   Testing chat WITH RAG...")
        response2 = self.session.post(
            f"{BASE_URL}/api/v1/chat",
            json={
                "content": "Was ist der Pyramid Enterprise Server ES-5000?",
                "rag_enabled": True
            },
            headers=headers,
            timeout=15
        )

        if response2.status_code == 200:
            data = response2.json()
            print(f"   ✅ Chat with RAG works")

            # Check for citations
            meta_data = data.get('meta_data', {})
            sources = meta_data.get('sources', [])

            if sources:
                print(f"   ✅ Citations found: {len(sources)} sources")
                for source in sources[:2]:
                    print(f"      • {source.get('document_title', 'Unknown')}")
            else:
                print(f"   ⚠️  No citations found (documents may not be indexed)")
        else:
            print(f"   ❌ Chat with RAG failed: {response2.status_code}")

        return response1.status_code == 200 and response2.status_code == 200

    def test_admin_features(self):
        """Test admin-only features"""
        print("\n5. TESTING ADMIN FEATURES")
        print("-" * 40)

        headers = {"Authorization": f"Bearer {self.token}"}

        # Test user list (admin only)
        print("\n   Testing user management...")
        users_response = self.session.get(
            f"{BASE_URL}/api/v1/users",
            headers=headers
        )

        if users_response.status_code == 200:
            users = users_response.json()
            print(f"   ✅ User list retrieved: {len(users)} users")
            for user in users[:3]:
                print(f"      • {user.get('email')} ({user.get('primary_department')})")
        else:
            print(f"   ❌ Failed to get users: {users_response.status_code}")

        # Test admin stats
        print("\n   Testing admin statistics...")
        stats_response = self.session.get(
            f"{BASE_URL}/api/v1/admin/stats",
            headers=headers
        )

        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"   ✅ Admin stats retrieved")
            print(f"      • Total users: {stats.get('total_users', 0)}")
            print(f"      • Total documents: {stats.get('total_documents', 0)}")
            print(f"      • Documents with embeddings: {stats.get('documents_with_embeddings', 0)}")
        else:
            print(f"   ❌ Failed to get stats: {stats_response.status_code}")

        return users_response.status_code == 200

    def test_document_upload(self):
        """Test document upload"""
        print("\n6. TESTING DOCUMENT UPLOAD")
        print("-" * 40)

        headers = {"Authorization": f"Bearer {self.token}"}

        # Create test document
        test_content = f"""
Test Document - {datetime.now().isoformat()}
This is a test document for the Pyramid RAG system.
It contains information about testing and validation.
Frontend integration test.
        """

        files = {
            'file': ('test_doc.txt', test_content, 'text/plain')
        }

        data = {
            'title': f'Test Document {datetime.now().strftime("%H:%M:%S")}',
            'description': 'Frontend integration test document',
            'department': 'Support'
        }

        response = self.session.post(
            f"{BASE_URL}/api/v1/documents",
            headers=headers,
            files=files,
            data=data,
            timeout=10
        )

        if response.status_code == 200:
            doc = response.json()
            print(f"✅ Document uploaded successfully")
            print(f"   ID: {doc.get('id')}")
            print(f"   Title: {doc.get('title')}")
            print(f"   Processed: {doc.get('processed')}")
            return True
        else:
            print(f"❌ Document upload failed: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text[:200]}")
            return False

    def test_health_monitoring(self):
        """Test health monitoring endpoints"""
        print("\n7. TESTING HEALTH MONITORING")
        print("-" * 40)

        # Basic health (no auth)
        print("\n   Testing basic health check...")
        health_response = self.session.get(f"{BASE_URL}/health")

        if health_response.status_code == 200:
            health = health_response.json()
            print(f"   ✅ Basic health check works")
            print(f"      Status: {health.get('status')}")
        else:
            print(f"   ❌ Health check failed: {health_response.status_code}")

        # Detailed health (with auth)
        print("\n   Testing detailed system health...")
        headers = {"Authorization": f"Bearer {self.token}"}
        system_health_response = self.session.get(
            f"{BASE_URL}/api/v1/system/health",
            headers=headers
        )

        if system_health_response.status_code == 200:
            sys_health = system_health_response.json()
            print(f"   ✅ System health endpoint works")
            print(f"      Overall status: {sys_health.get('status')}")

            components = sys_health.get('components', {})
            for comp_name, comp_data in components.items():
                status = comp_data.get('status', 'unknown')
                print(f"      • {comp_name}: {status}")
        else:
            print(f"   ❌ System health failed: {system_health_response.status_code}")

        return health_response.status_code == 200

    def test_frontend_routes(self):
        """Check if frontend routes are accessible"""
        print("\n8. TESTING FRONTEND ROUTES")
        print("-" * 40)

        routes = [
            "/",
            "/login",
            "/dashboard",
            "/chat",
            "/upload",
            "/admin"
        ]

        accessible = 0
        for route in routes:
            try:
                response = requests.get(f"{FRONTEND_URL}{route}", timeout=2)
                if response.status_code == 200:
                    print(f"   ✅ {route} - Accessible")
                    accessible += 1
                else:
                    print(f"   ⚠️  {route} - Status: {response.status_code}")
            except:
                print(f"   ❌ {route} - Not accessible")

        return accessible > 0

    def run_all_tests(self):
        """Run complete frontend integration test suite"""
        print("=" * 60)
        print("PYRAMID RAG - FRONTEND INTEGRATION TEST")
        print("=" * 60)
        print(f"API URL: {BASE_URL}")
        print(f"Frontend URL: {FRONTEND_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        # Run tests
        results = []

        # Must login first
        if self.login():
            results.append(("Login", True))

            # Run other tests
            tests = [
                ("User Info", self.test_user_info),
                ("Dashboard Data", self.test_dashboard_data),
                ("Chat Functionality", self.test_chat_functionality),
                ("Admin Features", self.test_admin_features),
                ("Document Upload", self.test_document_upload),
                ("Health Monitoring", self.test_health_monitoring),
                ("Frontend Routes", self.test_frontend_routes)
            ]

            for test_name, test_func in tests:
                try:
                    result = test_func()
                    results.append((test_name, result))
                except Exception as e:
                    print(f"\n❌ Error in {test_name}: {str(e)}")
                    results.append((test_name, False))
        else:
            results.append(("Login", False))
            print("\n❌ Cannot proceed without authentication")

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        failed = len(results) - passed

        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:.<30} {status}")

        print("-" * 60)
        print(f"Total: {len(results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(results)*100):.1f}%")

        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! Frontend integration is working perfectly.")
        elif passed >= len(results) * 0.8:
            print("\n⚠️  Most tests passed. Some features may need attention.")
        else:
            print("\n❌ Multiple failures detected. Check the system configuration.")

        print("\n💡 FRONTEND TESTING TIPS:")
        print("1. Open http://localhost:3002 in your browser")
        print("2. Login with admin@pyramid-computer.de / admin123")
        print("3. Test each feature manually:")
        print("   • Chat with RAG toggle")
        print("   • Document upload via drag-and-drop")
        print("   • Admin panel (user management)")
        print("   • Dark mode toggle")
        print("   • Citation display in chat")

        return failed == 0

if __name__ == "__main__":
    tester = FrontendIntegrationTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)