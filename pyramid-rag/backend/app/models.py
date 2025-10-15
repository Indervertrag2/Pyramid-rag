from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Float, JSON, Table, Enum
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class Department(enum.Enum):
    MANAGEMENT = "Management"
    VERTRIEB = "Vertrieb"
    MARKETING = "Marketing"
    ENTWICKLUNG = "Entwicklung"
    PRODUKTION = "Produktion"
    QA = "Qualitätssicherung"
    SUPPORT = "Support"
    HR = "Personal"
    FINANZEN = "Finanzen"

class FileType(enum.Enum):
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    TEXT = "text"
    IMAGE = "image"
    CAD = "cad"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"

class ChatType(enum.Enum):
    NORMAL = "NORMAL"        # Permanent chat, access to company database
    TEMPORARY = "TEMPORARY"  # Auto-delete after 30 days, no company access

class FileScope(enum.Enum):
    GLOBAL = "GLOBAL"        # Available to all users (company database)
    CHAT = "CHAT"           # Only available in specific chat

class SearchMode(enum.Enum):
    HYBRID = "HYBRID"       # Combined vector + keyword search
    VECTOR = "VECTOR"       # Pure semantic search
    KEYWORD = "KEYWORD"     # Pure keyword search

class DocumentScope(enum.Enum):
    PERSONAL = "PERSONAL"   # Only accessible by owner
    DEPARTMENT = "DEPARTMENT"  # Accessible by department
    COMPANY = "COMPANY"     # Accessible by all users
    ADMIN = "ADMIN"         # Admin only

user_departments = Table(
    'user_departments',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), index=True),
    Column('department', Enum(Department))
)

document_permissions = Table(
    'document_permissions',
    Base.metadata,
    Column('document_id', UUID(as_uuid=True), ForeignKey('documents.id'), index=True),
    Column('department', Enum(Department))
)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    primary_department = Column(Enum(Department), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    # departments = relationship("Department", secondary=user_departments, backref="users")  # Disabled for now
    documents = relationship("Document", back_populates="uploaded_by_user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    searches = relationship("SearchHistory", back_populates="user")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String)
    file_hash = Column(String(64), unique=True, index=True)  # SHA-256 for deduplication

    title = Column(String)
    description = Column(Text)
    content = Column(Text)  # Extracted text content
    language = Column(String(10))  # Auto-detected language (de, en, etc.)
    meta_data = Column(JSON)

    department = Column(Enum(Department), nullable=False)
    # access_departments = relationship("Department", secondary=document_permissions)  # Disabled for now

    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    uploaded_by_user = relationship("User", back_populates="documents")

    processed = Column(Boolean, default=False)
    processing_error = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_length = Column(Integer)
    embedding = Column(Vector(768))  # 768-dimensional embeddings (paraphrase-multilingual-mpnet-base-v2) - UPDATED
    meta_data = Column(JSON)  # Changed from 'metadata' to avoid SQLAlchemy conflict
    token_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("DocumentEmbedding", back_populates="chunk", cascade="all, delete-orphan")

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('document_chunks.id'), nullable=False, index=True)
    embedding = Column(Vector(768))  # 768-dimensional embeddings (paraphrase-multilingual-mpnet-base-v2) - UPDATED
    model_name = Column(String, default="paraphrase-multilingual-mpnet-base-v2")
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="embeddings")
    chunk = relationship("DocumentChunk", back_populates="embeddings")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String)
    chat_type = Column(Enum(ChatType), default=ChatType.NORMAL, nullable=False)
    expires_at = Column(DateTime)  # For temporary chats (30 days from creation)
    folder_path = Column(String)  # Optional: folder organization (can be null)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    chat_files = relationship("ChatFile", back_populates="session", cascade="all, delete-orphan", lazy="dynamic")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id'), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
    sources = relationship("MessageSource", back_populates="message", cascade="all, delete-orphan")

class MessageSource(Base):
    __tablename__ = "message_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey('chat_messages.id'), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), index=True)
    chat_file_id = Column(UUID(as_uuid=True), ForeignKey('chat_files.id'), index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('document_chunks.id'), index=True)
    relevance_score = Column(Float)

    message = relationship("ChatMessage", back_populates="sources")

class ChatFile(Base):
    """Files uploaded directly to chat (not in global company database)"""
    __tablename__ = "chat_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id'), nullable=False, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String)
    file_hash = Column(String(64), index=True)  # SHA-256 for deduplication (not unique for chat files)

    title = Column(String)
    description = Column(Text)
    content = Column(Text)  # Extracted text content
    language = Column(String(10))  # Auto-detected language (de, en, etc.)
    meta_data = Column(JSON)

    scope = Column(Enum(FileScope), default=FileScope.CHAT, nullable=False)
    save_to_company = Column(Boolean, default=False)  # Toggle for saving to global database

    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("ChatSession", back_populates="chat_files")
    chunks = relationship("ChatFileChunk", back_populates="chat_file", cascade="all, delete-orphan")
    embeddings = relationship("ChatFileEmbedding", back_populates="chat_file", cascade="all, delete-orphan")

class ChatFileChunk(Base):
    """Text chunks from chat files"""
    __tablename__ = "chat_file_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_file_id = Column(UUID(as_uuid=True), ForeignKey('chat_files.id'), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON)
    token_count = Column(Integer)

    chat_file = relationship("ChatFile", back_populates="chunks")
    embeddings = relationship("ChatFileEmbedding", back_populates="chunk", cascade="all, delete-orphan")

class ChatFileEmbedding(Base):
    """Vector embeddings for chat file chunks"""
    __tablename__ = "chat_file_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_file_id = Column(UUID(as_uuid=True), ForeignKey('chat_files.id'), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('chat_file_chunks.id'), nullable=False, index=True)
    embedding = Column(Vector(768))  # 768-dimensional embeddings (paraphrase-multilingual-mpnet-base-v2) - UPDATED
    model_name = Column(String, default="paraphrase-multilingual-mpnet-base-v2")
    created_at = Column(DateTime, default=datetime.utcnow)

    chat_file = relationship("ChatFile", back_populates="embeddings")
    chunk = relationship("ChatFileChunk", back_populates="embeddings")

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    query = Column(Text, nullable=False)
    filters = Column(JSON)
    result_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="searches")

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)