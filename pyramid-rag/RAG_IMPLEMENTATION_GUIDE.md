# RAG Pipeline Implementation Guide - 2025
## Pyramid Computer GmbH - Enterprise RAG Platform

### IMPLEMENTATION STATUS: COMPLETED

---

## PROJECT OVERVIEW

### Objectives
Implement a complete on-premise RAG (Retrieval-Augmented Generation) pipeline with:
- Automatic Document Processing: OCR, metadata extraction, intelligent chunking
- File Scope Management: Company database vs Chat-only storage
- SHA-256 Deduplication: Prevent duplicate file storage
- Multilingual Support: Optimized for German + English
- Modern Tech Stack: 2025 state-of-the-art libraries
- LLM Integration: Seamless document access for AI responses

### Key Requirements
- On-Premise: No external APIs or cloud dependencies
- Multi-Format: PDF, DOCX, XLSX, PPT, Images, TXT, MD
- OCR Integration: Automatic text extraction from scanned documents
- Metadata Extraction: Author, creation date, language, document type
- Performance: Handle 0.5-20MB files efficiently
- User-Friendly: No manual metadata input required

---

## ARCHITECTURE OVERVIEW

### Technology Stack (2025)

#### Document Processing Engine
- **OCR**: Surya OCR and Tesseract
- **Text/Data Extraction**: PyMuPDF, python-docx, openpyxl, python-pptx
- **Embedding Model**: `paraphrase-multilingual-mpnet-base-v2`
- **Chunking**: Custom logic in `document_processor.py`

#### Storage & Search
- **Vector Store**: PostgreSQL + pgvector
- **Deduplication**: SHA-256 Hashing
- **Search**: Hybrid Search (Vector + Keyword)

#### Processing Pipeline
- **API**: FastAPI
- **Async Tasks**: Celery + Redis

---

## DATABASE SCHEMA

### Models
- **Document**: Stores metadata for each document.
- **DocumentChunk**: Stores text chunks of documents.
- **DocumentEmbedding**: Stores vector embeddings for each chunk.
- **ChatFile**: Stores files uploaded in a chat context.

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation
- [x] **Dependencies Installation**
- [x] **Database Schema Updates**

### Phase 2: Backend Core
- [x] **New Upload API Endpoint**
- [x] **SHA-256 Deduplication System**
- [x] **Document Processing Pipeline**

### Phase 3: Advanced Processing
- [x] **OCR Integration (Surya + Tesseract)**
- [x] **Metadata Extraction Engine**
- [x] **Intelligent Text Chunking**
- [x] **Embedding Generation Pipeline**

### Phase 4: Frontend Integration
- [x] **File Scope Toggle UI**
- [x] **Upload Component Updates**
- [x] **Progress Tracking Interface**

### Phase 5: LLM Integration
- [x] **Document Access APIs**
- [x] **RAG Query Enhancement**
- [x] **Citation System**

### Phase 6: Cleanup & Optimization
- [x] **Remove Legacy Endpoints**
- [x] **Performance Optimization**
- [x] **Testing & Validation**

---

## DETAILED IMPLEMENTATION

### Dependencies

The following libraries were installed via `requirements.txt`:
- `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `asyncpg`, `psycopg2-binary`, `pgvector`
- `sentence-transformers`, `torch`, `transformers`
- `pypdf`, `PyMuPDF`, `python-docx`, `openpyxl`, `python-pptx`
- `surya-ocr`, `tesseract`
- `celery`, `redis`

### Upload API

The `upload_document_unified` endpoint in `backend/app/api/endpoints/documents.py` handles all document uploads. It uses the `DocumentProcessor` service to process the files.

### Document Processing

The `DocumentProcessor` class in `backend/app/services/document_processor.py` implements the entire RAG pipeline:
1.  **File Hashing:** Calculates the SHA-256 hash for deduplication.
2.  **File Type Detection:** Detects the file type based on the extension and MIME type.
3.  **Text Extraction:** Extracts text from various file formats using libraries like `PyMuPDF` and `python-docx`.
4.  **OCR:** Uses `surya-ocr` for OCR.
5.  **Language Detection:** Detects the language of the extracted text using `langdetect`.
6.  **Metadata Extraction:** Extracts metadata from the file and content.
7.  **Chunking:** Splits the text into smaller chunks.
8.  **Embedding Generation:** Generates embeddings for each chunk using the `sentence-transformers` library and the `paraphrase-multilingual-mpnet-base-v2` model.

### Frontend

The `ChatInterface.tsx` component provides the UI for uploading files and interacting with the RAG system. It includes toggles for controlling the search scope and document indexing.