"""
MCP (Model Context Protocol) Server Implementation
Provides standardized AI model interactions for the Pyramid RAG Platform
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, DocumentChunk, ChatSession, ChatMessage
from app.vector_store import VectorStore
from app.ollama_simple import SimpleOllamaClient  # Using simple sync client
# from app.document_processor import DocumentProcessor  # Commented out for now
import numpy as np

logger = logging.getLogger(__name__)

class ToolType(Enum):
    """Available MCP tools"""
    DOCUMENT_SEARCH = "document_search"
    DOCUMENT_UPLOAD = "document_upload"
    VECTOR_SEARCH = "vector_search"
    KEYWORD_SEARCH = "keyword_search"
    HYBRID_SEARCH = "hybrid_search"
    CHAT = "chat"
    DEPARTMENT_FILTER = "department_filter"
    GET_CONTEXT = "get_context"
    SAVE_CONTEXT = "save_context"
    RAG_DOC_RESOURCE = "rag_doc_resource"

@dataclass
class MCPMessage:
    """MCP message format"""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

@dataclass
class MCPContext:
    """Context management for MCP sessions"""
    session_id: str
    user_id: str
    department: str
    messages: List[MCPMessage]
    documents: List[str]  # Document IDs in context
    max_tokens: int = 8192
    temperature: float = 0.7

class MCPTool:
    """Base class for MCP tools"""

    def __init__(self, db: Session):
        self.db = db

    async def execute(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

class DocumentSearchTool(MCPTool):
    """Search documents in the database"""

    async def execute(self, query: str, department: Optional[str] = None,
                      limit: int = 10, **kwargs) -> Dict[str, Any]:
        try:
            documents = self.db.query(Document).filter(
                Document.is_active == True
            )

            if department:
                documents = documents.filter(Document.department == department)

            if query:
                # Simple text search - in production, use full-text search
                documents = documents.filter(
                    Document.filename.ilike(f"%{query}%") |
                    Document.title.ilike(f"%{query}%")
                )

            results = documents.limit(limit).all()

            return {
                "success": True,
                "documents": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "title": doc.title,
                        "department": doc.department,
                        "file_type": doc.file_type,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None
                    }
                    for doc in results
                ]
            }
        except Exception as e:
            logger.error(f"Document search error: {str(e)}")
            return {"success": False, "error": str(e)}

class VectorSearchTool(MCPTool):
    """Semantic search using vector embeddings"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.vector_store = VectorStore()

    async def execute(self, query: str, department: Optional[str] = None,
                      limit: int = 5, **kwargs) -> Dict[str, Any]:
        try:
            logger.info(f"VectorSearchTool executing semantic search for: {query}")

            results = await self.vector_store.semantic_search(
                query=query,
                db=self.db,
                limit=limit,
                user_department=department
            )

            return {
                "success": True,
                "tool": "vector_search",
                "query": query,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            return {"success": False, "error": str(e)}

class KeywordSearchTool(MCPTool):
    """Keyword-based search in document content"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.vector_store = VectorStore()

    async def execute(self, query: str, department: Optional[str] = None,
                      limit: int = 10, **kwargs) -> Dict[str, Any]:
        try:
            logger.info(f"KeywordSearchTool executing keyword search for: {query}")

            results = await self.vector_store.keyword_search(
                query=query,
                db=self.db,
                limit=limit,
                user_department=department
            )

            return {
                "success": True,
                "tool": "keyword_search",
                "query": query,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Keyword search error: {str(e)}")
            return {"success": False, "error": str(e)}

class HybridSearchTool(MCPTool):
    """Hybrid search combining semantic and keyword search"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.vector_store = VectorStore()

    async def execute(self, query: str, department: Optional[str] = None,
                      limit: int = 10, semantic_weight: float = 0.7,
                      keyword_weight: float = 0.3, **kwargs) -> Dict[str, Any]:
        try:
            logger.info(f"HybridSearchTool executing hybrid search for: {query}")

            results = await self.vector_store.hybrid_search(
                query=query,
                db=self.db,
                limit=limit,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
                user_department=department
            )

            return {
                "success": True,
                "tool": "hybrid_search",
                "query": query,
                "results": results,
                "count": len(results),
                "semantic_weight": semantic_weight,
                "keyword_weight": keyword_weight
            }
        except Exception as e:
            logger.error(f"Hybrid search error: {str(e)}")
            return {"success": False, "error": str(e)}

class RagDocResourceTool(MCPTool):
    """Handle rag://doc/{id} resource pattern for document references"""

    async def execute(self, document_id: str, chunk_id: Optional[str] = None,
                      department: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        try:
            logger.info(f"RagDocResourceTool fetching document: {document_id}, chunk: {chunk_id}")

            # Get document
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {"success": False, "error": f"Document {document_id} not found"}

            # Check department access if specified
            if department and document.department and document.department.value != department:
                return {"success": False, "error": f"Access denied to document {document_id}"}

            result = {
                "success": True,
                "resource": f"rag://doc/{document_id}",
                "document": {
                    "id": str(document.id),
                    "title": document.title or document.filename,
                    "filename": document.filename,
                    "file_type": document.file_type.value if document.file_type else None,
                    "department": document.department.value if document.department else None,
                    "created_at": document.created_at.isoformat() if document.created_at else None,
                    "description": document.description
                }
            }

            # If specific chunk requested, get chunk details
            if chunk_id:
                chunk = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id == chunk_id,
                    DocumentChunk.document_id == document_id
                ).first()

                if chunk:
                    result["chunk"] = {
                        "id": str(chunk.id),
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "meta_data": chunk.meta_data or {}
                    }
                    result["resource"] = f"rag://doc/{document_id}/chunk/{chunk_id}"
                else:
                    result["error"] = f"Chunk {chunk_id} not found in document {document_id}"
            else:
                # Get all chunks for the document
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).order_by(DocumentChunk.chunk_index).all()

                result["chunks"] = [
                    {
                        "id": str(chunk.id),
                        "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                        "chunk_index": chunk.chunk_index
                    }
                    for chunk in chunks
                ]
                result["total_chunks"] = len(chunks)

            return result

        except Exception as e:
            logger.error(f"RAG doc resource error: {str(e)}")
            return {"success": False, "error": str(e)}

class ChatTool(MCPTool):
    """Handle chat interactions with Ollama using improved RAG flow"""

    def __init__(self, db: Session):
        super().__init__(db)
        # Using simple sync client
        self.ollama_client = SimpleOllamaClient()
        self.vector_store = VectorStore()

    async def execute(self, message: str, context: MCPContext,
                      rag_enabled: bool = True, **kwargs) -> Dict[str, Any]:
        try:
            logger.info(f"ChatTool executing with message: {message}, RAG enabled: {rag_enabled}")

            # Step 1: Check Access (validate department permissions)
            access_granted = self._check_access(context.department)
            if not access_granted:
                return {
                    "success": False,
                    "error": f"Access denied for department: {context.department}"
                }

            response_data = {
                "success": True,
                "model": "qwen2.5:7b",
                "context_used": len(context.messages),
                "rag_enabled": rag_enabled
            }

            manual_docs = []
            if context.documents:
                for doc in context.documents[-5:]:
                    content = (doc.get("content") or "").strip()
                    if not content:
                        continue
                    manual_docs.append({
                        "id": doc.get("id") or str(uuid.uuid4()),
                        "title": doc.get("title") or "Dokument",
                        "content": content[:1000]
                    })

            if rag_enabled:
                # Step 2: Search - Use hybrid search for better results
                logger.info("Performing hybrid search for RAG context")
                search_results = await self.vector_store.hybrid_search(
                    query=message,
                    db=self.db,
                    limit=5,
                    user_department=context.department
                )

                # Step 3: Retrieve - Get document references
                citations = []
                context_chunks = []
                for result in search_results:
                    if result.get('hybrid_score', 0) > 0.3:  # Only use high-scoring results
                        context_chunks.append(result['chunk_content'])
                        citations.append({
                            "resource": f"rag://doc/{result['document_id']}/chunk/{result['chunk_id']}",
                            "document_title": result['document_title'],
                            "chunk_content": result['chunk_content'][:100] + "..." if len(result['chunk_content']) > 100 else result['chunk_content'],
                            "score": result['hybrid_score']
                        })

                manual_citations = []
                if manual_docs:
                    for doc in manual_docs:
                        context_chunks.append(f"{doc['title']}: {doc['content']}")
                        manual_citations.append({
                            "resource": f"chat://doc/{doc['id']}",
                            "document_title": doc['title'],
                            "chunk_content": doc['content'][:100] + ("..." if len(doc['content']) > 100 else ""),
                            "score": 1.0
                        })
                citations.extend(manual_citations)

                # Step 4: Generate response with RAG context
                rag_prompt = self._build_rag_prompt(message, context_chunks, context, manual_docs)
                response = self.ollama_client.generate_response(
                    query=rag_prompt,
                    temperature=context.temperature
                )

                response_data.update({
                    "response": response,
                    "citations": citations,
                    "context_chunks_used": len(context_chunks),
                    "search_results_found": len(search_results)
                })

            else:
                # Direct chat without RAG
                logger.info("Generating direct response without RAG")
                basic_prompt = self._build_prompt(message, context, manual_docs)
                response = self.ollama_client.generate_response(
                    query=basic_prompt,
                    temperature=context.temperature
                )

                manual_citations = []
                if manual_docs:
                    for doc in manual_docs:
                        manual_citations.append({
                            "resource": f"chat://doc/{doc['id']}",
                            "document_title": doc['title'],
                            "chunk_content": doc['content'][:100] + ("..." if len(doc['content']) > 100 else ""),
                            "score": 1.0
                        })

                response_data.update({
                    "response": response,
                    "citations": manual_citations,
                    "context_chunks_used": len(manual_docs)
                })

            logger.info(f"Ollama response generated: {len(response_data.get('response', ''))} chars")
            return response_data

        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return {"success": False, "error": str(e)}

    def _check_access(self, department: str) -> bool:
        """Check if user has access rights"""
        # For now, allow all departments - in production, implement proper RBAC
        allowed_departments = ["Management", "Vertrieb", "Marketing", "Entwicklung",
                              "Produktion", "Qualitätssicherung", "Support",
                              "Personal", "Finanzen"]
        return department in allowed_departments

    def _build_rag_prompt(self, message: str, context_chunks: List[str], context: MCPContext, uploaded_docs: Optional[List[Dict[str, str]]] = None) -> str:
        """Build prompt with RAG context from search results"""
        prompt_parts = []

        # System prompt with RAG context
        system_prompt = (
            f"Du bist ein hilfreicher KI-Assistent für die Pyramid Computer GmbH. "
            f"Der Benutzer ist aus der Abteilung {context.department}. "
        )

        if context_chunks:
            system_prompt += (
                "Im Folgenden findest du relevante Dokumente aus der Firmendatenbank. "
                "Verwende diese NUR wenn sie zur Frage passen. "
                "Zitiere die Dokumente NUR wenn du sie tatsächlich verwendest. "
                "Für einfache Begrüßungen oder allgemeine Fragen, antworte natürlich ohne die Dokumente zu erwähnen.\n"
            )
        else:
            system_prompt += (
                "Es wurden keine relevanten Dokumente gefunden. "
                "Antworte basierend auf deinem allgemeinen Wissen.\n"
            )

        prompt_parts.append(system_prompt)

        # Add document context
        if context_chunks:
            prompt_parts.append("RELEVANT COMPANY DOCUMENTS:")
            for i, chunk in enumerate(context_chunks[:3], 1):  # Limit to 3 most relevant chunks
                prompt_parts.append(f"Document {i}: {chunk}\n")

        if uploaded_docs:
            prompt_parts.append("CHAT-KONTEXT-DOKUMENTE:")
            for doc in uploaded_docs[:3]:
                prompt_parts.append(f"{doc['title']}: {doc['content']}\n")

        # Add conversation history
        prompt_parts.append("CONVERSATION HISTORY:")
        for msg in context.messages[-3:]:  # Last 3 messages
            if msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        # Add current question
        prompt_parts.append(f"\nCurrent User Question: {message}")
        prompt_parts.append("\nPlease provide a helpful response based on the company documents above. If you reference information from the documents, mention which document number you're citing.")
        prompt_parts.append("\nAssistant:")

        return "\n".join(prompt_parts)

    def _build_prompt(self, message: str, context: MCPContext, uploaded_docs: Optional[List[Dict[str, str]]] = None) -> str:
        """Build prompt without RAG context"""
        prompt_parts = []

        # Add system prompt
        prompt_parts.append(
            "Du bist ein hilfreicher KI-Assistent für die Pyramid Computer GmbH. "
            f"Der Benutzer ist aus der Abteilung {context.department}. "
            "Antworte freundlich und hilfreich auf Deutsch. "
            "Du hast KEINEN Zugriff auf Firmendokumente - antworte nur mit deinem allgemeinen Wissen."
        )

        # Add chat-specific documents if available
        if uploaded_docs:
            prompt_parts.append("Dokumente aus dem aktuellen Chat:")
            for doc in uploaded_docs[:3]:
                prompt_parts.append(f"{doc['title']}: {doc['content']}")

        # Add recent context
        for msg in context.messages[-5:]:  # Last 5 messages
            if msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        # Add current message
        prompt_parts.append(f"User: {message}")
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

class MCPServer:
    """Main MCP Server implementation"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.tools = {
            ToolType.DOCUMENT_SEARCH: DocumentSearchTool(db_session),
            ToolType.VECTOR_SEARCH: VectorSearchTool(db_session),
            ToolType.KEYWORD_SEARCH: KeywordSearchTool(db_session),
            ToolType.HYBRID_SEARCH: HybridSearchTool(db_session),
            ToolType.RAG_DOC_RESOURCE: RagDocResourceTool(db_session),
            ToolType.CHAT: ChatTool(db_session)
        }
        self.contexts: Dict[str, MCPContext] = {}

    def update_session(self, db_session: Session):
        """Refresh database session for server and tools."""
        self.db = db_session
        for tool in self.tools.values():
            tool.db = db_session

    async def process_message(self,
                             message: Dict[str, Any],
                             session_id: str,
                             user_id: str,
                             department: str) -> Dict[str, Any]:
        """Process incoming MCP message"""

        # Get or create context
        context = self.contexts.get(session_id)
        if not context:
            context = MCPContext(
                session_id=session_id,
                user_id=user_id,
                department=department,
                messages=[],
                documents=[]
            )
            self.contexts[session_id] = context

        # Persist uploaded documents (if provided) into context
        uploaded_docs = message.get("uploaded_documents") or []
        if uploaded_docs:
            existing_ids = {doc.get("id") for doc in context.documents}
            for doc in uploaded_docs:
                content = doc.get("content")
                if not content:
                    continue
                doc_id = doc.get("id") or doc.get("document_id") or str(uuid.uuid4())
                if doc_id in existing_ids:
                    continue
                sanitized_content = content.replace("\x00", " ")
                context.documents.append({
                    "id": doc_id,
                    "title": doc.get("title") or doc.get("filename") or "Dokument",
                    "content": sanitized_content,
                    "scope": doc.get("scope", "CHAT"),
                    "visibility": doc.get("visibility", "chat")
                })
                existing_ids.add(doc_id)

            if len(context.documents) > 5:
                context.documents = context.documents[-5:]

        # Parse message
        mcp_message = MCPMessage(
            role=message.get("role", "user"),
            content=message.get("content", ""),
            tool_calls=message.get("tool_calls"),
            tool_call_id=message.get("tool_call_id"),
            name=message.get("name")
        )

        # Add to context
        context.messages.append(mcp_message)

        # Handle tool calls
        if mcp_message.tool_calls:
            return await self._handle_tool_calls(mcp_message.tool_calls, context)

        # Handle regular chat
        return await self._handle_chat(mcp_message.content, context)

    async def _handle_tool_calls(self,
                                tool_calls: List[Dict],
                                context: MCPContext) -> Dict[str, Any]:
        """Execute tool calls"""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})

            # Map string to enum
            tool_type = None
            for t in ToolType:
                if t.value == tool_name:
                    tool_type = t
                    break

            if tool_type and tool_type in self.tools:
                tool = self.tools[tool_type]
                result = await tool.execute(**tool_args, context=context)
                results.append({
                    "tool": tool_name,
                    "result": result
                })
            else:
                results.append({
                    "tool": tool_name,
                    "error": f"Unknown tool: {tool_name}"
                })

        return {
            "type": "tool_results",
            "results": results
        }

    async def _handle_chat(self,
                          content: str,
                          context: MCPContext) -> Dict[str, Any]:
        """Handle regular chat message"""
        chat_tool = self.tools[ToolType.CHAT]
        result = await chat_tool.execute(
            message=content,
            context=context
        )

        if result["success"]:
            # Add assistant response to context
            context.messages.append(MCPMessage(
                role="assistant",
                content=result["response"]
            ))

            return {
                "type": "assistant",
                "content": result["response"],
                "model": result.get("model"),
                "context_tokens": self._estimate_tokens(context)
            }
        else:
            return {
                "type": "error",
                "error": result.get("error", "Unknown error")
            }

    def _estimate_tokens(self, context: MCPContext) -> int:
        """Estimate token count for context"""
        # Simple estimation: ~4 characters per token
        total_chars = sum(len(msg.content) for msg in context.messages)
        return total_chars // 4

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            {
                "name": ToolType.DOCUMENT_SEARCH.value,
                "description": "Search for documents by name, title, or department",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "department": {"type": "string", "description": "Filter by department", "optional": True},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 10}
                }
            },
            {
                "name": ToolType.VECTOR_SEARCH.value,
                "description": "Semantic search using AI embeddings",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "department": {"type": "string", "description": "Filter by department", "optional": True},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 5}
                }
            },
            {
                "name": ToolType.KEYWORD_SEARCH.value,
                "description": "Keyword-based search in document content",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "department": {"type": "string", "description": "Filter by department", "optional": True},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 10}
                }
            },
            {
                "name": ToolType.HYBRID_SEARCH.value,
                "description": "Hybrid search combining semantic and keyword search",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "department": {"type": "string", "description": "Filter by department", "optional": True},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 10},
                    "semantic_weight": {"type": "number", "description": "Weight for semantic search", "default": 0.7},
                    "keyword_weight": {"type": "number", "description": "Weight for keyword search", "default": 0.3}
                }
            },
            {
                "name": ToolType.RAG_DOC_RESOURCE.value,
                "description": "Retrieve document or chunk content using rag://doc/{id} pattern",
                "parameters": {
                    "document_id": {"type": "string", "description": "Document ID"},
                    "chunk_id": {"type": "string", "description": "Specific chunk ID", "optional": True},
                    "department": {"type": "string", "description": "User department for access control", "optional": True}
                }
            },
            {
                "name": ToolType.CHAT.value,
                "description": "Chat with AI assistant",
                "parameters": {
                    "message": {"type": "string", "description": "User message"}
                }
            }
        ]

    def clear_context(self, session_id: str):
        """Clear context for a session"""
        if session_id in self.contexts:
            del self.contexts[session_id]

    def get_context_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of current context"""
        context = self.contexts.get(session_id)
        if not context:
            return None

        return {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "department": context.department,
            "message_count": len(context.messages),
            "document_count": len(context.documents),
            "estimated_tokens": self._estimate_tokens(context)
        }

# Global MCP server instance
_mcp_server_instance = None

def get_mcp_server(db: Session = None) -> MCPServer:
    """Get or create MCP server instance"""
    global _mcp_server_instance

    if _mcp_server_instance is None and db:
        _mcp_server_instance = MCPServer(db)

    return _mcp_server_instance

async def initialize_mcp_server(db: Session):
    """Initialize MCP server"""
    global _mcp_server_instance
    _mcp_server_instance = MCPServer(db)
    logger.info("MCP Server initialized")
    return _mcp_server_instance
