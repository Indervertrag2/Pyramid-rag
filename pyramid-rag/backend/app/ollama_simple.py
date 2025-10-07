"""Simple Ollama client using urllib"""
import json
import urllib.request
import urllib.error
from typing import Dict, Any

class SimpleOllamaClient:
    """Simple synchronous Ollama client"""

    def __init__(self, base_url: str = "http://pyramid-ollama:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:7b"

    def generate_response(self, query: str, temperature: float = 0.7) -> str:
        """Generate a response using Ollama"""

        system_prompt = """Du bist ein hilfreicher KI-Assistent für die Pyramid Computer GmbH.
        Antworte immer auf Deutsch, es sei denn, der Benutzer fragt explizit auf Englisch."""

        prompt = f"""{system_prompt}

Frage: {query}

Antwort:"""

        try:
            data = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False
            }).encode('utf-8')

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    return result.get("response", "Keine Antwort generiert.")
                else:
                    return f"Fehler bei der Antwortgenerierung: Status {response.status}"

        except urllib.error.URLError as e:
            if hasattr(e, 'reason') and 'timeout' in str(e.reason).lower():
                return "Die Anfrage hat zu lange gedauert. Bitte versuchen Sie es erneut."
            return f"Verbindungsfehler: {str(e)}"
        except Exception as e:
            return f"Es ist ein Fehler aufgetreten: {str(e)}"
