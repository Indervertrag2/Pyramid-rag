import httpx
import json
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio
import os
from app.services.search_service import SearchService
from app.services.ollama_embedding_service import OllamaEmbeddingService


class LLMService:
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
        self.timeout = float(os.getenv('OLLAMA_TIMEOUT', '30.0'))
        self.search_service = SearchService()
        self.embedding_service = OllamaEmbeddingService()

    async def check_model_availability(self) -> bool:
        """Check if the specified model is available in Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0
                )
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return any(model["name"] == self.model for model in models)
                return False
        except:
            return False

    async def pull_model(self) -> bool:
        """Pull the specified model if not available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model},
                    timeout=600.0  # 10 minutes for model download
                )
                return response.status_code == 200
        except:
            return False

    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False
    ) -> str:
        """Generate response from LLM."""
        temperature = temperature or float(os.getenv('TEMPERATURE', '0.7'))
        # Remove max_tokens limitation - let the model decide when to stop naturally
        # For 70B models, use very high limit or omit entirely
        max_tokens = max_tokens or int(os.getenv('MAX_TOKENS', '32768'))  # Increased for 70B models

        # Prepare the full prompt
        full_prompt = self._prepare_prompt(prompt, context)

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "stream": stream
        }

        # Only add num_predict if explicitly set (don't limit by default)
        if max_tokens and max_tokens < 32768:
            payload["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    raise Exception(f"LLM API error: {response.status_code}")
        except httpx.TimeoutException:
            raise Exception("LLM request timeout")
        except Exception as e:
            raise Exception(f"LLM error: {str(e)}")

    async def generate_response_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from LLM."""
        temperature = temperature or float(os.getenv('TEMPERATURE', '0.7'))
        # Remove max_tokens limitation for streaming as well
        max_tokens = max_tokens or int(os.getenv('MAX_TOKENS', '32768'))  # Increased for 70B models

        full_prompt = self._prepare_prompt(prompt, context)

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "stream": True
        }

        # Only add num_predict if explicitly set (don't limit by default)
        if max_tokens and max_tokens < 32768:
            payload["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield f"Error: {str(e)}"

    async def generate_rag_response(
        self,
        db,
        user,
        query: str,
        use_rag: bool = True,
        search_mode: str = "hybrid",
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate response with optional RAG context."""

        retrieved_documents = []
        context = None
        search_results = None

        if use_rag:
            # Perform document search
            search_results = await self.search_service.search(
                db=db,
                query=query,
                user=user,
                mode=search_mode,
                limit=int(os.getenv('MAX_SEARCH_RESULTS', '5'))
            )

            if search_results and search_results.get("results"):
                # Build context from search results
                context_parts = []
                for i, result in enumerate(search_results["results"][:5]):  # Top 5 results
                    context_parts.append(
                        f"[Dokument {i+1}]: {result.get('document_title', 'Unbekannt')}\n"
                        f"{result.get('content', result.get('content_preview', ''))[:1000]}"
                    )

                    retrieved_documents.append({
                        "document_id": result.get("document_id"),
                        "title": result.get("document_title", result.get("title")),
                        "filename": result.get("filename"),
                        "score": result.get("similarity_score", result.get("relevance_score", 0))
                    })

                context = "\n\n".join(context_parts)

        # Generate response
        start_time = datetime.utcnow()

        if stream:
            # For streaming, we'll collect the response
            response_parts = []
            async for chunk in self.generate_response_stream(
                prompt=query,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                response_parts.append(chunk)
                # You could yield chunks here for real streaming
            response = "".join(response_parts)
        else:
            response = await self.generate_response(
                prompt=query,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens
            )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Count tokens (approximate)
        prompt_tokens = self.embedding_service.count_tokens(
            self._prepare_prompt(query, context)
        )
        response_tokens = self.embedding_service.count_tokens(response)

        return {
            "response": response,
            "use_rag": use_rag,
            "retrieved_documents": retrieved_documents,
            "search_results": search_results,
            "tokens_used": prompt_tokens + response_tokens,
            "processing_time": processing_time,
            "model": self.model
        }

    def _prepare_prompt(self, prompt: str, context: Optional[str] = None) -> str:
        """Prepare the full prompt with context and instructions."""

        if context:
            # RAG prompt template - Model-agnostic, optimized for 70B+ models
            full_prompt = f"""Sie sind ein KI-Assistent für die Pyramid Computer GmbH mit Zugriff auf interne Firmendokumente.

RELEVANTE DOKUMENTE:
{context}

AUFGABE:
Beantworten Sie die folgende Frage präzise und fundiert basierend auf den obigen Dokumenten.
- Nennen Sie die Quelle Ihrer Informationen (z.B. "laut Dokument 1...")
- Falls die Dokumente keine Antwort enthalten, geben Sie dies klar an
- Antworten Sie auf Deutsch, außer die Frage ist auf Englisch
- Seien Sie präzise und vermeiden Sie Spekulationen

FRAGE: {prompt}

ANTWORT:"""
        else:
            # Standard prompt without RAG
            full_prompt = f"""Sie sind ein KI-Assistent für die Pyramid Computer GmbH.
Beantworten Sie die folgende Frage basierend auf Ihrem Wissen.
Antworten Sie auf Deutsch, außer die Frage ist auf Englisch.

FRAGE: {prompt}

ANTWORT:"""

        return full_prompt

    async def summarize_document(
        self,
        document_content: str,
        max_length: int = 500
    ) -> str:
        """Generate a summary of a document."""

        prompt = f"""Erstellen Sie eine prägnante Zusammenfassung des folgenden Dokuments.
Die Zusammenfassung sollte die wichtigsten Punkte enthalten und maximal {max_length} Wörter lang sein.

DOKUMENT:
{document_content[:5000]}  # Limit input length

ZUSAMMENFASSUNG:"""

        summary = await self.generate_response(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more focused summary
            max_tokens=max_length * 2  # Approximate token count
        )

        return summary

    async def extract_keywords(
        self,
        text: str,
        num_keywords: int = 10
    ) -> List[str]:
        """Extract keywords from text."""

        prompt = f"""Extrahieren Sie die {num_keywords} wichtigsten Schlüsselwörter aus dem folgenden Text.
Geben Sie nur die Schlüsselwörter zurück, getrennt durch Kommas.

TEXT:
{text[:3000]}

SCHLÜSSELWÖRTER:"""

        response = await self.generate_response(
            prompt=prompt,
            temperature=0.2,
            max_tokens=100
        )

        # Parse keywords from response
        keywords = [k.strip() for k in response.split(",")]
        return keywords[:num_keywords]

    async def answer_question_with_sources(
        self,
        db,
        user,
        question: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Answer a question based on specific documents."""

        # Build context from documents
        context_parts = []
        for doc in documents:
            context_parts.append(
                f"[{doc['title']}]:\n{doc['content'][:2000]}"
            )

        context = "\n\n".join(context_parts)

        # Generate answer
        response = await self.generate_response(
            prompt=question,
            context=context,
            temperature=0.5
        )

        return {
            "question": question,
            "answer": response,
            "sources": [{"title": doc["title"], "id": doc.get("id")} for doc in documents],
            "model": self.model
        }

    async def check_health(self) -> Dict[str, Any]:
        """Check LLM service health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/version",
                    timeout=5.0
                )

                if response.status_code == 200:
                    version_info = response.json()

                    # Check model availability
                    model_available = await self.check_model_availability()

                    return {
                        "status": "healthy" if model_available else "degraded",
                        "ollama_version": version_info.get("version"),
                        "model": self.model,
                        "model_available": model_available,
                        "base_url": self.base_url
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"Ollama API returned {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }