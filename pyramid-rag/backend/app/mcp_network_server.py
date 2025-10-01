#!/usr/bin/env python3
"""
MCP Server with HTTP/WebSocket interface
Runs as a separate Docker service and communicates over network
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime
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
        """Hybrid search tool"""
        query = params.get("query", "")
        limit = params.get("limit", 5)

        # TODO: Implement actual search
        return {
            "results": [],
            "query": query,
            "count": 0
        }

    async def _tool_vector_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vector search tool"""
        query = params.get("query", "")
        limit = params.get("limit", 5)

        # TODO: Implement actual vector search
        return {
            "results": [],
            "query": query,
            "count": 0
        }

    async def _tool_keyword_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Keyword search tool"""
        query = params.get("query", "")
        limit = params.get("limit", 5)

        # TODO: Implement actual keyword search
        return {
            "results": [],
            "query": query,
            "count": 0
        }

    async def _tool_document_upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Document upload tool"""
        # TODO: Implement document handling
        return {
            "status": "success",
            "document_id": str(uuid.uuid4())
        }

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

            # Send completion event
            yield f"event: done\ndata: {json.dumps({'status': 'complete', 'session_id': session_id})}\n\n"
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