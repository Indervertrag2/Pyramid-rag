#!/usr/bin/env python3
'''Comprehensive system test including citation display'''

import requests
import json

print('=' * 60)
print('PYRAMID RAG SYSTEM TEST - CITATION DISPLAY')
print('=' * 60)

# 1. Login
print('\n1. LOGIN')
login = requests.post(
    'http://localhost:18000/api/v1/auth/login',
    json={'email': 'admin@pyramid-computer.de', 'password': 'admin123'}
)

if login.status_code == 200:
    token = login.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print('   [OK] Logged in')
else:
    print(f'   [FAIL] Login failed: {login.status_code}')
    exit(1)

# 2. Test chat with citations
print('\n2. TESTING CHAT WITH CITATIONS')
response = requests.post(
    'http://localhost:18000/api/v1/chat',
    json={'content': 'Was ist der Pyramid Enterprise Server ES-5000?', 'rag_enabled': True},
    headers=headers,
    timeout=10
)

if response.status_code == 200:
    data = response.json()
    print(f'   [OK] Got response')
    
    # Check citations
    if 'meta_data' in data and 'sources' in data['meta_data']:
        sources = data['meta_data']['sources']
        print(f'   [OK] Found {len(sources)} citations')
        for s in sources[:2]:
            print(f'      • {s.get("document_title", "Unknown")}')
    else:
        print('   [WARN] No citations in response')
else:
    print(f'   [FAIL] Chat failed: {response.status_code}')

print('\n3. UI CITATION TEST')
print('   Open http://localhost:3002')
print('   Ask about Pyramid products with RAG enabled')
print('   Citations should appear below the answer')

