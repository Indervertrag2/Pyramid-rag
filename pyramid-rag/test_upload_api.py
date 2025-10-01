import requests
import json

# Read the token
with open('test_login.json', 'r') as f:
    auth_data = json.load(f)
    token = auth_data.get('access_token')

# Prepare the file
with open('test_upload.txt', 'rb') as f:
    files = {'file': ('test_upload.txt', f, 'text/plain')}
    data = {
        'scope': 'GLOBAL',
        'visibility': 'all'
    }
    headers = {
        'Authorization': f'Bearer {token}'
    }

    # Make the request
    response = requests.post(
        'http://localhost:18000/api/v1/documents/upload',
        headers=headers,
        files=files,
        data=data
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")