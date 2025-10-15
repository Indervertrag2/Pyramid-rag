# MCP Migration Plan - Pyramid RAG Platform
## Datum: 2025-10-15

## Ziel
Migration aller LLM-bezogenen Funktionen von REST API zu MCP (Model Context Protocol) für bessere Standardisierung und einfache Integration mit Microsoft Dynamics MCP Server.

---

## IST-Zustand Analyse

### Aktuelle Architektur
```
Frontend (React)
    ↓
REST API Calls & MCP Client
    ├── /api/v1/mcp/stream (SSE for Chat)
    ├── /api/v1/documents/upload → Backend Processing
    └── /api/v1/mcp/search → MCP Search Endpoint

MCP Server (teilweise implementiert)
    ├── Tools für Suche und Chat definiert
    └── Wird für Chat und Suche verwendet, aber nicht für Dokumenten-Upload
```

### Probleme der aktuellen Lösung
1. **Teilweise Migration**: Nur Chat und Suche verwenden MCP, Dokumenten-Upload nicht.
2. **Keine vollständige Standardisierung**: Der Dokumenten-Upload-Prozess ist nicht in MCP integriert.
3. **Schwierige Erweiterung**: MS Dynamics Integration ist noch nicht möglich.
4. **Kein einheitliches Monitoring**: Verschiedene Log-Punkte.

---

## SOLL-Zustand: Unified MCP Architecture

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

## Phase 1: MCP Core Migration

### 1.1 Chat über MCP umstellen
- **Status**: Weitgehend abgeschlossen. Der Chat verwendet den `/api/v1/mcp/stream` Endpunkt für SSE.

### 1.2 Frontend MCP Client
- **Status**: Implementiert in `frontend/src/services/MCPClient.ts`.

### 1.3 MCP Tool Implementations erweitern
- **Status**: In `backend/app/api/endpoints/mcp.py` und dem `MCPGateway` Service implementiert.

---

## Phase 2: Document Processing über MCP

### 2.1 Document Upload als MCP Resource
- **Status**: Nicht implementiert. Der `uploadDocument` im `MCPClient` verwendet weiterhin den alten REST-Endpunkt.

### 2.2 MCP Resource Access
- **Status**: Nicht implementiert.

---

## Phase 3: MCP Inspector Integration

- **Status**: Nicht implementiert.

---

## Phase 4: MS Dynamics Integration

- **Status**: Nicht implementiert.

---

## Implementation Timeline

### Woche 1-2: Core MCP Migration
- [x] Chat über MCP umstellen
- [x] Frontend MCP Client implementieren
- [x] Basic MCP Tools (chat, search)
- [x] Testing mit Postman/curl

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

## Erfolgs-Kriterien

1. **Alle LLM Calls über MCP**: Kein direkter Ollama-Zugriff mehr
2. **Unified Interface**: Ein Endpoint für alle AI-Operationen
3. **MS Dynamics Ready**: Einfache Integration möglich
4. **MCP Inspector funktioniert**: Debugging aller Tools möglich
5. **Performance**: Keine Verschlechterung vs. aktuelle Lösung

---

## Risiken und Mitigationen

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

## Benötigte Ressourcen

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

## Next Steps

1. **Review mit Team**: Diesen Plan besprechen
2. **Proof of Concept**: Den Dokumenten-Upload auf MCP umstellen.
3. **Performance Test**: Overhead messen
4. **Decision**: Go/No-Go für Full Migration
5. **Sprint Planning**: User Stories erstellen

---

## Vorteile nach Migration

- **Einheitliche AI-Schnittstelle** - Ein Protocol für alles
- **Einfache Erweiterbarkeit** - Neue Tools easy hinzufügen
- **Besseres Debugging** - MCP Inspector für alles
- **MS Dynamics Ready** - Nahtlose Integration
- **Zukunftssicher** - MCP ist der Standard
- **Monitoring** - Zentrale Metriken

---

## Notizen

- MCP ist von Anthropic entwickelt, wird aber zum Industry Standard
- Microsoft adoptiert MCP für Dynamics 365 AI Features
- Inspector hat Sicherheitslücke (CVE-2025-49596) - nur localhost!
- Performance-Overhead ca. 10-20ms pro Call (akzeptabel)

---

*Erstellt: 2025-10-15*
*Status: IN PROGRESS - Zur Review*