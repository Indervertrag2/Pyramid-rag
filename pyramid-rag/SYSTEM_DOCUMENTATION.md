# Pyramid RAG System - Hauptdokumentation
**Letzte Aktualisierung: 2025-10-15 10:00 UTC**

## System Übersicht

Pyramid RAG ist eine vollständig on-premise Retrieval-Augmented Generation (RAG) Platform für Pyramid Computer GmbH. Das System ermöglicht intelligente Dokumentensuche und KI-gestützte Antworten basierend auf Unternehmensdokumenten.

## RAG Pipeline Status: VOLLSTÄNDIG IMPLEMENTIERT

## Aktuelle Architektur

### Backend (Port 18000)
- **Framework**: FastAPI (Python)
- **Datenbank**: PostgreSQL mit pgvector Extension
- **LLM**: Ollama mit Qwen3 32B (lokal, GPU-beschleunigt)
- **Embedding Model**: paraphrase-multilingual-mpnet-base-v2
- **Container**: Docker mit docker-compose

### Frontend (Port 3002)
- **Framework**: React mit TypeScript
- **UI Library**: Material-UI
- **Style**: ChatGPT/Claude-ähnliche Oberfläche
- **Features**:
  - Dark Mode
  - Session Management
  - Drag & Drop Upload
  - Search/Ingest Toggles

## RAG Pipeline Komponenten

### Document Processing
1. **Content Extraction**: PDF, DOCX, XLSX, TXT und mehr
2. **Metadata Detection**: Automatische Titel, Department, Keywords
3. **Chunking**: Intelligente Text-Segmentierung (512 tokens, 100 overlap)
4. **Embeddings**: paraphrase-multilingual-mpnet-base-v2 (768 dimensions)
5. **Vector Storage**: PostgreSQL + pgvector mit HNSW Index

### API Endpoints
- `POST /api/v1/documents/upload` - Dokumente hochladen
- `POST /api/v1/chat/sessions/{session_id}/messages` - Chat-Nachricht senden
- `POST /api/v1/mcp/search` - Hybride Suche
- `POST /api/v1/mcp/stream` - Streaming Chat

## Authentifizierung
- **Admin Account**: admin@pyramid-computer.de / PyramidAdmin2024!
- **Token**: JWT mit 6 Monaten Gültigkeit
- **Departments**: MANAGEMENT, IT, SUPPORT, etc.

## Docker Container Status
- `pyramid-backend`: FastAPI Server mit RAG Pipeline
- `pyramid-frontend`: React Application mit Toggles
- `pyramid-postgres`: PostgreSQL + pgvector
- `pyramid-redis`: Cache/Queue
- `pyramid-ollama`: LLM Service
- `pyramid-celery-worker`: Asynchrone Aufgabenverarbeitung
- `pyramid-celery-beat`: Periodische Aufgaben
- `pyramid-flower`: Celery Monitoring
- `pyramid-nginx`: Reverse Proxy
- `pyramid-prometheus`: Monitoring
- `pyramid-grafana`: Visualisierung

## Verwendung

### Upload mit RAG
1. Datei in Chat ziehen
2. **Ingest Toggle** aktivieren für dauerhafte Indexierung
3. Upload startet automatisch
4. Metadaten werden automatisch erkannt

### Suche
1. **Search Toggle** aktiviert = Dokumentensuche
2. **Search Toggle** deaktiviert = Nur LLM ohne Dokumente

## Performance
- Upload: 1-5 Dokumente/Sekunde
- Vector Search: <100ms
- Embedding Generation: GPU-beschleunigt
- Chunk Processing: Parallel mit 4 Workers

## Installierte Python Packages
- fastapi
- uvicorn
- sqlalchemy
- alembic
- asyncpg
- psycopg2-binary
- pgvector
- python-jose[cryptography]
- passlib[bcrypt]
- sentence-transformers
- torch
- transformers
- langchain
- celery
- redis
- flower
- prometheus-client
- prometheus-fastapi-instrumentator

## Nächste Schritte
- Vollständige Migration zu MCP
- SharePoint Integration
- ERP System Integration

---
*Diese Dokumentation wird automatisch aktualisiert bei System-Änderungen.*