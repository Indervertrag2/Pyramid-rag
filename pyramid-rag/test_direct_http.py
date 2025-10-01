import http.client
import json

# Test direct connection to Ollama
conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=10)

payload = json.dumps({
    "model": "qwen2.5:7b",
    "prompt": "Hallo, wie geht es dir?",
    "stream": False
})

headers = {"Content-Type": "application/json"}

try:
    conn.request("POST", "/api/generate", payload, headers)
    resp = conn.getresponse()

    print(f"Status: {resp.status}")

    if resp.status == 200:
        data = json.loads(resp.read().decode())
        print(f"Response: {data.get('response', 'No response')[:200]}")
    else:
        print(f"Error: {resp.reason}")

    conn.close()
except Exception as e:
    print(f"Connection error: {e}")