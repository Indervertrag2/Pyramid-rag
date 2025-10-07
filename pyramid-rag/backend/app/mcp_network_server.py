#!/usr/bin/env python3
"""
MCP Server with HTTP/WebSocket interface
Runs as a separate Docker service and communicates over network
"""

import asyncio
import base64
import json
import logging
import os
import re
import unicodedata
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _sanitize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\x00", " ")
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized

app = FastAPI(title="MCP Server", version="1.0.0")

class ToolType(str, Enum):
    CHAT = "chat"
    SEARCH = "hybrid_search"
    VECTOR_SEARCH = "vector_search"
    KEYWORD_SEARCH = "keyword_search"
    DOCUMENT_UPLOAD = "document_upload"
    GET_CONTEXT = "get_context"

@dataclass
class MCPRequest:
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

@dataclass
class MCPResponse:
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class MCPServer:
    """MCP Server implementation with network interface"""

    def __init__(self):
        self.tools = {}
        self.resources = {}
        self.sessions = {}
        self.backend_url = os.getenv("MCP_BACKEND_URL", "http://pyramid-backend:8000")
        self.service_email = os.getenv("MCP_SERVICE_EMAIL")
        self.service_password = os.getenv("MCP_SERVICE_PASSWORD")
        self.service_token: Optional[str] = None
        self.token_expiry: datetime = datetime.utcnow()
        self.token_lock = asyncio.Lock()
        self._setup_tools()

    def _setup_tools(self):
        """Register available MCP tools"""
        self.tools = {
            ToolType.CHAT: self._tool_chat,
            ToolType.SEARCH: self._tool_search,
            ToolType.VECTOR_SEARCH: self._tool_vector_search,
            ToolType.KEYWORD_SEARCH: self._tool_keyword_search,
            ToolType.DOCUMENT_UPLOAD: self._tool_document_upload,
            ToolType.GET_CONTEXT: self._tool_get_context,
        }

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP request"""
        try:
            method = request.method
            params = request.params or {}

            # Route to appropriate handler
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_list_tools(params)
            elif method == "tools/call":
                result = await self._handle_tool_call(params)
            elif method == "resources/list":
                result = await self._handle_list_resources(params)
            elif method == "resources/get":
                result = await self._handle_get_resource(params)
            else:
                raise ValueError(f"Unknown method: {method}")

            return MCPResponse(result=result, id=request.id)

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return MCPResponse(
                error={"code": -32603, "message": str(e)},
                id=request.id
            )

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization"""
        return {
            "protocolVersion": "1.0.0",
            "capabilities": {
                "tools": True,
                "resources": True,
                "streaming": True
            },
            "serverInfo": {
                "name": "Pyramid RAG MCP Server",
                "version": "1.0.0"
            }
        }

    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools"""
        tools_list = []
        for name in self.tools:
            tools_list.append({
                "name": name,
                "description": f"Tool: {name}",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            })
        return {"tools": tools_list}

    async def _handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool"""
        tool_name = params.get("name")
        tool_params = params.get("arguments", {})

        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Execute the tool
        result = await self.tools[tool_name](tool_params)
        return result

    async def _handle_list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resources"""
        return {"resources": list(self.resources.values())}

    async def _handle_get_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a resource by URI"""
        uri = params.get("uri")
        if not uri:
            raise ValueError("Missing required parameter: uri")

        if uri not in self.resources:
            raise ValueError(f"Resource not found: {uri}")

        return self.resources[uri]

    async def stream_chat(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response from Ollama"""
        try:
            # Build system prompt based on context
            system_prompt = "Du bist ein hilfreicher KI-Assistent für die Pyramid Computer GmbH."

            if context:
                department = context.get("department", "UNKNOWN")
                system_prompt += f"\nDer Benutzer ist aus der Abteilung {department}."

                if context.get("rag_enabled", False):
                    system_prompt += "\nVerwende die verfügbaren Dokumente nur wenn sie zur Frage passen."

            uploaded_docs = context.get("uploaded_documents") or []
            search_results = context.get("search_results") or []
            document_summaries = []

            for doc in uploaded_docs:
                content = _sanitize_text(doc.get("content") or doc.get("content_preview") or "")
                document_summaries.append({
                    "source": "chat",
                    "scope": doc.get("scope", "CHAT"),
                    "document_id": doc.get("document_id") or doc.get("id"),
                    "title": doc.get("title") or doc.get("filename") or "Dokument",
                    "content_preview": content[:500],
                    "mime_type": doc.get("mime_type"),
                    "uploaded_by": doc.get("uploaded_by"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                })

            for result in search_results:
                snippet = result.get("chunk_content") or result.get("content") or result.get("text") or result.get("excerpt") or ""
                snippet = _sanitize_text(snippet)[:500]
                document_summaries.append({
                    "source": "knowledge_base",
                    "scope": result.get("scope", "GLOBAL"),
                    "document_id": result.get("document_id"),
                    "chunk_id": result.get("chunk_id"),
                    "title": result.get("document_title") or result.get("title") or "Dokument",
                    "content_preview": snippet,
                    "score": result.get("hybrid_score") or result.get("score")
                })

            self.sessions[session_id] = {
                "documents": document_summaries,
            }

            # Connect to Ollama with streaming
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    'POST',
                    'http://pyramid-ollama:11434/api/chat',
                    json={
                        "model": "qwen2.5:7b",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ],
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if 'message' in data and 'content' in data['message']:
                                    chunk = data['message']['content']
                                    if chunk:
                                        yield chunk
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error: {e}"

    async def _ensure_service_token(self) -> Optional[str]:
        """Ensure we have a backend service token for API calls."""
        if not self.service_email or not self.service_password:
            return None

        async with self.token_lock:
            now = datetime.utcnow()
            if self.service_token and now < self.token_expiry:
                return self.service_token

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{self.backend_url}/api/v1/auth/login",
                        json={
                            "email": self.service_email,
                            "password": self.service_password
                        }
                    )

                if response.status_code != 200:
                    logger.error(
                        "Service login failed (%s): %s",
                        response.status_code,
                        response.text
                    )
                    return None

                data = response.json()
                self.service_token = data.get("access_token")
                self.token_expiry = now + timedelta(minutes=25)
                return self.service_token

            except Exception as exc:
                logger.error(f"Service token error: {exc}")
                return None

    async def _call_backend_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate search to backend API with service token."""
        token = await self._ensure_service_token()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.post(
                f"{self.backend_url}/api/v1/mcp/search",
                json=payload,
                headers=headers
            )

        if response.status_code != 200:
            logger.error(
                "Backend search failed (%s): %s",
                response.status_code,
                response.text
            )
            raise HTTPException(status_code=500, detail="Backend search failed")

        return response.json()

    # Tool implementations
    async def _tool_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Chat tool for non-streaming responses"""
        message = params.get("message", "")
        session_id = params.get("session_id", str(uuid.uuid4()))
        context = params.get("context", {})

        # For non-streaming, collect full response
        full_response = ""
        async for chunk in self.stream_chat(message, session_id, context):
            full_response += chunk

        return {
            "response": full_response,
            "timestamp": datetime.now().isoformat()
        }

    async def _tool_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Hybrid search tool via backend."""
        query = params.get("query", "")
        limit = params.get("limit", 5)
        department = params.get("department")

        if not query:
            raise HTTPException(status_code=400, detail="Missing query for hybrid search")

        payload = {
            "query": query,
            "mode": "HYBRID",
            "limit": limit,
            "department": department
        }

        result = await self._call_backend_search(payload)
        return {
            "results": result.get("results", []),
            "query": result.get("query", query),
            "count": result.get("total_results", len(result.get("results", []))),
            "mode": result.get("mode", "HYBRID")
        }

    async def _tool_vector_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vector search tool via backend."""
        query = params.get("query", "")
        limit = params.get("limit", 5)
        department = params.get("department")

        if not query:
            raise HTTPException(status_code=400, detail="Missing query for vector search")

        payload = {
            "query": query,
            "mode": "VECTOR",
            "limit": limit,
            "department": department
        }

        result = await self._call_backend_search(payload)
        return {
            "results": result.get("results", []),
            "query": result.get("query", query),
            "count": result.get("total_results", len(result.get("results", []))),
            "mode": result.get("mode", "VECTOR")
        }

    async def _tool_keyword_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Keyword search tool via backend."""
        query = params.get("query", "")
        limit = params.get("limit", 5)
        department = params.get("department")

        if not query:
            raise HTTPException(status_code=400, detail="Missing query for keyword search")

        payload = {
            "query": query,
            "mode": "KEYWORD",
            "limit": limit,
            "department": department
        }

        result = await self._call_backend_search(payload)
        return {
            "results": result.get("results", []),
            "query": result.get("query", query),
            "count": result.get("total_results", len(result.get("results", []))),
            "mode": result.get("mode", "KEYWORD")
        }

    async def _tool_document_upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Document upload tool bridging to backend pipeline."""
        file_name = params.get("file_name") or params.get("filename")
        file_content_b64 = params.get("file_content") or params.get("content_base64")
        if not file_name or not file_content_b64:
            raise HTTPException(status_code=400, detail="file_name and file_content are required")

        scope = (params.get("scope") or "GLOBAL").upper()
        visibility = (params.get("visibility") or "department").lower()
        session_id = params.get("session_id")
        content_type = params.get("content_type") or "application/octet-stream"

        if scope not in {"GLOBAL", "CHAT"}:
            raise HTTPException(status_code=400, detail="scope must be GLOBAL or CHAT")
        if scope == "CHAT" and not session_id:
            raise HTTPException(status_code=400, detail="session_id required when scope is CHAT")

        try:
            file_bytes = base64.b64decode(file_content_b64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 content: {exc}")

        token = await self._ensure_service_token()
        headers: Dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        form_data = {
            "scope": scope,
            "visibility": visibility,
        }
        if session_id:
            form_data["session_id"] = session_id

        files = {
            "file": (file_name, file_bytes, content_type)
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.backend_url}/api/v1/documents/upload",
                data=form_data,
                files=files,
                headers=headers
            )

        if response.status_code not in (200, 201):
            logger.error(
                "Backend document upload failed (%s): %s",
                response.status_code,
                response.text
            )
            raise HTTPException(status_code=500, detail="Backend document upload failed")

        result = response.json()
        result.setdefault("scope", scope)
        result.setdefault("visibility", visibility)
        return result

    async def _tool_get_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get conversation context"""
        session_id = params.get("session_id")
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return {
            "session_id": session_id,
            "messages": []
        }

# Singleton instance
mcp_server = MCPServer()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server"}

@app.post("/mcp/request")
async def mcp_request(request: dict):
    """Handle MCP JSON-RPC requests"""
    mcp_req = MCPRequest(
        method=request.get("method"),
        params=request.get("params"),
        id=request.get("id")
    )

    response = await mcp_server.handle_request(mcp_req)
    return asdict(response)

@app.post("/mcp/stream")
async def mcp_stream(request: dict):
    """Stream chat responses"""
    message = request.get("message", "")
    session_id = request.get("session_id", str(uuid.uuid4()))
    context = request.get("context", {})

    async def generate():
        """Generate SSE stream"""
        try:
            async for chunk in mcp_server.stream_chat(message, session_id, context):
                # Send as SSE format
                yield f"event: message\ndata: {json.dumps({'chunk': chunk})}\n\n"

            session_snapshot = mcp_server.sessions.get(session_id, {})
            documents = session_snapshot.get('documents', [])
            # Send completion event
            yield f"event: done\ndata: {json.dumps({'status': 'complete', 'session_id': session_id, 'documents': documents})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for bidirectional communication"""
    await websocket.accept()
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            # Handle as MCP request
            mcp_req = MCPRequest(
                method=data.get("method"),
                params=data.get("params"),
                id=data.get("id")
            )

            # Special handling for streaming
            if mcp_req.method == "chat/stream":
                message = mcp_req.params.get("message", "")
                session_id = mcp_req.params.get("session_id", str(uuid.uuid4()))
                context = mcp_req.params.get("context", {})

                # Stream response
                async for chunk in mcp_server.stream_chat(message, session_id, context):
                    await websocket.send_json({
                        "type": "stream",
                        "chunk": chunk,
                        "id": mcp_req.id
                    })

                # Send completion
                await websocket.send_json({
                    "type": "complete",
                    "id": mcp_req.id
                })
            else:
                # Handle regular request
                response = await mcp_server.handle_request(mcp_req)
                await websocket.send_json(asdict(response))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
