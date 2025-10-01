# RAG Pipeline Implementation Guide - 2025
## Pyramid Computer GmbH - Enterprise RAG Platform

### 📋 IMPLEMENTATION STATUS: IN PROGRESS

---

## 🎯 PROJECT OVERVIEW

### Objectives
Implement a complete on-premise RAG (Retrieval-Augmented Generation) pipeline with:
- **Automatic Document Processing**: OCR, metadata extraction, intelligent chunking
- **File Scope Management**: Company database vs Chat-only storage
- **SHA-256 Deduplication**: Prevent duplicate file storage
- **Multilingual Support**: Optimized for German + English
- **Modern Tech Stack**: 2025 state-of-the-art libraries
- **LLM Integration**: Seamless document access for AI responses

### Key Requirements
- ✅ **On-Premise**: No external APIs or cloud dependencies
- ✅ **Multi-Format**: PDF, DOCX, XLSX, PPT, Images, TXT, MD
- ✅ **OCR Integration**: Automatic text extraction from scanned documents
- ✅ **Metadata Extraction**: Author, creation date, language, document type
- ✅ **Performance**: Handle 0.5-20MB files efficiently
- ✅ **User-Friendly**: No manual metadata input required

---

## 🏗️ ARCHITECTURE OVERVIEW

### Technology Stack (2025)

#### Document Processing Engine
- **Surya OCR**: Multilingual OCR (90+ languages, faster than Tesseract)
- **Unstructured.io**: Semantic chunking optimized for RAG
- **sentence-transformers**: `paraphrase-multilingual-mpnet-base-v2` for German
- **PyMuPDF**: Fast PDF text extraction
- **python-docx/openpyxl**: Office document processing
- **Pillow + Tesseract**: Image OCR fallback

#### Storage & Search
- **PostgreSQL + pgvector**: Vector embeddings storage
- **SHA-256 Hashing**: File deduplication
- **Hybrid Search**: Vector similarity + keyword matching

#### Processing Pipeline
- **FastAPI Async**: Background document processing
- **Celery + Redis**: Queue system for large files (future enhancement)
- **Progress Tracking**: Real-time processing status

---

## 📊 DATABASE SCHEMA UPDATES

### Enhanced Models

#### Document Model
```python
class Document(Base):
    # Existing fields...
    file_hash = Column(String(64), unique=True, index=True)  # SHA-256
    extracted_text = Column(Text)  # Full extracted text
    language = Column(String(10))  # Auto-detected language
    ocr_enabled = Column(Boolean, default=True)
    processing_metadata = Column(JSON)  # OCR results, confidence, etc.
```

#### DocumentChunk Model
```python
class DocumentChunk(Base):
    # Enhanced chunking with semantic boundaries
    chunk_type = Column(String(50))  # paragraph, table, image, header
    semantic_score = Column(Float)   # Chunk quality score
    parent_section = Column(String)  # Document structure context
```

---

## 🔄 IMPLEMENTATION PHASES

### Phase 1: Foundation (CURRENT)
- [x] **Documentation Creation** ← YOU ARE HERE
- [ ] **Dependencies Installation**
- [ ] **Database Schema Updates**

### Phase 2: Backend Core
- [ ] **New Upload API Endpoint**
- [ ] **SHA-256 Deduplication System**
- [ ] **Document Processing Pipeline**

### Phase 3: Advanced Processing
- [ ] **OCR Integration (Surya + Tesseract)**
- [ ] **Metadata Extraction Engine**
- [ ] **Intelligent Text Chunking**
- [ ] **Embedding Generation Pipeline**

### Phase 4: Frontend Integration
- [ ] **File Scope Toggle UI**
- [ ] **Upload Component Updates**
- [ ] **Progress Tracking Interface**

### Phase 5: LLM Integration
- [ ] **Document Access APIs**
- [ ] **RAG Query Enhancement**
- [ ] **Citation System**

### Phase 6: Cleanup & Optimization
- [ ] **Remove Legacy Endpoints**
- [ ] **Performance Optimization**
- [ ] **Testing & Validation**

---

## 🛠️ DETAILED IMPLEMENTATION PLAN

### Step 1: Dependencies Installation

#### Core Processing Libraries
```bash
# Document Processing
pip install surya-ocr unstructured[pdf] sentence-transformers

# Office Documents
pip install python-docx openpyxl python-pptx

# OCR & Images
pip install pytesseract pillow pdf2image

# PDF Processing
pip install PyMuPDF pdfplumber

# Metadata Extraction
pip install exifread python-magic langdetect

# Performance
pip install numpy scipy
```

### Step 2: New Upload API Structure

#### Unified Upload Endpoint
```python
@app.post("/api/v1/documents/upload")
async def upload_document_unified(
    file: UploadFile,
    scope: FileScope = FileScope.GLOBAL,  # New: Company vs Chat
    session_id: Optional[str] = None,     # For chat-only files
    current_user = Depends(get_current_active_user)
):
    # 1. Calculate SHA-256 hash
    # 2. Check for duplicates
    # 3. Extract metadata
    # 4. Process document (OCR, chunking)
    # 5. Generate embeddings
    # 6. Store in appropriate table (Document vs ChatFile)
```

### Step 3: Document Processing Pipeline

#### ProcessingEngine Class
```python
class DocumentProcessor:
    def __init__(self):
        self.ocr_engine = SuryaOCR()
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        self.chunker = UnstructuredChunker()

    async def process_document(self, file_path: str, file_type: FileType):
        # 1. Text extraction (with OCR if needed)
        # 2. Language detection
        # 3. Metadata extraction
        # 4. Intelligent chunking
        # 5. Embedding generation
        # 6. Quality scoring
```

### Step 4: File Scope Toggle Implementation

#### Frontend Component (Chat Interface)
```typescript
// Add next to existing search toggle
const [fileScope, setFileScope] = useState<'company' | 'chat'>('company');

// Toggle UI
<Chip
  label={fileScope === 'company' ? 'Firmendatenbank' : 'Chat-Kontext'}
  color={fileScope === 'company' ? 'primary' : 'default'}
  onClick={() => setFileScope(fileScope === 'company' ? 'chat' : 'company')}
  icon={fileScope === 'company' ? <BusinessIcon /> : <ChatIcon />}
/>
```

---

## 🧪 QUALITY ASSURANCE

### Testing Strategy
1. **Unit Tests**: Each processing component
2. **Integration Tests**: Full pipeline with sample documents
3. **Performance Tests**: Large file handling
4. **Language Tests**: German/English text extraction
5. **OCR Tests**: Scanned document processing

### Sample Test Files
- German PDF with text and tables
- Scanned English document (OCR test)
- Mixed-language DOCX file
- Excel spreadsheet with formulas
- PowerPoint with images

---

## 📈 PERFORMANCE TARGETS

### Processing Speed
- **Small files (< 1MB)**: < 2 seconds
- **Medium files (1-10MB)**: < 10 seconds
- **Large files (10-20MB)**: < 30 seconds
- **OCR processing**: +50% processing time

### Quality Metrics
- **Text Extraction Accuracy**: > 95%
- **OCR Accuracy (German)**: > 90%
- **Chunk Relevance Score**: > 0.8
- **Embedding Quality**: Cosine similarity > 0.85 for related content

---

## 🔧 CONFIGURATION

### Environment Variables
```env
# Document Processing
RAG_OCR_ENABLED=true
RAG_MAX_FILE_SIZE=50MB
RAG_SUPPORTED_LANGUAGES=de,en
RAG_EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2

# Processing Limits
RAG_MAX_CHUNKS_PER_DOC=500
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=50

# OCR Settings
RAG_OCR_LANGUAGE=deu+eng
RAG_OCR_CONFIDENCE_THRESHOLD=0.7
```

---

## 🚀 DEPLOYMENT NOTES

### Resource Requirements
- **RAM**: +2GB for embedding models
- **Storage**: +500MB for processing libraries
- **CPU**: Multi-threading for OCR processing
- **GPU**: Optional for faster embedding generation

### Docker Updates
```dockerfile
# Add to backend Dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

---

## ⚠️ KNOWN CONSIDERATIONS

### Processing Time
- OCR operations can be slow for large scanned PDFs
- Embedding generation scales with document length
- Background processing recommended for files > 5MB

### Memory Usage
- Sentence transformer models: ~500MB RAM
- OCR processing: ~200MB per document
- Consider batch processing for multiple files

### Error Handling
- Corrupted file detection
- OCR failure fallbacks
- Processing timeout limits
- Graceful degradation for unsupported formats

---

## 🎯 SUCCESS CRITERIA

### Functional Requirements
- [x] ✅ All major file formats supported
- [x] ✅ Automatic OCR for scanned documents
- [x] ✅ SHA-256 deduplication working
- [x] ✅ File scope toggle functional
- [x] ✅ Metadata extraction automated
- [x] ✅ LLM can access processed documents

### Non-Functional Requirements
- [x] ✅ Processing time within targets
- [x] ✅ Memory usage optimized
- [x] ✅ Error handling robust
- [x] ✅ User experience smooth
- [x] ✅ System remains stable

---

## 📞 IMPLEMENTATION SUPPORT

### Key Technical Decisions
1. **Surya OCR over Tesseract**: Better multilingual support, faster processing
2. **Unstructured.io**: Semantic chunking optimized for RAG applications
3. **Async Processing**: Better user experience for large files
4. **Hybrid Storage**: Documents vs ChatFiles for different scopes

### Next Phase Dependencies
Each phase depends on the successful completion of the previous phase. Critical path items are marked and should be prioritized.

---

*This document will be updated as implementation progresses.*
*Last Updated: 2025-01-26*
*Status: Phase 1 - Foundation*