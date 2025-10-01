from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class DepartmentEnum(str, Enum):
    MANAGEMENT = "Management"
    VERTRIEB = "Vertrieb"
    MARKETING = "Marketing"
    ENTWICKLUNG = "Entwicklung"
    PRODUKTION = "Produktion"
    QA = "Qualitätssicherung"
    SUPPORT = "Support"
    HR = "Personal"
    FINANZEN = "Finanzen"

class FileTypeEnum(str, Enum):
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

class ChatTypeEnum(str, Enum):
    NORMAL = "NORMAL"
    TEMPORARY = "TEMPORARY"

class FileScopeEnum(str, Enum):
    GLOBAL = "GLOBAL"
    CHAT = "CHAT"

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    primary_department: DepartmentEnum

class UserCreate(UserBase):
    password: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    primary_department: Optional[DepartmentEnum] = None
    is_active: Optional[bool] = None

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    department: str
    is_superuser: bool = False

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    primary_department: Optional[str] = None

class UserResponse(UserBase):
    id: UUID4
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

# Auth Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Document Schemas
class DocumentBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: DepartmentEnum
    access_departments: List[DepartmentEnum] = []

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    access_departments: Optional[List[DepartmentEnum]] = None

class DocumentResponse(DocumentBase):
    id: UUID4
    filename: str
    original_filename: str
    file_type: FileTypeEnum
    file_size: int
    mime_type: Optional[str] = None
    content: Optional[str] = None
    meta_data: Optional[Dict] = None
    processed: bool
    uploaded_by: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int

# Chat Schemas
class UploadedDocument(BaseModel):
    id: str
    title: str
    content: Optional[str] = None

class ChatMessageRequest(BaseModel):
    content: str
    session_id: Optional[UUID4] = None
    rag_enabled: bool = True
    uploaded_documents: List[UploadedDocument] = []

class ChatMessageResponse(BaseModel):
    id: UUID4
    role: str
    content: str
    created_at: datetime
    sources: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True

# New Chat System Schemas
class ChatSessionCreateRequest(BaseModel):
    title: Optional[str] = None
    chat_type: ChatTypeEnum = ChatTypeEnum.NORMAL
    folder_path: Optional[str] = None

class ChatSessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    folder_path: Optional[str] = None

class ChatFileResponse(BaseModel):
    id: UUID4
    filename: str
    original_filename: str
    file_type: FileTypeEnum
    file_size: int
    title: Optional[str] = None
    description: Optional[str] = None
    scope: FileScopeEnum
    save_to_company: bool
    processed: bool
    processing_error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: UUID4
    title: Optional[str] = None
    chat_type: ChatTypeEnum
    expires_at: Optional[datetime] = None
    folder_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []
    chat_files: List[ChatFileResponse] = []

    class Config:
        from_attributes = True

# Search Schemas
class SearchRequest(BaseModel):
    query: str
    departments: Optional[List[DepartmentEnum]] = None
    file_types: Optional[List[FileTypeEnum]] = None
    limit: int = Field(default=20, le=100)
    offset: int = Field(default=0, ge=0)

class SearchResultItem(BaseModel):
    document_id: UUID4
    filename: str
    title: Optional[str] = None
    excerpt: str
    relevance_score: float
    department: DepartmentEnum
    file_type: FileTypeEnum

class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int
    query: str
    took_ms: int

# System Schemas
class SystemStatsResponse(BaseModel):
    total_documents: int
    total_users: int
    documents_this_week: int
    active_chats: int
    storage_used_gb: float
    storage_total_gb: float

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]