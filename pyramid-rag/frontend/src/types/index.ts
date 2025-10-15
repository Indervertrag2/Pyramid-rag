export type MessageRole = 'user' | 'assistant' | 'system';
export type DocumentScope = 'GLOBAL' | 'CHAT';
export type DocumentSource = 'chat' | 'knowledge_base';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  primary_department: string;
  is_superuser: boolean;
  roles?: string[];
}

export interface ConversationDocument {
  id: string;
  documentId?: string;
  title: string;
  scope: DocumentScope;
  source: DocumentSource;
  contentPreview?: string;
  mimeType?: string;
  chunkId?: string;
  score?: number;
  alias?: string;
}

export interface UploadedDocumentInfo {
  id: string;
  documentId: string;
  title: string;
  filename: string;
  originalFilename: string;
  scope: DocumentScope;
  fileType?: string;
  mimeType?: string;
  content?: string;
  contentPreview?: string;
  contentLength?: number;
  metadata?: Record<string, any>;
  department?: string;
  accessDepartments?: string[];
  uploadedBy?: string;
  createdAt?: string;
  updatedAt?: string;
  source?: DocumentSource;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  attachments?: File[];
  citations?: ConversationDocument[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  folderId?: string;
  uploadedDocuments?: UploadedDocumentInfo[];
  isTemporary?: boolean;
}

export interface ChatFolder {
  id: string;
  name: string;
  color?: string;
  expanded: boolean;
}

export interface DocumentPreviewState {
  id: string;
  title: string;
  scope: DocumentScope;
  source: DocumentSource;
  content?: string;
  contentPreview?: string;
  mimeType?: string;
  createdAt?: string;
  updatedAt?: string;
  chunkId?: string;
}

export type UploadOutcome = {
  documents: UploadedDocumentInfo[];
  notices: string[];
};

export interface UploadedDocumentPayload {
  id: string;
  title: string;
  scope: DocumentScope;
  content?: string;
  content_length?: number;
  mime_type?: string;
  meta_data?: Record<string, any>;
}
