#!/usr/bin/env python3
"""
MCP Server with STDIO Transport
Implements Model Context Protocol with JSON-RPC 2.0 over standard input/output
Supports streaming responses for real-time chat experience
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/mcp_server.log')]
)
logger = logging.getLogger(__name__)

class JSONRPCError(Exception):
    """JSON-RPC Error"""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

# JSON-RPC Error Codes
class ErrorCode(Enum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

@dataclass
class JSONRPCRequest:
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None

@dataclass
class JSONRPCResponse:
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None

class MCPServerSTDIO:
    """MCP Server that communicates via STDIO using JSON-RPC 2.0"""

    def __init__(self):
        self.tools = {}
        self.resources = {}
        self.sessions = {}
        self.running = False
        self._setup_tools()

    def _setup_tools(self):
        """Register available MCP tools"""
        self.tools = {
            "chat": self._tool_chat,
            "search": self._tool_search,
            "document_upload": self._tool_document_upload,
            "get_context": self._tool_get_context,
        }

    async def start(self):
        """Start the STDIO server"""
        self.running = True
        logger.info("MCP STDIO Server starting...")

        try:
            # Read from stdin, write to stdout
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

            while self.running:
                try:
                    # Read line from stdin
                    line = await reader.readline()
                    if not line:
                        break

                    # Process the JSON-RPC request
                    response = await self.handle_request(line.decode('utf-8').strip())

                    # Write response to stdout
                    if response:
                        sys.stdout.write(json.dumps(response) + '\n')
                        sys.stdout.flush()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    error_response = JSONRPCResponse(
                        error={
                            "code": ErrorCode.INTERNAL_ERROR.value,
                            "message": str(e)
                        }
                    )
                    sys.stdout.write(json.dumps(asdict(error_response)) + '\n')
                    sys.stdout.flush()

        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("MCP STDIO Server stopped")

    async def handle_request(self, request_str: str) -> Optional[Dict[str, Any]]:
        """Handle a JSON-RPC request"""
        try:
            # Parse JSON-RPC request
            request_data = json.loads(request_str)
            logger.info(f"Received request: {request_data.get('method', 'unknown')}")

            # Validate JSON-RPC format
            if request_data.get("jsonrpc") != "2.0":
                raise JSONRPCError(
                    ErrorCode.INVALID_REQUEST.value,
                    "Invalid JSON-RPC version"
                )

            method = request_data.get("method")
            params = request_data.get("params", {})
            request_id = request_data.get("id")

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
            elif method == "chat/stream":
                # Special handling for streaming
                await self._handle_streaming_chat(params, request_id)
                return None  # Streaming handles its own responses
            else:
                raise JSONRPCError(
                    ErrorCode.METHOD_NOT_FOUND.value,
                    f"Method not found: {method}"
                )

            # Return response
            response = JSONRPCResponse(result=result, id=request_id)
            return asdict(response)

        except JSONRPCError as e:
            response = JSONRPCResponse(
                error={
                    "code": e.code,
                    "message": e.message,
                    "data": e.data
                },
                id=request_data.get("id") if 'request_data' in locals() else None
            )
            return asdict(response)
        except json.JSONDecodeError as e:
            response = JSONRPCResponse(
                error={
                    "code": ErrorCode.PARSE_ERROR.value,
                    "message": f"Parse error: {e}"
                }
            )
            return asdict(response)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            response = JSONRPCResponse(
                error={
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": str(e)
                },
                id=request_data.get("id") if 'request_data' in locals() else None
            )
            return asdict(response)

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization"""
        return {
            "protocolVersion": "1.0.0",
            "capabilities": {
                "tools": True,
                "resources": True,
                "streaming": True,
                "prompts": True
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
            raise JSONRPCError(
                ErrorCode.INVALID_PARAMS.value,
                f"Unknown tool: {tool_name}"
            )

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
            raise JSONRPCError(
                ErrorCode.INVALID_PARAMS.value,
                "Missing required parameter: uri"
            )

        if uri not in self.resources:
            raise JSONRPCError(
                ErrorCode.INVALID_PARAMS.value,
                f"Resource not found: {uri}"
            )

        return self.resources[uri]

    async def _handle_streaming_chat(self, params: Dict[str, Any], request_id: Any):
        """Handle streaming chat responses"""
        message = params.get("message", "")
        session_id = params.get("session_id", str(uuid.uuid4()))

        # Stream the response
        async for chunk in self._stream_chat_response(message, session_id):
            # Send streaming response
            response = {
                "jsonrpc": "2.0",
                "method": "chat/streamChunk",
                "params": {
                    "chunk": chunk,
                    "session_id": session_id
                }
            }
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()

        # Send final response
        final_response = JSONRPCResponse(
            result={
                "status": "complete",
                "session_id": session_id
            },
            id=request_id
        )
        sys.stdout.write(json.dumps(asdict(final_response)) + '\n')
        sys.stdout.flush()

    async def _stream_chat_response(self, message: str, session_id: str) -> AsyncGenerator[str, None]:
        """Stream chat response from Ollama"""
        try:
            import httpx

            # Connect to Ollama with streaming
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    'POST',
                    'http://ollama:11434/api/chat',
                    json={
                        "model": "qwen2.5:7b",
                        "messages": [
                            {"role": "system", "content": "Du bist ein hilfreicher KI-Assistent für die Pyramid Computer GmbH."},
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

        # For non-streaming, collect full response
        full_response = ""
        async for chunk in self._stream_chat_response(message, str(uuid.uuid4())):
            full_response += chunk

        return {
            "response": full_response,
            "timestamp": datetime.now().isoformat()
        }

    async def _tool_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search tool implementation"""
        query = params.get("query", "")
        # TODO: Implement actual search
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

async def main():
    """Main entry point"""
    server = MCPServerSTDIO()
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)