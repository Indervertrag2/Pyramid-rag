"""Helper script to call Ollama API - works around uvicorn context issues"""
import sys
import json
import http.client

def call_ollama(prompt, temperature=0.7):
    """Call Ollama API and return response"""
    try:
        # Use 0.0.0.0 which seems to work in this context
        conn = http.client.HTTPConnection("0.0.0.0", 11434, timeout=30)

        payload = json.dumps({
            "model": "qwen2.5:7b",
            "prompt": prompt,
            "stream": False,
            "temperature": temperature
        })

        headers = {"Content-Type": "application/json"}

        conn.request("POST", "/api/generate", payload, headers)
        resp = conn.getresponse()

        if resp.status == 200:
            data = json.loads(resp.read().decode())
            response = data.get("response", "Keine Antwort erhalten")
        else:
            response = f"HTTP-Fehler {resp.status}: {resp.reason}"

        conn.close()
        return response

    except Exception as e:
        return f"Fehler: {str(e)}"

if __name__ == "__main__":
    # Get prompt from command line
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
        temperature = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7

        response = call_ollama(prompt, temperature)
        print(response)
    else:
        print("Fehler: Kein Prompt angegeben")