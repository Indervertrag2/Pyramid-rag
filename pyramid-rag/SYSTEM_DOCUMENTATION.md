# Pyramid RAG System - Hauptdokumentation
**Letzte Aktualisierung: 2025-09-26 09:15 UTC**

## System Übersicht

Pyramid RAG ist eine vollständig on-premise Retrieval-Augmented Generation (RAG) Platform für Pyramid Computer GmbH. Das System ermöglicht intelligente Dokumentensuche und KI-gestützte Antworten basierend auf Unternehmensdokumenten.

## 🚀 RAG Pipeline Status: VOLLSTÄNDIG IMPLEMENTIERT

### Neue Features (2025-09-26 09:15)
- ✅ **Komplette RAG Pipeline** mit Embeddings und Vector Search
- ✅ **Automatische Metadaten-Erkennung** (keine Nutzereingabe nötig)
- ✅ **Search Toggle** (ehemals RAG Ein/Aus) - umbenannt
- ✅ **Ingest Toggle** - Dokumente dauerhaft indexieren oder nur temporär
- ✅ **Drag & Drop im Chat** - direkte Integration
- ✅ **15 Minuten Timeout** für große Dateien
- ✅ **Deutsche Sprache optimiert** mit T-Systems RoBERTa Model

## Aktuelle Architektur

### Backend (Port 18000)
- **Framework**: FastAPI (Python)
- **Datenbank**: PostgreSQL mit pgvector Extension
- **LLM**: Ollama mit qwen2.5:7b (lokal, GPU-beschleunigt)
- **Embedding Model**: T-Systems-onsite/german-roberta-sentence-transformer-v2
- **Container**: Docker mit docker-compose

### Frontend (Port 3002)
- **Framework**: React mit TypeScript
- **UI Library**: Material-UI
- **Style**: ChatGPT/Claude-ähnliche Oberfläche
- **Features**:
  - Dark Mode
  - Session Management
  - Drag & Drop Upload
  - Search/Ingest Toggles (NEU!)

## RAG Pipeline Komponenten

### Document Processing
1. **Content Extraction**: PDF, DOCX, XLSX, TXT und mehr
2. **Metadata Detection**: Automatische Titel, Department, Keywords
3. **Chunking**: Intelligente Text-Segmentierung (512 tokens, 100 overlap)
4. **Embeddings**: German RoBERTa (768 dimensions)
5. **Vector Storage**: PostgreSQL + pgvector mit HNSW Index

### API Endpoints
- `POST /api/v2/chat/{session_id}/files` - Upload mit auto-metadata
- `POST /api/v2/chat/{session_id}/search` - Vector search
- `POST /api/v1/chat` - Chat mit RAG-Integration

## Authentifizierung
- **Admin Account**: admin@pyramid-computer.de / admin123
- **Token**: JWT mit 6 Monaten Gültigkeit
- **Departments**: MANAGEMENT, IT, SUPPORT

## Docker Container Status
- `pyramid-backend`: FastAPI Server mit RAG Pipeline
- `pyramid-frontend`: React Application mit Toggles
- `pyramid-postgres`: PostgreSQL + pgvector
- `pyramid-redis`: Cache/Queue
- `pyramid-ollama`: LLM Service

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
- sentence-transformers==2.7.0
- pypdf2==3.0.1
- python-docx==1.1.0
- openpyxl==3.1.2
- langdetect==1.0.9
- pgvector==0.2.3

## Nächste Schritte
- Monitoring Dashboard
- SharePoint Integration (geplant)
- ERP System Integration (geplant)

---
*Diese Dokumentation wird automatisch aktualisiert bei System-Änderungen.*