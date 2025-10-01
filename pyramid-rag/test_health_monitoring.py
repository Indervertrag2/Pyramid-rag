#!/usr/bin/env python3
"""
Test health monitoring endpoints
"""

import requests
import json
from pprint import pprint

print("=" * 60)
print("TESTING HEALTH MONITORING ENDPOINTS")
print("=" * 60)

# 1. Test basic health check (no auth required)
print("\n1. BASIC HEALTH CHECK (/health)")
print("-" * 40)

try:
    response = requests.get("http://localhost:18000/health", timeout=5)
    if response.status_code == 200:
        print(f"[OK] Status: {response.status_code}")
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Version: {data.get('version')}")
        print("Services:")
        for service, status in data.get('services', {}).items():
            print(f"  • {service}: {status}")
    else:
        print(f"[FAIL] Status: {response.status_code}")
except Exception as e:
    print(f"[ERROR] {str(e)}")

# 2. Login for authenticated endpoints
print("\n2. AUTHENTICATION")
print("-" * 40)

login_response = requests.post(
    "http://localhost:18000/api/v1/auth/login",
    json={"email": "admin@pyramid-computer.de", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"[FAIL] Login failed: {login_response.status_code}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[OK] Logged in as admin")

# 3. Test detailed system health endpoint
print("\n3. DETAILED SYSTEM HEALTH (/api/v1/system/health)")
print("-" * 40)

try:
    response = requests.get(
        "http://localhost:18000/api/v1/system/health",
        headers=headers,
        timeout=10
    )

    if response.status_code == 200:
        print(f"[OK] Status: {response.status_code}")
        data = response.json()

        print(f"\nOverall Status: {data.get('status')}")
        print(f"Timestamp: {data.get('timestamp')}")

        components = data.get('components', {})

        # Database component
        if 'database' in components:
            print("\nDatabase Health:")
            db = components['database']
            print(f"  Status: {db.get('status')}")
            if 'version' in db:
                print(f"  Version: {db.get('version', 'N/A')[:50]}...")
            print(f"  Size: {db.get('size_mb', 0):.2f} MB")
            print(f"  Active Connections: {db.get('active_connections', 0)}")

        # LLM component
        if 'llm' in components:
            print("\nLLM Health:")
            llm = components['llm']
            print(f"  Status: {llm.get('status')}")
            print(f"  Available Models: {llm.get('model_count', 0)}")
            if llm.get('available_models'):
                for model in llm['available_models'][:3]:
                    print(f"    - {model}")

        # System resources
        if 'system' in components:
            print("\nSystem Resources:")
            sys = components['system']
            print(f"  Status: {sys.get('status')}")
            print(f"  CPU Usage: {sys.get('cpu_percent', 0):.1f}%")

            if 'memory' in sys:
                mem = sys['memory']
                print(f"  Memory: {mem.get('used_gb', 0):.1f}/{mem.get('total_gb', 0):.1f} GB ({mem.get('percent', 0):.1f}%)")

            if 'disk' in sys:
                disk = sys['disk']
                print(f"  Disk: {disk.get('used_gb', 0):.1f}/{disk.get('total_gb', 0):.1f} GB ({disk.get('percent', 0):.1f}%)")

        # Document processor
        if 'document_processor' in components:
            print("\nDocument Processor:")
            dp = components['document_processor']
            print(f"  Status: {dp.get('status')}")
            print(f"  Total Documents: {dp.get('total_documents', 0)}")
            print(f"  Processed: {dp.get('processed_documents', 0)}")
            print(f"  Failed: {dp.get('failed_documents', 0)}")
            print(f"  Processing Rate: {dp.get('processing_rate', 'N/A')}")

        # Vector store
        if 'vector_store' in components:
            print("\nVector Store:")
            vs = components['vector_store']
            print(f"  Status: {vs.get('status')}")
            print(f"  Total Chunks: {vs.get('total_chunks', 0)}")
            print(f"  With Embeddings: {vs.get('chunks_with_embeddings', 0)}")
            print(f"  Coverage: {vs.get('embedding_coverage', 'N/A')}")

    else:
        print(f"[FAIL] Status: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"[ERROR] {str(e)}")

# 4. Test Prometheus metrics endpoint
print("\n4. PROMETHEUS METRICS (/api/v1/system/metrics)")
print("-" * 40)

try:
    response = requests.get(
        "http://localhost:18000/api/v1/system/metrics",
        headers=headers,
        timeout=10
    )

    if response.status_code == 200:
        print(f"[OK] Status: {response.status_code}")
        metrics = response.text.split('\n')
        print(f"Total metrics exported: {len(metrics)}")
        print("\nSample metrics:")
        for metric in metrics[:10]:
            if metric and not metric.startswith('#'):
                print(f"  {metric}")
    else:
        print(f"[FAIL] Status: {response.status_code}")
except Exception as e:
    print(f"[ERROR] {str(e)}")

print("\n" + "=" * 60)
print("HEALTH MONITORING TEST COMPLETE")
print("=" * 60)

print("\nSUMMARY:")
print("• Basic health check endpoint: /health")
print("• Detailed health with auth: /api/v1/system/health")
print("• Prometheus metrics: /api/v1/system/metrics")
print("\nAll endpoints provide real-time system monitoring data!")