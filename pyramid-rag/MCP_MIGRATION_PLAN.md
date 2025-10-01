# 🚀 MCP Migration Plan - Pyramid RAG Platform
## Datum: 2025-09-30

## 🎯 Ziel
Migration aller LLM-bezogenen Funktionen von REST API zu MCP (Model Context Protocol) für bessere Standardisierung und einfache Integration mit Microsoft Dynamics MCP Server.

---

## 📊 IST-Zustand Analyse

### Aktuelle Architektur
```
Frontend (React)
    ↓
REST API Calls
    ├── /api/v1/chat → Direkt zu Ollama
    ├── /api/v1/documents/upload → Backend Processing
    └── /api/v1/search → Direkte DB-Queries

MCP Server (vorhanden aber ungenutzt)
    ├── Tools definiert
    └── Nicht vom Frontend verwendet
```

### Probleme der aktuellen Lösung
1. **Fragmentierung**: LLM-Calls über verschiedene Wege
2. **Keine Standardisierung**: Jeder Endpoint eigene Implementierung
3. **Schwierige Erweiterung**: MS Dynamics Integration kompliziert
4. **Kein einheitliches Monitoring**: Verschiedene Log-Punkte

---

## 🏗️ SOLL-Zustand: Unified MCP Architecture

### Ziel-Architektur
```
Frontend (React)
    ↓
MCP Client Interface
    ↓
MCP Gateway (/api/v1/mcp/*)
    ↓
MCP Router
    ├── Pyramid MCP Server (intern)
    │   ├── RAG Tools
    │   ├── Document Tools
    │   └── Ollama Integration
    └── MS Dynamics MCP Server (extern)
        ├── CRM Tools
        ├── ERP Tools
        └── Business Logic
```

---

## 📋 Phase 1: MCP Core Migration (Woche 1-2)

### 1.1 Chat über MCP umstellen
```python
# ALT: Direkter Ollama Call in main.py
@app.post("/api/v1/chat")
async def chat(request):
    # Direkt zu Ollama
    response = ollama_client.generate(...)

# NEU: MCP Tool Call
@app.post("/api/v1/chat")
async def chat(request):
    # Über MCP Server
    mcp_response = await mcp_server.process_message({
        "tool": "chat",
        "parameters": {
            "message": request.content,
            "rag_enabled": request.rag_enabled,
            "context": request.context
        }
    })
```

### 1.2 Frontend MCP Client
```typescript
// NEU: MCP Client Service
class MCPClient {
    async sendMessage(content: string, tools?: string[]): Promise<MCPResponse> {
        return fetch('/api/v1/mcp/message', {
            method: 'POST',
            body: JSON.stringify({
                messages: [{role: 'user', content}],
                tools: tools || ['chat', 'search', 'rag']
            })
        })
    }
}

// In ChatInterface.tsx
const sendMessage = async () => {
    const response = await mcpClient.sendMessage(
        inputMessage,
        searchEnabled ? ['chat', 'hybrid_search'] : ['chat']
    );
}
```

### 1.3 MCP Tool Implementations erweitern
```python
# mcp_server.py
class MCPServer:
    async def tool_chat(self, params: Dict):
        """Enhanced chat with RAG integration"""
        if params.get('rag_enabled'):
            # 1. Search for context
            context = await self.tool_hybrid_search({
                'query': params['message'],
                'department': params.get('department'),
                'limit': 5
            })

            # 2. Build prompt with context
            prompt = self._build_rag_prompt(
                params['message'],
                context['results']
            )
        else:
            prompt = params['message']

        # 3. Call Ollama
        response = await self.ollama_client.generate(prompt)

        # 4. Add citations if RAG
        if params.get('rag_enabled'):
            response['citations'] = context['citations']

        return response
```

---

## 📋 Phase 2: Document Processing über MCP (Woche 2-3)

### 2.1 Document Upload als MCP Resource
```python
# MCP Resource Pattern
class DocumentResource:
    async def create(self, file_data: bytes, metadata: Dict):
        """Upload and process document via MCP"""
        # 1. Save file
        doc_id = await self.save_document(file_data)

        # 2. Extract text
        text = await self.extract_text(doc_id)

        # 3. Generate chunks
        chunks = await self.create_chunks(text)

        # 4. Create embeddings
        embeddings = await self.generate_embeddings(chunks)

        # 5. Return resource URI
        return f"rag://doc/{doc_id}"
```

### 2.2 MCP Resource Access
```python
# Resource URI Pattern: rag://doc/{id}/chunk/{chunk_id}
async def get_resource(uri: str):
    if uri.startswith("rag://doc/"):
        parts = uri.split("/")
        doc_id = parts[3]

        if len(parts) > 4 and parts[4] == "chunk":
            chunk_id = parts[5]
            return await get_chunk(doc_id, chunk_id)
        else:
            return await get_document(doc_id)
```

---

## 📋 Phase 3: MCP Inspector Integration (Woche 3)

### 3.1 Installation und Setup
```bash
# Backend Dockerfile erweitern
RUN npm install -g @modelcontextprotocol/inspector

# Docker-compose.yml
services:
  mcp-inspector:
    image: node:20-alpine
    command: npx @modelcontextprotocol/inspector python /app/mcp_server.py
    ports:
      - "5173:5173"  # Inspector UI
    volumes:
      - ./backend:/app
    environment:
      - MCP_SERVER_PATH=/app/mcp_server.py
```

### 3.2 Frontend Integration
```typescript
// Add MCP Inspector Button to Admin Panel
const MCPInspectorButton = () => {
    const openInspector = () => {
        window.open('http://localhost:5173', '_blank');
    };

    return (
        <Button onClick={openInspector}>
            Open MCP Inspector 🔍
        </Button>
    );
};
```

### 3.3 Custom Inspector Views
```javascript
// mcp-inspector-config.js
module.exports = {
    customViews: [
        {
            name: "RAG Pipeline",
            tools: ["hybrid_search", "vector_search", "keyword_search"]
        },
        {
            name: "Document Processing",
            tools: ["document_upload", "extract_text", "generate_embeddings"]
        },
        {
            name: "MS Dynamics",
            tools: ["dynamics_crm_*", "dynamics_erp_*"]
        }
    ]
};
```

---

## 📋 Phase 4: MS Dynamics Integration (Woche 4-5)

### 4.1 MCP Server Registry
```python
# mcp_registry.py
class MCPServerRegistry:
    servers = {
        'internal': PyramidMCPServer(),
        'dynamics': None  # Will be registered
    }

    async def register_server(self, name: str, config: Dict):
        """Register external MCP server"""
        if name == 'dynamics':
            self.servers['dynamics'] = DynamicsMCPClient(
                endpoint=config['endpoint'],
                auth=config['auth']
            )

    async def route_tool_call(self, tool: str, params: Dict):
        """Route to appropriate server"""
        if tool.startswith('dynamics_'):
            return await self.servers['dynamics'].call_tool(tool, params)
        else:
            return await self.servers['internal'].call_tool(tool, params)
```

### 4.2 Dynamics MCP Client
```python
# dynamics_mcp_client.py
class DynamicsMCPClient:
    async def call_tool(self, tool: str, params: Dict):
        """Call MS Dynamics MCP Server"""
        response = await self.session.post(
            f"{self.endpoint}/mcp/tools/{tool}",
            json=params,
            headers=self.auth_headers
        )
        return response.json()

    # Available Dynamics Tools
    tools = {
        'dynamics_crm_get_customer': {...},
        'dynamics_crm_create_ticket': {...},
        'dynamics_erp_get_inventory': {...},
        'dynamics_erp_create_order': {...}
    }
```

### 4.3 Unified Tool Discovery
```python
async def get_all_tools():
    """Get tools from all MCP servers"""
    tools = {}

    # Internal tools
    tools.update(pyramid_mcp.get_tools())

    # Dynamics tools
    if dynamics_mcp:
        tools.update(await dynamics_mcp.get_tools())

    return tools
```

---

## 🔧 Implementation Timeline

### Woche 1-2: Core MCP Migration
- [ ] Chat über MCP umstellen
- [ ] Frontend MCP Client implementieren
- [ ] Basic MCP Tools (chat, search)
- [ ] Testing mit Postman/curl

### Woche 2-3: Document Processing
- [ ] Document Upload als MCP Resource
- [ ] Resource URI Pattern implementieren
- [ ] Chunking und Embedding über MCP
- [ ] Frontend Upload über MCP

### Woche 3: MCP Inspector
- [ ] Inspector Setup mit Docker
- [ ] Custom Views konfigurieren
- [ ] Admin Panel Integration
- [ ] Debugging Workflows erstellen

### Woche 4-5: MS Dynamics
- [ ] MCP Server Registry
- [ ] Dynamics Client implementieren
- [ ] Tool Routing Logic
- [ ] End-to-End Testing

### Woche 5-6: Testing & Optimization
- [ ] Performance Testing
- [ ] Error Handling
- [ ] Monitoring Setup
- [ ] Documentation

---

## 🎯 Erfolgs-Kriterien

1. **Alle LLM Calls über MCP**: Kein direkter Ollama-Zugriff mehr
2. **Unified Interface**: Ein Endpoint für alle AI-Operationen
3. **MS Dynamics Ready**: Einfache Integration möglich
4. **MCP Inspector funktioniert**: Debugging aller Tools möglich
5. **Performance**: Keine Verschlechterung vs. aktuelle Lösung

---

## 🚨 Risiken und Mitigationen

### Risiko 1: Performance-Overhead
**Mitigation**:
- Caching in MCP Layer
- Connection Pooling
- Async/Await optimal nutzen

### Risiko 2: Komplexität steigt
**Mitigation**:
- Schrittweise Migration
- Ausführliche Tests
- Rollback-Plan

### Risiko 3: MS Dynamics Kompatibilität
**Mitigation**:
- Früh Dynamics MCP Docs studieren
- Mock Server für Tests
- Flexible Adapter-Layer

---

## 📚 Benötigte Ressourcen

### Tools & Libraries
- `@modelcontextprotocol/sdk` - MCP SDK
- `@modelcontextprotocol/inspector` - Debug Tool
- `mcp-server-toolkit` - Python MCP utilities

### Documentation
- [MCP Specification](https://modelcontextprotocol.io/docs)
- [MS Dynamics MCP Docs](https://docs.microsoft.com/dynamics-mcp)
- [Anthropic MCP Best Practices](https://anthropic.com/mcp)

### Team Skills
- MCP Protocol Knowledge
- Async Python Programming
- TypeScript/React für Frontend
- MS Dynamics Basics

---

## 🎬 Next Steps

1. **Review mit Team**: Diesen Plan besprechen
2. **Proof of Concept**: Einen Tool (z.B. chat) migrieren
3. **Performance Test**: Overhead messen
4. **Decision**: Go/No-Go für Full Migration
5. **Sprint Planning**: User Stories erstellen

---

## 💡 Vorteile nach Migration

✅ **Einheitliche AI-Schnittstelle** - Ein Protocol für alles
✅ **Einfache Erweiterbarkeit** - Neue Tools easy hinzufügen
✅ **Besseres Debugging** - MCP Inspector für alles
✅ **MS Dynamics Ready** - Nahtlose Integration
✅ **Zukunftssicher** - MCP ist der Standard
✅ **Monitoring** - Zentrale Metriken

---

## 📝 Notizen

- MCP ist von Anthropic entwickelt, wird aber zum Industry Standard
- Microsoft adoptiert MCP für Dynamics 365 AI Features
- Inspector hat Sicherheitslücke (CVE-2025-49596) - nur localhost!
- Performance-Overhead ca. 10-20ms pro Call (akzeptabel)

---

*Erstellt: 2025-09-30*
*Status: DRAFT - Zur Review*