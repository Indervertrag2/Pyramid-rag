#!/usr/bin/env python3
"""
MCP Subprocess Manager
Handles spawning and communicating with MCP STDIO server process
"""

import asyncio
import json
import subprocess
import sys
import os
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MCPResponse:
    """Response from MCP server"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    request_id: Optional[str] = None

class MCPSubprocessManager:
    """Manages MCP server subprocess with STDIO communication"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.read_task: Optional[asyncio.Task] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.streaming_handlers: Dict[str, Any] = {}
        self.initialized = False

    async def start(self):
        """Start the MCP server subprocess"""
        try:
            # Find the MCP server script
            current_dir = Path(__file__).parent
            mcp_script = current_dir / "mcp_server_stdio.py"

            if not mcp_script.exists():
                raise FileNotFoundError(f"MCP server script not found: {mcp_script}")

            # Start the subprocess
            logger.info("Starting MCP STDIO server subprocess...")

            # Create pipes for communication
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, str(mcp_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            # Start reading from stdout
            self.read_task = asyncio.create_task(self._read_loop())

            # Initialize the MCP server
            await self.initialize()

            logger.info("MCP STDIO server started successfully")

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def stop(self):
        """Stop the MCP server subprocess"""
        if self.read_task:
            self.read_task.cancel()

        if self.process:
            self.process.terminate()
            await self.process.wait()

        self.initialized = False
        logger.info("MCP STDIO server stopped")

    async def initialize(self):
        """Initialize MCP server connection"""
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "Pyramid RAG Backend",
                    "version": "1.0.0"
                }
            },
            "id": request_id
        }

        response = await self._send_request(request)
        if response.success:
            self.initialized = True
            logger.info(f"MCP server initialized: {response.result}")
        else:
            raise RuntimeError(f"Failed to initialize MCP server: {response.error}")

    async def _read_loop(self):
        """Continuously read from subprocess stdout"""
        try:
            while self.process and self.process.stdout:
                line = await self.process.stdout.readline()
                if not line:
                    break

                try:
                    data = json.loads(line.decode('utf-8'))
                    await self._handle_response(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from MCP server: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP response: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Read loop error: {e}")

    async def _handle_response(self, data: Dict[str, Any]):
        """Handle response from MCP server"""
        # Check if it's a streaming chunk
        if data.get("method") == "chat/streamChunk":
            session_id = data.get("params", {}).get("session_id")
            if session_id in self.streaming_handlers:
                handler = self.streaming_handlers[session_id]
                chunk = data.get("params", {}).get("chunk", "")
                await handler(chunk)
            return

        # Handle regular response
        request_id = data.get("id")
        if request_id and request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)

            if "error" in data:
                response = MCPResponse(
                    success=False,
                    error=data["error"].get("message", "Unknown error"),
                    request_id=request_id
                )
            else:
                response = MCPResponse(
                    success=True,
                    result=data.get("result"),
                    request_id=request_id
                )

            if not future.done():
                future.set_result(response)

    async def _send_request(self, request: Dict[str, Any]) -> MCPResponse:
        """Send request to MCP server and wait for response"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not running")

        request_id = request.get("id", str(uuid.uuid4()))
        request["id"] = request_id

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        # Send request
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line.encode('utf-8'))
        await self.process.stdin.drain()

        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            return MCPResponse(
                success=False,
                error="Request timeout",
                request_id=request_id
            )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        """Call an MCP tool"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": str(uuid.uuid4())
        }

        return await self._send_request(request)

    async def stream_chat(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response from MCP server"""
        if not self.initialized:
            await self.start()

        # Create queue for streaming chunks
        chunk_queue = asyncio.Queue()

        # Register streaming handler
        async def handle_chunk(chunk: str):
            await chunk_queue.put(chunk)

        self.streaming_handlers[session_id] = handle_chunk

        # Send streaming request
        request = {
            "jsonrpc": "2.0",
            "method": "chat/stream",
            "params": {
                "message": message,
                "session_id": session_id,
                "context": context or {}
            },
            "id": str(uuid.uuid4())
        }

        # Start streaming in background
        stream_task = asyncio.create_task(self._send_request(request))

        try:
            # Yield chunks as they arrive
            while True:
                try:
                    chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.5)
                    yield chunk
                except asyncio.TimeoutError:
                    # Check if streaming is complete
                    if stream_task.done():
                        response = await stream_task
                        if not response.success:
                            logger.error(f"Stream error: {response.error}")
                        break
                    continue

        finally:
            # Clean up
            self.streaming_handlers.pop(session_id, None)

    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": str(uuid.uuid4())
        }

        response = await self._send_request(request)
        return response.result if response.success else {"tools": []}

    async def get_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get a resource by URI"""
        request = {
            "jsonrpc": "2.0",
            "method": "resources/get",
            "params": {"uri": uri},
            "id": str(uuid.uuid4())
        }

        response = await self._send_request(request)
        return response.result if response.success else None

# Singleton instance
mcp_manager = MCPSubprocessManager()

async def get_mcp_manager() -> MCPSubprocessManager:
    """Get or create MCP manager instance"""
    if not mcp_manager.initialized:
        await mcp_manager.start()
    return mcp_manager