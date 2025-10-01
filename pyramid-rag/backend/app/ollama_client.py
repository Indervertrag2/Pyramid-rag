import httpx
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
from datetime import datetime

class OllamaClient:
    """Client for interacting with Ollama LLM"""

    def __init__(self, base_url: str = "http://ollama:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:7b"  # Using available model
        self.timeout = 120  # seconds
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def check_health(self) -> Dict[str, Any]:
        """Check if Ollama service is available"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                return {
                    "status": "healthy",
                    "available_models": model_names,
                    "model_available": self.model in model_names
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"Status code: {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def pull_model(self, model_name: str = None) -> bool:
        """Pull a model from Ollama registry"""
        model = model_name or self.model
        try:
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json={"name": model}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error pulling model {model}: {e}")
            return False

    async def generate_response(
        self,
        query: str,
        context: str = "",
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate a response using Ollama"""

        if system_prompt is None:
            system_prompt = """Du bist ein hilfreicher KI-Assistent für die Pyramid Computer GmbH.
            Deine Aufgabe ist es, präzise und hilfreiche Antworten basierend auf dem gegebenen Kontext zu geben.
            Antworte immer auf Deutsch, es sei denn, der Benutzer fragt explizit auf Englisch.
            Wenn du die Antwort nicht im Kontext findest, sage das ehrlich."""

        prompt = f"""{system_prompt}

Kontext:
{context}

Frage: {query}

Antwort:"""

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stream": False
                }
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Keine Antwort generiert.")
            else:
                return f"Fehler bei der Antwortgenerierung: Status {response.status_code}"

        except httpx.TimeoutException:
            return "Die Anfrage hat zu lange gedauert. Bitte versuchen Sie es erneut."
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Es ist ein Fehler bei der Antwortgenerierung aufgetreten."

    async def generate_stream(
        self,
        query: str,
        context: str = "",
        system_prompt: str = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response"""

        if system_prompt is None:
            system_prompt = """Du bist ein hilfreicher KI-Assistent für die Pyramid Computer GmbH.
            Antworte immer auf Deutsch, es sei denn, der Benutzer fragt explizit auf Englisch."""

        prompt = f"""{system_prompt}

Kontext:
{context}

Frage: {query}

Antwort:"""

        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            print(f"Error in stream generation: {e}")
            yield "Fehler bei der Stream-Generierung."

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama (if model supports it)"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("embedding", [])
            else:
                return []

        except Exception as e:
            print(f"Error generating embedding with Ollama: {e}")
            return []

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Chat completion with message history"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "options": {
                        "num_predict": max_tokens
                    },
                    "stream": False
                }
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "Keine Antwort generiert.")
            else:
                return f"Fehler: Status {response.status_code}"

        except Exception as e:
            print(f"Error in chat completion: {e}")
            return "Fehler bei der Chat-Vervollständigung."

    async def summarize_document(self, content: str, max_length: int = 500) -> str:
        """Summarize a document"""
        prompt = f"""Erstelle eine präzise Zusammenfassung des folgenden Texts in maximal {max_length} Zeichen:

{content[:3000]}  # Limit input to avoid token limits

Zusammenfassung:"""

        return await self.generate_response(
            query="Zusammenfassung erstellen",
            context=content[:3000],
            system_prompt="Du bist ein Experte für Textzusammenfassungen. Erstelle präzise und informative Zusammenfassungen.",
            temperature=0.5
        )

    async def answer_with_rag(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Answer a query using RAG (Retrieval Augmented Generation)"""

        # Prepare context from documents
        context_parts = []
        sources = []

        for idx, doc in enumerate(documents[:5]):  # Use top 5 documents
            context_parts.append(f"Dokument {idx + 1} ({doc.get('filename', 'Unbekannt')}):\n{doc.get('content', '')}")
            sources.append({
                "document_id": doc.get("document_id"),
                "filename": doc.get("filename"),
                "excerpt": doc.get("excerpt"),
                "relevance_score": doc.get("score", 0)
            })

        context = "\n\n".join(context_parts)

        # Generate response
        response_text = await self.generate_response(
            query=query,
            context=context,
            system_prompt="""Du bist ein KI-Assistent für die Pyramid Computer GmbH.
            Beantworte Fragen basierend auf den bereitgestellten Dokumenten.
            Gib immer die Quelle deiner Antwort an (Dokumentname).
            Wenn die Information nicht in den Dokumenten enthalten ist, sage das klar.""",
            temperature=0.7
        )

        return {
            "answer": response_text,
            "sources": sources,
            "query": query,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Fallback implementation when Ollama is not available
class MockOllamaClient(OllamaClient):
    """Mock Ollama client for testing without Ollama"""

    async def check_health(self) -> Dict[str, Any]:
        return {
            "status": "mock",
            "available_models": ["mock-model"],
            "model_available": False
        }

    async def generate_response(
        self,
        query: str,
        context: str = "",
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        return f"Dies ist eine Demo-Antwort für die Anfrage: '{query}'. In der Produktionsumgebung würde hier eine echte KI-Antwort generiert werden basierend auf dem Kontext."

    async def generate_embedding(self, text: str) -> List[float]:
        # Return a random embedding
        import random
        return [random.random() for _ in range(768)]